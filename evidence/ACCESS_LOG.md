# Access log — what was and was not inspected

Session date: 2026-11-12. Everything below was done from a cloud container whose network allowed only
`youtube.com`, `i.ytimg.com` and `youtubei.googleapis.com` (added for this analysis).

| Step | Result |
|---|---|
| Channel page `@Tacticalpath` (flat listing) | ✅ name, ID, ~55 K subscribers, description, **55 Shorts** with titles + approx. views |
| "Videos" / "Live" tabs | ✅ checked — **do not exist** (Shorts-only channel) |
| Pagination beyond the first 55 Shorts | ❌ HTTP 403 on the continuation request — total count unknown |
| Full player metadata | ✅ for **1 video** (`oB518y0L7fI`, 43 s, 30 fps, uploaded 2026-10-21); ❌ others: "Sign in to confirm you're not a bot" |
| Video/audio streams | ❌ googlevideo returned 403 (PO-token / bot check). **Not circumvented** — no cookies, tokens or evasion used |
| Watching in headless Chromium | ❌ same bot wall ("Sign in to confirm you're not a bot") |
| Auto-captions / transcripts | ❌ HTTP 429 (rate-limited) |
| Storyboard sprites (1 fps) | ✅ for `oB518y0L7fI` (44 frames) — others need the signed URL from the player response |
| Cover frames (`oardefault`, 1080×1920) | ✅ 44 videos |
| Auto mid-frames (`hq1/hq2/hq3` ≈ 25/50/75 %) | ✅ 54 videos → 162 frames |
| Upload dates | ✅ 1 video only — publishing frequency cannot be measured |
| Durations | ✅ 1 video only (43 s) |

## Consequences for the analysis

* **Visual grammar** (typography, colour, composition, shot mix, caption logic): strong evidence — 206 real frames + 1 full storyboard.
* **Pacing**: measured only as a **lower bound** from a 1 fps storyboard of one video. Sub-second cuts are invisible.
* **Transitions, camera motion inside shots, caption entry animation**: not directly observable from still frames → treated as
  *inferred* or *recommended*, never as *observed*.
* **Audio (voice, music, SFX, mix)**: **not inspected at all**. Every audio value in the deliverables is labelled
  *RECOMMENDATION — unverified*. Run `tools/forensics/audio_profile.py` on legally obtained files to replace them with measurements.

## How to close the gaps

Download 6–10 of the channel's Shorts **on your own machine** (where YouTube does not bot-block you), put them in
`analysis_input/` (git-ignored) and run:

```bash
bash tools/forensics/run_all.sh analysis_input/
```

It produces shot lists, cuts/min, caption colours and loudness/BPM reports that drop straight into
`docs/07_style_profile.json` fields marked `"status": "unverified"`.

Frames used for this analysis are kept out of this public repository on purpose (third-party footage
and identifiable people). Only measurements and original templates are committed.
