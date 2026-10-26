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

import canon  # noqa: E402
import imagini  # noqa: E402
import pregatire  # noqa: E402
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

    def test_categories_must_be_known(self):
        self.data["categories"] = ["dinozauri"]
        self.assertError("categories")
        self.data["categories"] = ["aventuri", "animale", "amuzante", "invatam"]
        self.assertError("categories")
        del self.data["categories"]
        self.assertError("lipsește câmpul obligatoriu 'categories'")

    def test_index_lists_categories_for_the_library(self):
        entry = stories.index_entry(DEMO, demo_data())
        self.assertEqual(entry["categories"], demo_data()["categories"])

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


class QualityTests(StoryCase):
    def test_review_is_required(self):
        del self.data["review"]
        self.assertError("review")

    def test_review_needs_two_humor_moments_with_pages(self):
        self.data["review"]["umor"] = ["ceva amuzant"]
        self.assertError("review.umor")
        self.data["review"]["umor"] = ["pagina 1: a", "pagina 99: b"]
        self.assertError("o pagină indicată nu există")

    def test_review_fields_must_be_written(self):
        self.data["review"]["siguranta"] = "ok"
        self.assertError("review.siguranta")

    def test_style_must_be_iamlio_style(self):
        self.data["illustrationStyle"] = "Watercolor painting"
        self.assertError("illustrationStyle nu e stilul Iamlio")

    def test_every_prompt_contains_the_style(self):
        self.data["pages"][3]["imagePrompt"] = self.data["pages"][3]["imagePrompt"].replace("3D animated", "2D")
        self.assertError("pagina 4: imagePrompt trebuie să conțină illustrationStyle")

    def test_character_description_is_copied_in_prompts(self):
        prompt = self.data["pages"][5]["imagePrompt"]
        self.data["pages"][5]["imagePrompt"] = prompt.replace(self.data["characters"][2]["description"], "a purple owl")
        self.assertError("pagina 6: Ula apare în imagePrompt, dar fără descrierea completă")

    def test_lio_must_look_and_sound_like_lio(self):
        self.data["characters"][0]["description"] = "a big grey lion with a red hat and a long beard, very serious"
        self.data["characters"][0]["voice"] = {"pitch": -20}
        self.assertError("descrierea oficială a lui Lio")
        self.assertError("profilul de voce oficial")

    def test_speakers_need_voice_profiles(self):
        del self.data["characters"][1]["voice"]
        self.assertError("Steluța vorbește, dar nu are profil de voce")

    def test_dialogue_needs_a_speaker(self):
        for item in self.data["pages"][0]["narration"]:
            item.pop("speaker", None)
        self.assertError("pagina 1: are dialog")

    def test_voice_must_not_be_monotone(self):
        for page in self.data["pages"]:
            for item in page["narration"]:
                item["mood"] = "calm"
        self.assertError("tonuri")

    def test_known_character_needs_detailed_description(self):
        self.data["characters"].append({"name": "Scufița Roșie", "description": "a little girl with a red hood and a basket",
                                        "knownCharacter": True, "source": "basm popular"})
        self.assertError("foarte detaliată")

    def test_unfinished_template_is_rejected(self):
        self.data["summary"] = f"{canon.PLACEHOLDER}: rezumat"
        self.assertError("șablonul nu e completat")


class LioAndQuizTests(StoryCase):
    def test_lio_greets_and_says_goodbye_by_category(self):
        intro, outro = stories.lio_texts(self.data)
        self.assertIn(intro, canon.LIO_INTROS["de-culcare"])
        self.assertIn(outro, canon.LIO_OUTROS["de-culcare"])
        self.assertEqual(stories.lio_texts(self.data), (intro, outro), "aceeași poveste are mereu același salut")
        items = dict(stories.narration_items(self.data))
        self.assertEqual(items["coperta.mp3"][0].text, intro)
        self.assertEqual(items["final.mp3"][-1].text, outro)
        self.assertEqual(items["final.mp3"][-1].mood, "somnoros")

    def test_questions_get_audio_with_options_read_aloud(self):
        items = dict(stories.narration_items(self.data))
        self.assertEqual(items["intrebare-2.mp3"][1].text, "Ziua sau Noaptea?")
        self.assertIn("raspuns-1.mp3", items)

    def test_question_rules(self):
        question = self.data["questions"][0]
        question["answer"] = 5
        self.assertError("answer")
        question["answer"] = 0
        question["options"][1].pop("emoji")
        self.assertError("varianta 2: are nevoie de o imagine")
        question["options"] = question["options"][:1]
        self.assertError("2–3 variante")
        self.data["questions"] = [question] * 4
        self.assertError("între 1 și 3 întrebări")

    def test_question_image_must_exist_in_story(self):
        self.data["questions"][0]["options"][0]["image"] = "images/nu-exista.png"
        self.assertError("întrebarea 1, varianta 1")

    def test_lio_lines_include_praise_and_encouragement(self):
        names = [name for name, _ in stories.lio_items()]
        self.assertIn("bravo-01.mp3", names)
        self.assertIn("incearca-01.mp3", names)


class PersonalizedTests(StoryCase):
    def make_personal(self, name="Ana"):
        self.data["personalized"] = {"for": name}
        self.data["approved"] = False
        self.data["id"] = "poveste-test-k7p2qx"
        folder = self.folder.with_name("poveste-test-k7p2qx")
        self.folder.rename(folder)
        self.folder = folder
        self.data["pages"][0]["text"] = self.data["pages"][0]["text"].replace("Lio, puiul", f"{name} și Lio, puiul")
        self.data["pages"][0]["narration"] = None
        self.data["pages"][0].pop("narration")

    def test_valid_personalized_story(self):
        self.make_personal()
        errors = [e for e in self.errors() if "narration" not in e and "regia" not in e]
        self.assertEqual(errors, [])
        intro, outro = stories.lio_texts(self.data)
        self.assertIn("Ana", intro)
        self.assertIn("Ana", outro)

    def test_only_a_first_name_is_allowed(self):
        self.make_personal("Ana Popescu 7")
        self.assertError("doar prenumele copilului")

    def test_link_must_be_secret(self):
        self.make_personal()
        self.data["id"] = "poveste-test"
        self.assertError("cod aleator")

    def test_name_must_appear_in_story(self):
        self.make_personal()
        self.data["personalized"]["for"] = "Maria"
        self.assertError("trebuie să apară în poveste")

    def test_personalized_stories_stay_out_of_the_library(self):
        self.make_personal()
        saved = stories.STORIES_DIR, stories.INDEX_FILE
        stories.STORIES_DIR, stories.INDEX_FILE = self.tmp, self.tmp / "index.json"
        try:
            (self.folder / "story.json").write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
            stories.cmd_index()
        finally:
            stories.STORIES_DIR, stories.INDEX_FILE = saved
        index = json.loads((self.tmp / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["stories"], [])

    def test_unapproved_stories_leave_the_public_site(self):
        import hashlib
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)
            public = build / "stories" / "ana-k7p2qx"
            public.mkdir(parents=True)
            (public / "story.json").write_text("{}", encoding="utf-8")
            with mock.patch.object(stories, "BUILD_DIR", build), mock.patch.dict("os.environ", {"ADMIN_PASSWORD": "secret"}):
                stories.stage_previews([public])
            self.assertFalse(public.exists())
            self.assertTrue((build / "api/data/previzualizare/ana-k7p2qx/story.json").exists())
            config = json.loads((build / "api/data/parola.json").read_text(encoding="utf-8"))
            self.assertNotIn("secret", json.dumps(config))
            self.assertEqual(config["hash"], hashlib.sha256((config["salt"] + "secret").encode()).hexdigest())

            other = build / "stories" / "bob-q9w3zz"
            other.mkdir()
            with mock.patch.object(stories, "BUILD_DIR", build), mock.patch.dict("os.environ", {"ADMIN_PASSWORD": "", "PREVIEW_PASSWORD": ""}):
                stories.stage_previews([other])
            self.assertFalse(other.exists(), "fără parolă, povestea neaprobată nu se urcă deloc")
            self.assertFalse((build / "api/data/previzualizare/bob-q9w3zz").exists())

    def test_new_personalized_story_gets_secret_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = stories.STORIES_DIR
            stories.STORIES_DIR = Path(tmp)
            try:
                self.assertEqual(stories.cmd_new("Ana și dragonul", "Ana"), 0)
            finally:
                stories.STORIES_DIR = original
            folder = next(Path(tmp).iterdir())
            self.assertRegex(folder.name, r"^ana-si-dragonul-[a-z0-9]{6}$")
            data = json.loads((folder / "story.json").read_text(encoding="utf-8"))
            self.assertEqual((data["personalized"], data["approved"]), ({"for": "Ana"}, False))


class PublicationDateTests(unittest.TestCase):
    def test_dates_are_recorded_only_when_publishing(self):
        from datetime import date
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "publicari.json"
            registry.write_text(json.dumps({"veche": "2026-01-02"}), encoding="utf-8")
            today = date.today().isoformat()
            with mock.patch.object(stories, "PUBLICATIONS_FILE", registry), mock.patch.dict("os.environ", {"PUBLICARE": ""}):
                self.assertEqual(stories.publication_dates(["veche", "noua"]), {"veche": "2026-01-02", "noua": today})
            self.assertNotIn("noua", json.loads(registry.read_text(encoding="utf-8")), "fără publicare reală nu se notează")
            with mock.patch.object(stories, "PUBLICATIONS_FILE", registry), mock.patch.dict("os.environ", {"PUBLICARE": "1"}):
                stories.publication_dates(["veche", "noua"])
            self.assertEqual(json.loads(registry.read_text(encoding="utf-8")), {"veche": "2026-01-02", "noua": today})

    def test_library_lists_newest_publications_first(self):
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "publicari.json"
            registry.write_text(json.dumps({"a": "2026-01-01", "b": "2026-03-01"}), encoding="utf-8")
            entries = [{"id": "a", "created": "2026-05-01", "title": "A"}, {"id": "b", "created": "2026-01-01", "title": "B"}]
            with mock.patch.object(stories, "PUBLICATIONS_FILE", registry):
                stories.write_index(Path(tmp) / "index.json", entries)
            index = json.loads((Path(tmp) / "index.json").read_text(encoding="utf-8"))
            self.assertEqual([(s["id"], s["published"]) for s in index["stories"]], [("b", "2026-03-01"), ("a", "2026-01-01")])


class TemplateTests(unittest.TestCase):
    def test_committed_template_matches_canon(self):
        committed = json.loads((ROOT / "sablon" / "story.json").read_text(encoding="utf-8"))
        self.assertEqual(committed, stories.template_story(), "rulează: python3 scripts/stories.py template")

    def test_demo_story_uses_canon(self):
        data = demo_data()
        self.assertEqual(data["illustrationStyle"], canon.STYLE)
        lio = next(c for c in data["characters"] if c["name"] == "Lio")
        self.assertEqual(lio["description"], canon.LIO_DESCRIPTION)

    def test_new_story_starts_from_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = stories.STORIES_DIR
            stories.STORIES_DIR = Path(tmp)
            try:
                self.assertEqual(stories.cmd_new("Aricelul și Luna"), 0)
                data = json.loads((Path(tmp) / "aricelul-si-luna" / "story.json").read_text(encoding="utf-8"))
                self.assertEqual(data["title"], "Aricelul și Luna")
                errors, _ = stories.validate_story(Path(tmp) / "aricelul-si-luna", data)
                self.assertTrue(any("șablonul nu e completat" in e for e in errors))
            finally:
                stories.STORIES_DIR = original


def sloppy_story(folder, data):
    """O poveste scrisă neglijent: tot ce poate repara proiectul e greșit."""
    from PIL import Image

    data = copy.deepcopy(data)
    (folder / "imgs").mkdir(parents=True, exist_ok=True)
    data.update(id="altceva", age="3–7 ani", created="azi", learning="numărăm stelele", illustrationStyle="cartoon")
    for character in data["characters"]:
        character.pop("voice", None)
    data["characters"][0]["description"] = "a lion"
    for number, page in enumerate(data["pages"], start=1):
        page.pop("narration")
        page["text"] = page["text"].replace("ș", "ş").replace("— ", "- ").replace("…", "...")
        page["imagePrompt"] = "Lio in the forest" if number % 2 else ""
        page["image"] = f"imgs/{number}.png"
        Image.new("RGB", (1600, 1100), (20 * number, 90, 140)).save(folder / "imgs" / f"{number}.png")
    data["cover"] = {"image": "cover.jpg", "imagePrompt": ""}
    Image.new("RGB", (1600, 1000), (200, 150, 60)).save(folder / "cover.jpg")
    return data


class AnimationTests(StoryCase):
    """Animația paginii (camera și efectul): aleasă de poveste, completată automat dacă lipsește."""

    def test_demo_story_has_an_animation_on_every_page(self):
        for entry in [self.data["cover"]] + self.data["pages"]:
            self.assertIn(entry["animation"]["camera"], canon.CAMERAS)
            self.assertIn(entry["animation"]["effect"], canon.EFFECTS)

    def test_unknown_camera_or_effect_is_rejected(self):
        self.data["pages"][0]["animation"] = {"camera": "salt-mortal", "effect": "none"}
        self.assertError("animation.camera necunoscută")
        self.data["pages"][0]["animation"] = {"camera": "zoom-in", "effect": "artificii"}
        self.assertError("animation.effect necunoscut")
        self.data["cover"]["animation"] = "zoom"
        self.assertError("copertă: animation trebuie să fie un obiect")

    def test_missing_animation_is_only_a_warning_and_is_filled_from_the_scene(self):
        for entry in [self.data["cover"]] + self.data["pages"]:
            del entry["animation"]
        errors, warnings = stories.validate_story(self.folder, self.data)
        self.assertEqual(errors, [])
        self.assertTrue(any("lipsește animation" in w for w in warnings))
        data, changes = pregatire.prepare(self.folder, self.data)
        self.assertTrue(any("animația paginii" in c for c in changes))
        cameras = [p["animation"]["camera"] for p in data["pages"]]
        self.assertEqual(cameras[:4], list(canon.CAMERA_CYCLE), "camera variază de la o pagină la alta")
        self.assertEqual(data["pages"][0]["animation"]["effect"], "stars", "pagina 1: Lio numără stelele")
        self.assertEqual(stories.validate_story(self.folder, data)[1], [])

    def test_effect_ignores_the_style_and_the_character_descriptions(self):
        # „magical” din stil și „stars” din eșarfa lui Lio nu sunt scena paginii
        characters = [{"name": "Lio", "description": canon.LIO_DESCRIPTION}]
        prompt = f"{canon.STYLE} Characters in this scene: Lio: {canon.LIO_DESCRIPTION}. Action: Lio eats an apple."
        self.assertEqual(pregatire.guess_effect("Lio mănâncă un măr.", prompt, characters), "none")
        self.assertEqual(pregatire.guess_effect("Tata aprinde lumânarea.", prompt, characters), "glow")


class PreparationTests(StoryCase):
    def setUp(self):
        super().setUp()
        shutil.rmtree(self.folder / "images")
        self.data = sloppy_story(self.folder, self.data)

    def test_sloppy_story_is_repaired_until_valid(self):
        self.assertGreater(len(self.errors()), 30)
        data, changes = pregatire.prepare(self.folder, self.data)
        self.assertEqual(stories.validate_story(self.folder, data)[0], [])
        self.assertTrue(any("regia de voce" in c for c in changes))
        self.assertEqual(data["pages"][0]["image"], "images/pagina-01.png")
        self.assertTrue((self.folder / "images" / "coperta.jpg").is_file())
        self.assertFalse((self.folder / "imgs").exists())

    def test_preparation_is_idempotent(self):
        data, _ = pregatire.prepare(self.folder, self.data)
        again, changes = pregatire.prepare(self.folder, copy.deepcopy(data))
        self.assertEqual(changes, [])
        self.assertEqual(again, data)

    def test_narration_punctuation_is_copied_from_text(self):
        text = "Lio a strigat: „Hai la joacă!” Ariciul a zâmbit."
        narration = [{"text": "Lio a strigat", "mood": "vesel"}, {"text": "Hai la joaca", "speaker": "Lio"},
                     {"text": "Ariciul a zambit!"}]
        self.assertTrue(pregatire.Preparer.realign(narration, text))
        self.assertEqual([i["text"] for i in narration], ["Lio a strigat:", "„Hai la joacă!”", "Ariciul a zâmbit."])
        self.assertEqual((narration[0]["mood"], narration[1]["speaker"]), ("vesel", "Lio"))
        self.assertTrue(stories.narration_in_text({"text": text, "narration": narration}))
        self.assertFalse(pregatire.Preparer.realign(narration, text))

    def test_correct_story_is_left_alone(self):
        data, changes = pregatire.prepare(DEMO, demo_data())
        self.assertEqual(changes, [])
        self.assertEqual(data, demo_data())

    def test_missing_categories_are_guessed(self):
        del self.data["categories"]
        self.data["title"] = "Ursulețul care nu putea adormi"
        self.data["tags"] = ["somn", "noapte", "urs"]
        data, changes = pregatire.prepare(self.folder, self.data)
        self.assertEqual(data["categories"][0], "de-culcare")
        self.assertIn("animale", data["categories"])
        self.assertLessEqual(len(data["categories"]), 3)
        self.assertTrue(any("categoriile au fost alese automat" in c for c in changes))

    def test_text_normalization(self):
        self.assertEqual(pregatire.normalize_text('- Bună... a spus "Lio" cu  ş.'), "— Bună… a spus „Lio” cu ș.")

    def test_folder_is_renamed_after_title(self):
        bad = self.tmp / "Ariciul Ţepişor"
        self.folder.rename(bad)
        new = pregatire.rename_folder(bad, self.data)
        self.assertEqual(new.name, pregatire.slugify(self.data["title"]))
        self.assertEqual(self.data["id"], new.name)

    def test_missing_image_is_reported_not_invented(self):
        (self.folder / "imgs" / "3.png").unlink()
        data, _ = pregatire.prepare(self.folder, self.data)
        errors = stories.validate_story(self.folder, data)[0]
        self.assertEqual(errors, ["pagina 3: imaginea images/pagina-03.png nu există"])


class FakeImages:
    def __init__(self, fail_on=None):
        self.calls, self.fail_on = [], fail_on

    def _result(self):
        import base64
        import io
        from types import SimpleNamespace

        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (1536, 1024), (240, 200, 90)).save(buffer, "PNG")
        return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(buffer.getvalue()).decode())])

    def generate(self, **kwargs):
        self.calls.append(("generate", kwargs["prompt"]))
        return self._result()

    def edit(self, **kwargs):
        self.calls.append(("edit", kwargs["prompt"]))
        if self.fail_on and self.fail_on in kwargs["prompt"]:
            raise RuntimeError("refuzat")
        return self._result()


class ImageGenerationTests(StoryCase):
    def setUp(self):
        super().setUp()
        for image in (self.folder / "images").iterdir():
            image.unlink()
        for entry in [self.data["cover"]] + self.data["pages"]:
            entry["image"] = entry["image"].replace(".webp", ".png")
        from types import SimpleNamespace

        self.fake = FakeImages()
        self.client = SimpleNamespace(images=self.fake)

    def test_cover_first_then_pages_from_cover(self):
        changes, errors, made = imagini.generate_missing(self.folder, self.data, client=self.client, budget=50)
        self.assertEqual(errors, [])
        self.assertEqual(made, len(self.data["pages"]) + 1)
        self.assertEqual(self.fake.calls[0][0], "generate")
        self.assertTrue(all(kind == "edit" for kind, _ in self.fake.calls[1:]))
        self.assertTrue(self.fake.calls[1][1].startswith(imagini.CONSISTENCY))
        self.assertEqual(self.errors(), [])

    def test_budget_limits_cost(self):
        _, errors, made = imagini.generate_missing(self.folder, self.data, client=self.client, budget=3)
        self.assertEqual(made, 3)
        self.assertTrue(any("limita" in e for e in errors))

    def test_monthly_budget_is_respected_and_recorded(self):
        from datetime import date
        from unittest import mock

        budget_file = self.tmp / "buget.json"
        month = date.today().strftime("%Y-%m")
        budget_file.write_text(json.dumps({month: 198}), encoding="utf-8")  # formatul vechi
        with mock.patch.dict("os.environ", {"MAX_IMAGES_MONTH": "200"}):
            budget = imagini.Budget(budget_file)
        _, _, made = imagini.generate_missing(self.folder, self.data, client=self.client, budget=budget)
        self.assertEqual(made, 2)
        budget.save()
        self.assertEqual(json.loads(budget_file.read_text(encoding="utf-8"))[month]["imagini"], 200)
        self.assertIn("| " + month + " | 200 |", budget_file.with_suffix(".md").read_text(encoding="utf-8"))

    def test_monthly_money_limit_stops_generation(self):
        from datetime import date
        from types import SimpleNamespace
        from unittest import mock

        budget_file = self.tmp / "buget.json"
        month = date.today().strftime("%Y-%m")
        budget_file.write_text(json.dumps({month: {"imagini": 10, "lei": 9.0}}), encoding="utf-8")
        with mock.patch.dict("os.environ", {"MAX_LEI_MONTH": "10"}):
            budget = imagini.Budget(budget_file)  # media: 0,90 lei pe imagine → încă o imagine
            _, errors, made = imagini.generate_missing(self.folder, self.data, client=self.client, budget=budget)
        self.assertEqual(made, 1)
        self.assertTrue(any("cost" in e for e in errors))
        usage = SimpleNamespace(output_tokens=1_000_000, input_tokens=0,
                                input_tokens_details=SimpleNamespace(text_tokens=0, image_tokens=0))
        with mock.patch.dict("os.environ", {"IMAGE_PRICE_OUT": "40", "USD_LEI": "5"}):
            self.assertAlmostEqual(imagini.cost_lei(SimpleNamespace(usage=usage)), 200.0)

    def test_failed_image_is_reported(self):
        self.fake.fail_on = self.data["pages"][1]["imagePrompt"][-40:]
        _, errors, _ = imagini.generate_missing(self.folder, self.data, client=self.client, budget=50)
        self.assertTrue(errors and errors[0].startswith("pagina 2"))


class CloudflareTests(unittest.TestCase):
    """Generarea gratuită de imagini (Cloudflare Workers AI), cu un server simulat."""

    @staticmethod
    def _image(size=(1024, 1024), fmt="JPEG"):
        import io

        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", size, (90, 140, 200)).save(buffer, fmt)
        return buffer.getvalue()

    def _client(self, kind, payload, model=imagini.CLOUDFLARE_MODEL):
        import io

        sent = []

        class Response(io.BytesIO):
            headers = {"Content-Type": kind}

        def opener(request, timeout):
            sent.append(json.loads(request.data.decode("utf-8")))
            self.assertIn("/ai/run/" + model, request.full_url)
            self.assertEqual(request.get_header("Authorization"), "Bearer jeton")
            return Response(payload)

        return imagini.CloudflareClient("cont", "jeton", model, "arici-zboara", opener=opener), sent

    def test_flux_answer_becomes_a_wide_page_image_for_free(self):
        import base64
        import io

        from PIL import Image

        answer = json.dumps({"success": True, "result": {"image": base64.b64encode(self._image()).decode()}}).encode()
        client, sent = self._client("application/json", answer)
        result = client.images.edit(prompt=imagini.CONSISTENCY + "A hedgehog " + "x" * 3000, model="m")
        with Image.open(io.BytesIO(base64.b64decode(result.data[0].b64_json))) as image:
            self.assertEqual((image.format, image.size), ("PNG", (1536, 1024)))
        self.assertEqual(imagini.cost_lei(result), 0.0)
        body = sent[0]
        self.assertNotIn("reference image", body["prompt"], "fără referință: textul despre ea nu se trimite")
        self.assertTrue(body["prompt"].startswith("A hedgehog"), "scena e prima: FLUX citește doar începutul")
        self.assertLessEqual(len(body["prompt"]), imagini.CLOUDFLARE_MAX_PROMPT)
        # FLUX.1 schnell primește doar prompt și steps (alți parametri sunt refuzați de Cloudflare)
        self.assertEqual(set(body), {"prompt", "steps"})
        self.assertEqual(body["steps"], 8)

    def test_scene_goes_first_and_character_descriptions_last(self):
        characters = [{"name": "Aricel", "description": "a tiny round hedgehog with a teal scarf"},
                      {"name": "Piu", "description": "a small sky-blue songbird"},
                      {"name": "Lio", "description": "a lion cub who is not on this page"}]
        prompt = (f"{canon.STYLE} Characters in this scene: Aricel: a tiny round hedgehog with a teal scarf; "
                  "Piu: a small sky-blue songbird. Setting and action: Aricel jumps off a low stump with leaf wings.")
        result = imagini.scene_first(prompt, characters)
        self.assertTrue(result.startswith("Setting and action: Aricel (a tiny round hedgehog) jumps off a low stump"),
                        "scena e prima, cu ce fel de personaj e lângă nume")
        self.assertNotIn(canon.STYLE, result)
        self.assertIn(imagini.SHORT_STYLE, result)
        self.assertTrue(result.endswith("Characters: Aricel: a tiny round hedgehog with a teal scarf; "
                                        "Piu: a small sky-blue songbird."), result)
        self.assertNotIn("lion cub", result, "doar personajele din scenă")

    def test_models_that_answer_with_an_image_get_the_page_size(self):
        client, sent = self._client("image/png", self._image((1536, 1024), "PNG"), model="@cf/leonardo/lucid-origin")
        client.images.generate(prompt="Cover")
        self.assertEqual((sent[0]["width"], sent[0]["height"]), (1536, 1024))
        client.images.generate(prompt="Page")
        self.assertEqual(sent[0]["seed"], sent[1]["seed"], "aceeași sămânță pentru toată povestea")

    def test_errors_are_reported(self):
        client, _ = self._client("application/json", json.dumps({"success": False, "errors": [{"message": "cota zilnică"}]}).encode())
        with self.assertRaisesRegex(RuntimeError, "cota zilnică"):
            client.images.generate(prompt="Cover")

    def test_free_variant_is_preferred_when_configured(self):
        from unittest import mock

        both = {"CLOUDFLARE_ACCOUNT_ID": "a", "CLOUDFLARE_API_TOKEN": "t", "OPENAI_API_KEY": "k"}
        with mock.patch.dict("os.environ", both):
            self.assertEqual(imagini.provider(), "cloudflare")
            chain = imagini.make_client("poveste")
            self.assertIsInstance(chain.clients[0], imagini.CloudflareClient, "gratuit întâi, OpenAI doar dacă dă eroare")
        with mock.patch.dict("os.environ", {"CLOUDFLARE_ACCOUNT_ID": "", "CLOUDFLARE_API_TOKEN": "", "OPENAI_API_KEY": "k"}):
            self.assertEqual(imagini.provider(), "openai")
        with mock.patch.dict("os.environ", {"CLOUDFLARE_ACCOUNT_ID": "", "CLOUDFLARE_API_TOKEN": "", "OPENAI_API_KEY": ""}):
            self.assertFalse(imagini.enabled())


class PollinationsTests(unittest.TestCase):
    """Rezerva gratuită după Cloudflare, cu un server simulat."""

    def _client(self, status, answer):
        import io
        import urllib.error

        sent = []

        def opener(request, timeout):
            sent.append((request, json.loads(request.data.decode("utf-8"))))
            if status != 200:
                raise urllib.error.HTTPError(request.full_url, status, "eroare", {}, io.BytesIO(json.dumps(answer).encode()))
            return io.BytesIO(json.dumps(answer).encode())

        characters = [{"name": "Aricel", "description": "a tiny round hedgehog with a teal scarf"}]
        return imagini.PollinationsClient("sk_cheie", imagini.POLLINATIONS_MODEL, "arici", opener=opener,
                                          characters=characters), sent

    def test_answer_becomes_a_free_page_image_with_the_scene_first(self):
        import base64
        import io

        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (1024, 1024), (90, 140, 200)).save(buffer, "JPEG")
        client, sent = self._client(200, {"data": [{"b64_json": base64.b64encode(buffer.getvalue()).decode()}]})
        prompt = (f"{canon.STYLE} Characters in this scene: Aricel: a tiny round hedgehog with a teal scarf. "
                  "Setting and action: Aricel jumps.")
        result = client.images.edit(prompt=imagini.CONSISTENCY + prompt, model="m")
        with Image.open(io.BytesIO(base64.b64decode(result.data[0].b64_json))) as image:
            self.assertEqual(image.size, (1536, 1024))
        self.assertEqual(imagini.cost_lei(result), 0.0)
        request, body = sent[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer sk_cheie")
        self.assertTrue(body["prompt"].startswith("Setting and action: Aricel (a tiny round hedgehog) jumps."))
        self.assertEqual((body["model"], body["size"], body["response_format"]),
                         (imagini.POLLINATIONS_MODEL, "1536x1024", "b64_json"))

    def test_exhausted_credit_is_reported(self):
        client, _ = self._client(402, {"error": "PAYMENT_REQUIRED: balance exhausted"})
        with self.assertRaisesRegex(RuntimeError, "Pollinations: .*exhausted"):
            client.images.generate(prompt="Cover")

    def test_comes_before_cloudflare_and_openai(self):
        from unittest import mock

        env = {"GEMINI_API_KEY": "", "CLOUDFLARE_ACCOUNT_ID": "a", "CLOUDFLARE_API_TOKEN": "t",
               "POLLINATIONS_API_KEY": "sk", "OPENAI_API_KEY": "k"}
        with mock.patch.dict("os.environ", env):
            self.assertEqual(imagini.providers(), ["pollinations", "cloudflare", "openai"])


class GeminiAndFallbackTests(unittest.TestCase):
    """Gemini („Nano Banana”) cu imaginea copertei ca referință și trecerea la următoarea variantă la eroare."""

    def _gemini(self, status, answer):
        import io
        import urllib.error

        sent = []

        def opener(request, timeout):
            sent.append((request, json.loads(request.data.decode("utf-8"))))
            if status != 200:
                raise urllib.error.HTTPError(request.full_url, status, "eroare", {}, io.BytesIO(json.dumps(answer).encode()))
            return io.BytesIO(json.dumps(answer).encode())

        return imagini.GeminiClient("cheie", "gemini-2.5-flash-image", opener=opener), sent

    def test_gemini_uses_the_cover_as_reference_and_returns_a_page(self):
        import base64
        import io

        from PIL import Image

        picture = CloudflareTests._image((1536, 1024), "PNG")
        answer = {"candidates": [{"content": {"parts": [{"text": "gata"}, {"inlineData": {"mimeType": "image/png",
                  "data": base64.b64encode(picture).decode()}}]}}]}
        client, sent = self._gemini(200, answer)
        reference = io.BytesIO(b"coperta")
        reference.name = "images/coperta.png"
        result = client.images.edit(prompt=imagini.CONSISTENCY + "Page", image=[reference], model="x")
        request, body = sent[0]
        self.assertEqual(request.get_header("X-goog-api-key"), "cheie")
        self.assertIn("gemini-2.5-flash-image:generateContent", request.full_url)
        parts = body["contents"][0]["parts"]
        self.assertEqual(parts[1]["inline_data"]["data"], base64.b64encode(b"coperta").decode())
        self.assertEqual(body["generationConfig"]["imageConfig"]["aspectRatio"], "3:2")
        with Image.open(io.BytesIO(base64.b64decode(result.data[0].b64_json))) as image:
            self.assertEqual(image.size, (1536, 1024))
        self.assertEqual(imagini.cost_lei(result), 0.0)

    def test_gemini_quota_error_is_readable(self):
        client, _ = self._gemini(429, {"error": {"message": "Quota exceeded, limit: 0"}})
        with self.assertRaisesRegex(RuntimeError, "Gemini: Quota exceeded, limit: 0"):
            client.images.generate(prompt="Cover")

    def test_chain_falls_back_to_the_next_free_variant(self):
        from types import SimpleNamespace

        calls = []

        class Broken:
            model = "gemini"
            images = SimpleNamespace(generate=lambda **k: (_ for _ in ()).throw(RuntimeError("limit: 0")))

        class Works:
            model = "flux"
            images = SimpleNamespace(generate=lambda **k: calls.append(k["model"]) or SimpleNamespace(free=True))

        chain = imagini.ChainClient([Broken(), Works()])
        chain.images.generate(prompt="a", model="gemini")
        chain.images.generate(prompt="b", model="gemini")
        self.assertEqual(calls, ["flux", "flux"], "fiecare variantă primește numele ei de model")
        self.assertEqual(chain.model, "flux")
        self.assertEqual(len(chain.clients), 1, "varianta care a dat eroare nu se mai încearcă")

    def test_order_gemini_cloudflare_openai(self):
        from unittest import mock

        every = {"GEMINI_API_KEY": "g", "CLOUDFLARE_ACCOUNT_ID": "a", "CLOUDFLARE_API_TOKEN": "t", "OPENAI_API_KEY": ""}
        with mock.patch.dict("os.environ", every):
            self.assertEqual(imagini.providers(), ["gemini", "cloudflare"])
            self.assertIsInstance(imagini.make_client("p"), imagini.ChainClient)


class RobustnessTests(unittest.TestCase):
    def test_malformed_story_files_do_not_stop_the_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shutil.copytree(DEMO, tmp / DEMO.name)
            shapes = [{"pages": "abc", "characters": [1, 2], "cover": []}, [1, 2, 3], {"pages": [1, "x"], "title": 5},
                      {"characters": "Lio", "review": [1]}, "text"]
            for n, shape in enumerate(shapes):
                (tmp / f"ciudata-{n}").mkdir()
                (tmp / f"ciudata-{n}" / "story.json").write_text(json.dumps(shape), encoding="utf-8")
            (tmp / "stricata").mkdir()
            (tmp / "stricata" / "story.json").write_text("{ nu e json", encoding="utf-8")
            saved = stories.STORIES_DIR, stories.REPORTS_DIR, stories.INDEX_FILE
            stories.STORIES_DIR, stories.REPORTS_DIR, stories.INDEX_FILE = tmp, tmp / "rapoarte", tmp / "index.json"
            try:
                for command in (stories.cmd_validate, stories.cmd_prepare, stories.cmd_optimize, stories.cmd_index):
                    command()
            finally:
                stories.STORIES_DIR, stories.REPORTS_DIR, stories.INDEX_FILE = saved
            index = json.loads((tmp / "index.json").read_text(encoding="utf-8"))
            self.assertEqual([s["id"] for s in index["stories"]], [DEMO.name])
            self.assertIn("NEPUBLICATĂ", (tmp / "rapoarte" / "ciudata-0.md").read_text(encoding="utf-8"))


@unittest.skipUnless(shutil.which("git"), "git lipsește")
class PreviousVersionTests(unittest.TestCase):
    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

    def test_last_valid_version_stays_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.repo = Path(tmp) / "repo"
            folder = self.repo / "public" / "stories" / DEMO.name
            shutil.copytree(DEMO, folder)
            self.git("init", "-q")
            self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "bună", "--allow-empty")
            self.git("add", "-A")
            self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "versiune bună")
            good = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, capture_output=True, text=True).stdout.strip()
            data = demo_data()
            data["pages"] = data["pages"][:2]
            (folder / "story.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "versiune stricată")

            from unittest import mock
            with mock.patch.object(stories, "missing_audio", return_value=[]):  # vocea e testată separat
                found = stories.previous_published(DEMO.name, Path(tmp) / "lucru", repo=self.repo)
            self.assertIsNotNone(found)
            self.assertEqual(found[1], good)
            kept = json.loads((found[0] / "story.json").read_text(encoding="utf-8"))
            self.assertEqual(len(kept["pages"]), len(demo_data()["pages"]))

    def test_never_published_story_has_no_previous_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.repo = Path(tmp)
            self.git("init", "-q")
            self.assertIsNone(stories.previous_published("nu-exista", Path(tmp) / "lucru", repo=self.repo))


class OptimizeTests(StoryCase):
    def test_optimize_never_touches_files_outside_the_story(self):
        from PIL import Image

        victim = self.tmp / "victima.png"
        Image.new("RGB", (2000, 1500)).save(victim)
        data = copy.deepcopy(self.data)
        data["cover"]["image"] = "../victima.png"
        data["pages"][0]["image"] = "images/../../victima.png"
        (self.folder / "story.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        original = stories.STORIES_DIR
        stories.STORIES_DIR = self.tmp
        try:
            stories.cmd_optimize()
        finally:
            stories.STORIES_DIR = original
        self.assertTrue(victim.is_file())
        self.assertFalse((self.tmp / "victima.webp").exists())

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
        segments = voce.auto_segments("Lio a zâmbit. — Bună! a spus el. Apoi a plecat.", [{"name": "Lio"}])
        self.assertEqual([s.mood for s in segments], ["calm", "entuziasmat", "calm", "calm"])
        self.assertEqual([s.speaker for s in segments], ["", "Lio", "", ""])

    def test_speaker_and_mood_come_from_dialogue_tag(self):
        characters = [{"name": "Lio"}, {"name": "Steluța"}]
        segments = voce.auto_segments("— Nu mai știu drumul, a suspinat Steluța. — Te ajut, a șoptit Lio.", characters)
        self.assertEqual([(s.speaker, s.mood) for s in segments],
                         [("Steluța", "trist"), ("", "calm"), ("Lio", "șoptit"), ("", "calm")])

    def test_short_line_after_tag_belongs_to_speaker(self):
        segments = voce.auto_segments("— Nu-ți fie teamă, a zis Lio. Te ajut eu! Apoi a plecat.", [{"name": "Lio"}])
        self.assertEqual(segments[2].speaker, "Lio")
        self.assertEqual(segments[3].speaker, "")

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
        pages = len(demo_data()["pages"])
        self.assertEqual(names[0], "coperta.mp3")
        self.assertEqual(names[pages + 1], "final.mp3")
        self.assertEqual(names[1:pages + 1], [f"pagina-{n:02d}.mp3" for n in range(1, pages + 1)])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg lipsește")
    def test_corrupt_or_short_audio_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad, short = Path(tmp) / "bun.mp3", Path(tmp) / "corupt.mp3", Path(tmp) / "scurt.mp3"
            for target, seconds in ((good, 2), (short, 0.2)):
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                f"sine=frequency=440:sample_rate=24000:duration={seconds}", "-ac", "1", "-b:a", "48k",
                                str(target)], check=True)
            data = good.read_bytes()
            bad.write_bytes(data[:600] + bytes(range(256)) * 20 + data[600:])
            self.assertEqual(stories.audio_problem(good), "")
            self.assertIn("corupt", stories.audio_problem(bad))
            self.assertTrue(stories.audio_problem(short))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg lipsește")
    def test_render_joins_segments_with_pauses(self):
        async def fake_synth(text, params, target):
            # în loc de edge-tts: un ton de 0,5 secunde
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "sine=frequency=440:sample_rate=24000:duration=0.5", "-ac", "1", str(target)], check=True)

        segments = [voce.Segment("Unu.", pause=0.5), voce.Segment("Doi.", "vesel", pause=0.5)]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "pagina.mp3"
            timings = asyncio.run(voce.render(segments, "feminin", [], target, synth=fake_synth))
            duration = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(target)],
                capture_output=True, text=True, check=True).stdout)
        expected = voce.LEAD_IN + 0.5 + 0.5 + 0.5 + voce.TAIL
        self.assertAlmostEqual(duration, expected, delta=0.15)
        # momentele replicilor (pentru evidențierea textului): după pauza de început, apoi după pauza dintre ele
        self.assertEqual(len(timings), 2)
        self.assertAlmostEqual(timings[0][0], voce.LEAD_IN, delta=0.01)
        self.assertAlmostEqual(timings[1][0], timings[0][1] + 0.5, delta=0.01)
        self.assertAlmostEqual(timings[1][1], duration - voce.TAIL, delta=0.15)


if __name__ == "__main__":
    unittest.main()
