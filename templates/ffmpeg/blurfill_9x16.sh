#!/usr/bin/env bash
# blurfill_9x16.sh — fit a horizontal / 4:5 source into 1080x1920 over a blurred, darkened copy of itself.
# Observed (≈2 % of sampled frames): podcast frame placed high, blurred extension underneath.
# Usage: blurfill_9x16.sh IN OUT [FG_WIDTH=1080] [FG_Y=top|center] [START] [DURATION]
set -euo pipefail
IN=$1; OUT=$2; FW=${3:-1080}; POS=${4:-top}; SS=${5:-}; DUR=${6:-}
SEEK=(); [ -n "$SS" ] && SEEK=(-ss "$SS"); LEN=(); [ -n "$DUR" ] && LEN=(-t "$DUR")
[ "$POS" = top ] && Y=0 || Y="(H-h)/2"
ffmpeg -hide_banner -y "${SEEK[@]}" -i "$IN" "${LEN[@]}" -filter_complex \
 "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40,eq=brightness=-0.06:saturation=1.1[bg];\
  [0:v]scale=${FW}:-2:flags=lanczos[fg];[bg][fg]overlay=x=(W-w)/2:y=${Y},setsar=1,fps=30[v]" \
 -map "[v]" -map 0:a? -c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p -c:a aac -b:a 320k "$OUT"
