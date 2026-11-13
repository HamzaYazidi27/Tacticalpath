"""Visual matching with CLIP: does this footage show what is being said, and *when*?

Runs locally on CPU (openai/clip-vit-base-patch32, ~600 MB, downloaded once). Optional: without
`torch` + `transformers` the pipeline falls back to file-name / metadata matching.

Scoring: for every sampled frame we compare the image with "a photo of <query>" and with a few
negative prompts (talking head, text screen, black frame…). `prob` is the softmax share of the query —
a calibrated "is this really the thing?" — and `sim` is the raw cosine similarity.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import numpy as np

from .util import log, proc_env

MODEL_ID = "openai/clip-vit-base-patch32"
NEGATIVES = ["a person talking to the camera in a studio", "text or a title on a screen", "a black or blank screen",
             "a blurry out of focus image", "a video game screenshot", "a sexually suggestive image"]
MIN_PROB = 0.60          # query must clearly beat the negatives
MIN_SIM = 0.235          # and look like it in absolute terms

SAFETY = ["a sexually suggestive close-up of a woman's body", "a close-up of buttocks", "a person in underwear or a bikini",
          "a woman's buttocks in tight shorts or leggings", "a close-up of a woman's chest"]


def unsafe_mask(emb: np.ndarray, query_sim: np.ndarray) -> np.ndarray:
    """True where a frame reads more as suggestive than as the query (calibrated on real stock frames)."""
    return (emb @ embed_texts(SAFETY).T).max(1) >= query_sim

_model = None


def available() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _load():
    global _model
    if _model is None:
        import torch
        from transformers import CLIPModel, CLIPProcessor
        torch.set_num_threads(max(1, torch.get_num_threads()))
        _model = (CLIPModel.from_pretrained(MODEL_ID).eval(), CLIPProcessor.from_pretrained(MODEL_ID))
        log("vision: CLIP loaded")
    return _model


def embed_images(images) -> np.ndarray:
    import torch
    m, p = _load()
    out = []
    for i in range(0, len(images), 32):
        with torch.no_grad():
            x = p(images=images[i:i + 32], return_tensors="pt")
            e = m.get_image_features(**x)
            e = e if isinstance(e, torch.Tensor) else e.pooler_output
        out.append(torch.nn.functional.normalize(e, dim=-1).numpy())
    return np.concatenate(out) if out else np.zeros((0, 512), np.float32)


def embed_texts(texts) -> np.ndarray:
    import torch
    m, p = _load()
    with torch.no_grad():
        x = p(text=list(texts), return_tensors="pt", padding=True)
        e = m.get_text_features(**x)
        e = e if isinstance(e, torch.Tensor) else e.pooler_output
    return torch.nn.functional.normalize(e, dim=-1).numpy()


def _competitors(query: str) -> list[str]:
    """For a phrase, its generic head noun competes: 'baby powder' must look more like baby powder than
    like any 'powder' (stops an explosion of coloured powder passing as baby powder)."""
    words = query.lower().split()
    if len(words) < 2:
        return []
    head = query.lower().split(" of ")[0].split()[-1] if " of " in query.lower() else words[-1]
    return [f"a photo of {head}"] if head != query.lower() else []


def score(img_emb: np.ndarray, query: str) -> tuple[np.ndarray, np.ndarray]:
    """Per-frame (prob, sim) for a query."""
    t = embed_texts([f"a photo of {query}"] + NEGATIVES + _competitors(query))
    sims = img_emb @ t.T                                  # (frames, 1+neg)
    logits = 100.0 * sims
    logits -= logits.max(1, keepdims=True)
    prob = np.exp(logits[:, 0]) / np.exp(logits).sum(1)
    return prob, sims[:, 0]


def grab_frames(src: str, times: list[float], width: int = 336, headers: str | None = None):
    """Frames at given times from a local file or an http(s) URL (uses range requests, no full download)."""
    from PIL import Image
    imgs, ok_t = [], []
    for t in times:
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
        if src.startswith("http"):
            cmd += ["-user_agent", "AutoeditClipFinder/1.0 (open-source video editing tool)"]
        if headers:
            cmd += ["-headers", headers]
        cmd += ["-ss", f"{max(t, 0):.2f}", "-i", src, "-frames:v", "1", "-vf", f"scale={width}:-2",
                "-f", "image2pipe", "-vcodec", "png", "-"]
        p = subprocess.run(cmd, capture_output=True, timeout=60, env=proc_env())
        if p.returncode == 0 and p.stdout:
            import io
            imgs.append(Image.open(io.BytesIO(p.stdout)).convert("RGB"))
            ok_t.append(t)
    return imgs, ok_t


def best_moment(src: str, duration: float, query: str, hint: float | None = None, samples: int = 16,
                headers: str | None = None) -> dict | None:
    """Find when `query` is visible. Returns {t, prob, sim} or None if it never convincingly is."""
    if duration <= 0:
        return None
    if hint is not None:
        times = list(np.clip(np.linspace(hint - 4, hint + 6, 11), 0, max(duration - 1.5, 0)))
    else:
        a, b = duration * 0.04, max(duration * 0.96 - 1.5, duration * 0.04)
        times = list(np.linspace(a, b, samples))
    imgs, ts = grab_frames(src, times, headers=headers)
    if not imgs:
        return None
    emb = embed_images(imgs)
    prob, sim = score(emb, query)
    comb = np.where(unsafe_mask(emb, sim), -1.0, prob + sim)   # never pick a frame that reads as suggestive
    k = int(np.argmax(comb))
    if comb[k] < 0 or prob[k] < MIN_PROB or sim[k] < MIN_SIM:
        return None
    # refine around the best sample
    step = (times[1] - times[0]) if len(times) > 1 else 1.0
    fine = [ts[k] + d for d in np.linspace(-step / 2, step / 2, 5) if 0 <= ts[k] + d <= duration - 1.0]
    imgs2, ts2 = grab_frames(src, fine, headers=headers)
    if imgs2:
        e2 = embed_images(imgs2)
        p2, s2 = score(e2, query)
        c2 = np.where(unsafe_mask(e2, s2), -1.0, p2 + s2)
        j = int(np.argmax(c2))
        if c2[j] >= prob[k] + sim[k]:
            return {"t": float(ts2[j]), "prob": float(p2[j]), "sim": float(s2[j])}
    return {"t": float(ts[k]), "prob": float(prob[k]), "sim": float(sim[k])}


def best_crop(src: str, t: float, query: str, positions: int = 5) -> float:
    """Where to put the 9:16 window on a wide frame so the subject stays in shot (0 = left … 1 = right)."""
    imgs, _ = grab_frames(src, [t], width=640)
    if not imgs:
        return 0.5
    im = imgs[0]
    w, h = im.size
    cw = int(h * 9 / 16)
    if cw >= w:
        return 0.5
    xs = np.linspace(0, w - cw, positions)
    crops = [im.crop((int(x), 0, int(x) + cw, h)) for x in xs]
    _, sim = score(embed_images(crops), query)
    k = int(np.argmax(sim))
    return round(float(xs[k] / (w - cw)), 3)


def clean_shot(path: str, t: float, before: float = 2.5, after: float = 4.0, fps: float = 12.0) -> dict:
    """The continuous shot (no internal cut) around time t in a LOCAL clip, and how much it moves.
    B-roll must never contain a cut of its own — that is what makes a montage feel smooth."""
    import cv2
    cap = cv2.VideoCapture(str(path))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / src_fps
    a = max(0.0, t - before)
    cap.set(cv2.CAP_PROP_POS_MSEC, a * 1000)
    step = max(1, int(round(src_fps / fps)))
    times, hists, grays, i = [], [], [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        cur = a + i / src_fps
        if cur > t + after:
            break
        if i % step == 0:
            ok, fr = cap.retrieve()
            if not ok:
                break
            sm = cv2.resize(fr, (96, 54))
            hsv = cv2.cvtColor(sm, cv2.COLOR_BGR2HSV)
            h = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256])
            hists.append(cv2.normalize(h, h).flatten())
            grays.append(cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY).astype(np.float32))
            times.append(cur)
        i += 1
    cap.release()
    if len(times) < 3:
        return {"start": t, "end": t + 1.5, "motion": 1.0, "total": total}
    cuts = [times[k] for k in range(1, len(times))
            if cv2.compareHist(hists[k - 1], hists[k], cv2.HISTCMP_BHATTACHARYYA) > 0.35]
    start = max([c for c in cuts if c <= t] + [times[0]])
    end = min([c for c in cuts if c > t] + [times[-1]])
    seg = [g for g, tt in zip(grays, times) if start <= tt <= end]
    motion = float(np.mean([np.abs(seg[k] - seg[k - 1]).mean() for k in range(1, len(seg))])) if len(seg) > 1 else 0.0
    return {"start": round(start + 0.08, 3), "end": round(end - 0.08, 3), "motion": round(motion, 2), "total": total}


class VisualIndex:
    """CLIP embeddings of every ~0.5 s of a set of local clips/images, cached on disk. Semantic search."""

    def __init__(self, files: list[dict], cache: Path, fps: float = 2.0, max_len: float = 600.0):
        self.entries = []          # (asset, times, emb)
        cache.mkdir(parents=True, exist_ok=True)
        for a in files:
            p = Path(a["path"])
            key = hashlib.md5(f"{p.resolve()}|{p.stat().st_mtime}|{fps}".encode()).hexdigest()[:16]
            f = cache / f"{key}.npz"
            if f.exists():
                z = np.load(f)
                self.entries.append((a, z["t"], z["e"]))
                continue
            if a["kind"] == "image":
                from PIL import Image
                imgs, ts = [Image.open(p).convert("RGB")], [0.0]
            else:
                from .util import probe
                dur = min(probe(p)["duration"], max_len)
                ts = list(np.arange(0.25, max(dur - 0.5, 0.3), 1 / fps)) or [0.0]
                imgs, ts = _frames_fast(p, ts)
            if not imgs:
                continue
            e = embed_images(imgs)
            np.savez(f, t=np.array(ts), e=e)
            self.entries.append((a, np.array(ts), e))
        log(f"vision index: {len(self.entries)} file(s) embedded")

    def search(self, query: str, top: int = 3) -> list[dict]:
        out = []
        t = embed_texts([f"a photo of {query}"] + NEGATIVES + _competitors(query))
        for a, ts, e in self.entries:
            sims = e @ t.T
            logits = 100 * sims
            logits -= logits.max(1, keepdims=True)
            prob = np.exp(logits[:, 0]) / np.exp(logits).sum(1)
            comb = np.where(unsafe_mask(e, sims[:, 0]), -1.0, prob + sims[:, 0])
            if len(comb) >= 3:                                # best ~1.5 s window, not a single lucky frame
                comb = np.convolve(comb, np.ones(3) / 3, mode="same")
            k = int(np.argmax(comb))
            if comb[k] > 0 and prob[k] >= MIN_PROB and sims[k, 0] >= MIN_SIM:
                out.append({**a, "in": max(0.0, float(ts[k]) - 0.5), "match": round(float(prob[k]), 3),
                            "sim": round(float(sims[k, 0]), 3), "query": query})
        out.sort(key=lambda x: -(x["match"] + x["sim"]))
        return out[:top]


def _frames_fast(path: Path, times):
    """Decode a local video once and keep frames nearest to `times` (much faster than one seek per frame)."""
    import cv2
    from PIL import Image
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    want = {int(round(t * fps)): t for t in times}
    imgs, ts, i = [], [], 0
    last = max(want) if want else 0
    while i <= last:
        ok = cap.grab()
        if not ok:
            break
        if i in want:
            ok, fr = cap.retrieve()
            if ok:
                h, w = fr.shape[:2]
                s = 336 / max(w, h)
                fr = cv2.resize(fr, (int(w * s), int(h * s)))
                imgs.append(Image.fromarray(fr[..., ::-1]))
                ts.append(want[i])
        i += 1
    cap.release()
    return imgs, ts
