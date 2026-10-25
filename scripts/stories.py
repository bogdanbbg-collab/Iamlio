#!/usr/bin/env python3
"""Instrumente pentru poveștile Iamlio.

Comenzi:
  new "Titlu"   creează o poveste nouă din șablon (public/stories/<id>/)
  template  regenerează sablon/story.json din scripts/canon.py
  optimize  transformă imaginile .png/.jpg în .webp (max 1536×1024) și actualizează story.json
  validate  verifică toate poveștile după REGULI_POVESTI.md
  audio     generează vocea feminină și masculină (mp3, edge-tts + regie de voce) pentru povești și replicile lui Lio
  verify-audio  verifică faptul că toate fișierele audio există pentru ambele voci
  index     regenerează public/stories/index.json
  all       optimize + validate + audio + verify-audio + index
"""

import asyncio
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import canon
import voce

ROOT = Path(__file__).resolve().parent.parent
STORIES_DIR = ROOT / "public" / "stories"
INDEX_FILE = STORIES_DIR / "index.json"
LIO_LINES_FILE = ROOT / "public" / "assets" / "lio-replici.json"
LIO_AUDIO_DIR = ROOT / "public" / "assets" / "audio"

# Fiecare poveste primește ambele voci; cititorul alege una.
VOICES = voce.VOICES
TEMPLATE_FILE = ROOT / "sablon" / "story.json"
LIO_PROFILE = {"name": "Lio", "voice": canon.LIO_VOICE}  # Lio e un pui: voce puțin mai înaltă
RASTER_EXTENSIONS = {".webp", ".jpg", ".jpeg", ".png"}
IMAGE_PATH = re.compile(r"^images/[a-z0-9][a-z0-9-]*\.(?:webp|png|jpe?g)$")
MAX_IMAGE_SIZE = (1536, 1024)
WEBP_QUALITIES = (82, 72, 62)  # se încearcă pe rând până imaginea scade sub MAX_IMAGE_KB
MIN_PAGES, MAX_PAGES = 6, 24
MIN_WORDS, MAX_WORDS = 20, 70
MIN_MINUTES, MAX_MINUTES = 2, 10
WORDS_PER_MINUTE = 130  # ritmul vocii edge-tts cu regia de voce
SECONDS_PER_PAGE_TURN = 2.5
MP3_BYTES_PER_SECOND = 48000 / 8  # edge-tts: mp3 mono 48 kbit/s
MAX_IMAGE_KB = 450
MIN_PROMPT_CHARS = 60
MIN_DESCRIPTION_CHARS = 40
AGES = {"3-5", "5-7", "3-7"}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CEDILLA = re.compile("[şţŞŢ]")
LONG_SENTENCE_WORDS = 25
SUMMARY_WORDS = (8, 60)
# Cuvinte care de obicei nu au ce căuta într-o poveste pentru 3–7 ani (avertisment, nu eroare).
SENSITIVE_WORDS = ["moarte", "mort", "moartă", "murit", "sânge", "ucide", "omoară", "omorât", "armă", "pistol",
                   "cuțit", "bătaie", "prost", "proastă", "idiot", "urât", "drac", "iad", "înjur"]
REQUIRED_FIELDS = ["id", "title", "summary", "moral", "learning", "created", "illustrationStyle", "characters",
                   "cover", "pages", "review"]


def load_stories():
    stories = []
    for story_file in sorted(STORIES_DIR.glob("*/story.json")):
        try:
            data = json.loads(story_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            data = {"_error": f"JSON invalid: {exc}"}
        stories.append((story_file.parent, data))
    return stories


def word_count(text):
    return len(re.findall(r"[\wăâîșțĂÂÎȘȚ]+", text))


def plain(text):
    """Text fără diacritice, cu litere mici (pentru comparații)."""
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()


def estimated_minutes(pages):
    words = sum(word_count(p.get("text") or "") for p in pages)
    return words / WORDS_PER_MINUTE + len(pages) * SECONDS_PER_PAGE_TURN / 60


def check_image(folder, rel_path, label, errors, warnings):
    if not rel_path:
        errors.append(f"{label}: lipsește câmpul image")
        return
    if not IMAGE_PATH.match(rel_path):
        errors.append(f"{label}: calea imaginii trebuie să fie de forma images/nume.webp|png|jpg (primit: {rel_path})")
        return
    path = folder / rel_path
    if not path.resolve().is_relative_to(folder.resolve()):
        errors.append(f"{label}: imaginea trebuie să fie în folderul poveștii")
        return
    if not path.is_file():
        errors.append(f"{label}: imaginea {rel_path} nu există")
    elif path.stat().st_size > MAX_IMAGE_KB * 1024:
        warnings.append(f"{label}: {rel_path} are {path.stat().st_size // 1024} KB (recomandat sub {MAX_IMAGE_KB} KB)")


def validate_voice_profile(name, profile):
    if profile is None:
        return []
    errors = []
    if not isinstance(profile, dict):
        return [f"personajul {name}: voice trebuie să fie un obiect"]
    if "type" in profile and profile["type"] not in VOICES:
        errors.append(f"personajul {name}: voice.type trebuie să fie {' sau '.join(VOICES)}")
    for key, bounds in (("pitch", voce.CHARACTER_PITCH), ("rate", voce.CHARACTER_RATE)):
        value = profile.get(key, 0)
        if not isinstance(value, int) or not bounds[0] <= value <= bounds[1]:
            errors.append(f"personajul {name}: voice.{key} trebuie să fie un număr întreg între {bounds[0]} și {bounds[1]}")
    return errors


def validate_narration(page, character_names):
    """Regia de voce (opțională) trebuie să conțină exact cuvintele textului afișat."""
    narration = page.get("narration")
    if narration is None:
        return []
    if not isinstance(narration, list) or not narration:
        return ["narration trebuie să fie o listă de replici"]
    errors = []
    for item in narration:
        if not isinstance(item, dict) or not str(item.get("text") or "").strip():
            errors.append("narration: fiecare replică trebuie să aibă text")
            continue
        if item.get("mood", voce.NARRATOR_MOOD) not in voce.MOODS:
            errors.append(f"narration: ton necunoscut „{item.get('mood')}” (permise: {', '.join(voce.MOODS)})")
        if item.get("speaker") and item["speaker"] not in character_names:
            errors.append(f"narration: vorbitorul „{item['speaker']}” nu e în characters")
        pause = item.get("pause", 0)
        if not isinstance(pause, (int, float)) or not 0 <= pause <= voce.PAUSE_MAX:
            errors.append(f"narration: pause trebuie să fie între 0 și {voce.PAUSE_MAX} secunde")
    if not errors:
        spoken = re.findall(r"[\wăâîșțĂÂÎȘȚ]+", plain(" ".join(i["text"] for i in narration)))
        shown = re.findall(r"[\wăâîșțĂÂÎȘȚ]+", plain(page.get("text") or ""))
        if spoken != shown:
            errors.append("narration nu conține exact aceleași cuvinte ca text (vocea trebuie să citească ce scrie)")
    return errors


def validate_story(folder, data):
    errors, warnings = [], []
    if "_error" in data:
        return [data["_error"]], warnings

    for field in REQUIRED_FIELDS:
        if not data.get(field):
            errors.append(f"lipsește câmpul obligatoriu '{field}'")

    story_id = data.get("id", "")
    if story_id != folder.name:
        errors.append(f"id-ul '{story_id}' trebuie să fie identic cu numele folderului '{folder.name}'")
    if not ID_PATTERN.match(folder.name):
        errors.append("numele folderului trebuie să conțină doar litere mici fără diacritice, cifre și cratime")

    title = (data.get("title") or "").strip()
    if title and word_count(title) > 10:
        errors.append(f"titlul are {word_count(title)} cuvinte (maximum 10; recomandat 2–7)")
    if data.get("age", "3-7") not in AGES:
        errors.append(f"age trebuie să fie unul dintre {', '.join(sorted(AGES))}")

    learning = data.get("learning")
    if learning is not None and (not isinstance(learning, list) or not 1 <= len(learning) <= 3
                                 or not all(isinstance(x, str) and x.strip() for x in learning)):
        errors.append("learning trebuie să fie o listă cu 1–3 lucruri de învățat")

    characters = data.get("characters") or []
    for character in characters:
        name = character.get("name") or "?"
        if not character.get("name"):
            errors.append("un personaj nu are nume")
        if len(character.get("description") or "") < MIN_DESCRIPTION_CHARS:
            errors.append(f"personajul {name}: descrierea vizuală lipsește sau e prea scurtă")
        if character.get("knownCharacter") and not character.get("source"):
            errors.append(f"personajul {name}: e marcat knownCharacter, dar lipsește source")
        errors.extend(validate_voice_profile(name, character.get("voice")))
    character_names = {c.get("name") for c in characters}

    texts = [title, data.get("summary", ""), data.get("moral", "")]
    cover = data.get("cover") or {}
    check_image(folder, cover.get("image"), "copertă", errors, warnings)
    if len(cover.get("imagePrompt") or "") < MIN_PROMPT_CHARS:
        errors.append("copertă: lipsește imagePrompt sau e prea scurt")

    pages = data.get("pages") or []
    if not MIN_PAGES <= len(pages) <= MAX_PAGES:
        errors.append(f"povestea are {len(pages)} pagini (trebuie {MIN_PAGES}–{MAX_PAGES})")
    for number, page in enumerate(pages, start=1):
        label = f"pagina {number}"
        text = (page.get("text") or "").strip()
        texts.append(text)
        words = word_count(text)
        if not MIN_WORDS <= words <= MAX_WORDS:
            errors.append(f"{label}: are {words} cuvinte (trebuie {MIN_WORDS}–{MAX_WORDS})")
        if re.search(r"\d", text):
            warnings.append(f"{label}: conține cifre; scrie numerele în litere pentru citirea cu voce")
        if not page.get("narration"):
            errors.append(f"{label}: lipsește regia de voce (narration) — vezi REGULI_POVESTI.md, secțiunea 7")
        errors.extend(f"{label}: {m}" for m in validate_narration(page, character_names))
        for sentence in re.split(r"(?<=[.!?…])\s+", text):
            if word_count(sentence) > LONG_SENTENCE_WORDS:
                warnings.append(f"{label}: o propoziție are {word_count(sentence)} cuvinte; împarte-o (ideal sub 15)")
        found = [w for w in SENSITIVE_WORDS if re.search(rf"\b{w}\b", text.lower())]
        if found:
            warnings.append(f"{label}: verifică dacă e potrivit pentru 3–7 ani: {', '.join(found)}")
        check_image(folder, page.get("image"), label, errors, warnings)
        prompt = page.get("imagePrompt") or ""
        if len(prompt) < MIN_PROMPT_CHARS:
            errors.append(f"{label}: lipsește imagePrompt sau e prea scurt (imaginea trebuie să descrie pagina)")
            continue
        for character in characters:
            name = plain(character.get("name") or "")
            if name and re.search(rf"\b{re.escape(name)}\b", plain(text)) and name not in plain(prompt):
                warnings.append(f"{label}: {character['name']} apare în text, dar nu și în imagePrompt")

    if data.get("summary") and not SUMMARY_WORDS[0] <= word_count(data["summary"]) <= SUMMARY_WORDS[1]:
        warnings.append(f"summary ar trebui să aibă {SUMMARY_WORDS[0]}–{SUMMARY_WORDS[1]} cuvinte")

    if pages:
        minutes = estimated_minutes(pages)
        if not MIN_MINUTES <= minutes <= MAX_MINUTES:
            errors.append(f"durata estimată e {minutes:.1f} minute (trebuie {MIN_MINUTES}–{MAX_MINUTES})")

    if any(CEDILLA.search(t) for t in texts):
        errors.append("folosește ș/ț cu virgulă, nu ş/ţ cu sedilă")
    if canon.PLACEHOLDER in json.dumps(data, ensure_ascii=False):
        errors.append(f"șablonul nu e completat: mai există „{canon.PLACEHOLDER}”")
    errors.extend(validate_quality(data))
    return errors, warnings


def validate_quality(data):
    """Regulile de calitate care nu țin de structură: stil, personaje identice, Lio, voce, autoevaluare."""
    errors = []
    pages = data.get("pages") or []
    characters = data.get("characters") or []
    style = data.get("illustrationStyle") or ""

    missing = [m for m in canon.STYLE_MARKERS if m not in style.lower()]
    if style and missing:
        errors.append(f"illustrationStyle nu e stilul Iamlio (lipsește: {', '.join(missing)}) — copiază-l din sablon/story.json")
    prompts = [("copertă", (data.get("cover") or {}).get("imagePrompt") or "")]
    prompts += [(f"pagina {n}", p.get("imagePrompt") or "") for n, p in enumerate(pages, start=1)]
    for label, prompt in prompts:
        if not prompt:
            continue
        if style and style not in prompt:
            errors.append(f"{label}: imagePrompt trebuie să conțină illustrationStyle cuvânt cu cuvânt (același stil pe toate imaginile)")
        for character in characters:
            name, description = character.get("name") or "", character.get("description") or ""
            if name and description and re.search(rf"\b{re.escape(plain(name))}\b", plain(prompt)) and description not in prompt:
                errors.append(f"{label}: {name} apare în imagePrompt, dar fără descrierea completă din characters (personajele trebuie să arate identic)")

    for character in characters:
        name = character.get("name") or ""
        if name == "Lio":
            description = (character.get("description") or "").lower()
            if not all(m in description for m in canon.LIO_MARKERS):
                errors.append("Lio: folosește descrierea oficială a lui Lio (REGULI_POVESTI.md, secțiunea 4)")
            if character.get("voice") != canon.LIO_VOICE:
                errors.append(f"Lio: folosește profilul de voce oficial {json.dumps(canon.LIO_VOICE)}")
        if character.get("knownCharacter") and len(character.get("description") or "") < canon.MIN_KNOWN_CHARACTER_DESCRIPTION:
            errors.append(f"{name}: un personaj cunoscut are nevoie de o descriere vizuală foarte detaliată (fidelă originalului)")

    with_voice = {c.get("name") for c in characters if c.get("voice")}
    moods = set()
    for number, page in enumerate(pages, start=1):
        narration = page.get("narration") if isinstance(page.get("narration"), list) else []
        moods.update(item.get("mood", voce.NARRATOR_MOOD) for item in narration if isinstance(item, dict))
        speakers = {item.get("speaker") for item in narration if isinstance(item, dict) and item.get("speaker")}
        if "—" in (page.get("text") or "") and narration and not speakers:
            errors.append(f"pagina {number}: are dialog, dar nicio replică din narration nu are speaker")
        for speaker in sorted(speakers - with_voice):
            errors.append(f"pagina {number}: {speaker} vorbește, dar nu are profil de voce (voice) în characters")
    if pages and len(moods) < canon.MIN_DISTINCT_MOODS:
        errors.append(f"regia de voce folosește doar {len(moods)} tonuri; folosește cel puțin {canon.MIN_DISTINCT_MOODS} ca povestea să nu sune monoton")

    errors.extend(validate_review(data.get("review"), len(pages)))
    return errors


def validate_review(review, page_count):
    if review is None:
        return []
    if not isinstance(review, dict):
        return ["review trebuie să fie un obiect cu autoevaluarea poveștii"]
    errors = []
    for key, meaning in canon.REVIEW_FIELDS.items():
        value = review.get(key)
        if key == "umor":
            moments = value if isinstance(value, list) else []
            pages = [int(m.group(1)) for m in (re.match(r"\s*pagina (\d+)\s*:", str(x)) for x in moments) if m]
            if len(pages) < canon.MIN_HUMOR_MOMENTS or len(pages) != len(moments):
                errors.append(f"review.umor: cel puțin {canon.MIN_HUMOR_MOMENTS} momente amuzante, fiecare de forma „pagina N: …”")
            elif any(not 1 <= p <= page_count for p in pages):
                errors.append("review.umor: o pagină indicată nu există")
        elif not isinstance(value, str) or len(value.strip()) < canon.MIN_REVIEW_CHARS:
            errors.append(f"review.{key}: scrie {meaning}")
    return errors


def optimize_image(folder, rel_path):
    """Micșorează imaginea la MAX_IMAGE_SIZE și o salvează ca .webp. Întoarce noua cale relativă."""
    from PIL import Image

    path = folder / rel_path
    if path.suffix.lower() not in RASTER_EXTENSIONS or not path.is_file():
        return rel_path
    target = path.with_suffix(".webp")
    with Image.open(path) as img:
        too_big = img.width > MAX_IMAGE_SIZE[0] or img.height > MAX_IMAGE_SIZE[1]
        if path.suffix.lower() == ".webp" and not too_big and path.stat().st_size <= MAX_IMAGE_KB * 1024:
            return rel_path
        img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")
        img.thumbnail(MAX_IMAGE_SIZE, Image.LANCZOS)
        for quality in WEBP_QUALITIES:
            img.save(target, "WEBP", quality=quality, method=6)
            if target.stat().st_size <= MAX_IMAGE_KB * 1024:
                break
    if target != path:
        path.unlink()
    print(f"    🖼  {folder.name}/{rel_path} → {target.name} ({target.stat().st_size // 1024} KB)")
    return str(Path(rel_path).with_suffix(".webp"))


def cmd_optimize():
    for folder, data in load_stories():
        if "_error" in data:
            continue
        changed = False
        entries = [data.get("cover") or {}] + list(data.get("pages") or [])
        for entry in entries:
            if entry.get("image"):
                new_path = optimize_image(folder, entry["image"])
                if new_path != entry["image"]:
                    entry["image"] = new_path
                    changed = True
        if changed:
            (folder / "story.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", plain(title)).strip("-")


def template_story(story_id="id-ul-povestii", title=f"{canon.PLACEHOLDER}: titlul poveștii"):
    todo = canon.PLACEHOLDER
    lio = {"name": "Lio", "description": canon.LIO_DESCRIPTION, "voice": canon.LIO_VOICE}
    page = {
        "text": f"{todo}: textul paginii (20–70 de cuvinte).",
        "narration": [{"text": f"{todo}: textul paginii (20–70 de cuvinte).", "mood": "calm"}],
        "image": "images/pagina-01.png",
        "imagePrompt": f"{canon.STYLE} Characters in this scene: Lio: {canon.LIO_DESCRIPTION}. "
                       f"Setting: {todo}. Action: {todo}. Emotions: {todo}. Important details: {todo}. Camera: {todo}.",
    }
    return {
        "id": story_id,
        "title": title,
        "summary": f"{todo}: una-două propoziții care îi fac pe copii curioși.",
        "age": "3-7",
        "moral": f"{todo}: morala, o singură propoziție pozitivă.",
        "learning": [f"{todo}: ce învață copilul"],
        "created": "2026-01-01",
        "tags": [],
        "illustrationStyle": canon.STYLE,
        "characters": [lio],
        "cover": {
            "image": "images/coperta.png",
            "imagePrompt": f"{canon.STYLE} Characters in this scene: Lio: {canon.LIO_DESCRIPTION}. Setting: {todo}. Action: {todo}.",
        },
        "pages": [page],
        "review": {key: f"{todo}: {meaning}" for key, meaning in canon.REVIEW_FIELDS.items()},
    }


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_template():
    TEMPLATE_FILE.parent.mkdir(exist_ok=True)
    write_json(TEMPLATE_FILE, template_story())
    print(f"Șablon actualizat: {TEMPLATE_FILE.relative_to(ROOT)}")
    return 0


def cmd_new(title):
    from datetime import date

    story_id = slugify(title)
    folder = STORIES_DIR / story_id
    if not story_id or folder.exists():
        print(f"Nu pot crea „{story_id}”: id gol sau povestea există deja.")
        return 1
    (folder / "images").mkdir(parents=True)
    data = template_story(story_id, title)
    data["created"] = date.today().isoformat()
    write_json(folder / "story.json", data)
    print(f"Poveste nouă: public/stories/{story_id}/story.json — completează tot ce e marcat „{canon.PLACEHOLDER}”.")
    return 0


def cmd_validate():
    stories = load_stories()
    failed = False
    for folder, data in stories:
        errors, warnings = validate_story(folder, data)
        status = "EROARE" if errors else "OK"
        print(f"[{status}] {folder.name}")
        for message in errors:
            print(f"    ✗ {message}")
        for message in warnings:
            print(f"    ! {message}")
        failed = failed or bool(errors)
    print(f"{len(stories)} povești verificate.")
    return 1 if failed else 0


def narration_items(data):
    """Fișierele audio ale unei povești: (nume fișier, listă de bucăți cu intonație)."""
    Segment = voce.Segment
    items = [("coperta.mp3", [Segment("Lio îți citește povestea:", "vesel", "Lio", 0.4),
                              Segment(f"{data['title']}.", "entuziasmat", "Lio")])]
    for number, page in enumerate(data["pages"], start=1):
        items.append((f"pagina-{number:02d}.mp3", voce.page_segments(page)))
    items.append(("final.mp3", [Segment("Sfârșit.", "calm", pause=0.6), Segment(data["moral"], "calm")]))
    return items


async def generate_audio_set(audio_dir, items, characters):
    """Generează items pentru fiecare voce, doar ce s-a schimbat (după amprenta regiei)."""
    manifest_file = audio_dir / "manifest.json"
    old = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    manifest = {}
    for key in VOICES:
        voice_dir = audio_dir / key
        voice_dir.mkdir(parents=True, exist_ok=True)
        previous = old.get(key, {}) if isinstance(old.get(key), dict) else {}
        manifest[key] = {}
        for name, segments in items:
            digest = hashlib.sha1(voce.fingerprint(segments, key, characters).encode()).hexdigest()
            target = voice_dir / name
            if previous.get(name) != digest or not target.exists():
                print(f"    🔊 {target.relative_to(ROOT)}")
                await voce.render(segments, key, characters, target)
            manifest[key][name] = digest
            # scriem manifestul după fiecare fișier, ca o eroare să nu piardă munca făcută
            manifest_file.write_text(json.dumps({**old, **manifest}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for stale in voice_dir.glob("*.mp3"):
            if stale.name not in manifest[key]:
                stale.unlink()
    for leftover in audio_dir.glob("*.mp3"):  # format vechi, fără folder pe voce
        leftover.unlink()
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def lio_items():
    if not LIO_LINES_FILE.exists():
        return []
    lines = json.loads(LIO_LINES_FILE.read_text(encoding="utf-8"))["replici"]
    return [(f"replica-{n:02d}.mp3", [voce.Segment(text, "vesel", "Lio")]) for n, text in enumerate(lines, start=1)]


def story_characters(data):
    characters = list(data.get("characters") or [])
    if not any(c.get("name") == "Lio" for c in characters):
        characters.append(LIO_PROFILE)
    return characters


def valid_stories():
    for folder, data in load_stories():
        errors, _ = validate_story(folder, data)
        if errors:
            print(f"[sărit] {folder.name} (nu trece validarea)")
            continue
        yield folder, data


def cmd_audio():
    for folder, data in valid_stories():
        print(f"[audio] {folder.name}")
        asyncio.run(generate_audio_set(folder / "audio", narration_items(data), story_characters(data)))
    items = lio_items()
    if items:
        print("[audio] replicile lui Lio")
        asyncio.run(generate_audio_set(LIO_AUDIO_DIR, items, [LIO_PROFILE]))
    return 0


def missing_audio(audio_dir, names):
    manifest_file = audio_dir / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    missing = []
    for key in VOICES:
        for name in names:
            path = audio_dir / key / name
            if name not in manifest.get(key, {}) or not path.is_file() or path.stat().st_size < 1024:
                missing.append(f"{key}/{name}")
    return missing


def cmd_verify_audio():
    failed = False
    groups = [(folder.name, folder / "audio", [n for n, _ in narration_items(data)]) for folder, data in valid_stories()]
    items = lio_items()
    if items:
        groups.append(("replicile lui Lio", LIO_AUDIO_DIR, [n for n, _ in items]))
    for label, audio_dir, names in groups:
        missing = missing_audio(audio_dir, names)
        print(f"[{'LIPSĂ' if missing else 'OK'}] audio {label}")
        for name in missing:
            print(f"    ✗ {name}")
        failed = failed or bool(missing)
    return 1 if failed else 0


def cmd_index():
    entries = []
    for folder, data in load_stories():
        errors, _ = validate_story(folder, data)
        if errors:
            print(f"[exclus din bibliotecă] {folder.name}")
            continue
        minutes = estimated_minutes(data["pages"])
        audio_dir = folder / "audio" / "feminin"
        mp3s = list(audio_dir.glob("*.mp3"))
        if len(mp3s) == len(data["pages"]) + 2:
            seconds = sum(f.stat().st_size for f in mp3s) / MP3_BYTES_PER_SECOND
            minutes = (seconds + len(data["pages"]) * SECONDS_PER_PAGE_TURN) / 60
        entries.append({
            "id": data["id"],
            "title": data["title"],
            "summary": data["summary"],
            "age": data.get("age", "3-7"),
            "tags": data.get("tags", []),
            "created": data["created"],
            "cover": f"stories/{data['id']}/{data['cover']['image']}",
            "pages": len(data["pages"]),
            "minutes": max(1, round(minutes)),
        })
    entries.sort(key=lambda e: (e["created"], e["title"]), reverse=True)
    INDEX_FILE.write_text(json.dumps({"stories": entries}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Bibliotecă actualizată: {len(entries)} povești.")
    return 0


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if command == "new" and len(sys.argv) > 2:
        return cmd_new(" ".join(sys.argv[2:]))
    if command == "template":
        return cmd_template()
    if command == "optimize":
        return cmd_optimize()
    if command == "validate":
        return cmd_validate()
    if command == "audio":
        return cmd_audio()
    if command == "verify-audio":
        return cmd_verify_audio()
    if command == "index":
        return cmd_index()
    if command == "all":
        cmd_optimize()
        result = cmd_validate()
        if result == 0:
            cmd_audio()
            result = cmd_verify_audio()
        cmd_index()
        return result
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
