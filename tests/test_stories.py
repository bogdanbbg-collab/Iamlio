"""Teste pentru scripts/stories.py și scripts/voce.py. Rulare: python3 -m unittest discover -s tests"""

import asyncio
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import stories  # noqa: E402
import voce  # noqa: E402

DEMO = ROOT / "public" / "stories" / "lio-si-steluta-cazatoare"


def demo_data():
    return json.loads((DEMO / "story.json").read_text(encoding="utf-8"))


class StoryCase(unittest.TestCase):
    """Copiază povestea demonstrativă într-un folder temporar, ca s-o putem strica în siguranță."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.folder = self.tmp / "poveste-test"
        shutil.copytree(DEMO, self.folder, ignore=shutil.ignore_patterns("audio"))
        self.data = demo_data()
        self.data["id"] = "poveste-test"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def errors(self, data=None):
        return stories.validate_story(self.folder, data or self.data)[0]

    def assertError(self, fragment, data=None):
        errors = self.errors(data)
        self.assertTrue(any(fragment in e for e in errors), f"lipsește eroarea „{fragment}” în {errors}")


class ValidationTests(StoryCase):
    def test_demo_story_is_valid(self):
        self.assertEqual(self.errors(), [])

    def test_learning_is_required(self):
        del self.data["learning"]
        self.assertError("learning")

    def test_age_must_be_known(self):
        self.data["age"] = "2-9"
        self.assertError("age")

    def test_too_short_story_is_rejected(self):
        self.data["pages"] = self.data["pages"][:4]
        self.assertError("pagini")
        self.assertError("durata estimată")

    def test_page_word_limits(self):
        self.data["pages"][0]["text"] = "Prea scurt."
        self.data["pages"][0].pop("narration")
        self.assertError("pagina 1: are 2 cuvinte")

    def test_cedilla_is_rejected(self):
        self.data["moral"] = "Prietenia e frumoasă şi bună."
        self.assertError("sedilă")

    def test_every_page_needs_an_image_prompt(self):
        self.data["pages"][2]["imagePrompt"] = "scurt"
        self.assertError("pagina 3: lipsește imagePrompt")

    def test_image_path_cannot_leave_story_folder(self):
        self.data["pages"][0]["image"] = "images/../../secret.png"
        self.assertError("pagina 1: calea imaginii")

    def test_svg_is_not_accepted(self):
        self.data["cover"]["image"] = "images/coperta.svg"
        self.assertError("copertă: calea imaginii")

    def test_missing_image_file(self):
        self.data["pages"][1]["image"] = "images/nu-exista.webp"
        self.assertError("nu există")

    def test_known_character_needs_source(self):
        self.data["characters"].append({
            "name": "Scufița Roșie",
            "description": "a little girl with a bright red hooded cape, brown braids and a wicker basket",
            "knownCharacter": True,
        })
        self.assertError("lipsește source")

    def test_narration_must_match_text(self):
        self.data["pages"][0]["narration"][0]["text"] = "Era o seară furtunoasă."
        self.assertError("narration nu conține exact aceleași cuvinte")

    def test_narration_is_required(self):
        self.data["pages"][4].pop("narration")
        self.assertError("pagina 5: lipsește regia de voce")

    def test_narration_rejects_unknown_mood_and_speaker(self):
        self.data["pages"][0]["narration"][0]["mood"] = "nervos"
        self.data["pages"][0]["narration"][1]["speaker"] = "Necunoscut"
        self.assertError("ton necunoscut")
        self.assertError("nu e în characters")

    def test_character_voice_limits(self):
        self.data["characters"][0]["voice"] = {"type": "robot", "pitch": 99}
        self.assertError("voice.type")
        self.assertError("voice.pitch")

    def test_sensitive_words_warn(self):
        self.data["pages"][0]["narration"] = None
        self.data["pages"][0]["text"] = self.data["pages"][0]["text"] + " Nimeni nu a murit."
        warnings = stories.validate_story(self.folder, self.data)[1]
        self.assertTrue(any("murit" in w for w in warnings))


class OptimizeTests(StoryCase):
    def test_png_becomes_small_webp_and_json_is_updated(self):
        from PIL import Image

        stories_dir = self.tmp
        Image.new("RGB", (3000, 2000), (200, 120, 40)).save(self.folder / "images" / "pagina-01.png")
        data = copy.deepcopy(self.data)
        data["pages"][0]["image"] = "images/pagina-01.png"
        (self.folder / "story.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        original = stories.STORIES_DIR
        stories.STORIES_DIR = stories_dir
        try:
            stories.cmd_optimize()
        finally:
            stories.STORIES_DIR = original

        saved = json.loads((self.folder / "story.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["pages"][0]["image"], "images/pagina-01.webp")
        self.assertFalse((self.folder / "images" / "pagina-01.png").exists())
        with Image.open(self.folder / "images" / "pagina-01.webp") as img:
            self.assertEqual(img.size, (1536, 1024))


class VoiceTests(unittest.TestCase):
    def test_auto_segments_make_dialogue_livelier(self):
        segments = voce.auto_segments("Lio a zâmbit. — Bună! a spus el. Apoi a plecat.")
        self.assertEqual([s.mood for s in segments], ["calm", "vesel", "vesel", "calm"])

    def test_ellipsis_gets_longer_pause(self):
        segments = voce.auto_segments("A zburat, a zburat… și a căzut.")
        self.assertEqual(segments[0].pause, voce.PAUSE_ELLIPSIS)

    def test_character_profile_changes_voice(self):
        characters = [{"name": "Steluța", "voice": {"type": "feminin", "pitch": 22, "rate": 2}}]
        segment = voce.Segment("— Bună!", "trist", "Steluța")
        params = voce.segment_params(segment, "masculin", characters)
        self.assertEqual(params.voice, "ro-RO-AlinaNeural")
        self.assertEqual((params.rate, params.pitch, params.volume), (-16, 14, -10))

    def test_narrator_follows_listener_choice(self):
        params = voce.segment_params(voce.Segment("Era odată."), "masculin", [])
        self.assertEqual(params.voice, "ro-RO-EmilNeural")

    def test_limits_are_applied(self):
        characters = [{"name": "X", "voice": {"pitch": 40, "rate": 30}}]
        params = voce.segment_params(voce.Segment("Hei!", "entuziasmat", "X"), "feminin", characters)
        self.assertEqual((params.rate, params.pitch), (30, 40))

    def test_fingerprint_changes_with_mood(self):
        a = voce.fingerprint([voce.Segment("Bună.", "calm")], "feminin", [])
        b = voce.fingerprint([voce.Segment("Bună.", "vesel")], "feminin", [])
        self.assertNotEqual(a, b)

    def test_demo_story_has_both_voices_for_every_page(self):
        names = [name for name, _ in stories.narration_items(demo_data())]
        self.assertEqual(names[0], "coperta.mp3")
        self.assertEqual(names[-1], "final.mp3")
        self.assertEqual(len(names), len(demo_data()["pages"]) + 2)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg lipsește")
    def test_render_joins_segments_with_pauses(self):
        async def fake_synth(text, params, target):
            # în loc de edge-tts: un ton de 0,5 secunde
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "sine=frequency=440:sample_rate=24000:duration=0.5", "-ac", "1", str(target)], check=True)

        segments = [voce.Segment("Unu.", pause=0.5), voce.Segment("Doi.", "vesel", pause=0.5)]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "pagina.mp3"
            asyncio.run(voce.render(segments, "feminin", [], target, synth=fake_synth))
            duration = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(target)],
                capture_output=True, text=True, check=True).stdout)
        expected = voce.LEAD_IN + 0.5 + 0.5 + 0.5 + voce.TAIL
        self.assertAlmostEqual(duration, expected, delta=0.15)


if __name__ == "__main__":
    unittest.main()
