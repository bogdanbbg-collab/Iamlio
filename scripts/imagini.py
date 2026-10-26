"""Generarea imaginilor care lipsesc (OpenAI), ca o poveste să se publice chiar dacă AI-ul care a scris-o
nu a putut face imagini.

Se activează doar dacă există secretul OPENAI_API_KEY. Opțional (variabile de repository):
  IMAGE_MODEL     modelul de imagine (implicit gpt-image-2)
  IMAGE_QUALITY   low | medium | high (implicit medium)
  MAX_IMAGES      câte imagini se pot genera într-o publicare (implicit 40)
  MAX_IMAGES_MONTH  câte imagini se pot genera într-o lună calendaristică (implicit 200)
  MAX_LEI_MONTH   cât se poate cheltui pe imagini într-o lună, în lei (implicit 100)
  Prețurile (verifică-le pe pagina de prețuri OpenAI pentru modelul ales): IMAGE_PRICE_TEXT_IN, IMAGE_PRICE_IMAGE_IN,
  IMAGE_PRICE_OUT (dolari pe 1 milion de tokeni; implicit 5, 10, 40), USD_LEI (cursul, implicit 4.6) și
  IMAGE_COST_LEI (estimarea pentru o imagine când răspunsul nu spune câți tokeni a folosit; implicit 0.5).

Costul fiecărei imagini se calculează din tokenii raportați de OpenAI în răspuns. Totalul lunii (imagini și lei)
stă în rapoarte/buget-imagini.json, iar raportul lunar în rapoarte/buget-imagini.md (salvate de robot).

Coperta se generează prima; paginile se generează pornind de la copertă ca imagine de referință,
ca personajele să arate la fel pe toate paginile.
"""

import base64
import os
from pathlib import Path

DEFAULT_MODEL = "gpt-image-2"
DEFAULT_QUALITY = "medium"
DEFAULT_MAX_IMAGES = 40
DEFAULT_MAX_IMAGES_MONTH = 200
DEFAULT_MAX_LEI_MONTH = 100
DEFAULT_IMAGE_COST_LEI = 0.5
SIZE = "1536x1024"
CONSISTENCY = ("Use the reference image ONLY to keep the characters identical (same faces, fur, colors, clothes, "
               "proportions) and the same art style. Draw a NEW scene: ")


def _number(name, default):
    try:
        return float(os.environ.get(name) or default)
    except ValueError:
        return float(default)


class Budget:
    """Cât se mai poate genera: imagini pe publicare, imagini pe lună și lei pe lună."""

    def __init__(self, path=None, images=None):
        from datetime import date

        self.path = Path(path) if path else None
        self.month = date.today().strftime("%Y-%m")
        self.history = self._load()
        current = self.history.get(self.month) or {}
        self.used_images = int(current.get("imagini", 0))
        self.used_lei = float(current.get("lei", 0))
        self.run_left = int(_number("MAX_IMAGES", DEFAULT_MAX_IMAGES)) if images is None else images
        self.month_images = int(_number("MAX_IMAGES_MONTH", DEFAULT_MAX_IMAGES_MONTH))
        self.month_lei = _number("MAX_LEI_MONTH", DEFAULT_MAX_LEI_MONTH)
        self.made = 0

    def _load(self):
        import json

        try:
            data = json.loads(self.path.read_text(encoding="utf-8")) if self.path else {}
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            return {}
        # formatul vechi: {"2026-10": 12} (doar numărul de imagini)
        return {month: value if isinstance(value, dict) else {"imagini": value, "lei": 0}
                for month, value in data.items() if isinstance(value, (dict, int))}

    def estimate(self):
        """Cât ar costa următoarea imagine: media de până acum în luna aceasta sau estimarea implicită."""
        if self.used_images and self.used_lei:
            return self.used_lei / self.used_images
        return _number("IMAGE_COST_LEI", DEFAULT_IMAGE_COST_LEI)

    def allows(self):
        return (self.made < self.run_left and self.used_images < self.month_images
                and self.used_lei + self.estimate() <= self.month_lei)

    def spend(self, lei):
        self.made += 1
        self.used_images += 1
        self.used_lei += lei

    def save(self):
        import json

        if not self.path or not self.made:
            return
        self.history[self.month] = {"imagini": self.used_images, "lei": round(self.used_lei, 2)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.history, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rows = "".join(f"| {month} | {v['imagini']} | {v['lei']:.2f} lei |\n" for month, v in sorted(self.history.items()))
        self.path.with_suffix(".md").write_text(
            "# Costul imaginilor generate automat\n\n"
            f"Limita lunară: {self.month_images} imagini și {self.month_lei:.0f} lei (variabilele MAX_IMAGES_MONTH și "
            "MAX_LEI_MONTH). Costul e calculat din tokenii raportați de OpenAI și prețurile din `scripts/imagini.py`; "
            "suma exactă facturată se vede în contul OpenAI.\n\n"
            "| Luna | Imagini | Cost estimat |\n| --- | --- | --- |\n" + rows, encoding="utf-8")


def cost_lei(result):
    """Costul unei imagini, în lei, din tokenii raportați în răspunsul OpenAI."""
    usage = getattr(result, "usage", None)
    if usage is None or getattr(usage, "output_tokens", None) is None:
        return _number("IMAGE_COST_LEI", DEFAULT_IMAGE_COST_LEI)
    details = getattr(usage, "input_tokens_details", None)
    text_in = getattr(details, "text_tokens", None)
    image_in = getattr(details, "image_tokens", None)
    if text_in is None or image_in is None:
        text_in, image_in = getattr(usage, "input_tokens", 0) or 0, 0
    dollars = (text_in * _number("IMAGE_PRICE_TEXT_IN", 5) + image_in * _number("IMAGE_PRICE_IMAGE_IN", 10)
               + usage.output_tokens * _number("IMAGE_PRICE_OUT", 40)) / 1_000_000
    return dollars * _number("USD_LEI", 4.6)


def enabled():
    return bool(os.environ.get("OPENAI_API_KEY"))


def make_client():
    from openai import OpenAI

    return OpenAI()


def safe_image(folder, rel):
    from pregatire import safe_image as check

    return check(folder, rel)


def missing(folder, data):
    """Lista (etichetă, intrare din story.json) pentru imaginile care nu există încă (doar căi sigure)."""
    entries = [("coperta", data.get("cover") or {})]
    entries += [(f"pagina {n}", p) for n, p in enumerate(data.get("pages") or [], start=1)]
    return [(label, entry) for label, entry in entries
            if safe_image(folder, entry.get("image")) is not None and not safe_image(folder, entry["image"]).is_file()]


def save(result, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(base64.b64decode(result.data[0].b64_json))


def generate_missing(folder, data, client=None, budget=None):
    """Generează imaginile lipsă. Întoarce (modificări, erori, câte imagini s-au generat)."""
    folder = Path(folder)
    todo = missing(folder, data)
    if not todo:
        return [], [], 0
    client = client or make_client()
    model = os.environ.get("IMAGE_MODEL") or DEFAULT_MODEL
    quality = os.environ.get("IMAGE_QUALITY") or DEFAULT_QUALITY
    if not isinstance(budget, Budget):
        budget = Budget(images=budget)
    changes, errors, made = [], [], 0
    cover_entry = data.get("cover") or {}

    for label, entry in todo:
        if not budget.allows():
            errors.append(f"{label}: limita de imagini sau de cost (pe publicare sau pe lună) a fost atinsă; restul "
                          "se generează la o publicare următoare sau luna viitoare (vezi rapoarte/buget-imagini.md)")
            break
        target = safe_image(folder, str(Path(entry["image"]).with_suffix(".png")))
        cover_file = safe_image(folder, cover_entry.get("image"))
        if target is None:
            continue
        try:
            if entry is not cover_entry and cover_file is not None and cover_file.is_file():
                with open(cover_file, "rb") as reference:
                    result = client.images.edit(model=model, image=[reference], prompt=CONSISTENCY + entry["imagePrompt"],
                                                size=SIZE, quality=quality)
            else:
                result = client.images.generate(model=model, prompt=entry["imagePrompt"], size=SIZE, quality=quality)
            save(result, target)
        except Exception as exc:  # cheie greșită, limită de cost, prompt refuzat de filtrul de siguranță…
            errors.append(f"{label}: imaginea nu a putut fi generată ({type(exc).__name__}: {str(exc)[:160]})")
            continue
        entry["image"] = str(Path(entry["image"]).with_suffix(".png"))
        budget.spend(cost_lei(result))
        made += 1
        changes.append(f"{label}: imaginea a fost generată automat ({model})")
    return changes, errors, made
