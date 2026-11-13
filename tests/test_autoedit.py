"""Fast unit tests (no rendering, no network). Run: python3 -m unittest discover -s tests -v"""
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autoedit import broll, language as L, planner, selector  # noqa: E402
from autoedit.config import Config  # noqa: E402
from autoedit.render import brand_split  # noqa: E402

STORY = ("Did you know a shark can smell blood from far away? Um, a great white shark lives in the ocean. "
         "It hunts seals near the beach at night. Divers watch from a cage in the water. "
         "The shark bites the boat and swims away. Then a whale appears near the island. "
         "Nobody expected the whale to chase the shark. And here's the crazy part. The shark was scared. "
         "Scientists filmed everything with a camera on the boat. Anyway, let's talk about something else.")


def fake_words(text=STORY, wps=2.8, sentence_gap=0.5):
    words, t = [], 0.0
    for tok in text.split():
        d = max(0.12, len(tok) / 14)
        words.append({"word": tok, "start": round(t, 3), "end": round(t + d, 3)})
        t += 1 / wps + (sentence_gap if tok[-1] in ".?!" else 0)
    return words


class TestLanguage(unittest.TestCase):
    def test_meta_and_hooks(self):
        self.assertTrue(L.is_meta("Anyway, let's talk about something else."))
        self.assertGreater(L.hook_score("Did you know a cat once flew to space?"), L.hook_score("Um, so, yeah."))

    def test_keywords_keep_every_occurrence(self):
        w = fake_words()
        kws = L.keywords(w, 0, len(w) - 1)
        self.assertGreaterEqual(sum(1 for k in kws if k["word"] == "shark"), 3)


class TestSelector(unittest.TestCase):
    def test_picks_story_not_outro(self):
        w = fake_words()
        cfg = Config(min_dur=15, max_dur=40, target_dur=25, llm="off")
        clips, sents = selector.select(w, cfg)
        self.assertEqual(len(clips), 1)
        c = clips[0]
        self.assertTrue(sents[c["s0"]]["text"].startswith("Did you know"))
        self.assertNotIn("Anyway", " ".join(s["text"] for s in sents[c["s0"]:c["s1"] + 1]))

    def test_llm_answer_is_parsed(self):
        w = fake_words()
        sents = L.sentences(w)
        answer = {"clips": [{"start_sentence": 0, "end_sentence": 9, "title": "Shark vs whale", "why": "hook",
                             "broll": [{"sentence": 1, "word": "shark", "query": "great white shark"}]}]}
        block = types.SimpleNamespace(type="text", text=json.dumps(answer))
        resp = types.SimpleNamespace(stop_reason="end_turn", content=[block])
        fake = mock.MagicMock()
        fake.Anthropic.return_value.beta.messages.create.return_value = resp
        fake.APIStatusError = type("APIStatusError", (Exception,), {})
        fake.APIConnectionError = type("APIConnectionError", (Exception,), {})
        cfg = Config(min_dur=15, max_dur=60, llm="on")
        with mock.patch.dict(sys.modules, {"anthropic": fake}):
            clips = selector.llm_rerank(w, sents, cfg, 1)
        self.assertEqual(clips[0]["title"], "Shark vs whale")
        self.assertIn("great white shark", clips[0]["queries"].values())
        kwargs = fake.Anthropic.return_value.beta.messages.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-opus-5-5")
        self.assertEqual(kwargs["output_config"]["format"]["type"], "json_schema")


class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.w = fake_words()
        self.cfg = Config(min_dur=15, max_dur=40, target_dur=25, llm="off")
        clips, _ = selector.select(self.w, self.cfg)
        self.clip = clips[0]
        imgs = [{"path": f"/lib/{n}.jpg", "kind": "image", "source": "local", "credit": ""}
                for n in ("shark", "shark2", "ocean", "seal", "beach", "cage", "boat", "whale", "island", "camera")]
        self.found = {}
        for k, q in self.clip["queries"].items():
            m = [a for a in imgs if q.rstrip("s") in a["path"]]
            if m:
                self.found[k] = m

    def test_invariants(self):
        p = planner.plan(self.w, self.clip, self.found, [], self.cfg)
        shots = p["shots"]
        self.assertEqual(shots[0]["kind"], "A")                       # cold open on the speaker
        self.assertEqual(shots[-1]["kind"], "A")                      # ends on the speaker
        self.assertAlmostEqual(shots[-1]["t1"], p["duration"], places=3)
        for a, b in zip(shots, shots[1:]):
            self.assertAlmostEqual(a["t1"], b["t0"], places=3)        # contiguous, no holes
            if a["kind"] == b["kind"] == "B":
                self.assertNotEqual(a["asset"]["path"], b["asset"]["path"])
        for s in shots:
            self.assertGreater(s["t1"] - s["t0"], 0.3)
            if s["kind"] == "B":
                self.assertLessEqual(s["t1"] - s["t0"], self.cfg.broll_shot_max + 0.05)
        self.assertGreaterEqual(p["stats"]["cuts_per_min"], 40)
        self.assertTrue(all(L.bare(x["word"]) not in L.FILLERS for x in p["words"]))   # "Um" removed


class TestBrollAndBrand(unittest.TestCase):
    def test_pexels_parsing(self):
        data = {"videos": [{"id": 7, "url": "https://www.pexels.com/video/7/", "user": {"name": "Ana"},
                            "video_files": [{"link": "https://x/a.mp4", "width": 1080, "height": 1920},
                                            {"link": "https://x/b.mp4", "width": 360, "height": 640}]}]}
        with mock.patch.object(broll, "_get_json", return_value=data), \
             mock.patch.object(broll, "_download", side_effect=lambda url, dest: dest):
            res = broll.Pexels("KEY", Path("/tmp/cache")).find("shark", limit=1)
        self.assertEqual(len(res), 1)
        self.assertIn("Ana", res[0]["credit"])

    def test_brand_split(self):
        self.assertEqual(brand_split("WILD|FRAME"), ("WILDFRAME", 4))
        self.assertEqual(brand_split("TACTICAL|PATH"), ("TACTICALPATH", 8))
        self.assertEqual(brand_split("WildFrame"), ("WildFrame", 4))


if __name__ == "__main__":
    unittest.main()


class TestSocialSources(unittest.TestCase):
    def test_license_filter(self):
        from autoedit.social import license_ok
        ok = ["Creative Commons Attribution license (reuse allowed)", "CC BY 4.0", "CC0", "Public domain",
              "https://creativecommons.org/licenses/by/4.0/", "http://creativecommons.org/publicdomain/zero/1.0/"]
        bad = ["CC BY-SA 4.0", "CC BY-NC 2.0", "https://creativecommons.org/licenses/by-nc-sa/3.0/",
               "Standard YouTube License", ""]
        self.assertTrue(all(license_ok(x) for x in ok))
        self.assertFalse(any(license_ok(x) for x in bad))

    def test_youtube_caption_hint(self):
        from autoedit import social
        info = {"automatic_captions": {"en": [{"ext": "json3", "url": "https://x/subs"}]}}
        subs = {"events": [{"tStartMs": 1000, "segs": [{"utf8": "look at the"}]},
                           {"tStartMs": 4200, "segs": [{"utf8": "big", "tOffsetMs": 0}, {"utf8": " baboon", "tOffsetMs": 300}]}]}
        with mock.patch.object(social, "_get_json", return_value=subs):
            self.assertAlmostEqual(social.YouTubeCC.caption_hint(info, "baboon"), 4.5)

    def test_openverse_keeps_licensed_relevant_photo(self):
        import numpy as np
        from PIL import Image
        from autoedit import social, vision
        tmp = Path(__file__).resolve().parent / "_tmp_ov"
        api = {"results": [
            {"id": "a", "url": "https://img/a.jpg", "width": 1024, "height": 768, "license": "by", "license_version": "2.0",
             "creator": "Ann", "title": "Baboon", "foreign_landing_url": "https://flickr/a"},
            {"id": "b", "url": "https://img/b.jpg", "width": 1024, "height": 768, "license": "by-nc", "license_version": "2.0",
             "creator": "Bob", "title": "Baboon NC", "foreign_landing_url": "https://flickr/b"}]}
        tmp.mkdir(exist_ok=True)
        Image.fromarray(np.zeros((40, 40, 3), np.uint8)).save(tmp / "openverse_a.jpg")

        class FakeResp:
            def __init__(self, data): self.data = data
            def read(self): return self.data
            def __enter__(self): return self
            def __exit__(self, *a): return False
        jpg = (tmp / "openverse_a.jpg").read_bytes()
        with mock.patch.object(social, "_get_json", return_value=api), \
             mock.patch.object(social.urllib.request, "urlopen", return_value=FakeResp(jpg)), \
             mock.patch.object(vision, "embed_images", return_value=np.zeros((1, 512))), \
             mock.patch.object(vision, "score", return_value=(np.array([0.95]), np.array([0.3]))):
            res = social.Openverse(tmp).find("baboon")
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(len(res), 1)                       # the NC photo was never even downloaded
        self.assertIn("Ann", res[0]["credit"])
        self.assertEqual(res[0]["kind"], "image")


class TestPlacementRules(unittest.TestCase):
    def test_early_word_is_not_shifted_onto_another_word(self):
        w = fake_words("Nobody wants this. A glass of water sits on the table near the sea and the beach.")
        cfg = Config(min_dur=1, max_dur=60, target_dur=10, llm="off")
        clip = {"i0": 0, "i1": len(w) - 1, "start": 0, "end": w[-1]["end"], "queries": {0: "nobody", 4: "glass of water"}}
        found = {0: [{"path": "/a.jpg", "kind": "image"}], 4: [{"path": "/b.jpg", "kind": "image"}]}
        p = planner.plan(w, clip, found, [], cfg)
        keys = [s.get("key") for s in p["shots"] if s["kind"] == "B"]
        self.assertNotIn(0, keys)                          # word at t=0 can't get B-roll (speaker first)
        self.assertIn(4, keys)


class TestVideoBrollRules(unittest.TestCase):
    def test_phrase_words_not_searched_alone(self):
        w = fake_words("Do I need to bring baby powder today? Is the glass of water cold?")
        qs = [k["query"] for k in L.keywords(w, 0, len(w) - 1)]
        self.assertIn("baby powder", qs)
        self.assertIn("glass of water", qs)
        self.assertNotIn("powder", qs)          # covered by "baby powder"

    def test_unsafe_titles_filtered(self):
        from autoedit.social import UNSAFE
        self.assertTrue(UNSAFE.search("a young woman in small shorts performing a sexy dance"))
        self.assertFalse(UNSAFE.search("filling a glass with sparkling water"))

    def test_youtube_circuit_breaker(self):
        from autoedit import social
        y = social.YouTubeCC(Path("/tmp/none"))
        y._fail(hard=True)
        self.assertTrue(y.disabled)
        self.assertEqual(y.find("anything"), [])   # no network call once paused

    def test_video_only_default(self):
        cfg = Config()
        self.assertFalse(cfg.allow_photos)
        self.assertEqual(cfg.broll_sources[:3], ["library", "urls", "youtube_cc"])
