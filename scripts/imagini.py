"""Generarea imaginilor care lipsesc, ca o poveste să se publice chiar dacă AI-ul care a scris-o nu a putut
face imagini. Se încearcă, în ordine, variantele configurate; dacă una refuză (de ex. cota gratuită e 0 sau
s-a terminat), imaginea se face cu următoarea:

0. Google Gemini („Nano Banana”) — secretul GEMINI_API_KEY (din aistudio.google.com). Gratuit cât timp proiectul
   Google rămâne pe „Free tier” (fără cont de plată legat), dacă Google oferă imagini pe nivelul gratuit.
   Pornește de la imaginea copertei, ca personajele să fie identice. Opțional: GEMINI_IMAGE_MODEL.
1. Pollinations — GRATUIT, prima variantă (imaginile ies cele mai frumoase): secretul POLLINATIONS_API_KEY
   (cheia secretă „sk_…” din enter.pollinations.ai, cont gratuit). Opțional, variabila POLLINATIONS_IMAGE_MODEL
   (implicit Z-Image Turbo). Ca la Cloudflare: fără imaginea copertei ca referință, aceeași „sămânță” pe poveste.
2. Cloudflare Workers AI — GRATUIT, rezerva (cota zilnică a planului gratuit, fără card): secretele CLOUDFLARE_ACCOUNT_ID
   și CLOUDFLARE_API_TOKEN. Opțional, variabila CLOUDFLARE_IMAGE_MODEL (implicit FLUX.1 schnell). Imaginile nu
   pornesc de la copertă ca referință (modelul nu poate), dar fiecare prompt are descrierea completă a
   personajelor (și, la modelele care o acceptă, aceeași „sămânță” pentru toată povestea), ca să semene
   între ele. Pe planul gratuit nu se plătește nimic: când cota zilei se termină, restul imaginilor se
   generează la publicarea de a doua zi.
3. OpenAI (cu plată) — secretul OPENAI_API_KEY. Opțional (variabile de repository):
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
import re
from pathlib import Path

import canon

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
    """Costul unei imagini, în lei, din tokenii raportați în răspunsul OpenAI (0 pentru varianta gratuită)."""
    if getattr(result, "free", False):
        return 0.0
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


def providers():
    """Variantele configurate, în ordinea în care se încearcă: gemini, pollinations, cloudflare (gratuite), openai."""
    found = []
    if os.environ.get("GEMINI_API_KEY"):
        found.append("gemini")
    # Pollinations înaintea Cloudflare: imaginile ies mai frumoase și personajele mai asemănătoare între pagini
    if os.environ.get("POLLINATIONS_API_KEY"):
        found.append("pollinations")
    if os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN"):
        found.append("cloudflare")
    if os.environ.get("OPENAI_API_KEY"):
        found.append("openai")
    return found


def provider():
    """Prima variantă configurată sau "" (generarea automată nu e activată)."""
    found = providers()
    return found[0] if found else ""


def enabled():
    return bool(providers())


def single_client(name, story_id="", characters=()):
    if name == "gemini":
        return GeminiClient(os.environ["GEMINI_API_KEY"], os.environ.get("GEMINI_IMAGE_MODEL") or GEMINI_MODEL)
    if name == "cloudflare":
        return CloudflareClient(os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"],
                                os.environ.get("CLOUDFLARE_IMAGE_MODEL") or CLOUDFLARE_MODEL, story_id,
                                characters=characters)
    if name == "pollinations":
        return PollinationsClient(os.environ["POLLINATIONS_API_KEY"],
                                  os.environ.get("POLLINATIONS_IMAGE_MODEL") or POLLINATIONS_MODEL, story_id,
                                  characters=characters)
    from openai import OpenAI

    client = OpenAI()
    client.model = os.environ.get("IMAGE_MODEL") or DEFAULT_MODEL
    return client


def make_client(story_id="", characters=()):
    clients = [single_client(name, story_id, characters) for name in providers()]
    return clients[0] if len(clients) == 1 else ChainClient(clients)


class ChainClient:
    """Încearcă variantele pe rând; una care a dat eroare nu se mai încearcă în aceeași publicare."""

    def __init__(self, clients):
        self.clients = list(clients)
        self.model = getattr(self.clients[0], "model", "")
        self.images = self
        self.problems = []  # motivele rămân și pentru imaginile următoare, după ce variantele au fost scoase

    def _call(self, method, kwargs):
        problems = self.problems
        for client in list(self.clients):
            reference = kwargs.get("image")
            for handle in reference or []:
                handle.seek(0)  # fiecare variantă citește imaginea de referință de la început
            try:
                result = getattr(client.images, method)(**dict(kwargs, model=getattr(client, "model", kwargs.get("model"))))
            except Exception as exc:
                problems.append(f"{getattr(client, 'model', '?')}: {str(exc)[:200]}")
                self.clients.remove(client)
                continue
            self.model = getattr(client, "model", self.model)
            return result
        raise RuntimeError("nicio variantă nu a mers — " + " | ".join(problems))

    def generate(self, **kwargs):
        return self._call("generate", kwargs)

    def edit(self, **kwargs):
        return self._call("edit", kwargs)


# ---------- Google Gemini („Nano Banana”) ----------

GEMINI_MODEL = "gemini-2.5-flash-image"


class GeminiImages:
    def __init__(self, client):
        self.client = client

    def generate(self, prompt, **_):
        return self.client.run(prompt)

    def edit(self, prompt, image=None, **_):
        return self.client.run(prompt, image[0] if image else None)


class GeminiClient:
    def __init__(self, key, model, opener=None):
        self.key, self.model, self.opener = key, model, opener
        self.images = GeminiImages(self)

    def run(self, prompt, reference=None):
        import json
        import urllib.request

        parts = [{"text": prompt}]
        if reference is not None:
            name = str(getattr(reference, "name", ""))
            mime = "image/webp" if name.endswith(".webp") else "image/jpeg" if name.endswith((".jpg", ".jpeg")) else "image/png"
            parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(reference.read()).decode()}})
        body = {"contents": [{"parts": parts}],
                "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "3:2"}}}
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"x-goog-api-key": self.key, "Content-Type": "application/json"})
        opener = self.opener or urllib.request.urlopen
        try:
            with opener(request, timeout=180) as response:
                answer = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            detail = exc.read().decode("utf-8", "replace") if hasattr(exc, "read") else str(exc)
            try:
                detail = json.loads(detail)["error"]["message"]
            except (ValueError, KeyError, TypeError):
                pass
            raise RuntimeError(f"Gemini: {str(detail)[:300]}") from exc
        for candidate in answer.get("candidates") or []:
            for part in (candidate.get("content") or {}).get("parts") or []:
                data = (part.get("inlineData") or part.get("inline_data") or {}).get("data")
                if data:
                    result = _as_page_image(base64.b64decode(data))
                    result.free = _number("GEMINI_COST_LEI", 0) == 0
                    return result
        reason = (answer.get("promptFeedback") or {}).get("blockReason") or str(answer)[:300]
        raise RuntimeError(f"Gemini: nu a trimis nicio imagine ({reason})")


# ---------- Cloudflare Workers AI (gratuit) ----------

CLOUDFLARE_MODEL = "@cf/black-forest-labs/flux-1-schnell"
CLOUDFLARE_MAX_PROMPT = 2048
WIDE = ("Wide horizontal 3:2 composition: keep every character and the main action in the middle of the frame, "
        "with some empty background at the top and bottom.")
# FLUX citește doar începutul promptului (aproximativ 250 de cuvinte), așa că scena merge prima, apoi un stil scurt,
# iar descrierile personajelor la urmă; altfel toate imaginile ieșeau portrete, fără ce se întâmplă pe pagină.
SHORT_STYLE = ("3D animated feature film still for young children, cute expressive characters with big eyes, "
               "soft warm cinematic lighting, rich gentle colors, nothing scary, no text, no letters. Show the whole "
               "scene and the setting, characters with their full bodies, not a close-up portrait. Only the characters "
               "named here, no other animals or people.")
_LABEL = re.compile(r"Characters in this scene[^:]*:", re.I)


def scene_first(prompt, characters=()):
    """Promptul rearanjat pentru FLUX: scena (ce se întâmplă), stilul scurt, apoi descrierile personajelor."""
    body = prompt.replace(canon.STYLE, " ")
    people, present = [], []
    for c in characters or ():
        name, description = (c.get("name") or "").strip(), (c.get("description") or "").strip().rstrip(".")
        if not description or description not in body:
            continue
        people.append(f"{name}: {description}" if name else description)
        present.append((name, description))
        body = body.replace(f"{name}: {description}", " ").replace(description, " ") if name else body.replace(description, " ")
    body = _LABEL.sub(" ", body)
    scene = " ".join(re.sub(r"(?:\s*[;.,]\s*){2,}", ". ", " " + body).split()).lstrip(".;, ").strip()
    for name, description in present:
        if name:
            # ce fel de personaj e, chiar lângă nume: descrierile complete de la final pot fi tăiate de model
            short = re.split(r",| with ", description, maxsplit=1)[0].strip()
            scene = re.sub(rf"\b{re.escape(name)}\b", f"{name} ({short})", scene, count=1)
    parts = [scene, SHORT_STYLE, WIDE]
    if people:
        parts.append("Characters: " + "; ".join(people) + ".")
    return " ".join(p for p in parts if p)[:CLOUDFLARE_MAX_PROMPT]


class CloudflareImages:
    """images.generate / images.edit, ca la OpenAI, ca restul codului să nu știe ce serviciu folosește."""

    def __init__(self, client):
        self.client = client

    def generate(self, prompt, **_):
        return self.client.run(prompt)

    def edit(self, prompt, **_):
        # Modelul nu primește imaginea de referință: personajele vin din descrierile complete din prompt.
        return self.client.run(prompt[len(CONSISTENCY):] if prompt.startswith(CONSISTENCY) else prompt)


class CloudflareClient:
    def __init__(self, account, token, model, story_id="", opener=None, characters=()):
        import zlib

        self.account, self.token, self.model = account, token, model
        self.characters = list(characters or ())
        self.seed = zlib.crc32(story_id.encode("utf-8")) % 2_000_000_000  # aceeași pentru toată povestea
        self.images = CloudflareImages(self)
        self.opener = opener

    def run(self, prompt):
        import json
        import urllib.request

        prompt = scene_first(prompt, self.characters)
        body = {"prompt": prompt}
        if "flux-1-schnell" in self.model:
            body["steps"] = 8  # maximul modelului: cea mai bună calitate (modelul nu primește alți parametri)
        else:
            body.update(width=1536, height=1024, seed=self.seed)
        request = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/accounts/{self.account}/ai/run/{self.model}",
            data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            kind, payload = _send(self.opener or urllib.request.urlopen, request)
        except Exception as exc:
            detail = exc.read().decode("utf-8", "replace")[:300] if hasattr(exc, "read") else str(exc)
            raise RuntimeError(f"Cloudflare: {detail}") from exc
        if kind.startswith("image/"):
            raw = payload
        else:
            answer = json.loads(payload.decode("utf-8"))
            image = (answer.get("result") or {}).get("image") if answer.get("success", True) else None
            if not image:
                raise RuntimeError(f"Cloudflare: {str(answer.get('errors') or answer)[:300]}")
            raw = base64.b64decode(image)
        return _as_page_image(raw)


# ---------- Pollinations (rezerva gratuită, după Cloudflare) ----------

POLLINATIONS_MODEL = "tongyi-mai/z-image-turbo"


class PollinationsClient:
    """Pollinations (gen.pollinations.ai), cu cheia gratuită de la enter.pollinations.ai. Ca la Cloudflare, nu
    primește imaginea copertei: scena merge prima în prompt, apoi descrierile personajelor."""

    def __init__(self, key, model, story_id="", opener=None, characters=()):
        import zlib

        self.key, self.model = key, model
        self.characters = list(characters or ())
        self.seed = zlib.crc32(story_id.encode("utf-8")) % 2_000_000_000  # aceeași pentru toată povestea
        self.images = CloudflareImages(self)
        self.opener = opener

    def run(self, prompt):
        import json
        import urllib.request

        body = {"model": self.model, "prompt": scene_first(prompt, self.characters), "size": "1536x1024",
                "seed": self.seed, "response_format": "b64_json"}
        request = urllib.request.Request(
            "https://gen.pollinations.ai/v1/images/generations", data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        try:
            answer = json.loads(_send(self.opener or urllib.request.urlopen, request)[1].decode("utf-8"))
        except Exception as exc:  # 402: s-a terminat creditul gratuit al zilei
            detail = exc.read().decode("utf-8", "replace")[:300] if hasattr(exc, "read") else str(exc)
            raise RuntimeError(f"Pollinations: {detail}") from exc
        image = ((answer.get("data") or [{}])[0] or {}).get("b64_json")
        if not image:
            raise RuntimeError(f"Pollinations: {str(answer)[:300]}")
        return _as_page_image(base64.b64decode(image))


# O pană de câteva secunde a unui serviciu gratuit (503, prea multe cereri, rețea) nu trebuie să lase povestea fără
# imagini: cererea se mai încearcă de două ori, cu pauză. Alte erori (cheie greșită, credit terminat) nu se reîncearcă.
RETRY_STATUS = (429, 500, 502, 503, 504)
RETRY_WAITS = (5, 20)


def _sleep(seconds):
    import time

    time.sleep(seconds)


def _send(opener, request):
    """Întoarce (Content-Type, conținut) al răspunsului, cu reîncercări la penele temporare."""
    import urllib.error

    for wait in RETRY_WAITS + (None,):
        try:
            with opener(request, timeout=180) as response:
                headers = getattr(response, "headers", None) or {}
                return headers.get("Content-Type", ""), response.read()
        except urllib.error.HTTPError as exc:
            if wait is None or exc.code not in RETRY_STATUS:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if wait is None:
                raise
        _sleep(wait)


def _as_page_image(raw):
    """Orice imagine primită devine PNG 1536×1024 (3:2), tăiată din centru dacă are alt format."""
    import io
    from types import SimpleNamespace

    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(raw)) as image:
        page = ImageOps.fit(image.convert("RGB"), (1536, 1024), Image.LANCZOS, centering=(0.5, 0.5))
    buffer = io.BytesIO()
    page.save(buffer, "PNG")
    return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(buffer.getvalue()).decode())], free=True)


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
    client = client or make_client(folder.name, data.get("characters"))
    model = getattr(client, "model", None) or os.environ.get("IMAGE_MODEL") or DEFAULT_MODEL
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
            errors.append(f"{label}: imaginea nu a putut fi generată ({type(exc).__name__}: {str(exc)[:800]})")
            continue
        entry["image"] = str(Path(entry["image"]).with_suffix(".png"))
        budget.spend(cost_lei(result))
        made += 1
        changes.append(f"{label}: imaginea a fost generată automat ({getattr(client, 'model', None) or model})")
    return changes, errors, made


# ---------- test: care variantă merge? ----------

def test_providers(out_dir):
    """Generează câte o imagine de probă cu fiecare variantă configurată, separat. Întoarce [(variantă, mesaj, ok)]."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = f"{canon.STYLE} Lio, a little lion cub, waves hello in a sunny meadow. {canon.LIO_DESCRIPTION}"
    results = []
    for name in providers():
        try:
            client = single_client(name, "test")
            kwargs = {"prompt": prompt, "model": getattr(client, "model", None), "size": SIZE, "quality": DEFAULT_QUALITY}
            result = client.images.generate(**kwargs)
            save(result, out_dir / f"{name}.png")
            results.append((name, f"merge ({getattr(client, 'model', '')}); imaginea: {name}.png", True))
        except Exception as exc:
            results.append((name, f"nu merge: {str(exc)[:400]}", False))
    return results


def main(argv):
    import sys

    if argv[1:2] != ["test"]:
        print("Folosire: python3 scripts/imagini.py test")
        return 2
    results = test_providers(Path(__file__).resolve().parent.parent / "build" / "test-imagini")
    if not results:
        print("Nicio variantă configurată: adaugă GEMINI_API_KEY, CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN "
              "sau OPENAI_API_KEY ca secrete în GitHub.")
        return 1
    lines = ["## Test generare imagini", "", "| Variantă | Rezultat |", "| --- | --- |"]
    lines += [f"| {'✅' if ok else '❌'} {name} | {message} |" for name, message, ok in results]
    print("\n".join(lines))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    return 0 if any(ok for _, _, ok in results) else 1


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main(sys.argv))
