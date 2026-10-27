"""Regia de voce pentru Iamlio: împarte textul în replici, le dă intonație și le lipește cu pauze.

Vocea principală e Google Cloud Text-to-Speech, Chirp 3 HD (cheia în GOOGLE_TTS_API_KEY): voci naturale, iar
fiecare personaj primește o voce proprie. Dacă nu e cheie, serviciul nu răspunde sau s-a atins limita lunară de
caractere, se folosește edge-tts (gratuit, fără cont), unde personajele se deosebesc prin înălțime și viteză.
Fiecare bucată se generează separat, cu tonul ei (`mood`), apoi bucățile se lipesc cu ffmpeg.
Formatul explicit (câmpul `narration` al unei pagini) e descris în REGULI_POVESTI.md, secțiunea 7.
"""

import asyncio
import base64
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

VOICES = {"feminin": "ro-RO-AlinaNeural", "masculin": "ro-RO-EmilNeural"}

# Chirp 3 HD: vocea povestitorului, a lui Lio și vocile din care primesc personajele (după tip și înălțime).
# Între paranteze, descrierea Google a vocii.
CHIRP_NARRATOR = {"feminin": "Sulafat", "masculin": "Algieba"}  # caldă / catifelată
CHIRP_LIO = {"feminin": "Leda", "masculin": "Puck"}  # tinerească / veselă
CHIRP_POOLS = {
    "feminin": {
        "inalt": ["Laomedeia", "Zephyr", "Autonoe", "Leda"],  # veselă, luminoasă, luminoasă, tinerească
        "grav": ["Gacrux", "Kore", "Pulcherrima"],  # matură, fermă, directă
        "normal": ["Achernar", "Vindemiatrix", "Aoede", "Despina", "Callirrhoe", "Erinome"],
    },
    "masculin": {
        "inalt": ["Fenrir", "Sadachbia", "Puck"],  # entuziasmată, vioaie, veselă
        "grav": ["Algenib", "Charon", "Rasalgethi", "Alnilam"],  # răgușită, gravă, sfătoasă, fermă
        "normal": ["Achird", "Iapetus", "Umbriel", "Schedar", "Zubenelgenubi", "Orus", "Sadaltager", "Enceladus"],
    },
}
CHIRP_VOICES = sorted({v for pools in CHIRP_POOLS.values() for pool in pools.values() for v in pool}
                      | set(CHIRP_NARRATOR.values()) | set(CHIRP_LIO.values()))
CHIRP_HIGH, CHIRP_LOW = 10, -8  # de la ce înălțime (pitch) un personaj primește o voce „înaltă” sau „gravă”
CHIRP_RATE = 0.92  # puțin mai rar decât normal: ascultă copii mici
CHIRP_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
CHIRP_LANGUAGE = "ro-RO"
CHIRP_WAITS = (3, 6, 12, 24, 48)  # secunde între reîncercări (limita de cereri pe minut)
DEFAULT_CHIRP_MONTH_CHARS = 800_000  # din 1.000.000 gratuite pe lună; peste limită se trece pe edge-tts

# Versiunea regiei: schimb-o când modifici tonurile, ca să se regenereze toate fișierele audio.
ENGINE_VERSION = "3"  # 3: se salvează și momentul fiecărei replici (pentru evidențierea textului)

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
    engine: str = "edge"

    def key(self):
        base = f"{self.voice}|{self.rate}|{self.pitch}|{self.volume}"
        return base if self.engine == "edge" else f"{self.engine}|{base}"


def clamp(value, bounds):
    return max(bounds[0], min(bounds[1], value))


def default_pause(text):
    return PAUSE_ELLIPSIS if text.rstrip().endswith(("…", "...")) else PAUSE_DEFAULT


# „— Nu mai știu drumul, a suspinat ea.” → replica „— Nu mai știu drumul,” + tag-ul „a suspinat ea.”
DIALOGUE_TAG = re.compile(
    r"^(—.*?[,!?…])\s+((?:a|au|i-a|le-a|îi|i|spuse|zise|întrebă|strigă|răspunse|șopti)\s.*)$")
PRONOUN_TAG = re.compile(r"\b(el|ea|ei|ele)\b")


def plain(text):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()


def mention_positions(text, names):
    """(poziție, nume) pentru fiecare apariție a unui personaj în text."""
    found = []
    for name in names:
        for match in re.finditer(rf"\b{re.escape(plain(name))}\w*", plain(text)):
            found.append((match.start(), name))
    return sorted(found)


# Verbul din tag-ul de dialog („a suspinat ea”) și cuvintele din narațiune spun emoția.
TAG_MOODS = [
    (r"suspin|plâns|plânge|scânc|smiorc|oftat", "trist"),
    (r"șopt|soptit|murmur", "șoptit"),
    (r"strig|chiu|exclam|țip|tipat|bucur|râs|ras|chicot", "entuziasmat"),
    (r"întreb|intreb|mir", "mirat"),
    (r"tremur|speri|bâlbâ", "speriat"),
    (r"căsc|casc|mormă|morma|adorm", "somnoros"),
    (r"hotăr|hotar|ferm", "hotărât"),
]
NARRATION_MOODS = [
    (r"\b(plâng|plang|trist|lacrim|supărat|suparat|singur)", "trist"),
    (r"\b(adorm|somn|căsc|casc|noapte bună|noapte buna)", "somnoros"),
    (r"\b(deodată|deodata|dintr-odată|misterios|ciudat|întuneric)", "misterios"),
    (r"\b(șopt|sopt)", "șoptit"),
]


def mood_from(patterns, text):
    lowered = text.lower()
    for pattern, mood in patterns:
        if re.search(pattern, lowered):
            return mood
    return ""


def guess_mood(text, dialogue, tag=""):
    from_tag = mood_from(TAG_MOODS, tag) if tag else ""
    if from_tag:
        return from_tag
    if not dialogue:
        from_words = mood_from(NARRATION_MOODS, text)
        if from_words:
            return from_words
    end = text.rstrip()[-1:] if text.strip() else ""
    if end == "?":
        return "mirat"
    if end == "!":
        return "entuziasmat" if dialogue else "vesel"
    if end == "…" or text.rstrip().endswith("..."):
        return "misterios"
    return DIALOGUE_MOOD if dialogue else NARRATOR_MOOD


def auto_segments(text, characters=()):
    """Regie de voce automată: replicile de dialog primesc vorbitor și ton, tag-urile rămân la povestitor."""
    names = [c.get("name") for c in characters if c.get("name")]
    segments = []
    position = 0
    last_speaker = ""
    stripped = text.strip()
    # se taie doar înaintea unei majuscule sau a unei linii de dialog, ca „— Cine e? a întrebat Lio.” să rămână întreg
    # și după „…” (pauză de suspans), dacă nu urmează un tag de dialog
    for sentence in re.split(r"(?<=[.!?…])\s+(?=[A-ZĂÂÎȘȚ—„])|(?<=…)\s+(?!(?:a|au|i-a|le-a|îi|i|spuse|zise)\s)", stripped):
        if not sentence:
            continue
        start = stripped.find(sentence, position)
        position = start + len(sentence)
        if not sentence.startswith("—"):
            # „— Nu-ți fie teamă, a zis Lio. Te ajut eu!” — replica scurtă de după tag e tot a lui Lio
            continues = last_speaker and word_count(sentence) <= 6 and sentence.rstrip()[-1:] in "!?"
            speaker = last_speaker if continues else ""
            segments.append(Segment(sentence, guess_mood(sentence, bool(continues)), speaker, default_pause(sentence)))
            last_speaker = ""
            continue
        match = DIALOGUE_TAG.match(sentence)
        speech, tag = (match.group(1), match.group(2)) if match else (sentence, "")
        speaker = ""
        in_tag = mention_positions(tag, names)
        if in_tag:
            speaker = in_tag[0][1]
        elif names:
            before = mention_positions(stripped[:start], names)
            if before:
                speaker = before[-1][1]
            elif "Lio" in names:
                speaker = "Lio"
        segments.append(Segment(speech, guess_mood(speech, True, tag), speaker, default_pause(speech)))
        if tag:
            segments.append(Segment(tag, NARRATOR_MOOD, pause=default_pause(tag)))
        last_speaker = speaker if tag else ""
    return segments


def word_count(text):
    return len(re.findall(r"\w+", text))


def page_segments(page, characters=()):
    narration = page.get("narration")
    if not narration:
        return auto_segments(page.get("text") or "", characters)
    segments = []
    for item in narration:
        text = item["text"].strip()
        pause = item.get("pause", default_pause(text))
        segments.append(Segment(text, item.get("mood", NARRATOR_MOOD), item.get("speaker", ""), float(pause)))
    return segments


def chirp_cast(voice_key, characters):
    """Vocea Chirp a fiecărui personaj, în ordinea din characters: Lio are vocea lui, ceilalți primesc pe rând
    prima voce liberă potrivită tipului și înălțimii lor (sau vocea scrisă explicit în voice.chirp)."""
    used = {CHIRP_NARRATOR[voice_key], CHIRP_LIO[voice_key]}
    cast = {"Lio": CHIRP_LIO[voice_key]}
    for character in characters:
        name = character.get("name")
        if not name or name == "Lio":
            continue
        profile = character.get("voice") or {}
        if profile.get("chirp") in CHIRP_VOICES:
            cast[name] = profile["chirp"]
            used.add(profile["chirp"])
            continue
        gender = profile.get("type") if profile.get("type") in VOICES else voice_key
        pitch = int(profile.get("pitch", 0) or 0)
        height = "inalt" if pitch >= CHIRP_HIGH else "grav" if pitch <= CHIRP_LOW else "normal"
        pools = CHIRP_POOLS[gender]
        candidates = pools[height] + [v for h in ("normal", "inalt", "grav") if h != height for v in pools[h]]
        choice = next((v for v in candidates if v not in used), candidates[0])
        cast[name] = choice
        used.add(choice)
    return cast


def segment_params(segment, voice_key, characters, engine="edge"):
    """Vocea finală a unei bucăți: vocea aleasă + tonul + profilul personajului care vorbește."""
    rate, pitch, volume = MOODS.get(segment.mood, MOODS[NARRATOR_MOOD])
    profile = next((c.get("voice") or {} for c in characters if c.get("name") == segment.speaker), {})
    if engine == "chirp":
        # vocile Chirp au deja intonație naturală și voce proprie pentru fiecare personaj: tonul schimbă doar
        # puțin viteza (jumătate din cât la edge-tts) și volumul (șoptit, somnoros)
        voice = chirp_cast(voice_key, characters).get(segment.speaker) if segment.speaker else None
        rate = (rate + int(profile.get("rate", 0))) // 2
        return Params(voice or CHIRP_NARRATOR[voice_key], clamp(rate, LIMITS["rate"]), 0,
                      clamp(volume, LIMITS["volume"]), "chirp")
    voice = VOICES[voice_key]
    if profile.get("type") in VOICES:
        voice = VOICES[profile["type"]]
    rate += int(profile.get("rate", 0))
    pitch += int(profile.get("pitch", 0))
    return Params(voice, clamp(rate, LIMITS["rate"]), clamp(pitch, LIMITS["pitch"]), clamp(volume, LIMITS["volume"]))


def fingerprint(segments, voice_key, characters, engine="edge"):
    parts = [ENGINE_VERSION, voice_key]
    for s in segments:
        parts.append(f"{s.text}|{s.pause}|{segment_params(s, voice_key, characters, engine).key()}")
    return "\n".join(parts)


class ChirpUnavailable(RuntimeError):
    """Chirp nu poate genera acum (fără cheie, limita lunară, cheie greșită, serviciul nu răspunde): se trece pe edge-tts."""


class ChirpBudget:
    """Caracterele trimise la Google în fiecare lună (în rapoarte/buget-voce.json), ca să nu se treacă de partea gratuită."""

    def __init__(self, path=None):
        from datetime import date

        self.path = Path(path) if path else None
        self.month = date.today().strftime("%Y-%m")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8")) if self.path else {}
        except (OSError, ValueError):
            data = {}
        self.history = {m: int(v) for m, v in data.items() if isinstance(v, int)} if isinstance(data, dict) else {}
        self.used = self.history.get(self.month, 0)
        try:
            self.limit = int(os.environ.get("MAX_TTS_CHARS_MONTH") or DEFAULT_CHIRP_MONTH_CHARS)
        except ValueError:
            self.limit = DEFAULT_CHIRP_MONTH_CHARS

    def take(self, characters):
        if self.used + characters > self.limit:
            raise ChirpUnavailable(f"limita lunară de {self.limit} caractere (MAX_TTS_CHARS_MONTH) a fost atinsă")
        self.used += characters

    def save(self):
        if not self.path or self.used == self.history.get(self.month, 0):
            return
        self.history[self.month] = self.used
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.history, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class Chirp:
    """Clientul Google Cloud Text-to-Speech (Chirp 3 HD), cu limita lunară și oprire la prima eroare definitivă."""

    def __init__(self, key, budget):
        self.key = key
        self.budget = budget
        self.broken = ""  # după o eroare definitivă (cheie greșită, limită), restul fișierelor trec direct pe edge-tts

    def _call(self, body):
        import urllib.error
        import urllib.request

        request = urllib.request.Request(CHIRP_URL, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json", "X-Goog-Api-Key": self.key})
        for attempt, wait in enumerate((*CHIRP_WAITS, None), start=1):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:300]
                if exc.code != 429 and exc.code < 500 or wait is None:
                    raise ChirpUnavailable(f"Google TTS HTTP {exc.code} (încercarea {attempt}): {detail}") from None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if wait is None:
                    raise ChirpUnavailable(f"Google TTS nu răspunde: {exc}") from None
            time.sleep(wait)  # prea multe cereri pe minut sau o eroare temporară la Google
        raise ChirpUnavailable("Google TTS nu răspunde")

    async def synthesize(self, text, params, target):
        if self.broken:
            raise ChirpUnavailable(self.broken)
        spoken = text.lstrip("—– ").strip() or text
        try:
            self.budget.take(len(spoken))
            body = {
                "input": {"text": spoken},
                "voice": {"languageCode": CHIRP_LANGUAGE, "name": f"{CHIRP_LANGUAGE}-Chirp3-HD-{params.voice}"},
                "audioConfig": {"audioEncoding": "MP3", "speakingRate": round(CHIRP_RATE * (1 + params.rate / 100), 3)},
            }
            data = await asyncio.to_thread(self._call, body)
        except ChirpUnavailable as exc:
            self.broken = str(exc)
            raise
        audio = base64.b64decode(data.get("audioContent") or "")
        if not audio:
            raise ChirpUnavailable("Google TTS a trimis un fișier audio gol")
        target.write_bytes(audio)
        if params.volume:
            gain = 20 * math.log10(max(0.05, 1 + params.volume / 100))
            louder = target.with_name(target.stem + "-vol.mp3")
            await asyncio.to_thread(subprocess.run, [ffmpeg_binary(), "-y", "-loglevel", "error", "-i", str(target),
                                                     "-af", f"volume={gain:.1f}dB", str(louder)], check=True)
            os.replace(louder, target)


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


def trim_silence(source, target):
    """Taie liniștea de la începutul și sfârșitul unei bucăți (serviciile de voce lasă ~0,3 s la fiecare capăt),
    ca pauzele dintre replici să fie exact cele din regie. Păstrează puțin aer, ca să nu taie sfârșitul cuvintelor."""
    edge = "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB:start_silence={}"
    graph = f"{edge.format(0.04)},areverse,{edge.format(0.12)},areverse"
    subprocess.run([ffmpeg_binary(), "-y", "-loglevel", "error", "-i", str(source), "-af", graph,
                    "-ac", "1", "-ar", str(SAMPLE_RATE), str(target)], check=True)


def assemble(parts, pauses, target, lead_in=None):
    """Lipește fișierele audio cu pauzele date (secunde) într-un singur mp3 mono 48 kbit/s."""
    inputs, filters, labels = [], [], []
    plan = [("silence", LEAD_IN if lead_in is None else lead_in)]
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


def duration(path):
    """Durata unui mp3 în secunde (ffprobe; dacă lipsește, din mărime: mono 48 kbit/s)."""
    probe = shutil.which("ffprobe")
    if probe:
        result = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass
    return Path(path).stat().st_size / 6000


async def render(segments, voice_key, characters, target, synth=synthesize, engine="edge", trim=False, lead_in=None):
    """Generează un fișier audio complet din bucăți (synth poate fi înlocuit în teste).
    Întoarce momentele [început, sfârșit] (secunde) ale fiecărei replici, pentru evidențierea textului."""
    lead_in = LEAD_IN if lead_in is None else lead_in
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for number, segment in enumerate(segments):
            part = Path(tmp) / f"bucata-{number:03d}.mp3"
            await synth(segment.text, segment_params(segment, voice_key, characters, engine), part)
            if trim:
                trimmed = part.with_suffix(".wav")
                await asyncio.to_thread(trim_silence, part, trimmed)
                part = trimmed
            parts.append(part)
        # ffmpeg și ffprobe rulează în alt fir, ca celelalte fișiere să se genereze între timp
        await asyncio.to_thread(assemble, parts, [s.pause for s in segments], target, lead_in)
        lengths = await asyncio.to_thread(lambda: [duration(part) for part in parts])
        timings, moment = [], lead_in
        for number, (length, segment) in enumerate(zip(lengths, segments)):
            timings.append([round(moment, 2), round(moment + length, 2)])
            moment += length + (TAIL if number == len(segments) - 1 else segment.pause)
        return timings
