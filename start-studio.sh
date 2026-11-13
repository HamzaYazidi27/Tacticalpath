#!/usr/bin/env bash
# Starts autoedit Studio (web interface) and opens it in your browser.
# First run (or after an interrupted install): installs everything automatically.
cd "$(dirname "$0")"
if [ ! -f .venv/.installed ]; then
  echo "Installing autoedit (a few minutes, once)…"
  bash ./install.sh || { echo; echo "Installation failed — see the message above."; exit 1; }
fi
exec .venv/bin/python -m webui "$@"
