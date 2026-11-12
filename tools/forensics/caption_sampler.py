#!/usr/bin/env python3
"""
caption_sampler.py — measure a burned-in caption system from frames.

Works on still images (PNG/JPG, e.g. YouTube cover frames) or on a video (samples N frames).
Detects saturated caption pixels of a given hue family (default: neon green) inside a vertical
search band and reports: vertical centre (px and ratio), cap height, block width, fill colour
(median / mean / p90 / dominant bins), top-vs-bottom gradient, hard-shadow colour below glyphs.

This is the exact procedure used for evidence/measurements.json.

Requires: pillow, numpy (opencv only for video input).
Usage   : python3 caption_sampler.py frames/*.jpg
          python3 caption_sampler.py short.mp4 --video-samples 40
          python3 caption_sampler.py frames/*.png --hue yellow
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

HUES = {  # (channel that dominates, min value, min margin over the other two)
    "green": lambda R, G, B: (G > 170) & (R < 140) & (B < 170) & (G - R > 90) & (G - B > 60),
    "yellow": lambda R, G, B: (R > 190) & (G > 170) & (B < 110),
    "red": lambda R, G, B: (R > 180) & (G < 90) & (B < 90),
    "white": lambda R, G, B: (R > 225) & (G > 225) & (B > 225),
}


def hexs(c):
    return "#%02X%02X%02X" % tuple(int(round(x)) for x in c)


def frames_from(paths, video_samples):
    for p in paths:
        p = Path(p)
        if p.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv"):
            import cv2
            cap = cv2.VideoCapture(str(p))
            n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            for k in np.linspace(0, n - 1, video_samples).astype(int):
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(k))
                ok, fr = cap.read()
                if ok:
                    yield f"{p.name}@{k}", fr[..., ::-1].astype(int)
        else:
            yield p.name, np.asarray(Image.open(p).convert("RGB")).astype(int)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--hue", choices=HUES, default="green")
    ap.add_argument("--band", type=float, nargs=2, default=[0.30, 0.75], help="vertical search band as fractions")
    ap.add_argument("--video-samples", type=int, default=30)
    a = ap.parse_args()
    ys, hs, ws, px_all, tops, bots, shadows = [], [], [], [], [], [], []
    for name, im in frames_from(a.inputs, a.video_samples):
        H = im.shape[0]
        R, G, B = im[..., 0], im[..., 1], im[..., 2]
        m = HUES[a.hue](R, G, B)
        b0, b1 = int(H * a.band[0]), int(H * a.band[1])
        rows = np.where(m[b0:b1].sum(1) > 25)[0]
        if not len(rows):
            continue
        runs = np.split(rows, np.where(np.diff(rows) > 3)[0] + 1)
        cap = max(runs, key=len)
        y0, y1 = cap[0] + b0, cap[-1] + b0
        cols = np.where(m[y0:y1 + 1].sum(0) > 0)[0]
        ys.append((y0 + y1) / 2 / H)
        hs.append(y1 - y0)
        ws.append(int(cols[-1] - cols[0]))
        sel = m[y0:y1 + 1]
        px_all.append(im[y0:y1 + 1][sel])
        q = max(1, (y1 - y0) // 4)
        tops.append(im[y0:y0 + q][m[y0:y0 + q]].mean(0))
        bots.append(im[y1 - q:y1 + 1][m[y1 - q:y1 + 1]].mean(0))
        below = np.zeros_like(m)
        below[6:] = m[:-6]
        c = below & ~m
        sp = im[c]
        sp = sp[sp.sum(1) < 220]
        if len(sp):
            shadows.append(sp.mean(0))
    if not ys:
        raise SystemExit("no caption pixels found — try --hue / --band")
    allp = np.concatenate(px_all)
    dom = Counter(map(tuple, (allp // 8 * 8))).most_common(5)
    rep = {
        "frames_with_caption": len(ys),
        "vertical_centre_ratio_median": round(float(np.median(ys)), 3),
        "cap_height_px_median": float(np.median(hs)), "cap_height_px_range": [int(min(hs)), int(max(hs))],
        "block_width_px_median": float(np.median(ws)), "block_width_px_range": [int(min(ws)), int(max(ws))],
        "fill_median": hexs(np.median(allp, 0)), "fill_mean": hexs(allp.mean(0)),
        "fill_p90": hexs(np.percentile(allp, 90, axis=0)),
        "fill_dominant_bins": [hexs(k) for k, _ in dom],
        "top_quarter_mean": hexs(np.mean(tops, 0)), "bottom_quarter_mean": hexs(np.mean(bots, 0)),
        "shadow_below_mean": hexs(np.mean(shadows, 0)) if shadows else None,
    }
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
