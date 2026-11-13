#!/usr/bin/env bash
# install.sh — one-time setup for autoedit (macOS / Linux / WSL). Safe to run again.
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------- system tools
if [ "$(uname)" = "Darwin" ] && ! have brew; then
  if [ -x /opt/homebrew/bin/brew ]; then eval "$(/opt/homebrew/bin/brew shellenv)";
  elif [ -x /usr/local/bin/brew ]; then eval "$(/usr/local/bin/brew shellenv)";
  else
    echo "Homebrew is needed on macOS. Install it with this command, then run ./install.sh again:"
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
  fi
fi

install_pkg() {   # install_pkg <brew name> <apt name>
  if have brew; then brew install "$1"
  elif have apt-get; then sudo apt-get update -qq && sudo apt-get install -y "$2"
  else echo "Please install $1 yourself, then run ./install.sh again."; exit 1; fi
}

# Python >= 3.10 (macOS ships 3.9, which is too old)
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if have "$c" && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  say "Installing Python 3.12…"
  install_pkg python@3.12 python3.12
  PY="$(command -v python3.12 || true)"
  [ -n "$PY" ] || { echo "Python 3.10+ not found after install. Open a new terminal and run ./install.sh again."; exit 1; }
fi
echo "Python: $("$PY" --version) ($PY)"

if ! have ffmpeg; then say "Installing ffmpeg…"; install_pkg ffmpeg ffmpeg; fi
FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
case "$FILTERS" in
  *" ass "*) echo "ffmpeg: OK (with libass captions)";;
  *) echo "ffmpeg: OK — no libass in this build, captions will be drawn by Python (same style)";;
esac

if ! have deno && ! have node; then
  say "Installing deno (needed to read YouTube)…"
  if have brew; then brew install deno; else curl -fsSL https://deno.land/install.sh | sh || true; fi
fi

# ---------------------------------------------------------------- Python environment
say "Creating the Python environment (.venv)…"
"$PY" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt
pip install -r requirements-web.txt
pip install -r requirements-vision.txt || echo "⚠ vision (CLIP) not installed — B-roll will be matched by name only"

say "Downloading the speech + vision models (once, ~1 GB)…"
python - <<'PY'
from faster_whisper import WhisperModel
WhisperModel("small", device="auto", compute_type="auto")
try:
    from transformers import CLIPModel, CLIPProcessor
    CLIPModel.from_pretrained("openai/clip-vit-base-patch32"); CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    print("vision model ready")
except Exception as e:
    print("vision model skipped:", e)
print("models ready")
PY
[ -f autoedit.config.json ] || cp autoedit.config.example.json autoedit.config.json
mkdir -p inbox outbox broll music
chmod +x start-studio.sh 2>/dev/null || true
cat <<MSG

✔ Installed.
  Web studio (easiest):   ./start-studio.sh        → opens http://127.0.0.1:8765
  Command line:           . .venv/bin/activate && python -m autoedit my_video.mp4
  Autopilot folder:       . .venv/bin/activate && python -m autoedit --watch inbox --out outbox
MSG
