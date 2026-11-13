#!/usr/bin/env bash
# Starts autoedit Studio (web interface) and opens it in your browser.
cd "$(dirname "$0")"
. .venv/bin/activate
exec python -m webui "$@"
