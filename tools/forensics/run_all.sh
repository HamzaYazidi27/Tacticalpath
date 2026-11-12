#!/usr/bin/env bash
# run_all.sh — run every forensic measurement on a folder of legally obtained Shorts.
# Usage: bash tools/forensics/run_all.sh analysis_input/  [reports_dir]
# Produces reports/<name>_shots.csv, _rhythm.json, _audio.json and reports/SUMMARY.json
set -euo pipefail
IN="${1:?folder with .mp4/.webm files}"
OUT="${2:-reports}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT"
shopt -s nullglob
files=("$IN"/*.mp4 "$IN"/*.webm "$IN"/*.mkv "$IN"/*.mov)
[ ${#files[@]} -eq 0 ] && { echo "no media in $IN"; exit 1; }
for f in "${files[@]}"; do
  n="$(basename "${f%.*}")"
  echo "== $n"
  python3 "$HERE/scene_cuts.py" "$f" --out "$OUT/$n" > /dev/null
  python3 "$HERE/audio_profile.py" "$f" --out "$OUT/$n" > /dev/null
  python3 "$HERE/caption_sampler.py" "$f" --video-samples 40 > "$OUT/${n}_captions.json" || echo "  (no green captions found)"
done
python3 - "$OUT" <<'PY'
import json, glob, statistics as st, sys
out = sys.argv[1]
R = [json.load(open(p)) for p in sorted(glob.glob(f"{out}/*_rhythm.json"))]
A = [json.load(open(p)) for p in sorted(glob.glob(f"{out}/*_audio.json"))]
med = lambda xs: round(st.median([x for x in xs if x is not None]), 2) if any(x is not None for x in xs) else None
summary = {
  "videos": len(R),
  "cuts_per_minute": {"median": med([r["cuts_per_minute"] for r in R]), "range": [min(r["cuts_per_minute"] for r in R), max(r["cuts_per_minute"] for r in R)]},
  "shot_median_s": {"median": med([r["shot_median_s"] for r in R])},
  "cuts_in_first_3s": {"median": med([r["cuts_in_first"]["3s"] for r in R])},
  "duration_s": {"median": med([r["duration_s"] for r in R]), "range": [min(r["duration_s"] for r in R), max(r["duration_s"] for r in R)]},
  "integrated_lufs": {"median": med([a["integrated_lufs"] for a in A])},
  "true_peak_dbtp": {"median": med([a["true_peak_dbtp"] for a in A])},
  "tempo_bpm": {"values": [a.get("tempo_bpm_estimate") for a in A]},
}
json.dump(summary, open(f"{out}/SUMMARY.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
PY
