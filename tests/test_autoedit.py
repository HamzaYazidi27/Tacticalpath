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

    def test_video_first_photo_fallback_default(self):
        cfg = Config()
        self.assertTrue(cfg.photo_fallback)
        self.assertEqual(cfg.broll_sources[:3], ["library", "urls", "youtube_cc"])


class TestPhotoFallback(unittest.TestCase):
    def _run(self, video_hits, photo_hits, fallback=True):
        from autoedit import social, vision
        cfg = Config(vision="on", broll_sources=["mixkit", "openverse"], photo_fallback=fallback)
        clip = {"start": 0, "end": 10, "priority": []}
        with mock.patch.object(vision, "available", return_value=True), \
             mock.patch.object(social.Mixkit, "find", side_effect=lambda q, limit=1, verify=None: list(video_hits.get(q, []))), \
             mock.patch.object(social.Openverse, "find", side_effect=lambda q, limit=1, verify=None: list(photo_hits.get(q, []))):
            found, _ = broll.resolve({1: "glass of water", 5: "baby powder"}, cfg, Path("/tmp/_ae_test_cache"),
                                     Path("/x.mp4"), [], clip, needed=5)
        return found

    def test_video_first_then_photo(self):
        v = {"glass of water": [{"path": "/v.mp4", "kind": "video", "dur": 5, "in": 0.3, "max_len": 3}]}
        p = {"glass of water": [{"path": "/p1.jpg", "kind": "image"}], "baby powder": [{"path": "/p2.jpg", "kind": "image"}]}
        found = self._run(v, p)
        self.assertEqual(found[1][0]["kind"], "video")     # a video exists → the photo is never used
        self.assertEqual(found[5][0]["kind"], "image")     # no video → real photo fallback

    def test_no_photos_flag(self):
        p = {"baby powder": [{"path": "/p2.jpg", "kind": "image"}]}
        self.assertNotIn(5, self._run({}, p, fallback=False))


class TestWithoutVision(unittest.TestCase):
    def test_resolve_runs_without_clip(self):
        """Regression: resolve() crashed with NameError when torch/transformers are not installed."""
        import tempfile
        from autoedit import vision
        with tempfile.TemporaryDirectory() as d:
            lib = Path(d) / "lib"
            lib.mkdir()
            (lib / "glass_of_water.mp4").write_bytes(b"x")
            cfg = Config(broll_dirs=[str(lib)], online_broll=False)
            with mock.patch.object(vision, "available", return_value=False), \
                 mock.patch.object(broll, "probe", return_value={"duration": 5.0}):
                found, generic = broll.resolve({1: "glass of water", 2: "baby powder"}, cfg, Path(d) / "cache",
                                               Path("/x.mp4"), [], {"start": 0, "end": 0}, needed=4)
        self.assertEqual(found[1][0]["kind"], "video")
        self.assertNotIn(2, found)


class TestFfmpegCompat(unittest.TestCase):
    def test_filter_file_syntax_by_version(self):
        from autoedit import util
        cases = {"ffmpeg version 8.0 Copyright (c) 2000-2025": "-/filter_complex",
                 "ffmpeg version 7.1.1 Copyright": "-/filter_complex",
                 "ffmpeg version n7.1 Copyright": "-/filter_complex",
                 "ffmpeg version N-118000-g1234 Copyright": "-/filter_complex",
                 "ffmpeg version 6.1.1-3ubuntu5 Copyright": "-filter_complex_script",
                 "ffmpeg version 5.1.6 Copyright": "-filter_complex_script"}
        for banner, flag in cases.items():
            util._FFMAJOR = None
            with mock.patch.object(util.subprocess, "run", return_value=types.SimpleNamespace(stdout=banner)), \
                 mock.patch.dict(util.os.environ if hasattr(util, "os") else {}, {}, clear=False):
                import os
                os.environ.pop("AUTOEDIT_FFMPEG_MAJOR", None)
                self.assertEqual(util.filter_file_args("f.txt")[0], flag, banner)
        util._FFMAJOR = None


TEASE = ("So I was diving off the coast near the island last summer. The water was calm and very clear. "
         "We dropped the cage next to the boat around noon. Then the biggest shark in the world attacked our cage! "
         "It circled the cage three times and bumped the bars. My friend was filming the whole thing with his camera. "
         "After a while it just swam back into the deep blue water. We went home and could not sleep that night.")


class TestRetention(unittest.TestCase):
    def test_virality_score_range_and_order(self):
        from autoedit import viral
        w = fake_words()
        sents = L.sentences(w)
        cfg = Config(min_dur=15, max_dur=40, target_dur=25)
        good = viral.score(w, sents, 0, 8, 25, cfg)
        dull = viral.score(w, sents, 9, 10, 25, cfg)
        self.assertTrue(0 <= dull["total"] <= 100 and 0 <= good["total"] <= 100)
        self.assertGreater(good["total"], dull["total"])
        self.assertEqual(set(good["parts"]), set(viral.PARTS))

    def test_cold_open_teaser_plays_first(self):
        w = fake_words(TEASE)
        cfg = Config(min_dur=26, max_dur=40, target_dur=30, llm="off")     # forces the whole story: weak first line
        clips, sents = selector.select(w, cfg)
        c = clips[0]
        self.assertIsNotNone(c["teaser"], "the shark line should be used as a cold open")
        p = planner.plan(w, c, {}, [], cfg)
        tD = p["stats"]["teaser"]
        self.assertGreater(tD, 0.8)
        self.assertEqual(L.bare(p["words"][0]["word"]), L.bare(w[c["teaser"][0]]["word"]))   # teaser line first
        self.assertTrue(p["shots"][0].get("intro"))
        for s in p["shots"]:
            if s["t1"] <= tD + 1e-3:
                self.assertEqual(s["kind"], "A")
        self.assertTrue(any(abs(s["t0"] - tD) < 1e-3 for s in p["shots"]))                 # hard cut into the story
        for a, b in zip(p["shots"], p["shots"][1:]):
            self.assertAlmostEqual(a["t1"], b["t0"], places=3)
        self.assertAlmostEqual(p["shots"][-1]["t1"], p["duration"], places=3)

    def test_auto_count_ranks_by_virality(self):
        w = fake_words(" ".join([TEASE, STORY.replace("Anyway, let's talk about something else.", ""), TEASE, STORY,
                                 TEASE.replace("shark", "whale")]))
        cfg = Config(min_dur=15, max_dur=35, target_dur=25, llm="off", min_virality=0)
        clips, _ = selector.select(w, cfg)
        self.assertGreaterEqual(len(clips), 2)
        totals = [c["virality"]["total"] for c in clips]
        self.assertEqual(totals, sorted(totals, reverse=True))
        self.assertTrue(all(c["hook"] for c in clips))

    def test_hook_off_and_custom(self):
        w = fake_words()
        clips, _ = selector.select(w, Config(min_dur=15, max_dur=40, target_dur=25, llm="off", hook_title="off"))
        self.assertEqual(clips[0]["hook"], "")
        clips, _ = selector.select(w, Config(min_dur=15, max_dur=40, target_dur=25, llm="off", hook_title="Sharks fear whales"))
        self.assertEqual(clips[0]["hook"], "Sharks fear whales")

    def test_hook_card_png(self):
        from autoedit import render
        from PIL import Image
        out = Path("/tmp/_ae_hook.png")
        render.hook_card("Why a shark ran from 1 whale", out)
        im = Image.open(out)
        self.assertEqual(im.size[0], 1080)
        self.assertGreater(im.getbbox()[3] - im.getbbox()[1], 60)


if __name__ == "__main__":
    unittest.main()
