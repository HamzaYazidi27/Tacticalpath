"""Visual and audio analysis: face track, scene changes, shot quality, loudness envelope."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from .util import load_json, log, save_json


def _cv2():
    import cv2  # local import keeps `--help` fast
    return cv2


class _NoDetector:
    def detectMultiScale(self, *a, **k):
        return []


def _cascade(cv2, name):
    """Haar cascade, or a no-op detector on OpenCV builds without it (OpenCV 5 moved them out)."""
    if not hasattr(cv2, "CascadeClassifier"):
        log("⚠ this OpenCV build has no Haar cascades (OpenCV 5?) — faces not tracked, centre framing used. "
            "Fix: pip install 'opencv-python-headless<5'")
        return _NoDetector()
    return cv2.CascadeClassifier(cv2.data.haarcascades + name)


def face_track(video: Path, work: Path, sample_fps: float = 4.0, name: str = "faces") -> list[dict]:
    """Sample frames, detect the largest face. Returns [{t, x, y, w}] normalised 0..1 (x,y = face centre)."""
    cache = work / f"{name}.json"
    if cache.exists():
        return load_json(cache)
    cv2 = _cv2()
    det = _cascade(cv2, "haarcascade_frontalface_default.xml")
    prof = _cascade(cv2, "haarcascade_profileface.xml")
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(fps / sample_fps)))
    out, i = [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            h, w = frame.shape[:2]
            scale = 960 / max(w, h)
            small = cv2.resize(frame, (int(w * scale), int(h * scale)))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            faces = []
            for g in (gray, cv2.equalizeHist(gray)):          # raw first: equalising dark sets hurts
                faces = list(det.detectMultiScale(g, 1.1, 4, minSize=(22, 22)))
                if not faces:
                    faces = list(prof.detectMultiScale(g, 1.1, 4, minSize=(22, 22)))
                if faces:
                    break
            if faces:
                x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                sw, sh = small.shape[1], small.shape[0]
                out.append({"t": round(i / fps, 3), "x": (x + fw / 2) / sw, "y": (y + fh / 2) / sh, "w": fw / sw})
        i += 1
    cap.release()
    save_json(cache, out)
    log(f"face track ({name}): {len(out)} detections")
    return out


def face_at(track: list[dict], t0: float, t1: float, default=(0.5, 0.40, 0.0)) -> tuple[float, float, float]:
    """Median face centre (x, y, width) inside [t0, t1]; widens the window if empty."""
    for pad in (0.0, 1.5, 4.0, 1e9):
        pts = [f for f in track if t0 - pad <= f["t"] <= t1 + pad]
        if pts:
            return (float(np.median([p["x"] for p in pts])), float(np.median([p["y"] for p in pts])),
                    float(np.median([p["w"] for p in pts])))
    return default


def scenes(video: Path, work: Path, sample_fps: float = 5.0, thr: float = 0.32) -> list[dict]:
    """Shot boundaries + per-shot quality. Returns [{start, end, sharp, motion, bright, faces}]."""
    cache = work / "scenes.json"
    if cache.exists():
        return load_json(cache)
    cv2 = _cv2()
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(fps / sample_fps)))
    det = _cascade(cv2, "haarcascade_frontalface_default.xml")
    prev_h = prev_g = None
    bounds, stats, i = [0.0], [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            small = cv2.resize(frame, (160, int(160 * frame.shape[0] / frame.shape[1])))
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            h = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256])
            h = cv2.normalize(h, h).flatten()
            g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            t = i / fps
            if prev_h is not None and cv2.compareHist(prev_h, h, cv2.HISTCMP_BHATTACHARYYA) > thr and t - bounds[-1] > 0.4:
                bounds.append(t)
            motion = float(np.abs(g.astype(int) - prev_g.astype(int)).mean()) if prev_g is not None else 0.0
            nf = len(det.detectMultiScale(g, 1.15, 4, minSize=(14, 14)))
            stats.append((t, cv2.Laplacian(g, cv2.CV_64F).var(), motion, float(g.mean()), nf))
            prev_h, prev_g = h, g
        i += 1
    cap.release()
    end = i / fps
    bounds.append(end)
    out = []
    for a, b in zip(bounds, bounds[1:]):
        s = [x for x in stats if a <= x[0] < b]
        if not s:
            continue
        out.append({"start": round(a, 3), "end": round(b, 3),
                    "sharp": float(np.median([x[1] for x in s])), "motion": float(np.median([x[2] for x in s])),
                    "bright": float(np.mean([x[3] for x in s])), "faces": float(np.mean([x[4] > 0 for x in s]))})
    save_json(cache, out)
    log(f"scenes: {len(out)} shots detected")
    return out


def rms_envelope(wav: Path, hop: float = 0.1) -> np.ndarray:
    """RMS per `hop` seconds (dBFS) from a mono 16-bit wav."""
    with wave.open(str(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    n = int(sr * hop)
    if n == 0 or len(x) < n:
        return np.array([-90.0])
    x = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-9)
