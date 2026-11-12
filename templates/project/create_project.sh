#!/usr/bin/env bash
# create_project.sh — scaffold one Short using the Center-Punch production system.
# Usage: create_project.sh "2026-11-20_octopus-escape"  [root=./productions]
set -euo pipefail
NAME=${1:?project name, e.g. 2026-11-20_octopus-escape}; ROOT=${2:-./productions}
P="$ROOT/$NAME"
mkdir -p "$P"/{01_PROJECT_FILES/{autosave,timelines},02_SOURCE_AROLL/{podcast_raw,selects},03_BROLL/{stock,original_shot,generated_ai,licensed},\
04_ARCHIVAL_MEDIA,05_VOICE_AND_TRANSCRIPT/{audio,transcripts},06_MUSIC,07_SFX/{whooshes,impacts,risers,foley,ui},\
08_GRAPHICS/{captions_ass,callouts,maps},09_FONTS,10_PRECOMPS/{reframed_9x16,stills_to_clips},11_EXPORTS/{review,final,archive_master},\
12_COVERS,13_LICENSES}
cat > "$P/README.md" <<MD
# $NAME
| Field | Value |
|---|---|
| Source A-roll (podcast / interview) | |
| Rights / permission for A-roll | |
| Speaker(s) | |
| Target length | 35–60 s |
| Hook line (first 2 s) | |
| Loop line (last line → first line) | |
| Status | script ▢  select ▢  rough ▢  b-roll ▢  captions ▢  grade ▢  mix ▢  QC ▢  export ▢ |
MD
cat > "$P/13_LICENSES/asset_log.csv" <<CSV
asset_file,source_url,author,license,license_url,attribution_required,date_downloaded,used_in_shots
CSV
cp "$(dirname "$0")/../luts/crisp_pop_709.cube" "$P/08_GRAPHICS/" 2>/dev/null || true
echo "created $P"
