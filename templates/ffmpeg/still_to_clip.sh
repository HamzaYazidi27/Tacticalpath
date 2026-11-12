#!/usr/bin/env bash
# still_to_clip.sh — turn a photo / generated illustration into a 9:16 B-roll clip with a slow push-in.
# The reference uses many stills/AI images as B-roll; in-shot motion could not be observed from frames,
# so the push-in (100 → 106 % over the shot, linear) is a RECOMMENDATION that keeps stills from feeling frozen.
# Usage: still_to_clip.sh IMG OUT [DURATION=1.2] [END_ZOOM=1.06]
set -euo pipefail
IMG=$1; OUT=$2; D=${3:-1.2}; ZE=${4:-1.06}
FR=$(python3 -c "print(round($D*30))")
ffmpeg -hide_banner -y -loop 1 -i "$IMG" -t "$D" -filter_complex \
 "[0:v]scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,\
zoompan=z='1+($ZE-1)*on/$FR':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=$FR:s=1080x1920:fps=30,setsar=1[v]" \
 -map "[v]" -c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p "$OUT"
