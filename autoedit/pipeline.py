"""End-to-end orchestration: raw video in → finished Short(s) + report out."""
from __future__ import annotations

import dataclasses
import re
import shutil
from pathlib import Path

from . import analyze, broll, montage, planner, qc, render, selector
from .transcribe import extract_wav, transcribe
from .util import check_tools, load_json, log, probe, save_json


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:60].strip("_") or "video"


def process(src: Path, out_root: Path, cfg, keep_work: bool = False, dry_run: bool = False) -> list[Path]:
    check_tools()
    src = src.resolve()
    info = probe(src)
    if not info.get("has_video"):
        raise SystemExit(f"{src.name}: no video stream")
    name = _slug(src.stem)
    out_dir = out_root / name
    work = out_dir / "_work"
    work.mkdir(parents=True, exist_ok=True)
    save_json(work / "config.json", cfg.to_dict())
    log(f"input: {src.name} — {info['width']}x{info['height']} {info['duration']:.1f}s audio={info['has_audio']}")

    words = []
    if info["has_audio"]:
        tr = transcribe(src, work, cfg.whisper_model, cfg.language)
        words = tr["words"]
    wpm = len(words) / max(info["duration"], 1) * 60
    scenes = analyze.scenes(src, work)

    if wpm < 20:
        log(f"speech density {wpm:.0f} words/min → MONTAGE mode (no talking track)")
        plans = [montage.plan(src, info, scenes, cfg)]
        clips = [None]
    else:
        log(f"speech density {wpm:.0f} words/min → PODCAST-CLIP mode")
        env = analyze.rms_envelope(extract_wav(src, work / "audio16k.wav"))
        total = selector.est_out(words, 0, len(words) - 1, cfg.gap_trim)
        if total < cfg.min_dur:              # short input: keep the whole talk, adapt the targets
            cfg = dataclasses.replace(cfg, min_dur=max(3.0, total * 0.85), target_dur=total,
                                      max_dur=max(cfg.max_dur, total + 1), count=1)
            log(f"input speech is only {total:.1f}s (shorter than the minimum): using all of it")
        clips, _ = selector.select(words, cfg, env)
        plans = []
        for n, clip in enumerate(clips, 1):
            log(f"clip {n}: {clip['start']:.1f}–{clip['end']:.1f}s ({clip['dur']:.0f}s, {clip['source']}) «{clip['title'][:60]}»")
            needed = int(clip["dur"] * cfg.broll_share / 1.1) + 8
            found, generic = broll.resolve(clip["queries"], cfg, out_root / "_broll_cache", src, scenes, clip, needed)
            p = planner.plan(words, clip, found, generic, cfg)
            if p["stats"]["cuts_per_min"] < cfg.target_cuts_per_min - 4:   # self-correct the rhythm once
                tighter = dataclasses.replace(cfg, aroll_shot_max=1.2, aroll_shot_min=0.7)
                p2 = planner.plan(words, clip, found, generic, tighter)
                log(f"rhythm: {p['stats']['cuts_per_min']} → {p2['stats']['cuts_per_min']} cuts/min after tightening")
                p = p2
            if p["stats"]["broll_share"] < 0.35:
                log("⚠ little B-roll matched: add a --broll folder or a PEXELS_API_KEY for literal cutaways")
            plans.append(p)

    outputs = []
    for n, p in enumerate(plans, 1):
        p["source"], p["slug"], p["index"] = str(src), name, n          # makes the EDL re-renderable on its own
        p["targets"] = {"min_dur": cfg.min_dur, "max_dur": cfg.max_dur}
        if clips[n - 1]:
            p["clip"]["source_range"] = [clips[n - 1]["start"], clips[n - 1]["end"]]
        save_json(out_dir / f"{name}_short{n}_edl.json", {k: v for k, v in p.items()})
        log(f"plan {n}: {p['stats']}")
        if dry_run:
            continue
        outputs.append(render_one(p, out_dir, cfg, info))
    if not keep_work and not dry_run:
        for d in work.glob("clip*/shots"):
            shutil.rmtree(d, ignore_errors=True)
    return outputs


def render_one(p: dict, out_dir: Path, cfg, info: dict | None = None) -> Path:
    """Render one EDL to its final Short + cover, captions, credits and QC report."""
    src, name, n = Path(p["source"]), p["slug"], p["index"]
    info = info or probe(src)
    cw = out_dir / "_work" / f"clip{n}"
    cw.mkdir(parents=True, exist_ok=True)
    if p.get("mode") == "montage":
        video = render.render_video(p, src, cw)
        audio = render.render_audio_montage(p, src, cw, cfg)
    else:
        aroll = render.cut_aroll(src, p["islands"], cw / "aroll.mp4", info)
        video = render.render_video(p, aroll, cw)
        audio = render.render_audio(p, aroll, cw, cfg)
    ass = render.write_captions(p, cw, cfg)
    final = out_dir / f"{name}_short{n}.mp4"
    log("final grade + captions + encode…")
    tmp = final.with_suffix(".rendering.mp4")
    render.finish(video, audio, ass, tmp, cfg, plan=p)
    tmp.replace(final)
    shutil.copy(cw / "captions.srt", out_dir / f"{name}_short{n}.srt")
    first_b = next((s["t0"] for s in p["shots"] if s["kind"] == "B"), 1.0)
    render.cover(final, first_b + 0.3, out_dir / f"{name}_short{n}_cover.jpg")
    credits = sorted({s["asset"]["credit"] for s in p["shots"] if s["kind"] == "B" and s["asset"].get("credit")})
    (out_dir / f"{name}_short{n}_credits.txt").write_text(
        ("B-roll credits:\n" + "\n".join(credits) + "\n") if credits else "No third-party B-roll used.\n", encoding="utf-8")
    report = qc.run(final, p, cfg)
    save_json(out_dir / f"{name}_short{n}_qc.json", report)
    md = qc.markdown(report, p, p.get("title", ""))
    rng = p.get("clip", {}).get("source_range")
    if rng:
        md += f"\nSource range: {rng[0]:.1f}–{rng[1]:.1f} s · selection: {p['clip'].get('source', '')}\n"
    (out_dir / f"{name}_short{n}_report.md").write_text(md, encoding="utf-8")
    log(f"✔ {final.name} — QC {'PASS' if report['pass'] else 'WARN'}")
    for c in report["checks"]:
        if not c["ok"]:
            log(f"   ⚠ {c['check']}: {c['value']} (target {c['target']})")
    shutil.rmtree(cw / "shots", ignore_errors=True)
    return final


def rerender(edl_path: Path, cfg) -> Path:
    """Re-render an edited EDL (B-roll swapped, captions corrected…) without re-analysing the source."""
    check_tools()
    p = load_json(edl_path)
    for k, v in (p.get("targets") or {}).items():
        setattr(cfg, k, v)
    p["stats"]["broll_share"] = round(sum(s["t1"] - s["t0"] for s in p["shots"] if s["kind"] == "B")
                                      / max(p["duration"], 1e-6), 3)
    p["stats"]["first_broll_at"] = next((s["t0"] for s in p["shots"] if s["kind"] == "B"), None)
    p["stats"]["shots"] = len(p["shots"])
    p["stats"]["cuts_per_min"] = round((len(p["shots"]) - 1) / p["duration"] * 60, 1) if p["duration"] else 0
    save_json(edl_path, p)
    log(f"re-render: {edl_path.name}")
    return render_one(p, edl_path.parent, cfg)
