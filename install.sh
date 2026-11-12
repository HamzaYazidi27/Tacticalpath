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
ffmpeg -hide_banner -filters 2>/dev/null | grep -q " ass " || { echo "Your ffmpeg lacks libass (captions). Install a full build."; exit 1; }
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
echo "Downloading the speech model (once)…"
python - <<'PY'
from faster_whisper import WhisperModel
WhisperModel("small", device="auto", compute_type="auto")
print("model ready")
PY
[ -f autoedit.config.json ] || cp autoedit.config.example.json autoedit.config.json
mkdir -p inbox outbox broll music
cat <<MSG

✔ Installed.
  1. Edit autoedit.config.json (brand name, optional Pexels key folder settings).
  2. Optional but recommended: export PEXELS_API_KEY=...   (free: https://www.pexels.com/api/)
  3. Run once:      . .venv/bin/activate && python -m autoedit my_video.mp4
     Or autopilot:  . .venv/bin/activate && python -m autoedit --watch inbox --out outbox
MSG
