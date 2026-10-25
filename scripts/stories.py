#!/usr/bin/env python3
"""Instrumente pentru poveștile Iamlio.

Comenzi:
  validate  verifică toate poveștile după REGULI_POVESTI.md
  audio     generează vocea (mp3) pentru paginile care nu o au încă (edge-tts)
  index     regenerează public/stories/index.json
  all       validate + audio + index (folosit de GitHub Actions)
"""

import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORIES_DIR = ROOT / "public" / "stories"
INDEX_FILE = STORIES_DIR / "index.json"

ALLOWED_VOICES = {"ro-RO-AlinaNeural", "ro-RO-EmilNeural"}
DEFAULT_VOICE = "ro-RO-AlinaNeural"
SPEECH_RATE = "-8%"
IMAGE_EXTENSIONS = {".webp", ".jpg", ".jpeg", ".png", ".svg"}
MIN_PAGES, MAX_PAGES = 8, 12
MIN_WORDS, MAX_WORDS = 20, 60
MAX_IMAGE_KB = 400
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CEDILLA = re.compile("[şţŞŢ]")
REQUIRED_FIELDS = ["id", "title", "summary", "moral", "created", "characters", "cover", "pages"]
WORDS_PER_MINUTE = 100


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


def check_image(folder, rel_path, label, errors, warnings):
    if not rel_path:
        errors.append(f"{label}: lipsește câmpul image")
        return
    path = folder / rel_path
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        errors.append(f"{label}: extensie nepermisă {path.suffix}")
    if not path.is_file():
        errors.append(f"{label}: imaginea {rel_path} nu există")
    elif path.stat().st_size > MAX_IMAGE_KB * 1024:
        warnings.append(f"{label}: {rel_path} are {path.stat().st_size // 1024} KB (recomandat sub {MAX_IMAGE_KB} KB)")


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

    voice = data.get("voice", DEFAULT_VOICE)
    if voice not in ALLOWED_VOICES:
        errors.append(f"vocea '{voice}' nu este permisă ({', '.join(sorted(ALLOWED_VOICES))})")

    texts = [data.get("title", ""), data.get("summary", ""), data.get("moral", "")]
    check_image(folder, (data.get("cover") or {}).get("image"), "copertă", errors, warnings)

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
        check_image(folder, page.get("image"), label, errors, warnings)

    if any(CEDILLA.search(t) for t in texts):
        errors.append("folosește ș/ț cu virgulă, nu ş/ţ cu sedilă")
    return errors, warnings


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
    """Fișierele audio ale unei povești: (nume fișier, text de citit)."""
    items = [("coperta.mp3", f"Lio îți citește povestea: {data['title']}.")]
    for number, page in enumerate(data["pages"], start=1):
        items.append((f"pagina-{number:02d}.mp3", page["text"]))
    items.append(("final.mp3", f"Sfârșit. {data['moral']}"))
    return items


async def generate_story_audio(folder, data):
    import edge_tts

    voice = data.get("voice", DEFAULT_VOICE)
    audio_dir = folder / "audio"
    audio_dir.mkdir(exist_ok=True)
    manifest_file = audio_dir / "manifest.json"
    old = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    manifest = {}
    for name, text in narration_items(data):
        digest = hashlib.sha1(f"{voice}|{SPEECH_RATE}|{text}".encode()).hexdigest()
        target = audio_dir / name
        if old.get(name) != digest or not target.exists():
            print(f"    🔊 {folder.name}/audio/{name}")
            await edge_tts.Communicate(text, voice, rate=SPEECH_RATE).save(str(target))
        manifest[name] = digest
    for stale in set(old) - set(manifest):
        (audio_dir / stale).unlink(missing_ok=True)
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_audio():
    for folder, data in load_stories():
        errors, _ = validate_story(folder, data)
        if errors:
            print(f"[sărit] {folder.name} (nu trece validarea)")
            continue
        print(f"[audio] {folder.name}")
        asyncio.run(generate_story_audio(folder, data))
    return 0


def cmd_index():
    entries = []
    for folder, data in load_stories():
        errors, _ = validate_story(folder, data)
        if errors:
            print(f"[exclus din bibliotecă] {folder.name}")
            continue
        words = sum(word_count(p["text"]) for p in data["pages"])
        entries.append({
            "id": data["id"],
            "title": data["title"],
            "summary": data["summary"],
            "age": data.get("age", "3-7"),
            "tags": data.get("tags", []),
            "created": data["created"],
            "cover": f"stories/{data['id']}/{data['cover']['image']}",
            "pages": len(data["pages"]),
            "minutes": max(1, round(words / WORDS_PER_MINUTE)),
        })
    entries.sort(key=lambda e: (e["created"], e["title"]), reverse=True)
    INDEX_FILE.write_text(json.dumps({"stories": entries}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Bibliotecă actualizată: {len(entries)} povești.")
    return 0


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if command == "validate":
        return cmd_validate()
    if command == "audio":
        return cmd_audio()
    if command == "index":
        return cmd_index()
    if command == "all":
        result = cmd_validate()
        cmd_audio()
        cmd_index()
        return result
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
