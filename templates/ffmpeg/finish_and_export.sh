#!/usr/bin/env bash
# finish_and_export.sh — final pass for a 9:16 Short:
#   grade (CRISP-POP LUT) → clarity/sharpen (the reference's "crunchy" detail) → burn captions (ASS)
#   → loudness-normalise → YouTube Shorts H.264 export.
# Usage: finish_and_export.sh EDIT.mp4 CAPTIONS.ass OUT.mp4 [LUT_MIX=0.8] [SHARPEN=0.9]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
IN=$1; ASS=$2; OUT=$3; MIX=${4:-0.8}; SH=${5:-0.9}
LUT="$HERE/../luts/crisp_pop_709.cube"
ffmpeg -hide_banner -y -i "$IN" -filter_complex \
 "[0:v]split[a][b];[b]lut3d=file='${LUT}'[g];[a][g]blend=all_expr='A*(1-${MIX})+B*${MIX}',\
unsharp=lx=5:ly=5:la=${SH}:cx=5:cy=5:ca=0,\
ass='${ASS}',format=yuv420p[v];\
[0:a]loudnorm=I=-14:TP=-1.0:LRA=7[a]" \
 -map "[v]" -map "[a]" -r 30 -c:v libx264 -profile:v high -level 4.2 -preset slow -crf 16 -maxrate 20M -bufsize 40M \
 -g 15 -bf 2 -movflags +faststart -c:a aac -b:a 320k -ar 48000 "$OUT"
echo "exported $OUT"
