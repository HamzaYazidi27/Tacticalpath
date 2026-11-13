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


def proc_env() -> dict:
    """Environment for ffmpeg/ffprobe: they only read `http_proxy`, so forward HTTPS_PROXY when set."""
    import os
    env = dict(os.environ)
    px = env.get("HTTPS_PROXY") or env.get("https_proxy")
    if px and not env.get("http_proxy"):
        env["http_proxy"] = px
    return env


def run(cmd: list[str], quiet: bool = True) -> subprocess.CompletedProcess:
    """Run a command; raise with stderr tail on failure."""
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, env=proc_env())
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


EXTRA_PATHS = ["/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin", "/snap/bin",
               str(Path.home() / ".deno" / "bin"), r"C:\ffmpeg\bin", r"C:\Program Files\ffmpeg\bin"]


def fix_path() -> None:
    """Apps started by double-click (Finder, Explorer) often miss Homebrew/winget folders in PATH."""
    import os
    cur = os.environ.get("PATH", "").split(os.pathsep)
    add = [d for d in EXTRA_PATHS if Path(d).is_dir() and d not in cur]
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links"
    if os.environ.get("LOCALAPPDATA") and local.is_dir() and str(local) not in cur:
        add.append(str(local))
    if add:
        os.environ["PATH"] = os.pathsep.join(cur + add)


fix_path()
_LIBASS = None


_FFMAJOR = None


def ffmpeg_major() -> int:
    """Major version of ffmpeg (git/nightly builds count as new)."""
    global _FFMAJOR
    import os
    if os.environ.get("AUTOEDIT_FFMPEG_MAJOR"):          # testing hook
        return int(os.environ["AUTOEDIT_FFMPEG_MAJOR"])
    if _FFMAJOR is None:
        import re
        out = subprocess.run(["ffmpeg", "-hide_banner", "-version"], capture_output=True, text=True).stdout
        m = re.search(r"ffmpeg version n?(\d+)\.", out)
        _FFMAJOR = int(m.group(1)) if m else 99
    return _FFMAJOR


def filter_file_args(path) -> list:
    """Read a filtergraph from a file. '-filter_complex_script' was removed in recent ffmpeg (7.1+/8);
    the replacement '-/filter_complex <file>' only exists since 7.0 — use what this ffmpeg understands."""
    return ["-/filter_complex", str(path)] if ffmpeg_major() >= 7 else ["-filter_complex_script", str(path)]


def has_libass() -> bool:
    """True when ffmpeg can burn ASS captions. Without it captions are drawn in Python instead."""
    global _LIBASS
    import os
    if os.environ.get("AUTOEDIT_NO_LIBASS"):
        return False
    if _LIBASS is None:
        p = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
        _LIBASS = " ass " in p.stdout
    return _LIBASS


def check_tools() -> None:
    missing = [t for t in ("ffmpeg", "ffprobe") if not shutil.which(t)]
    if missing:
        sys.exit(f"ERROR: ffmpeg not found ({', '.join(missing)} missing). Install it — macOS: brew install ffmpeg · "
                 f"Windows: winget install Gyan.FFmpeg · Linux: sudo apt install ffmpeg — then restart the studio.")
    if not has_libass():
        log("note: this ffmpeg has no libass — captions will be drawn by Python (same style, no pop animation)")


def frames(t: float) -> int:
    return int(round(t * FPS))


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
