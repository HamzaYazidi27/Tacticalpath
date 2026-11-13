#!/usr/bin/env bash
# Starts autoedit Studio (web interface) and opens it in your browser.
# First run: installs everything automatically (./install.sh).
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "First launch: installing autoedit (a few minutes, once)…"
  bash ./install.sh || { echo "Installation failed — see the message above."; exit 1; }
fi
exec .venv/bin/python -m webui "$@"
