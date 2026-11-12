"""Shared helpers: logging, subprocess, ffprobe, paths."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # repository root
FPS = 30
W, H = 1080, 1920

_T0 = time.time()


def log(msg: str) -> None:
    print(f"[autoedit {time.time() - _T0:6.1f}s] {msg}", flush=True)


def run(cmd: list[str], quiet: bool = True) -> subprocess.CompletedProcess:
    """Run a command; raise with stderr tail on failure."""
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if p.returncode != 0:
        tail = "\n".join((p.stderr or "").strip().splitlines()[-15:])
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str, cmd[:6]))} …\n{tail}")
    if not quiet and p.stdout:
        print(p.stdout)
    return p


def ffmpeg(*args: str) -> subprocess.CompletedProcess:
    return run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args])


def probe(path: Path) -> dict:
    p = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    d = json.loads(p.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    info = {"duration": float(d["format"].get("duration", 0) or 0), "has_audio": a is not None, "has_video": v is not None}
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = abs(int(sd["rotation"]))
        if rot in (90, 270):
            w, h = h, w
        num, den = (v.get("avg_frame_rate") or "30/1").split("/")
        info.update(width=w, height=h, fps=(float(num) / float(den)) if float(den) else 30.0)
    return info


def check_tools() -> None:
    missing = [t for t in ("ffmpeg", "ffprobe") if not shutil.which(t)]
    if missing:
        sys.exit(f"Missing required tools: {', '.join(missing)} — install ffmpeg (with libass).")
    p = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    if " ass " not in p.stdout:
        sys.exit("Your ffmpeg has no libass (filter 'ass'). Install a full ffmpeg build.")


def frames(t: float) -> int:
    return int(round(t * FPS))


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
