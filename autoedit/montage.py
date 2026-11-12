"""Montage mode: footage without speech → best moments cut at ~1 s rhythm, optional text captions + music."""
from __future__ import annotations

import numpy as np

from .util import FPS


def _q(t):
    return round(round(t * FPS) / FPS, 4)


def plan(src, info, scene_list, cfg):
    usable = [s for s in scene_list if s["end"] - s["start"] >= 0.7 and s["bright"] >= 20]
    if not usable:  # one long take: slice it
        d = info["duration"]
        usable = [{"start": t, "end": min(t + 2.0, d), "sharp": 1.0, "motion": 1.0, "bright": 100, "faces": 0}
                  for t in np.arange(0, max(d - 1, 0.1), 2.0)]
    sh = np.array([s["sharp"] for s in usable]) + 1
    mo = np.array([s["motion"] for s in usable]) + 0.5
    score = np.log(sh) / max(np.log(sh).max(), 1e-6) + 0.6 * mo / mo.max()
    pattern = [1.2, 0.9, 1.0, 1.4, 0.8, 1.1]           # ~1 s average, varied
    # slice every scene into ~1 s windows (several per scene), keep 0.25 s margins
    windows = []
    for si, (s, sc) in enumerate(zip(usable, score)):
        t, k = s["start"] + 0.25, 0
        while t + 0.8 <= s["end"] - 0.25:
            d = min(pattern[(si + k) % len(pattern)], s["end"] - 0.25 - t)
            windows.append({"scene": si, "in": round(t, 3), "d": d, "score": float(sc) - 0.05 * k})
            t += d + 0.35
            k += 1
    total_avail = sum(w["d"] for w in windows)
    budget = min(cfg.montage_dur, total_avail)
    # hook = best window overall; then round-robin through scenes in chronological order (no scene twice in a row)
    windows.sort(key=lambda w: -w["score"])
    order, used, t, last_scene = [], set(), 0.0, None
    if windows:
        order.append(windows[0])
        used.add(id(windows[0]))
        t, last_scene = windows[0]["d"], windows[0]["scene"]
    by_scene = {}
    for w in sorted(windows, key=lambda w: (w["scene"], w["in"])):
        if id(w) not in used:
            by_scene.setdefault(w["scene"], []).append(w)
    scenes_cycle = sorted(by_scene)
    while t < budget and any(by_scene.values()):
        progressed = False
        for sc in scenes_cycle:
            if t >= budget:
                break
            if by_scene.get(sc) and (sc != last_scene or len([x for x in by_scene.values() if x]) == 1):
                w = by_scene[sc].pop(0)
                order.append(w)
                t += w["d"]
                last_scene = sc
                progressed = True
        if not progressed:
            break
    shots, t = [], 0.0
    for w in order:
        shots.append({"t0": _q(t), "t1": _q(t + w["d"]), "kind": "B", "in": w["in"],
                      "asset": {"path": str(src), "kind": "video", "source": "input", "credit": ""}})
        t = _q(t + w["d"])
    D = shots[-1]["t1"] if shots else 0
    words = []
    if cfg.montage_text:
        toks = cfg.montage_text.split()
        step = D / max(len(toks), 1)
        words = [{"word": w, "start": round(i * step, 3), "end": round((i + 1) * step, 3)} for i, w in enumerate(toks)]
    stats = {"duration": D, "shots": len(shots), "cuts_per_min": round((len(shots) - 1) / D * 60, 1) if D else 0,
             "broll_share": 1.0, "first_broll_at": 0.0, "jump_cuts_removed_s": 0}
    return {"mode": "montage", "duration": D, "islands": [], "words": words, "shots": shots, "stats": stats,
            "title": "montage", "clip": {"start": 0, "end": info["duration"], "source": "montage"}}
