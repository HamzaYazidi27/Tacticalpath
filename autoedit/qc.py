"""Automatic quality control of a finished Short against the Center-Punch targets."""
from __future__ import annotations

import importlib.util

import numpy as np

from .render import _loudnorm_measure
from .util import ROOT


def _scene_cuts():
    spec = importlib.util.spec_from_file_location("scene_cuts", ROOT / "tools" / "forensics" / "scene_cuts.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def caption_geometry(video, samples=24):
    import cv2
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ys, hs = [], []
    for k in np.linspace(0, max(n - 1, 0), samples).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(k))
        ok, fr = cap.read()
        if not ok:
            continue
        im = fr[..., ::-1].astype(int)
        R, G, B = im[..., 0], im[..., 1], im[..., 2]
        m = (G > 170) & (R < 140) & (B < 170) & (G - R > 90) & (G - B > 60)
        Hh = im.shape[0]
        band = m[int(Hh * 0.35): int(Hh * 0.65)]
        rows = np.where(band.sum(1) > 25)[0]
        if not len(rows):
            continue
        runs = np.split(rows, np.where(np.diff(rows) > 3)[0] + 1)
        c = max(runs, key=len)
        ys.append((c[0] + c[-1]) / 2 / Hh + 0.35)
        hs.append(c[-1] - c[0])
    cap.release()
    if not ys:
        return None
    return {"frames_with_caption": len(ys), "of": samples, "centre_ratio": round(float(np.median(ys)), 3),
            "cap_height_px": float(np.median(hs))}


def run(final, plan, cfg) -> dict:
    sc = _scene_cuts()
    fps, dur, cuts, _ = sc.analyse(final, 0.30, 0.12, 18.0)
    detected = (len(cuts) - 1) / dur * 60 if dur else 0
    cap = caption_geometry(final)
    loud = _loudnorm_measure(final)
    st = plan["stats"]
    checks = []

    def chk(name, ok, value, target):
        checks.append({"check": name, "ok": bool(ok), "value": value, "target": target})

    if plan.get("mode") == "montage":
        chk("duration", dur >= min(10.0, cfg.montage_dur), round(dur, 1), f"up to {cfg.montage_dur:.0f} s (limited by usable footage)")
    else:
        chk("duration", cfg.min_dur * 0.75 <= dur <= cfg.max_dur + 1, round(dur, 1), f"{cfg.min_dur:.0f}-{cfg.max_dur:.0f} s")
    chk("cuts per minute (edit)", st["cuts_per_min"] >= 45, st["cuts_per_min"], ">= 45 (style >= 49)")
    chk("cuts per minute (detected in render)", True, round(detected, 1), "info: punch-ins on the same take are not always detected")
    chk("b-roll share", st["broll_share"] >= 0.35 or plan.get("mode") == "montage", st["broll_share"], "0.55-0.77 (>= 0.35 to pass)")
    lim = 2.0 + (st.get("teaser") or 0)
    chk("first b-roll", st["first_broll_at"] is not None and st["first_broll_at"] <= lim, st["first_broll_at"],
        "<= 1.2 s ideal" + (f" (after the {st['teaser']:.1f} s cold open)" if st.get("teaser") else ""))
    if plan.get("mode") != "montage":
        chk("hook title (first seconds)", True, plan.get("hook") or "none", "info: short curiosity line on screen")
        chk("cold open", True, f"{st['teaser']:.1f} s" if st.get("teaser") else "no", "info: strongest line first")
    if plan.get("mode") != "montage" or cfg.montage_text:
        chk("captions present", cap is not None and cap["frames_with_caption"] >= cap["of"] * 0.8,
            cap and f"{cap['frames_with_caption']}/{cap['of']}", ">= 80 % of sampled frames")
        chk("caption centre", cap is not None and 0.47 <= cap["centre_ratio"] <= 0.53, cap and cap["centre_ratio"], "0.50")
    if loud:
        chk("loudness", abs(float(loud["input_i"]) - cfg.loudness_lufs) <= 1.5, float(loud["input_i"]), f"{cfg.loudness_lufs} LUFS ±1.5")
        chk("true peak", float(loud["input_tp"]) <= cfg.true_peak + 0.5, float(loud["input_tp"]), f"<= {cfg.true_peak} dBTP")
    return {"pass": all(c["ok"] for c in checks), "checks": checks}


def markdown(report: dict, plan: dict, title: str) -> str:
    lines = [f"# {title or 'Short'}", "", f"**QC: {'PASS ✅' if report['pass'] else 'WARN ⚠️'}**", "",
             "| Check | Value | Target | |", "|---|---|---|---|"]
    for c in report["checks"]:
        lines.append(f"| {c['check']} | {c['value']} | {c['target']} | {'✅' if c['ok'] else '⚠️'} |")
    s = plan["stats"]
    lines += ["", f"Shots: {s['shots']} · duration {s['duration']:.1f} s · B-roll {s['broll_share'] * 100:.0f} %", ""]
    v = plan.get("virality")
    if v:
        from .viral import LABELS
        lines += [f"**Virality score: {v['total']}/100**" + (f" (Claude: {v['claude']})" if "claude" in v else ""), "",
                  " · ".join(f"{LABELS[k]} {round(x * 10)}/10" for k, x in v.get("parts", {}).items()), ""]
    return "\n".join(lines)
