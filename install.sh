#!/usr/bin/env bash
# install.sh — one-time setup for autoedit (macOS / Linux / WSL).
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Install Python 3.10+ first."; exit 1; }
if ! command -v ffmpeg >/dev/null; then
  echo "ffmpeg not found."
  if command -v brew >/dev/null; then brew install ffmpeg
  elif command -v apt-get >/dev/null; then sudo apt-get update && sudo apt-get install -y ffmpeg
  else echo "Install ffmpeg (with libass) and re-run."; exit 1; fi
fi
FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
case "$FILTERS" in *" ass "*) ;; *) echo "Your ffmpeg lacks libass (captions). Install a full build."; exit 1;; esac
if ! command -v deno >/dev/null && ! command -v node >/dev/null; then
  echo "⚠ Neither deno nor node found: YouTube Creative Commons B-roll needs one of them."
  echo "  Install deno: curl -fsSL https://deno.land/install.sh | sh   (or: brew install deno)"
fi
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
pip install -r requirements-web.txt
pip install -r requirements-vision.txt || echo "⚠ vision (CLIP) not installed — B-roll will be matched by name only"
echo "Downloading the speech + vision models (once)…"
python - <<'PY'
from faster_whisper import WhisperModel
WhisperModel("small", device="auto", compute_type="auto")
try:
    from transformers import CLIPModel, CLIPProcessor
    CLIPModel.from_pretrained("openai/clip-vit-base-patch32"); CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
except Exception as e:
    print("vision model skipped:", e)
print("models ready")
PY
[ -f autoedit.config.json ] || cp autoedit.config.example.json autoedit.config.json
mkdir -p inbox outbox broll music
cat <<MSG

✔ Installed.
  1. Edit autoedit.config.json (brand name, optional Pexels key folder settings).
  2. Optional but recommended: export PEXELS_API_KEY=...   (free: https://www.pexels.com/api/)
  3. Run once:      . .venv/bin/activate && python -m autoedit my_video.mp4
     Or autopilot:  . .venv/bin/activate && python -m autoedit --watch inbox --out outbox
     Web studio:    ./start-studio.sh   (opens http://127.0.0.1:8765)
MSG
