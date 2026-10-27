"""Mostre de voce cu Google Cloud Text-to-Speech (Chirp 3 HD), ca să alegem vocile după ureche.

Pornit de workflow-ul „Test voce” (cheia în GOOGLE_TTS_API_KEY). Generează în build/test-voce/:
- naratoare-<Voce>.mp3 / narator-<Voce>.mp3 — pagina 1 din „Lio și ceasul care a uitat ora”, citită de o singură voce;
- regie-pagina-NN.mp3 — paginile 1 și 4 cu regie: naratoare + câte o voce diferită pentru fiecare personaj;
- edge-pagina-NN.mp3 — aceleași pagini cu vocea de acum (edge-tts), pentru comparație.
"""

import asyncio
import base64
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import voce

API = "https://texttospeech.googleapis.com/v1"
STORY = ROOT / "public/stories/lio-si-ceasul-care-a-uitat-ora/story.json"
OUT = ROOT / "build/test-voce"
LANGUAGE = "ro-RO"
RATE = 0.92  # puțin mai rar decât normal, pentru copii

# voci candidate (descrierea Google între paranteze)
FEMALE = ["Sulafat", "Achernar", "Vindemiatrix", "Aoede", "Kore"]  # caldă, moale, blândă, aerisită, fermă
MALE = ["Achird", "Algieba", "Enceladus", "Charon"]  # prietenoasă, catifelată, șoptită, informativă
CAST = {"": "Sulafat", "Cucu": "Puck", "Bunicul Ceas": "Algenib"}  # naratoare, cuc vioi, bunic cu voce gravă


def call(path, body=None):
    key = os.environ["GOOGLE_TTS_API_KEY"]
    sep = "&" if "?" in path else "?"
    request = urllib.request.Request(f"{API}/{path}{sep}key={urllib.parse.quote(key)}",
                                     data=json.dumps(body).encode() if body else None,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:600]}") from None


def synthesize(text, voice, target):
    data = call("text:synthesize", {
        "input": {"text": text},
        "voice": {"languageCode": LANGUAGE, "name": f"{LANGUAGE}-Chirp3-HD-{voice}"},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": RATE},
    })
    target.write_bytes(base64.b64decode(data["audioContent"]))


def spoken(text):
    return text.lstrip("—– ").strip()


def directed(page, target, cast):
    """O pagină cu regie: fiecare replică cu vocea personajului, lipite cu pauzele din narration."""
    segments = voce.page_segments(page)
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for number, segment in enumerate(segments):
            part = Path(tmp) / f"{number:03d}.mp3"
            synthesize(spoken(segment.text), cast.get(segment.speaker, cast[""]), part)
            parts.append(part)
        voce.assemble(parts, [s.pause for s in segments], target)


def main():
    if not os.environ.get("GOOGLE_TTS_API_KEY"):
        sys.exit("Lipsește secretul GOOGLE_TTS_API_KEY.")
    OUT.mkdir(parents=True, exist_ok=True)
    story = json.loads(STORY.read_text(encoding="utf-8"))
    pages = story["pages"]
    characters = story.get("characters") or []

    available = sorted(v["name"].rsplit("-", 1)[-1] for v in call(f"voices?languageCode={LANGUAGE}")["voices"]
                       if "Chirp3-HD" in v["name"])
    print(f"Voci Chirp 3 HD în română ({len(available)}): {', '.join(available) or 'niciuna'}")
    if not available:
        sys.exit("Nu există voci Chirp 3 HD pentru română pe acest cont.")

    text = " ".join(spoken(item["text"]) for item in pages[0]["narration"])
    characters_used = 0
    results = []
    for label, voices in (("naratoare", FEMALE), ("narator", MALE)):
        for voice in voices:
            if voice not in available:
                results.append(f"- {label} {voice}: nu există în română")
                continue
            try:
                synthesize(text, voice, OUT / f"{label}-{voice}.mp3")
                characters_used += len(text)
                results.append(f"- {label} {voice}: OK")
            except RuntimeError as exc:
                results.append(f"- {label} {voice}: EȘUAT — {exc}")

    cast = {who: (voice if voice in available else available[0]) for who, voice in CAST.items()}
    roles = ", ".join(f"{who or 'naratoare'}={voice}" for who, voice in cast.items())
    for index in (0, 3):
        try:
            directed(pages[index], OUT / f"regie-pagina-{index + 1:02d}.mp3", cast)
            characters_used += sum(len(n["text"]) for n in pages[index]["narration"])
            results.append(f"- regie pagina {index + 1} ({roles}): OK")
        except RuntimeError as exc:
            results.append(f"- regie pagina {index + 1}: EȘUAT — {exc}")
        try:
            asyncio.run(voce.render(voce.page_segments(pages[index], characters), "feminin", characters,
                                    OUT / f"edge-pagina-{index + 1:02d}.mp3"))
        except Exception as exc:  # noqa: BLE001 — doar pentru comparație
            results.append(f"- edge pagina {index + 1}: EȘUAT — {exc}")

    print("\n".join(results))
    print(f"Caractere consumate: ~{characters_used} (din 1.000.000 gratuite pe lună)")
    if not any(OUT.glob("*.mp3")):
        sys.exit(1)


if __name__ == "__main__":
    main()
