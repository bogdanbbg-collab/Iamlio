"""Regia de voce pentru Iamlio: împarte textul în replici, le dă intonație și le lipește cu pauze.

edge-tts nu acceptă SSML, așa că intonația se obține generând fiecare bucată separat, cu viteza,
înălțimea și volumul potrivite tonului (`mood`) și personajului, apoi lipind bucățile cu ffmpeg.
Formatul explicit (câmpul `narration` al unei pagini) e descris în REGULI_POVESTI.md, secțiunea 7.
"""

import asyncio
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

VOICES = {"feminin": "ro-RO-AlinaNeural", "masculin": "ro-RO-EmilNeural"}

# Versiunea regiei: schimb-o când modifici tonurile, ca să se regenereze toate fișierele audio.
ENGINE_VERSION = "2"

# ton → (viteză %, înălțime Hz, volum %)
MOODS = {
    "calm": (-8, 0, 0),
    "vesel": (2, 8, 0),
    "entuziasmat": (8, 14, 5),
    "mirat": (-4, 12, 0),
    "trist": (-18, -8, -10),
    "șoptit": (-15, -2, -35),
    "misterios": (-16, -6, -15),
    "somnoros": (-22, -6, -20),
    "speriat": (6, 10, -5),
    "hotărât": (-2, -3, 5),
}
NARRATOR_MOOD = "calm"
DIALOGUE_MOOD = "vesel"
LIMITS = {"rate": (-40, 30), "pitch": (-30, 40), "volume": (-50, 20)}
CHARACTER_PITCH = (-30, 40)
CHARACTER_RATE = (-30, 30)

PAUSE_DEFAULT = 0.3
PAUSE_ELLIPSIS = 0.7
PAUSE_MAX = 3.0
LEAD_IN = 0.15
TAIL = 0.35
RETRIES = 3

SAMPLE_RATE = 24000
BITRATE = "48k"


@dataclass
class Segment:
    text: str
    mood: str = NARRATOR_MOOD
    speaker: str = ""
    pause: float = PAUSE_DEFAULT


@dataclass
class Params:
    voice: str
    rate: int
    pitch: int
    volume: int

    def key(self):
        return f"{self.voice}|{self.rate}|{self.pitch}|{self.volume}"


def clamp(value, bounds):
    return max(bounds[0], min(bounds[1], value))


def default_pause(text):
    return PAUSE_ELLIPSIS if text.rstrip().endswith(("…", "...")) else PAUSE_DEFAULT


def auto_segments(text):
    """Fără regie explicită: propozițiile de dialog (cu „—”) sunt mai vii decât narațiunea."""
    segments = []
    in_dialogue = False
    for part in re.split(r"(?<=[.!?…])\s+", text.strip()):
        if not part:
            continue
        if part.startswith("—"):
            in_dialogue = True
        segments.append(Segment(part, DIALOGUE_MOOD if in_dialogue else NARRATOR_MOOD, pause=default_pause(part)))
        if not part.startswith("—"):
            in_dialogue = False
    return segments


def page_segments(page):
    narration = page.get("narration")
    if not narration:
        return auto_segments(page.get("text") or "")
    segments = []
    for item in narration:
        text = item["text"].strip()
        pause = item.get("pause", default_pause(text))
        segments.append(Segment(text, item.get("mood", NARRATOR_MOOD), item.get("speaker", ""), float(pause)))
    return segments


def segment_params(segment, voice_key, characters):
    """Vocea finală a unei bucăți: vocea aleasă + tonul + profilul personajului care vorbește."""
    rate, pitch, volume = MOODS.get(segment.mood, MOODS[NARRATOR_MOOD])
    voice = VOICES[voice_key]
    profile = next((c.get("voice") or {} for c in characters if c.get("name") == segment.speaker), {})
    if profile.get("type") in VOICES:
        voice = VOICES[profile["type"]]
    rate += int(profile.get("rate", 0))
    pitch += int(profile.get("pitch", 0))
    return Params(voice, clamp(rate, LIMITS["rate"]), clamp(pitch, LIMITS["pitch"]), clamp(volume, LIMITS["volume"]))


def fingerprint(segments, voice_key, characters):
    parts = [ENGINE_VERSION, voice_key]
    for s in segments:
        parts.append(f"{s.text}|{s.pause}|{segment_params(s, voice_key, characters).key()}")
    return "\n".join(parts)


async def synthesize(text, params, target):
    """Generează o bucată cu edge-tts, cu reîncercări la erori temporare de rețea."""
    import edge_tts

    for attempt in range(1, RETRIES + 1):
        try:
            await edge_tts.Communicate(
                text, params.voice,
                rate=f"{params.rate:+d}%", pitch=f"{params.pitch:+d}Hz", volume=f"{params.volume:+d}%",
            ).save(str(target))
            if target.stat().st_size > 0:
                return
            raise RuntimeError("fișier audio gol")
        except Exception as exc:  # rețea, limită de cereri, răspuns gol
            if attempt == RETRIES:
                raise RuntimeError(f"edge-tts a eșuat de {RETRIES} ori pentru „{text[:40]}…”: {exc}") from exc
            await asyncio.sleep(2 ** attempt)


def ffmpeg_binary():
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("ffmpeg nu este instalat")
    return binary


def assemble(parts, pauses, target):
    """Lipește fișierele mp3 cu pauzele date (secunde) într-un singur mp3 mono 48 kbit/s."""
    inputs, filters, labels = [], [], []
    plan = [("silence", LEAD_IN)]
    for part, pause in zip(parts, pauses):
        plan.append(("file", part))
        plan.append(("silence", pause))
    plan[-1] = ("silence", TAIL)
    for index, (kind, value) in enumerate(plan):
        if kind == "file":
            inputs += ["-i", str(value)]
        else:
            inputs += ["-f", "lavfi", "-t", f"{value:.2f}", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono"]
        filters.append(f"[{index}:a]aformat=sample_rates={SAMPLE_RATE}:channel_layouts=mono[a{index}]")
        labels.append(f"[a{index}]")
    graph = ";".join(filters) + f";{''.join(labels)}concat=n={len(plan)}:v=0:a=1[out]"
    subprocess.run(
        [ffmpeg_binary(), "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "[out]",
         "-ac", "1", "-ar", str(SAMPLE_RATE), "-b:a", BITRATE, str(target)],
        check=True,
    )


async def render(segments, voice_key, characters, target, synth=synthesize):
    """Generează un fișier audio complet din bucăți (synth poate fi înlocuit în teste)."""
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for number, segment in enumerate(segments):
            part = Path(tmp) / f"bucata-{number:03d}.mp3"
            await synth(segment.text, segment_params(segment, voice_key, characters), part)
            parts.append(part)
        assemble(parts, [s.pause for s in segments], target)
