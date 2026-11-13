"""On-demand B-roll search, used by the web interface to propose alternatives for one shot.

python -m autoedit.search "glass of water" --cache autoedit_out/_broll_cache [--photos] [--sources mixkit,openverse]
Prints a JSON list of candidate assets (best first)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import broll
from .config import Config


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--cache", default="autoedit_out/_broll_cache")
    ap.add_argument("--config")
    ap.add_argument("--sources")
    ap.add_argument("--photos", action="store_true", help="search photos instead of videos")
    a = ap.parse_args(argv)
    cfg = Config.load(Path(a.config) if a.config else (Path("autoedit.config.json")
                                                       if Path("autoedit.config.json").exists() else None))
    cfg.vision = "on" if cfg.vision == "auto" else cfg.vision
    if a.sources:
        cfg.broll_sources = [x.strip() for x in a.sources.split(",") if x.strip()]
    res = broll.candidates(a.query, cfg, Path(a.cache), photos=a.photos)
    print("@@RESULT@@" + json.dumps(res))


if __name__ == "__main__":
    main()
