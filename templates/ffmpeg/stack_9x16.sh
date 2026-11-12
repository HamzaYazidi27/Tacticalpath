#!/usr/bin/env bash
# stack_9x16.sh — two sources stacked top/bottom (1080x960 each). Observed occasionally (≈1 % of frames):
# two podcast speakers stacked, or reference footage on top + speaker reacting below.
# Usage: stack_9x16.sh TOP BOTTOM OUT [DURATION]   (audio taken from BOTTOM)
set -euo pipefail
T=$1; B=$2; OUT=$3; DUR=${4:-}
LEN=(); [ -n "$DUR" ] && LEN=(-t "$DUR")
ffmpeg -hide_banner -y -i "$T" -i "$B" "${LEN[@]}" -filter_complex \
 "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[t];\
  [1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[b];[t][b]vstack,setsar=1,fps=30[v]" \
 -map "[v]" -map 1:a? -c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p -c:a aac -b:a 320k "$OUT"
