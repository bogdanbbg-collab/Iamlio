"""Repararea automată a poveștilor înainte de publicare.

Orice AI ar fi scris povestea, aici se corectează automat tot ce e mecanic: diacritice și punctuație,
stilul imaginilor, Lio, descrierile personajelor din prompturi, regia de voce, vocile personajelor,
numele fișierelor. Ce ține de conținut (lipsă de umor, învățătură, autoevaluare) NU se inventează:
rămâne în raport, ca AI-ul să corecteze.
"""

import re
import shutil
from datetime import date
from pathlib import Path

import canon
import voce

CEDILLA = str.maketrans({"ş": "ș", "ţ": "ț", "Ş": "Ș", "Ţ": "Ț"})
RASTER = (".png", ".jpg", ".jpeg", ".webp")
IMAGE_PATH = re.compile(r"^images/[a-z0-9][a-z0-9-]*\.(?:webp|png|jpe?g)$")
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Profiluri de voce pentru personajele care vorbesc și nu au unul (fiecare altfel, ca să se deosebească).
VOICE_PALETTE = [{"pitch": 16, "rate": 2}, {"pitch": -8, "rate": -6}, {"pitch": 8, "rate": 4},
                 {"pitch": -14, "rate": -8}, {"pitch": 22, "rate": 6}, {"pitch": -4, "rate": 0}]


def plain(text):
    return voce.plain(text)


def safe_image(folder, rel):
    """Calea absolută a unei imagini DOAR dacă are forma images/nume.ext și stă în folderul poveștii; altfel None.
    Orice operație care citește, scrie, convertește sau șterge imagini trece întâi pe aici."""
    if not isinstance(rel, str) or not IMAGE_PATH.match(rel):
        return None
    root = Path(folder).resolve()
    path = (root / rel).resolve()
    return path if path.is_relative_to(root / "images") else None


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", plain(text)).strip("-")


def normalize_text(text):
    """ș/ț cu virgulă, „…”, linie de dialog, ghilimele românești, spații."""
    if not isinstance(text, str):
        return text
    text = text.translate(CEDILLA).replace("...", "…")
    text = re.sub(r"(^|[.!?…]\s+)[-–]\s*(?=\S)", lambda m: m.group(1) + "— ", text)
    text = re.sub(r'"([^"]+)"', r"„\1”", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def mentioned(name, text):
    return bool(name) and re.search(rf"\b{re.escape(plain(name))}\w*", plain(text or "")) is not None


class Preparer:
    def __init__(self, folder, data):
        self.folder = folder
        self.data = data
        self.changes = []

    def note(self, message):
        if message not in self.changes:
            self.changes.append(message)

    def run(self):
        self.fields()
        self.text()
        self.characters()
        self.images()
        self.narration()
        self.voices()
        self.remove_empty_folders()
        return self.data, self.changes

    def remove_empty_folders(self):
        for directory in sorted(self.folder.rglob("*"), reverse=True):
            if directory.is_dir() and directory.name not in ("images", "audio") and not any(directory.iterdir()):
                directory.rmdir()

    # ---------- câmpuri simple ----------

    def fields(self):
        d = self.data
        if d.get("id") != self.folder.name and ID_PATTERN.match(self.folder.name):
            d["id"] = self.folder.name
            self.note("id-ul a fost potrivit cu numele folderului")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(d.get("created") or "")):
            d["created"] = date.today().isoformat()
            self.note("data creării a fost completată")
        age = str(d.get("age") or "")
        digits = re.findall(r"\d", age)
        normalized = f"{digits[0]}-{digits[1]}" if len(digits) >= 2 else "3-7"
        if normalized not in ("3-5", "5-7", "3-7"):
            normalized = "3-7"
        if age != normalized:
            d["age"] = normalized
            self.note(f"vârsta a fost normalizată la {normalized}")
        if isinstance(d.get("learning"), str):
            d["learning"] = [d["learning"]]
            self.note("learning a fost transformat în listă")
        if not isinstance(d.get("tags"), list):
            d["tags"] = []
        if d.get("illustrationStyle") != canon.STYLE:
            d["illustrationStyle"] = canon.STYLE
            self.note("stilul imaginilor a fost setat la stilul oficial Iamlio")

    def text(self):
        d = self.data
        before = repr(d)
        for key in ("title", "summary", "moral"):
            d[key] = normalize_text(d.get(key))
        if isinstance(d.get("learning"), list):
            d["learning"] = [normalize_text(x) for x in d["learning"]]
        for page in d.get("pages") or []:
            page["text"] = normalize_text(page.get("text") or "")
            for item in page.get("narration") or []:
                if isinstance(item, dict):
                    item["text"] = normalize_text(item.get("text") or "")
        if repr(d) != before:
            self.note("textul a fost curățat (ș/ț cu virgulă, „…”, linie de dialog, ghilimele, spații)")

    # ---------- personaje ----------

    def characters(self):
        for character in self.data.get("characters") or []:
            if character.get("name") == "Lio":
                if character.get("description") != canon.LIO_DESCRIPTION or character.get("voice") != canon.LIO_VOICE:
                    character["description"] = canon.LIO_DESCRIPTION
                    character["voice"] = dict(canon.LIO_VOICE)
                    self.note("Lio a primit descrierea și vocea oficială")

    def present(self, text):
        return [c for c in self.data.get("characters") or [] if c.get("description") and mentioned(c.get("name"), text)]

    # ---------- imagini ----------

    def images(self):
        d = self.data
        cover = d.setdefault("cover", {})
        cover["image"] = self.resolve_image(cover.get("image"), "coperta", ["coperta", "copertă", "cover", "coperta-1"])
        story_text = " ".join(p.get("text") or "" for p in d.get("pages") or [])
        cover["imagePrompt"] = self.fix_prompt(cover.get("imagePrompt"), story_text[:600], cover=True)
        for number, page in enumerate(d.get("pages") or [], start=1):
            aliases = [f"pagina-{number:02d}", f"pagina-{number}", f"pagina{number}", f"page-{number}", f"page{number}",
                       f"{number:02d}", f"{number}", f"p{number}", f"imagine-{number}", f"imagine{number}"]
            page["image"] = self.resolve_image(page.get("image"), f"pagina-{number:02d}", aliases)
            page["imagePrompt"] = self.fix_prompt(page.get("imagePrompt"), page.get("text") or "")

    def resolve_image(self, rel, name, aliases):
        """Găsește imaginea (oricum ar fi fost numită) și o mută în images/<nume oficial>."""
        folder = self.folder
        if rel and IMAGE_PATH.match(rel) and (folder / rel).is_file():
            return rel
        candidates = []
        if rel:
            candidate = (folder / rel).resolve()
            if candidate.is_file() and candidate.is_relative_to(folder.resolve()):
                candidates.append(candidate)
        for directory in (folder / "images", folder):
            if directory.is_dir():
                for file in sorted(directory.iterdir()):
                    if file.suffix.lower() in RASTER and slugify(file.stem) in aliases:
                        candidates.append(file)
        for file in candidates:
            if file.suffix.lower() not in RASTER:
                continue
            ext = ".jpg" if file.suffix.lower() == ".jpeg" else file.suffix.lower()
            target = folder / "images" / f"{name}{ext}"
            target.parent.mkdir(exist_ok=True)
            if file != target:
                shutil.move(str(file), target)
                self.note(f"imaginea {file.name} a fost mutată în images/{target.name}")
            return f"images/{target.name}"
        return f"images/{name}.png"  # lipsește: o generează imagini.py sau o raportează validarea

    def fix_prompt(self, prompt, scene_text, cover=False):
        """Promptul conține mereu stilul oficial și descrierea completă a fiecărui personaj din scenă."""
        prompt = normalize_text(prompt or "")
        changed = False
        if len(prompt) < 60:
            what = "the cover of this story, showing its main characters and its world" if cover else "exactly this moment"
            prompt = f"Scene, show {what} (story text in Romanian): {scene_text}"
            changed = True
            self.note("prompturi de imagine lipsă au fost create din textul paginii")
        if canon.STYLE not in prompt:
            prompt = f"{canon.STYLE} {prompt.replace(canon.STYLE, '').strip()}"
            changed = True
        missing = [c for c in self.data.get("characters") or []
                   if c.get("description") and c["description"] not in prompt
                   and (mentioned(c.get("name"), prompt) or mentioned(c.get("name"), scene_text))]
        if missing:
            people = "; ".join(f"{c['name']}: {c['description']}" for c in missing)
            prompt = f"{prompt} Characters in this scene (draw them exactly like this): {people}."
            changed = True
        if changed:
            self.note("prompturile de imagine au primit stilul oficial și descrierile complete ale personajelor")
        return prompt

    # ---------- voce ----------

    def narration(self):
        characters = self.data.get("characters") or []
        for number, page in enumerate(self.data.get("pages") or [], start=1):
            narration = page.get("narration")
            if narration and self.matches(narration, page.get("text") or ""):
                continue
            segments = voce.auto_segments(page.get("text") or "", characters)
            page["narration"] = [
                {k: v for k, v in (("text", s.text), ("mood", s.mood), ("speaker", s.speaker),
                                   ("pause", s.pause if s.pause != voce.PAUSE_DEFAULT else None)) if v}
                for s in segments
            ]
            reason = "lipsea" if not narration else "nu corespundea cu textul"
            self.note(f"pagina {number}: regia de voce {reason} și a fost generată automat")

    @staticmethod
    def matches(narration, text):
        if not isinstance(narration, list) or not all(isinstance(i, dict) and i.get("text") for i in narration):
            return False
        words = lambda t: re.findall(r"\w+", plain(t))  # noqa: E731
        return words(" ".join(i["text"] for i in narration)) == words(text)

    def voices(self):
        characters = self.data.get("characters") or []
        speakers = []
        for page in self.data.get("pages") or []:
            for item in page.get("narration") or []:
                if isinstance(item, dict) and item.get("speaker") and item["speaker"] not in speakers:
                    speakers.append(item["speaker"])
        palette = iter(VOICE_PALETTE * 3)
        for character in characters:
            if character.get("name") in speakers and not character.get("voice"):
                character["voice"] = dict(next(palette))
                self.note(f"{character['name']} a primit automat un profil de voce")


def prepare(folder, data):
    """Întoarce (date reparate, listă de modificări)."""
    return Preparer(Path(folder), data).run()


def rename_folder(folder, data):
    """Dacă numele folderului nu e un id valid, îl redenumește după titlu. Întoarce noul folder."""
    if ID_PATTERN.match(folder.name):
        return folder
    new_id = slugify(data.get("title") or folder.name) or "poveste"
    target = folder.with_name(new_id)
    suffix = 2
    while target.exists():
        target = folder.with_name(f"{new_id}-{suffix}")
        suffix += 1
    shutil.move(str(folder), target)
    data["id"] = target.name
    return target
