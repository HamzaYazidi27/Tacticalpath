"""Settings. Defaults come from the measured Center-Punch profile (docs/07_style_profile.json).

Override any field with a JSON file (``--config autoedit.config.json``) or CLI flags.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Config:
    # --- output / clip selection
    min_dur: float = 30.0            # seconds
    max_dur: float = 60.0
    target_dur: float = 45.0
    count: int = 1                   # number of Shorts to cut from one input
    # --- transcription
    whisper_model: str = "small"     # tiny | base | small | medium | large-v3
    language: str | None = None      # None = auto-detect
    # --- intelligence (optional Claude)
    llm: str = "auto"                # auto | on | off
    llm_model: str = "claude-opus-5-5"
    # --- rhythm (measured: >= 49 cuts/min, ~1 s shots, 64-77 % B-roll)
    target_cuts_per_min: float = 52.0
    broll_share: float = 0.60
    aroll_shot_min: float = 0.8
    aroll_shot_max: float = 1.6
    broll_shot_min: float = 0.8
    broll_shot_max: float = 1.8
    first_broll_by: float = 1.2
    max_broll_run: float = 5.5       # return to the speaker at least this often
    end_on_speaker: float = 1.4      # last N seconds stay on the speaker
    gap_trim: float = 0.30           # pauses longer than this are cut (jump cut)
    punch_scales: tuple = (1.00, 1.12, 1.00, 1.20)
    # --- look
    brand: str = ""                  # watermark text, '' = none
    brand_accent_split: int | None = None
    lut_mix: float = 0.8
    sharpen: float = 0.9
    # --- audio (recommendations, unverified on the reference)
    music_db_under_voice: float = -19.0
    whoosh_share: float = 0.18       # share of B-roll entrances that get a whoosh
    loudness_lufs: float = -14.0
    true_peak: float = -1.0
    # --- B-roll sources
    broll_dirs: list = field(default_factory=list)
    music_dirs: list = field(default_factory=list)
    pexels_key: str = field(default_factory=lambda: os.environ.get("PEXELS_API_KEY", ""))
    pixabay_key: str = field(default_factory=lambda: os.environ.get("PIXABAY_API_KEY", ""))
    online_broll: bool = True
    # social video first: your own links (YouTube/TikTok…), then YouTube Creative Commons, then stock video.
    broll_sources: list = field(default_factory=lambda: ["library", "urls", "youtube_cc", "pexels", "pixabay",
                                                         "mixkit", "wikimedia", "openverse"])   # + "archive" on request
    allow_photos: bool = False                        # B-roll is VIDEO only unless this is true
    broll_urls: list = field(default_factory=list)   # links (or .txt files of links) to footage you may reuse
    vision: str = "auto"                              # auto | on | off — CLIP check that B-roll shows the word
    # --- montage mode (no speech)
    montage_text: str = ""
    montage_dur: float = 35.0

    @classmethod
    def load(cls, path: Path | None) -> "Config":
        cfg = cls()
        if path and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, tuple(v) if k == "punch_scales" else v)
        return cfg

    def to_dict(self) -> dict:
        d = asdict(self)
        d["pexels_key"] = "***" if self.pexels_key else ""
        d["pixabay_key"] = "***" if self.pixabay_key else ""
        return d
