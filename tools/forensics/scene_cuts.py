#!/usr/bin/env python3
"""
scene_cuts.py — measure editing rhythm of a video file.

Outputs (next to --out prefix):
  <prefix>_shots.csv     one row per shot: index, start, end, duration
  <prefix>_rhythm.json   cuts/min, mean/median shot, opening-window counts (3/5/10/30 s),
                         per-third intensity, punch-in candidates

Method: HSV 2-D histogram (H16 x S8) Bhattacharyya distance between consecutive frames,
analysed at the native frame rate. A cut is declared when distance > --threshold (default 0.30)
AND the frame is at least --min-gap seconds after the previous cut. "Punch-in candidates" are
frames with low histogram change but high pixel change (same colours, different scale) —
the signature of a digital zoom/jump on the same take.

Requires: opencv-python-headless, numpy.   pip install opencv-python-headless numpy
Usage   : python3 scene_cuts.py short.mp4 --out reports/short
"""
import argparse
import csv
import json
import statistics as st
from pathlib import Path

import cv2
import numpy as np


def hist(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256])
    return cv2.normalize(h, h).flatten()


def analyse(path, threshold, min_gap, punch_pix):
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    prev_h = prev_small = None
    cuts, punches = [0.0], []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.resize(frame, (90, 160), interpolation=cv2.INTER_AREA)
        h = hist(small)
        t = i / fps
        if prev_h is not None:
            hd = cv2.compareHist(prev_h, h, cv2.HISTCMP_BHATTACHARYYA)
            pd = float(np.abs(small.astype(int) - prev_small.astype(int)).mean())
            if hd > threshold and t - cuts[-1] >= min_gap:
                cuts.append(t)
            elif hd < threshold * 0.5 and pd > punch_pix and t - cuts[-1] >= min_gap:
                punches.append(round(t, 3))
        prev_h, prev_small = h, small
        i += 1
    dur = i / fps
    cap.release()
    return fps, dur, cuts, punches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--threshold", type=float, default=0.30)
    ap.add_argument("--min-gap", type=float, default=0.12)
    ap.add_argument("--punch-pix", type=float, default=18.0)
    a = ap.parse_args()
    fps, dur, cuts, punches = analyse(a.video, a.threshold, a.min_gap, a.punch_pix)
    bounds = cuts + [dur]
    shots = [(k, bounds[k], bounds[k + 1], bounds[k + 1] - bounds[k]) for k in range(len(cuts))]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(f"{a.out}_shots.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["shot", "start_s", "end_s", "duration_s"])
        for s in shots:
            w.writerow([s[0], round(s[1], 3), round(s[2], 3), round(s[3], 3)])
    durs = [s[3] for s in shots]
    n_cuts = len(cuts) - 1
    thirds = [sum(1 for c in cuts[1:] if dur * k / 3 <= c < dur * (k + 1) / 3) for k in range(3)]
    report = {
        "file": a.video.name, "fps": round(fps, 3), "duration_s": round(dur, 2),
        "shots": len(shots), "cuts": n_cuts,
        "cuts_per_minute": round(n_cuts / dur * 60, 1) if dur else None,
        "shot_mean_s": round(st.mean(durs), 3), "shot_median_s": round(st.median(durs), 3),
        "shot_p10_s": round(float(np.percentile(durs, 10)), 3), "shot_p90_s": round(float(np.percentile(durs, 90)), 3),
        "cuts_in_first": {f"{w}s": sum(1 for c in cuts[1:] if c < w) for w in (3, 5, 10, 30)},
        "cuts_per_third": thirds,
        "punch_in_candidates_s": punches,
        "method": f"HSV hist Bhattacharyya > {a.threshold}, min gap {a.min_gap}s",
    }
    Path(f"{a.out}_rhythm.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
