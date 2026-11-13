"""Command line: one file, a folder, or a watched inbox."""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

from .config import Config
from .pipeline import process
from .util import log

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}

EPILOG = """examples:
  python -m autoedit podcast.mp4
  python -m autoedit podcast.mp4 --broll ~/broll --music ~/music --brand WILDFRAME --count 3
  python -m autoedit --watch inbox/ --out outbox/          # drop videos in inbox/, Shorts appear in outbox/
environment:
  PEXELS_API_KEY / PIXABAY_API_KEY   automatic stock B-roll for every keyword (free keys)
  ANTHROPIC_API_KEY                  Claude chooses the best story and writes B-roll queries (optional)
"""


def build_cfg(a) -> Config:
    cfg = Config.load(Path(a.config) if a.config else (Path("autoedit.config.json") if Path("autoedit.config.json").exists() else None))
    for k in ("count", "brand", "whisper_model", "language", "llm", "min_dur", "max_dur"):
        v = getattr(a, k)
        if v is not None:
            setattr(cfg, k, v)
    if a.target is not None:
        cfg.target_dur = a.target
    cfg.target_dur = min(max(cfg.target_dur, cfg.min_dur), cfg.max_dur)
    if a.broll:
        cfg.broll_dirs = list(cfg.broll_dirs) + a.broll
    if a.music:
        cfg.music_dirs = list(cfg.music_dirs) + a.music
    if a.broll_urls:
        cfg.broll_urls = list(cfg.broll_urls) + a.broll_urls
    if a.sources:
        cfg.broll_sources = [x.strip() for x in a.sources.split(",") if x.strip()]
    if a.vision:
        cfg.vision = a.vision
    if a.offline:
        cfg.online_broll = False
    if a.text:
        cfg.montage_text = a.text
    return cfg


def watch(inbox: Path, outbox: Path, cfg, keep_work: bool, poll: float = 10.0):
    done = inbox / "_done"
    failed = inbox / "_failed"
    for d in (done, failed, outbox):
        d.mkdir(parents=True, exist_ok=True)
    sizes = {}
    log(f"watching {inbox} — drop videos there; results go to {outbox} (Ctrl+C to stop)")
    while True:
        for p in sorted(inbox.iterdir()):
            if not p.is_file() or p.suffix.lower() not in VIDEO_EXT:
                continue
            sz = p.stat().st_size
            if sizes.get(p) != sz:          # still being copied — wait for a stable size
                sizes[p] = sz
                continue
            try:
                process(p, outbox, cfg, keep_work)
                shutil.move(str(p), done / p.name)
            except Exception as e:  # keep the watcher alive
                log(f"✖ {p.name}: {e}")
                shutil.move(str(p), failed / p.name)
            sizes.pop(p, None)
        time.sleep(poll)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="autoedit", description="Raw video in → finished Center-Punch Short out.",
                                 epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", help="video file(s) or folder(s)")
    ap.add_argument("--out", default="autoedit_out", help="output folder (default: autoedit_out)")
    ap.add_argument("--watch", metavar="INBOX", help="process every video dropped into this folder, forever")
    ap.add_argument("--broll", action="append", help="folder of B-roll clips/images (repeatable)")
    ap.add_argument("--music", action="append", help="folder of music tracks (repeatable)")
    ap.add_argument("--broll-urls", action="append", dest="broll_urls",
                    help="link, or .txt file of links (YouTube, TikTok…), to footage you own or may reuse (repeatable)")
    ap.add_argument("--sources", help="B-roll source order, comma separated "
                    "(library,urls,pexels,pixabay,wikimedia,youtube_cc,archive)")
    ap.add_argument("--vision", choices=["auto", "on", "off"], help="CLIP visual check of B-roll (auto = if installed)")
    ap.add_argument("--brand", help="watermark text locked under the captions")
    ap.add_argument("--count", type=int, help="number of Shorts to cut from each input (default 1)")
    ap.add_argument("--min-dur", type=float, dest="min_dur")
    ap.add_argument("--max-dur", type=float, dest="max_dur")
    ap.add_argument("--target", type=float, help="preferred duration in seconds (default 45)")
    ap.add_argument("--language", help="force transcription language, e.g. en, fr, es")
    ap.add_argument("--whisper-model", dest="whisper_model", help="tiny|base|small|medium|large-v3 (default small)")
    ap.add_argument("--llm", choices=["auto", "on", "off"], help="use Claude for story selection (auto = if ANTHROPIC_API_KEY)")
    ap.add_argument("--text", help="montage mode only: caption text to show over speechless footage")
    ap.add_argument("--offline", action="store_true", help="never download stock B-roll")
    ap.add_argument("--config", help="JSON config file (default: ./autoedit.config.json if present)")
    ap.add_argument("--dry-run", action="store_true", help="analyse and plan only, no rendering")
    ap.add_argument("--keep-work", action="store_true", help="keep intermediate shot renders")
    a = ap.parse_args(argv)
    cfg = build_cfg(a)
    out = Path(a.out)
    if a.watch:
        return watch(Path(a.watch), out, cfg, a.keep_work)
    if not a.inputs:
        ap.error("give a video file/folder, or --watch INBOX")
    files = []
    for i in a.inputs:
        p = Path(i)
        files += sorted(x for x in p.iterdir() if x.suffix.lower() in VIDEO_EXT) if p.is_dir() else [p]
    results = []
    for f in files:
        results += process(f, out, cfg, a.keep_work, a.dry_run)
    if results:
        log("done:\n  " + "\n  ".join(str(r) for r in results))


if __name__ == "__main__":
    main()
