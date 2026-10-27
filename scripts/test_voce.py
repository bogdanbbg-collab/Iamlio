"""Mostre de voce, ca să alegem după ureche (workflow-ul „Test voce”). Generează în build/test-voce/,
pentru paginile 1 și 7 din „Matei și limonada fermecată”:

- chirp-ritm-pNN.mp3 — Google Chirp 3 HD ca pe site, dar cu liniștea tăiată de la capetele fiecărei replici
  (pauzele sunt exact cele din regie) și 0,6 s de liniște la început (pentru telefoane și căști Bluetooth);
- gemini-povestitor-pNN-<voce>.mp3 — Gemini TTS: toată pagina dintr-o dată, cu indicații de interpretare
  (povestitor de audiobook pentru copii, care face și vocile personajelor);
- gemini-replici-pNN.mp3 — Gemini TTS: fiecare replică cu emoția ei și cu vocea personajului.

Cheile: GOOGLE_TTS_API_KEY (Chirp) și GEMINI_API_KEY (Gemini, cota gratuită din Google AI Studio).
"""

import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import voce

STORY = ROOT / "public/stories/matei-si-limonada-fermecata/story.json"
OUT = ROOT / "build/test-voce"
PAGES = (1, 7)
LEAD_IN = 0.6
GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_WAITS = (20, 40, 60)  # cota gratuită are puține cereri pe minut

MOOD_EN = {
    "calm": "in a calm, warm storytelling voice",
    "vesel": "cheerfully, with a smile in your voice",
    "entuziasmat": "very excited and joyful",
    "mirat": "surprised and curious",
    "trist": "sadly, a little disappointed",
    "șoptit": "in a soft whisper, like telling a secret",
    "misterios": "mysteriously, with suspense",
    "somnoros": "sleepily and very softly",
    "speriat": "a little scared",
    "hotărât": "firmly and determined",
}


def gemini(model, text, voices, key):
    """O cerere Gemini TTS; voices = {vorbitor: voce} (2 = dialog cu două voci) sau o singură voce."""
    if len(voices) == 1:
        speech = {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": next(iter(voices.values()))}}}
    else:
        speech = {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
            {"speaker": who, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v}}} for who, v in voices.items()]}}
    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": speech}}
    request = urllib.request.Request(f"{GEMINI_API}/models/{model}:generateContent", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "X-Goog-Api-Key": key})
    for wait in (*GEMINI_WAITS, None):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.load(response)
            part = data["candidates"][0]["content"]["parts"][0]["inlineData"]
            return base64.b64decode(part["data"]), part.get("mimeType", "")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            if exc.code not in (429, 500, 503) or wait is None:
                raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from None
        time.sleep(wait)
    raise RuntimeError("Gemini nu răspunde")


def pcm_to_file(pcm, mime, target):
    rate = "24000"
    if "rate=" in mime:
        rate = mime.split("rate=")[1].split(";")[0]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", rate, "-ac", "1", "-i", "pipe:0",
                    "-ar", str(voce.SAMPLE_RATE), str(target)], input=pcm, check=True)


def tts_models(key):
    request = urllib.request.Request(f"{GEMINI_API}/models?pageSize=200", headers={"X-Goog-Api-Key": key})
    with urllib.request.urlopen(request, timeout=30) as response:
        names = [m["name"].split("/")[-1] for m in json.load(response).get("models", [])]
    tts = sorted((n for n in names if "tts" in n), reverse=True)
    # cel mai nou „flash” întâi (cota gratuită e de obicei la flash)
    return sorted(tts, key=lambda n: ("flash" not in n, n.count("preview")))


def describe(characters):
    return "; ".join(f"{c['name']}: {c.get('description', '').split(',')[0]}" for c in characters if c.get("name") != "Lio")


def storyteller_prompt(page, characters, variant):
    text = page["text"]
    if variant == "scurt":
        return ("Read aloud in Romanian, like a warm, very expressive storyteller reading a picture book to a "
                "four-year-old, with real emotions and a slightly different voice for each character: " + text)
    # formatul recomandat de Google pentru indicații lungi: notele regizorului separat de textul de citit
    return ("# AUDIO PROFILE: a warm, wonderfully expressive children's storyteller\n"
            "## THE SCENE: reading a picture book aloud, in Romanian, to a four-year-old child at bedtime\n"
            "### DIRECTOR'S NOTES\n"
            "Lively, natural intonation and real emotions: joy, surprise, suspense, tenderness. A smile in the "
            "voice on happy moments, small pauses before surprises, laughter where the characters laugh. A slightly "
            f"different voice for each character ({describe(characters)}). Read only the transcript, word for word.\n"
            "#### TRANSCRIPT\n" + text)


def line_prompt(segment, characters):
    who = next((c for c in characters if c.get("name") == segment.speaker), None)
    role = f", as {who.get('description', '').split(',')[0]}" if who else ""
    return f"Say {MOOD_EN.get(segment.mood, MOOD_EN['calm'])}{role}: {segment.text.lstrip('—– ').strip()}"


async def gemini_lines(model, key, page, characters, target):
    """Fiecare replică separat, cu emoția ei și vocea personajului (vocile Chirp au aceleași nume în Gemini)."""
    cast = voce.chirp_cast("feminin", characters)
    segments = voce.page_segments(page, characters)
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for number, segment in enumerate(segments):
            name = cast.get(segment.speaker) if segment.speaker else voce.CHIRP_NARRATOR["feminin"]
            pcm, mime = await asyncio.to_thread(gemini, model, line_prompt(segment, characters), {"x": name}, key)
            raw = Path(tmp) / f"{number:03d}.wav"
            pcm_to_file(pcm, mime, raw)
            trimmed = Path(tmp) / f"{number:03d}-t.wav"
            voce.trim_silence(raw, trimmed)
            parts.append(trimmed)
        voce.assemble(parts, [s.pause for s in segments], target, LEAD_IN)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    story = json.loads(STORY.read_text(encoding="utf-8"))
    characters = story.get("characters") or []
    results = []

    chirp_key = os.environ.get("GOOGLE_TTS_API_KEY")
    if chirp_key:
        chirp = voce.Chirp(chirp_key, voce.ChirpBudget())
        for number in PAGES:
            page = story["pages"][number - 1]
            try:
                asyncio.run(voce.render(voce.page_segments(page, characters), "feminin", characters,
                                        OUT / f"chirp-ritm-p{number:02d}.mp3", synth=chirp.synthesize,
                                        engine="chirp", trim=True, lead_in=LEAD_IN))
                results.append(f"- chirp-ritm p{number}: OK")
            except Exception as exc:  # noqa: BLE001 — o mostră eșuată nu le oprește pe celelalte
                results.append(f"- chirp-ritm p{number}: EȘUAT — {exc}")

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            models = tts_models(gemini_key)
        except (OSError, ValueError) as exc:
            models = []
            results.append(f"- lista modelelor Gemini: EȘUAT — {exc}")
        print(f"Modele Gemini TTS: {', '.join(models) or 'niciunul'}")
        jobs = [("gemini-povestitor-p07-feminin.mp3", "regie", 7, "feminin"),
                ("gemini-povestitor-scurt-p07-feminin.mp3", "scurt", 7, "feminin"),
                ("gemini-replici-p07.mp3", "replici", 7, "feminin"),
                ("gemini-povestitor-p07-masculin.mp3", "regie", 7, "masculin"),
                ("gemini-povestitor-p01-feminin.mp3", "regie", 1, "feminin")]
        for model in models[:2]:
            ok = False
            for name, kind, number, voice_key in jobs:
                page = story["pages"][number - 1]
                target = OUT / name.replace(".mp3", f"-{model}.mp3")
                try:
                    if kind != "replici":
                        pcm, mime = gemini(model, storyteller_prompt(page, characters, kind),
                                           {"x": voce.CHIRP_NARRATOR[voice_key]}, gemini_key)
                        with tempfile.TemporaryDirectory() as tmp:
                            raw, trimmed = Path(tmp) / "a.wav", Path(tmp) / "b.wav"
                            pcm_to_file(pcm, mime, raw)
                            voce.trim_silence(raw, trimmed)
                            voce.assemble([trimmed], [0], target, LEAD_IN)
                    else:
                        asyncio.run(gemini_lines(model, gemini_key, page, characters, target))
                    # citește și indicațiile? atunci mostra e mult mai lungă decât aceeași pagină cu Chirp
                    reference = OUT / f"chirp-ritm-p{number:02d}.mp3"
                    length = voce.duration(target)
                    if reference.exists() and length > 1.7 * voce.duration(reference):
                        target.rename(target.with_name("RESPINS-" + target.name))
                        results.append(f"- {target.name}: RESPINS ({length:.0f} s, probabil a citit și indicațiile)")
                        continue
                    results.append(f"- {target.name}: OK ({length:.0f} s)")
                    ok = True
                except Exception as exc:  # noqa: BLE001
                    results.append(f"- {target.name}: EȘUAT — {exc}")
                    if "HTTP 429" in str(exc) or "HTTP 403" in str(exc):
                        break  # fără cotă pentru modelul acesta: următorul
            if ok:
                break

    print("\n".join(results))
    if not any(OUT.glob("*.mp3")):
        sys.exit(1)


if __name__ == "__main__":
    main()
