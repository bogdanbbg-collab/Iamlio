#!/usr/bin/env python3
"""Instrumente pentru poveștile Iamlio.

Comenzi:
  prepare   repară automat poveștile, generează imaginile lipsă (dacă e configurat), optimizează, verifică
            și scrie rapoartele din rapoarte/ (folosit la publicare)
  stage     copiază în build/site doar ce se publică (poveștile care trec verificarea)
  status    iese cu eroare dacă vreo poveste nu trece verificarea
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
import shutil
import sys
import unicodedata
from pathlib import Path

import canon
import imagini
import pregatire
import voce

ROOT = Path(__file__).resolve().parent.parent
STORIES_DIR = ROOT / "public" / "stories"
INDEX_FILE = STORIES_DIR / "index.json"
LIO_LINES_FILE = ROOT / "public" / "assets" / "lio-replici.json"
LIO_AUDIO_DIR = ROOT / "public" / "assets" / "audio"

# Fiecare poveste primește ambele voci; cititorul alege una.
VOICES = voce.VOICES
TEMPLATE_FILE = ROOT / "sablon" / "story.json"
REPORTS_DIR = ROOT / "rapoarte"
PUBLICATIONS_FILE = REPORTS_DIR / "publicari.json"
BUILD_DIR = ROOT / "build" / "site"
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
REQUIRED_FIELDS = ["id", "title", "summary", "moral", "learning", "categories", "created", "illustrationStyle",
                   "characters", "cover", "pages", "review"]


def load_stories():
    stories = []
    for story_file in sorted(STORIES_DIR.glob("*/story.json")):
        try:
            data = json.loads(story_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            data = {"_error": f"JSON invalid: {exc}"}
        if not isinstance(data, dict):
            data = {"_error": "story.json trebuie să fie un obiect JSON ({…}), nu o listă sau o valoare"}
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
    path = pregatire.safe_image(folder, rel_path)
    if path is None:
        errors.append(f"{label}: calea imaginii trebuie să fie de forma images/nume.webp|png|jpg (primit: {rel_path})")
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


def validate_questions(folder, questions, image_errors, warnings):
    """Întrebările lui Lio (opționale): 1–3, fiecare cu 2–3 variante ilustrate (imagine sau emoji) și răspunsul corect."""
    if questions is None:
        return []
    if not isinstance(questions, list) or not 1 <= len(questions) <= canon.MAX_QUESTIONS:
        return [f"questions: între 1 și {canon.MAX_QUESTIONS} întrebări (sau deloc)"]
    errors = []
    low, high = canon.OPTIONS_PER_QUESTION
    for n, question in enumerate(questions, start=1):
        label = f"întrebarea {n}"
        if not isinstance(question, dict) or not str(question.get("text") or "").strip():
            errors.append(f"{label}: lipsește textul întrebării")
            continue
        if word_count(question["text"]) > canon.MAX_QUESTION_WORDS:
            errors.append(f"{label}: maximum {canon.MAX_QUESTION_WORDS} de cuvinte (e pentru copii mici)")
        options = question.get("options")
        if not isinstance(options, list) or not low <= len(options) <= high:
            errors.append(f"{label}: trebuie {low}–{high} variante de răspuns")
            continue
        for m, option in enumerate(options, start=1):
            if not isinstance(option, dict) or not str(option.get("text") or "").strip():
                errors.append(f"{label}, varianta {m}: lipsește textul")
                continue
            if option.get("image"):
                check_image(folder, option["image"], f"{label}, varianta {m}", image_errors, warnings)
            elif not str(option.get("emoji") or "").strip():
                errors.append(f"{label}, varianta {m}: are nevoie de o imagine (image) sau de un emoji")
        answer = question.get("answer")
        if not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer < len(options):
            errors.append(f"{label}: answer trebuie să fie numărul variantei corecte, începând de la 0")
        explanation = question.get("explanation")
        if explanation is not None and (not isinstance(explanation, str) or word_count(explanation) > 40):
            errors.append(f"{label}: explanation e o frază scurtă (maximum 40 de cuvinte)")
    return errors


def validate_personalized(data):
    """Poveștile personalizate: doar prenumele copilului, link secret, aprobare înainte de a fi trimise."""
    personalized = data.get("personalized")
    if personalized is None:
        return []
    errors = []
    name = personal_name(data)
    if not isinstance(personalized, dict) or not re.fullmatch(r"[^\W\d_]+(?:[ -][^\W\d_]+)?", name) or len(name) > 20:
        errors.append("personalized.for: doar prenumele copilului (sau un alint), fără nume de familie, cifre sau alte date")
    elif not any(name.lower() in (p.get("text") or "").lower() for p in data.get("pages") or [] if isinstance(p, dict)):
        errors.append(f"personalized: prenumele „{name}” trebuie să apară în poveste")
    if not re.search(rf"-[a-z0-9]{{{canon.PERSONAL_SUFFIX_LENGTH},}}$", str(data.get("id", ""))):
        errors.append(f"o poveste personalizată are un id care se termină cu un cod aleator de minimum "
                      f"{canon.PERSONAL_SUFFIX_LENGTH} caractere (folosește: stories.py new \"Titlu\" --pentru Nume)")
    if not isinstance(data.get("approved", False), bool):
        errors.append("approved trebuie să fie true sau false")
    return errors


def narration_in_text(page):
    """Fiecare replică apare, în ordine, exact așa în textul paginii (pentru evidențierea sincronă)."""
    text, cursor = page.get("text") or "", 0
    for item in page.get("narration") or []:
        part = item.get("text") if isinstance(item, dict) else None
        at = text.find(part, cursor) if part else -1
        if at == -1:
            return False
        cursor = at + len(part)
    return True


def validate_story(folder, data):
    """Verifică o poveste. O structură neașteptată devine o eroare a acestei povești, nu oprește restul."""
    if not isinstance(data, dict):
        return ["story.json trebuie să fie un obiect JSON"], []
    if "_error" in data:
        return [data["_error"]], []
    shape = structure_errors(data)
    if shape:
        return shape, []
    try:
        return check_story(folder, data)
    except Exception as exc:  # orice altă formă ciudată a datelor
        return [f"structură neașteptată în story.json ({type(exc).__name__}: {exc})"], []


def structure_errors(data):
    """Tipurile câmpurilor, verificate înainte de orice altă regulă."""
    errors = []
    expect = {"title": str, "summary": str, "moral": str, "created": str, "illustrationStyle": str,
              "characters": list, "pages": list, "cover": dict, "review": dict, "tags": list, "questions": list,
              "personalized": dict}
    for key, kind in expect.items():
        if key in data and data[key] is not None and not isinstance(data[key], kind):
            errors.append(f"câmpul '{key}' trebuie să fie {dict(str='text', list='listă', dict='obiect')[kind.__name__]}")
    for n, page in enumerate(data.get("pages") if isinstance(data.get("pages"), list) else [], start=1):
        if not isinstance(page, dict):
            errors.append(f"pagina {n} trebuie să fie un obiect cu text, narration, image, imagePrompt")
        elif "text" in page and not isinstance(page["text"], str):
            errors.append(f"pagina {n}: text trebuie să fie text")
    for character in data.get("characters") if isinstance(data.get("characters"), list) else []:
        if not isinstance(character, dict):
            errors.append("fiecare personaj din characters trebuie să fie un obiect cu name și description")
            break
    return errors


def check_story(folder, data):
    errors, warnings = [], []

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

    categories = data.get("categories")
    if categories is not None and (not isinstance(categories, list) or not 1 <= len(categories) <= canon.MAX_CATEGORIES
                                   or len(set(categories)) != len(categories)
                                   or any(c not in canon.CATEGORIES for c in categories)):
        errors.append(f"categories: alege 1–{canon.MAX_CATEGORIES} categorii dintre {', '.join(canon.CATEGORIES)}")

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
        if isinstance(page.get("narration"), list) and not narration_in_text(page):
            errors.append(f"{label}: replicile din narration nu sunt copiate exact (cu aceeași punctuație) din text; "
                          "rulează `python3 scripts/stories.py prepare` (le copiază automat din text)")
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

    errors.extend(validate_questions(folder, data.get("questions"), errors, warnings))
    errors.extend(validate_personalized(data))
    for question in data.get("questions") or []:
        if isinstance(question, dict):
            texts += [str(question.get("text", "")), str(question.get("explanation", ""))]
            texts += [str(o.get("text", "")) for o in question.get("options") or [] if isinstance(o, dict)]

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

    path = pregatire.safe_image(folder, rel_path)
    if path is None or path.suffix.lower() not in RASTER_EXTENSIONS or not path.is_file() or path.is_symlink():
        return rel_path  # căile nesigure nu se ating; validarea le respinge
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


def image_entries(data):
    """Toate locurile din story.json care au o imagine: coperta, paginile, variantele întrebărilor."""
    entries = [data.get("cover") or {}] + [p for p in data.get("pages") or [] if isinstance(p, dict)]
    for question in data.get("questions") or []:
        if isinstance(question, dict):
            entries += [o for o in question.get("options") or [] if isinstance(o, dict) and o.get("image")]
    return entries


def cmd_optimize():
    for folder, data in load_stories():
        if "_error" in data or structure_errors(data):
            continue  # structura greșită e raportată de validare
        changed = False
        entries = image_entries(data)
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
    return pregatire.slugify(title)


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
        "categories": [],
        "review": {key: f"{todo}: {meaning}" for key, meaning in canon.REVIEW_FIELDS.items()},
    }


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_template():
    TEMPLATE_FILE.parent.mkdir(exist_ok=True)
    write_json(TEMPLATE_FILE, template_story())
    print(f"Șablon actualizat: {TEMPLATE_FILE.relative_to(ROOT)}")
    return 0


def cmd_new(title, for_name=""):
    import secrets
    import string
    from datetime import date

    story_id = slugify(title)
    if for_name:  # link secret: un cod aleator la final
        alphabet = string.ascii_lowercase + string.digits
        story_id += "-" + "".join(secrets.choice(alphabet) for _ in range(canon.PERSONAL_SUFFIX_LENGTH))
    folder = STORIES_DIR / story_id
    if not story_id or folder.exists():
        print(f"Nu pot crea „{story_id}”: id gol sau povestea există deja.")
        return 1
    (folder / "images").mkdir(parents=True)
    data = template_story(story_id, title)
    data["created"] = date.today().isoformat()
    if for_name:
        data["personalized"] = {"for": for_name}
        data["approved"] = False
    write_json(folder / "story.json", data)
    print(f"Poveste nouă: public/stories/{story_id}/story.json — completează tot ce e marcat „{canon.PLACEHOLDER}”.")
    return 0


def cmd_prepare():
    """Repară, completează imaginile, optimizează și verifică; scrie câte un raport pentru fiecare poveste."""
    repairs = {}
    image_budget = imagini.Budget(REPORTS_DIR / "buget-imagini.json")
    for story_file in sorted(STORIES_DIR.glob("*/story.json")):
        folder = story_file.parent
        try:
            data = json.loads(story_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue  # validarea raportează JSON-ul invalid
        if not isinstance(data, dict) or structure_errors(data):
            continue  # structura greșită se raportează; nu încercăm să reparăm ce nu înțelegem
        try:
            repairs[folder.name] = prepare_one(folder, data, image_budget)
        except Exception as exc:
            repairs[folder.name] = ([], [f"repararea automată a eșuat ({type(exc).__name__}: {exc})"], 0)
    image_budget.save()
    cmd_optimize()
    write_reports(repairs)
    return 0


def prepare_one(folder, data, image_budget):
    """Repară o poveste; întoarce (modificări, note, imagini generate). Scrie story.json dacă s-a schimbat ceva."""
    if True:
        original = json.dumps(data, ensure_ascii=False, sort_keys=True)
        changes, notes, made = [], [], 0
        new_folder = pregatire.rename_folder(folder, data)
        if new_folder != folder:
            changes.append(f"folderul „{folder.name}” a fost redenumit „{new_folder.name}”")
            folder = new_folder
        data, repaired = pregatire.prepare(folder, data)
        changes += repaired
        if imagini.missing(folder, data):
            if imagini.enabled():
                made_changes, errors, made = imagini.generate_missing(folder, data, budget=image_budget)
                changes += made_changes
                notes += errors
            else:
                notes.append("lipsesc imagini: generează-le și salvează-le în images/ cu numele din story.json "
                             "(sau proprietarul proiectului poate activa generarea automată: gratuit cu Cloudflare, secretele "
                             "CLOUDFLARE_ACCOUNT_ID și CLOUDFLARE_API_TOKEN, cu rezerva gratuită POLLINATIONS_API_KEY, "
                             "ori cu plată cu OPENAI_API_KEY)")
        if json.dumps(data, ensure_ascii=False, sort_keys=True) != original:
            write_json(folder / "story.json", data)
        return changes, notes, made


def write_reports(repairs):
    import os
    import tempfile
    from datetime import datetime, timezone

    REPORTS_DIR.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows, summary = [], ["## Poveștile Iamlio", ""]
    seen = set()
    for folder, data in load_stories():
        errors, warnings = validate_story(folder, data)
        changes, notes, _ = repairs.get(folder.name, ([], [], 0))
        title = data.get("title") or folder.name
        published = not errors
        if errors and ID_PATTERN.match(folder.name):
            with tempfile.TemporaryDirectory() as workdir:
                found = previous_published(folder.name, workdir)
            if found:
                notes = notes + [f"pe site rămâne versiunea publicată anterior (commit {found[1][:7]}) până când "
                                 "corectezi problemele de mai sus"]
        seen.add(f"{folder.name}.md")
        write_if_changed(REPORTS_DIR / f"{folder.name}.md",
                         report_text(folder.name, str(title), published, changes, errors, notes, warnings, now,
                        personal=bool(personal_name(data)), approved=data.get("approved") is True), now)
        status = "✅ publicată" if published else "❌ nepublicată"
        rows.append(f"| [{title}]({folder.name}.md) | {status} | {len(errors)} | {len(changes)} |")
        summary.append(f"- {status}: **{title}** — {len(errors)} de corectat, {len(changes)} reparate automat")
        print(f"[{'OK' if published else 'EROARE'}] {folder.name}: {len(changes)} reparate automat, {len(errors)} de corectat")
        for message in errors:
            print(f"    ✗ {message}")
    for old in REPORTS_DIR.glob("*.md"):
        if old.name not in seen and old.name not in ("README.md", "buget-imagini.md"):
            old.unlink()
    write_if_changed(REPORTS_DIR / "README.md",
        "# Rapoartele poveștilor\n\n"
        "Generate automat la fiecare publicare. Un AI care a adăugat sau a modificat o poveste citește raportul ei "
        "și corectează tot ce scrie la „De corectat”, până când raportul spune „publicată”.\n\n"
        f"Ultima verificare: {now}\n\n| Poveste | Stare | De corectat | Reparate automat |\n| --- | --- | --- | --- |\n"
        + "\n".join(rows) + "\n", now)
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as handle:
            handle.write("\n".join(summary) + "\n")
    return 0


def write_if_changed(path, text, stamp):
    """Scrie raportul doar dacă s-a schimbat altceva decât ora verificării (fără commit-uri inutile)."""
    if path.exists():
        old = path.read_text(encoding="utf-8")
        old_stamp = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC", old)
        if old_stamp and old.replace(old_stamp.group(0), "") == text.replace(stamp, ""):
            return
    path.write_text(text, encoding="utf-8")


def report_text(story_id, title, published, changes, errors, notes, warnings, when, personal=False, approved=False):
    import os

    lines = [f"# {title}", "",
             f"**Stare: {'✅ PUBLICATĂ' if published else '❌ NEPUBLICATĂ'}** · verificată la {when}", "",
             f"Poveste: `public/stories/{story_id}/story.json`", ""]
    if errors:
        lines += ["## De corectat (de aceea nu este publicată)", ""] + [f"- {e}" for e in errors] + [""]
    if notes:
        lines += ["## Note de la publicare", ""] + [f"- {n}" for n in notes] + [""]
    if personal:
        site = (os.environ.get('SITE_URL') or 'https://iamlio.ro').rstrip('/')
        if approved:
            lines += ["## Poveste personalizată", "",
                      f"- Link secret (nu apare în bibliotecă și nici în motoarele de căutare): {site}/poveste.html?id={story_id}",
                      "- **Aprobată** — link-ul poate fi trimis părinților.", ""]
        else:
            lines += ["## Poveste personalizată", "",
                      "- **Așteaptă aprobarea.** Până atunci NU este publică: o poate deschide doar cine știe parola "
                      f"de administrator (secretul `ADMIN_PASSWORD` din GitHub): {site}/poveste.html?previzualizare={story_id}",
                      "- Dacă e în regulă, cere AI-ului „aprobă povestea " + story_id + "” (sau pune "
                      "`\"approved\": true` în story.json). După publicare, link-ul pentru părinți va fi "
                      f"{site}/poveste.html?id={story_id}", ""]
    if changes:
        lines += ["## Reparat automat", "",
                  "Aceste lucruri au fost corectate automat în `story.json` (preia versiunea din repository înainte "
                  "de a modifica din nou povestea):", ""] + [f"- {c}" for c in changes] + [""]
    if warnings:
        lines += ["## Avertismente (merită verificate, dar nu blochează publicarea)", ""] + [f"- {w}" for w in warnings] + [""]
    lines += ["## Ce faci mai departe", ""]
    if published:
        lines.append("Nimic: povestea este pe site, cu vocea feminină și masculină generate automat.")
    else:
        lines += ["1. Corectează în `story.json` (și în `images/`) fiecare punct de la „De corectat”, respectând "
                  "`REGULI_POVESTI.md`.",
                  "2. Rulează `python3 scripts/stories.py validate` dacă poți; trebuie să afișeze `[OK]`.",
                  "3. Fă commit pe `master`. După câteva minute, citește din nou acest raport.",
                  "4. Repetă până când starea este „PUBLICATĂ”."]
    return "\n".join(lines) + "\n"


MAX_HISTORY = 40  # câte versiuni anterioare ale unei povești se caută în istoricul git


def previous_published(story_id, workdir, repo=ROOT):
    """Cea mai recentă versiune din istoricul git a poveștii care trece verificarea și are vocea completă.
    Întoarce (folder extras, commit) sau None. Așa o poveste deja publicată nu dispare de pe site
    doar pentru că ultima ei modificare e greșită."""
    import io
    import subprocess
    import tarfile

    rel = f"public/stories/{story_id}"
    log = subprocess.run(["git", "log", f"-n{MAX_HISTORY}", "--format=%H", "--", rel],
                         cwd=repo, capture_output=True, text=True)
    if log.returncode != 0:
        return None
    for sha in log.stdout.split():
        archive = subprocess.run(["git", "archive", "--format=tar", sha, rel], cwd=repo, capture_output=True)
        if archive.returncode != 0:
            continue
        target = Path(workdir) / sha
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(target, filter="data")
        folder = target / rel
        try:
            data = json.loads((folder / "story.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if validate_story(folder, data)[0]:
            continue
        if missing_audio(folder / "audio", [name for name, _ in narration_items(data)]):
            continue
        return folder, sha
    return None


def version_story_assets(folder, data):
    """images/x.webp → images/x.webp?v=<amprentă>: după o modificare, browserul nu mai arată imaginea veche."""
    for entry in image_entries(data):
        path = pregatire.safe_image(folder, entry.get("image"))
        if path is not None and path.is_file():
            entry["image"] = f"{entry['image']}?v={hashlib.sha1(path.read_bytes()).hexdigest()[:10]}"
    write_json(folder / "story.json", data)


def cmd_stage():
    """build/site = ce se publică: poveștile valide; pentru una invalidă, ultima ei versiune bună (dacă a existat)."""
    import tempfile

    invalid = {folder.name for folder, data in load_stories() if validate_story(folder, data)[0]}
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    ignore = lambda directory, names: [n for n in names if Path(directory) == STORIES_DIR and n in invalid]  # noqa: E731
    shutil.copytree(ROOT / "public", BUILD_DIR, ignore=ignore)
    with tempfile.TemporaryDirectory() as workdir:
        for name in sorted(invalid):
            found = previous_published(name, workdir) if ID_PATTERN.match(name) else None
            if found:
                shutil.copytree(found[0], BUILD_DIR / "stories" / name)
                print(f"[versiunea anterioară] {name}: rămâne publicată versiunea din {found[1][:7]}")
            else:
                print(f"[nepublicată] {name}")
    entries, published, previews, personal = [], [], [], []
    for story_file in sorted((BUILD_DIR / "stories").glob("*/story.json")):
        data = json.loads(story_file.read_text(encoding="utf-8"))
        intro, outro = lio_texts(data)
        data["lio"] = {"intro": intro, "outro": outro}  # cititorul afișează ce spune Lio
        version_story_assets(story_file.parent, data)
        if personal_name(data):
            personal.append({"id": data["id"], "title": data.get("title", ""), "for": personal_name(data),
                             "approved": data.get("approved") is True})
        if personal_name(data) and data.get("approved") is not True:
            previews.append(story_file.parent)
            continue
        if personal_name(data):
            continue  # link secret: nu apare în bibliotecă, recomandări sau sitemap
        entries.append(index_entry(story_file.parent, data))
        published.append(data)
    by_id = {d["id"]: d for d in published}
    for entry in entries:
        entry["cover"] = f"stories/{entry['id']}/{by_id[entry['id']]['cover']['image']}"
    write_index(BUILD_DIR / "stories" / "index.json", entries)
    stage_previews(previews)
    write_admin_info(entries, personal, invalid)
    add_asset_versions(BUILD_DIR)
    write_seo_files(BUILD_DIR, published)
    write_share_pages(BUILD_DIR, published)
    print(f"Pregătit pentru publicare: {BUILD_DIR} ({len(entries)} povești pe site)")
    return 0


def admin_password():
    """Parola administratorului: secretul ADMIN_PASSWORD (PREVIEW_PASSWORD, numele vechi, merge în continuare)."""
    import os

    return os.environ.get("ADMIN_PASSWORD") or os.environ.get("PREVIEW_PASSWORD") or ""


def stage_previews(folders):
    """Poveștile personalizate neaprobate NU rămân în partea publică (stories/): se mută în api/data/previzualizare/,
    pe care serverul nu îl servește direct, și se citesc doar prin api/previzualizare.php, după autentificarea
    administratorului. Pe server ajunge doar o amprentă cu sare a parolei (api/data/parola.json), nu parola."""
    import secrets

    password = admin_password()
    target = BUILD_DIR / "api" / "data" / "previzualizare"
    for folder in folders:
        if password:
            target.mkdir(parents=True, exist_ok=True)
            shutil.move(str(folder), str(target / folder.name))
            print(f"[previzualizare] {folder.name}: doar cu parola, până la aprobare")
        else:
            shutil.rmtree(folder)
            print(f"[nepublicată] {folder.name}: personalizată neaprobată; adaugă secretul ADMIN_PASSWORD "
                  "ca s-o poți previzualiza")
    if password:
        salt = secrets.token_hex(16)
        config = {"salt": salt, "hash": hashlib.sha256((salt + password).encode("utf-8")).hexdigest()}
        (BUILD_DIR / "api" / "data").mkdir(parents=True, exist_ok=True)
        (BUILD_DIR / "api" / "data" / "parola.json").write_text(json.dumps(config) + "\n", encoding="utf-8")


def write_admin_info(entries, personal, invalid):
    """api/data/admin-info.json: ce știe panoul de administrare despre site (privat, ca toate datele din api/data):
    poveștile publicate, cele cu probleme, cele personalizate, versiunea publicată și costul imaginilor."""
    import os
    import subprocess
    from datetime import datetime, timezone

    try:
        commit = os.environ.get("GITHUB_SHA") or subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = ""
    problems = []
    for folder, data in load_stories():
        if folder.name in invalid:
            errors = validate_story(folder, data)[0]
            title = data.get("title") if isinstance(data, dict) else ""
            problems.append({"id": folder.name, "title": title or folder.name, "errors": errors[:5], "count": len(errors)})
    try:
        budget = json.loads((REPORTS_DIR / "buget-imagini.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        budget = {}
    info = {
        "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": commit,
        "categories": {key: {"label": label, "emoji": emoji} for key, (label, emoji) in canon.CATEGORIES.items()},
        "stories": [{k: e.get(k) for k in ("id", "title", "published", "minutes", "pages", "age", "categories")}
                    for e in entries],
        "problems": problems,
        "personal": personal,
        "image_budget": budget,
    }
    target = BUILD_DIR / "api" / "data" / "admin-info.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(info, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def add_asset_versions(site):
    """style.css → style.css?v=<amprentă>: după o actualizare, browserele iau sigur fișierele noi, toate odată."""
    for page in site.glob("*.html"):
        html = page.read_text(encoding="utf-8")
        for asset in sorted((site / "assets").rglob("*")):
            if asset.suffix in (".css", ".js"):
                rel = asset.relative_to(site).as_posix()
                version = hashlib.sha1(asset.read_bytes()).hexdigest()[:10]
                html = html.replace(f'"{rel}"', f'"{rel}?v={version}"')
        page.write_text(html, encoding="utf-8")


def write_seo_files(site, stories):
    import os
    from html import escape

    base = (os.environ.get("SITE_URL") or "https://iamlio.ro").rstrip("/")
    urls = [(f"{base}/", None), (f"{base}/confidentialitate.html", None)] + [(f"{base}/poveste.html?id={s['id']}", s.get("created")) for s in stories]
    entries = "".join(
        f"  <url><loc>{escape(url)}</loc>{f'<lastmod>{day}</lastmod>' if day else ''}</url>\n" for url, day in urls)
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n", encoding="utf-8")
    (site / "robots.txt").write_text(f"User-agent: *\nDisallow: /api/\nDisallow: /admin.html\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")


def write_share_pages(site, stories):
    """p/<id>.html: pagina de distribuire a fiecărei povești, cu titlul, rezumatul și coperta ei (Open Graph),
    ca un link trimis pe WhatsApp sau Facebook să arate povestea, nu doar site-ul. Trimite imediat la cititor."""
    import os
    from html import escape

    from PIL import Image, ImageOps

    base = (os.environ.get("SITE_URL") or "https://iamlio.ro").rstrip("/")
    folder = site / "p"
    folder.mkdir(exist_ok=True)
    for story in stories:
        sid = story["id"]
        cover = site / "stories" / sid / story["cover"]["image"].split("?")[0]
        with Image.open(cover) as image:
            card = ImageOps.fit(image.convert("RGB"), (1200, 630), Image.LANCZOS, centering=(0.5, 0.4))
            card.save(folder / f"{sid}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
        version = hashlib.sha1((folder / f"{sid}.jpg").read_bytes()).hexdigest()[:10]
        title, summary = escape(story["title"]), escape(story.get("summary") or "")
        reader = f"../poveste.html?id={sid}"
        (folder / f"{sid}.html").write_text(f"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; base-uri 'none'">
<title>{title} — Iamlio</title>
<meta name="description" content="{summary}">
<meta property="og:type" content="article">
<meta property="og:locale" content="ro_RO">
<meta property="og:site_name" content="Iamlio">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{summary}">
<meta property="og:url" content="{base}/p/{sid}.html">
<meta property="og:image" content="{base}/p/{sid}.jpg?v={version}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Coperta poveștii „{title}”">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{base}/poveste.html?id={sid}">
<meta http-equiv="refresh" content="0; url={reader}">
</head>
<body>
<p><a href="{reader}">{title} — o poveste citită de Lio</a></p>
</body>
</html>
""", encoding="utf-8")


def cmd_status():
    invalid = [folder.name for folder, data in load_stories() if validate_story(folder, data)[0]]
    if invalid:
        print("Povești nepublicate (vezi rapoarte/): " + ", ".join(invalid))
        return 1
    print("Toate poveștile sunt publicate.")
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


def personal_name(data):
    personalized = data.get("personalized")
    return personalized.get("for", "").strip() if isinstance(personalized, dict) else ""


def lio_texts(data):
    """(salutul de la început, rămas-bunul de la final) ale lui Lio pentru această poveste."""
    name = personal_name(data)
    if name:
        return canon.LIO_PERSONAL_INTRO.format(name=name), canon.LIO_PERSONAL_OUTRO.format(name=name)
    first = (data.get("categories") or ["aventuri"])[0]
    pick = int(hashlib.sha1(str(data.get("id", "")).encode()).hexdigest(), 16)
    intros = canon.LIO_INTROS.get(first, canon.LIO_INTROS["aventuri"])
    outros = canon.LIO_OUTROS.get(first, canon.LIO_OUTROS["default"])
    return intros[pick % len(intros)], outros[pick % len(outros)]


def options_sentence(options):
    """„Lio, Ula sau Luna?” — variantele citite cu voce, pentru copiii care nu știu încă să citească."""
    texts = [str(o.get("text", "")).strip().rstrip(".!?") for o in options]
    return (", ".join(texts[:-1]) + " sau " + texts[-1] + "?") if len(texts) > 1 else (texts[0] + "?")


def narration_items(data):
    """Fișierele audio ale unei povești: (nume fișier, listă de bucăți cu intonație)."""
    Segment = voce.Segment
    intro, outro = lio_texts(data)
    bedtime = (data.get("categories") or [""])[0] == "de-culcare"
    items = [("coperta.mp3", [Segment(intro, "vesel", "Lio", 0.6),
                              Segment(f"{data['title']}.", "entuziasmat", "Lio")])]
    for number, page in enumerate(data["pages"], start=1):
        items.append((f"pagina-{number:02d}.mp3", voce.page_segments(page, data.get("characters") or [])))
    items.append(("final.mp3", [Segment("Sfârșit.", "calm", pause=0.6), Segment(data["moral"], "calm", pause=0.8),
                                Segment(outro, "somnoros" if bedtime else "vesel", "Lio")]))
    for number, question in enumerate(data.get("questions") or [], start=1):
        items.append((f"intrebare-{number}.mp3", [Segment(question["text"], "mirat", "Lio", 0.5),
                                                   Segment(options_sentence(question["options"]), "vesel", "Lio")]))
        if question.get("explanation"):
            items.append((f"raspuns-{number}.mp3", [Segment(question["explanation"], "vesel", "Lio")]))
    return items


async def generate_audio_set(audio_dir, items, characters):
    """Generează items pentru fiecare voce, doar ce s-a schimbat (după amprenta regiei)."""
    manifest_file = audio_dir / "manifest.json"
    old = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    manifest = {}
    old_timing = old.get("timing") if isinstance(old.get("timing"), dict) else {}
    timing = {}
    for key in VOICES:
        voice_dir = audio_dir / key
        voice_dir.mkdir(parents=True, exist_ok=True)
        previous = old.get(key, {}) if isinstance(old.get(key), dict) else {}
        previous_timing = old_timing.get(key, {}) if isinstance(old_timing.get(key), dict) else {}
        manifest[key], timing[key] = {}, {}
        for name, segments in items:
            digest = hashlib.sha1(voce.fingerprint(segments, key, characters).encode()).hexdigest()
            target = voice_dir / name
            if previous.get(name) != digest or not target.exists() or name not in previous_timing:
                print(f"    🔊 {target.relative_to(ROOT)}")
                timing[key][name] = await voce.render(segments, key, characters, target)
            else:
                timing[key][name] = previous_timing[name]
            manifest[key][name] = digest
            manifest["timing"] = timing
            # scriem manifestul după fiecare fișier, ca o eroare să nu piardă munca făcută
            manifest_file.write_text(json.dumps({**old, **manifest}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for stale in voice_dir.glob("*.mp3"):
            if stale.name not in manifest[key]:
                stale.unlink()
    for leftover in audio_dir.glob("*.mp3"):  # format vechi, fără folder pe voce
        leftover.unlink()
    manifest["timing"] = timing
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# Grupurile de replici ale lui Lio din assets/lio-replici.json → fișierele lor audio și tonul lor.
LIO_GROUPS = {"replici": ("replica", "vesel"), "bravo": ("bravo", "entuziasmat"), "incearca": ("incearca", "calm")}


def lio_items():
    if not LIO_LINES_FILE.exists():
        return []
    groups = json.loads(LIO_LINES_FILE.read_text(encoding="utf-8"))
    items = []
    for key, (prefix, mood) in LIO_GROUPS.items():
        for n, text in enumerate(groups.get(key) or [], start=1):
            items.append((f"{prefix}-{n:02d}.mp3", [voce.Segment(text, mood, "Lio")]))
    return items


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


MIN_AUDIO_SECONDS = 0.5


def audio_problem(path):
    """Motivul pentru care un mp3 nu e bun, sau "" dacă se decodează complet și are durată rezonabilă."""
    import subprocess

    if not path.is_file() or path.stat().st_size < 1024:
        return "lipsește sau e gol"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return ""  # fără ffmpeg (ex. pe calculatorul cuiva) rămâne doar verificarea de mai sus
    decoded = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    if decoded.returncode != 0 or decoded.stderr.strip():
        return "fișier audio corupt"
    probe = subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        return "durata nu poate fi citită"
    return "" if duration >= MIN_AUDIO_SECONDS else f"prea scurt ({duration:.2f} s)"


def missing_audio(audio_dir, names):
    manifest_file = audio_dir / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    missing = []
    for key in VOICES:
        for name in names:
            path = audio_dir / key / name
            problem = "nu e în manifest" if name not in manifest.get(key, {}) else audio_problem(path)
            if problem:
                missing.append(f"{key}/{name}: {problem}")
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


def index_entry(folder, data):
    """Intrarea din bibliotecă a unei povești (durata vine din fișierele audio, dacă există)."""
    minutes = estimated_minutes(data["pages"])
    mp3s = list((folder / "audio" / "feminin").glob("*.mp3"))
    if len(mp3s) == len(data["pages"]) + 2:
        seconds = sum(f.stat().st_size for f in mp3s) / MP3_BYTES_PER_SECOND
        minutes = (seconds + len(data["pages"]) * SECONDS_PER_PAGE_TURN) / 60
    return {
        "id": data["id"],
        "title": data["title"],
        "summary": data["summary"],
        "age": data.get("age", "3-7"),
        "tags": data.get("tags", []),
        "categories": data.get("categories", []),
        "created": data["created"],
        "cover": f"stories/{data['id']}/{data['cover']['image']}",
        "pages": len(data["pages"]),
        "minutes": max(1, round(minutes)),
    }


def publication_dates(ids):
    """Data la care fiecare poveste a apărut prima oară pe site (rapoarte/publicari.json, scris de robot).
    Doar la o publicare reală (PUBLICARE=1 în GitHub Actions) se notează poveștile noi; altfel, o poveste
    nenotată încă primește data de azi doar în memorie (pentru previzualizare și teste)."""
    import os
    from datetime import date

    try:
        known = json.loads(PUBLICATIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        known = {}
    if not isinstance(known, dict):
        known = {}
    today = date.today().isoformat()
    missing = [i for i in ids if not isinstance(known.get(i), str)]
    if missing and os.environ.get("PUBLICARE") == "1":
        known.update({i: today for i in missing})
        PUBLICATIONS_FILE.parent.mkdir(exist_ok=True)
        PUBLICATIONS_FILE.write_text(json.dumps(known, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {i: known.get(i) if isinstance(known.get(i), str) else today for i in ids}


def write_index(path, entries):
    """index.json: poveștile, cele publicate cel mai recent primele (cu data publicării, pentru „Nou”)."""
    published = publication_dates([e["id"] for e in entries])
    for entry in entries:
        entry["published"] = published[entry["id"]]
    entries.sort(key=lambda e: (e["published"], e["created"], e["title"]), reverse=True)
    categories = [{"id": key, "label": label, "emoji": emoji} for key, (label, emoji) in canon.CATEGORIES.items()]
    path.write_text(json.dumps({"categories": categories, "stories": entries}, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def cmd_index():
    entries = []
    for folder, data in load_stories():
        if validate_story(folder, data)[0]:
            print(f"[exclus din bibliotecă] {folder.name}")
            continue
        if personal_name(data):
            continue  # poveștile personalizate au doar link secret, nu apar în bibliotecă
        entries.append(index_entry(folder, data))
    write_index(INDEX_FILE, entries)
    print(f"Bibliotecă actualizată: {len(entries)} povești.")
    return 0


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if command == "new" and len(sys.argv) > 2:
        args = sys.argv[2:]
        for_name = ""
        if "--pentru" in args:
            at = args.index("--pentru")
            for_name = " ".join(args[at + 1:])
            args = args[:at]
        return cmd_new(" ".join(args), for_name)
    if command == "template":
        return cmd_template()
    if command == "prepare":
        return cmd_prepare()
    if command == "stage":
        return cmd_stage()
    if command == "status":
        return cmd_status()
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
