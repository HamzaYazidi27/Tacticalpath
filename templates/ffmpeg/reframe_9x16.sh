#!/usr/bin/env bash
# reframe_9x16.sh — podcast 16:9 (or any) → 1080x1920 vertical "A-roll" shot.
# Observed on the reference: talking heads are full-bleed 9:16 crops of horizontal podcast cameras,
# face upper-centre, alternating framings (wide ↔ punch-in) on the same take.
#
# Usage: reframe_9x16.sh IN OUT [X_CENTER=0.5] [ZOOM=1.00] [Y_CENTER=0.5] [START] [DURATION]
#   X_CENTER : horizontal centre of the crop as fraction of source width (where the face is)
#   ZOOM     : 1.00 = full-height crop; 1.12 / 1.20 = punch-in variants (use on alternate cuts)
#   Y_CENTER : vertical centre (0.45 keeps headroom tight like the reference)
# Example: reframe_9x16.sh podcast.mp4 a_cam_punch.mp4 0.62 1.15 0.45 83.4 2.1
set -euo pipefail
IN=$1; OUT=$2; XC=${3:-0.5}; Z=${4:-1.00}; YC=${5:-0.5}; SS=${6:-}; DUR=${7:-}
SEEK=(); [ -n "$SS" ] && SEEK=(-ss "$SS"); LEN=(); [ -n "$DUR" ] && LEN=(-t "$DUR")
VF="crop=w='min(iw,ih*9/16)/${Z}':h='ih/${Z}':x='max(0,min(iw-ow,iw*${XC}-ow/2))':y='max(0,min(ih-oh,ih*${YC}-oh/2))',scale=1080:1920:flags=lanczos,setsar=1,fps=30"
ffmpeg -hide_banner -y "${SEEK[@]}" -i "$IN" "${LEN[@]}" -vf "$VF" -c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p -c:a aac -b:a 320k "$OUT"
