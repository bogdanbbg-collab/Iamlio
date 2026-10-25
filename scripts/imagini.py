"""Generarea imaginilor care lipsesc (OpenAI), ca o poveste să se publice chiar dacă AI-ul care a scris-o
nu a putut face imagini.

Se activează doar dacă există secretul OPENAI_API_KEY. Opțional (variabile de repository):
  IMAGE_MODEL     modelul de imagine (implicit gpt-image-2)
  IMAGE_QUALITY   low | medium | high (implicit medium)
  MAX_IMAGES      câte imagini se pot genera într-o publicare (implicit 40, ca protecție la costuri)

Coperta se generează prima; paginile se generează pornind de la copertă ca imagine de referință,
ca personajele să arate la fel pe toate paginile.
"""

import base64
import os
from pathlib import Path

DEFAULT_MODEL = "gpt-image-2"
DEFAULT_QUALITY = "medium"
DEFAULT_MAX_IMAGES = 40
SIZE = "1536x1024"
CONSISTENCY = ("Use the reference image ONLY to keep the characters identical (same faces, fur, colors, clothes, "
               "proportions) and the same art style. Draw a NEW scene: ")


def enabled():
    return bool(os.environ.get("OPENAI_API_KEY"))


def make_client():
    from openai import OpenAI

    return OpenAI()


def missing(folder, data):
    """Lista (etichetă, intrare din story.json) pentru imaginile care nu există încă."""
    entries = [("coperta", data.get("cover") or {})]
    entries += [(f"pagina {n}", p) for n, p in enumerate(data.get("pages") or [], start=1)]
    return [(label, entry) for label, entry in entries
            if entry.get("image") and not (Path(folder) / entry["image"]).is_file()]


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
    budget = int(os.environ.get("MAX_IMAGES") or DEFAULT_MAX_IMAGES) if budget is None else budget
    changes, errors, made = [], [], 0
    cover_entry = data.get("cover") or {}

    for label, entry in todo:
        if made >= budget:
            errors.append(f"{label}: limita de {budget} imagini pe publicare a fost atinsă; restul se generează data viitoare")
            break
        target = folder / Path(entry["image"]).with_suffix(".png")
        cover_file = folder / cover_entry.get("image", "")
        try:
            if entry is not cover_entry and cover_file.is_file():
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
        made += 1
        changes.append(f"{label}: imaginea a fost generată automat ({model})")
    return changes, errors, made
