# DELIVERABLE 5 — Preset Specification

Every number here can be dropped straight into an editor. Labels: **[M]** measured · **[O]** observed · **[I]** inferred · **[R]** recommendation.
Canvas reference: **1080 × 1920 px, 30 fps**.

---

## 1. Caption preset `CP_Caption`

| Parameter | Value | Label | Note |
|---|---|---|---|
| Font family | Montserrat | M (closest match) | Calibrated against reference frames |
| Weight | Black (900) | M | |
| Size | **82 px** | M | → 41–42 px cap height (ref. median 41) |
| Case | UPPERCASE | M | |
| Tracking | 0 | O | |
| Leading | n/a (single line) | M | |
| Max characters | **16** | M | Observed max 15, median 9 |
| Words per chunk | 1–3 (target mean 1.8) | M | Break on punctuation |
| Alignment | Centre / middle | M | |
| Anchor position | **X 540, Y 960** | M | Measured centre 961 / 1920 |
| Fill | `#19F464` | M | p90 hi-light `#30FF7D` |
| Fill gradient (optional) | top `#18C34A` → bottom `#24F577` | M | Subtle; flat fill reads the same at phone size |
| Outline | 2 px, `#06260D` | I | |
| Drop shadow | hard, `#0A3D16`, 100 %, **dx +1.5, dy +6 px**, blur 0 | M/I | Sampled mean incl. bleed `#04651C` |
| Glow | `#19F464`, opacity ~40 %, spread 10 px, blur 12 | O/R | |
| Chunk timing | Starts on the first word's onset; holds until the next chunk; drops after 0.15 s if a pause > 0.6 s follows | R | Captions are never empty mid-sentence [O: 206/206 frames captioned] |
| In-animation | **Pop:** scale 85 % → 106 % (70 ms) → 100 % (130 ms) | R | Not observable from stills |
| Out-animation | none (hard cut to next chunk) | R | |
| Profanity | Mask after the first letter: `F***`, `S***` | O | |
| Non-speech | `*SOUNDS*`, `*LAUGHS*`, `*IN SHOCK*` | O | |
| Punctuation | Keep `?` `!` `'`; drop `, . ; :` | O | |

**Shipped implementation:** `templates/captions/make_captions.py` (defaults = this table). Example ASS style line:

```
Style: Cap,Montserrat Black,82,&H0064F419,&H000000FF,&H000D2606,&H00163D0A,0,0,0,0,100,100,0,0,1,2.2,0,5,60,60,0,1
```

## 2. Watermark preset `CP_Watermark`

| Parameter | Value | Label |
|---|---|---|
| Text | Your brand, ≤ 14 characters, split in two tones (e.g. `WILD` + `FRAME`) | O (pattern) |
| Font | Montserrat ExtraBold (800) | I |
| Size | **33 px** (≈ 17 px cap height) | M |
| Tracking | **+11 px** (≈ +330 in Premiere / Illustrator units) | M (≈ 424 px total width for 12 characters) |
| Colour A (first part) | `#E6E2DE` @ 80 % (renders ≈ `#C6C2BE`) | M |
| Colour B (accent part) | `#54BB6F` @ 75 % | M |
| Position | X 540, **Y 1016** (centre 56 px below the caption centre) | M |
| Duration | Whole video | M |
| Animation | none | O |

## 3. Framing presets (A-roll)

| Name | Scale on a 9:16 crop | Eyes at | Use |
|---|---|---|---|
| `CP_W` | 100 % | 30–35 % height | Default, gestures |
| `CP_P1` | 112 % | 30–33 % | Alternate shot |
| `CP_P2` | 120 % | 28–32 % | Emphasis words, reactions, final line |
| Rule | Alternate W ↔ P on consecutive A-roll shots; never P → same P | | [O] |

## 4. Motion presets

| Name | Parameters | Label |
|---|---|---|
| `CP_PushIn` (stills / AI images) | Scale 100 → 106 %, linear, whole clip, centre anchor | R |
| `CP_PushInStrong` (reveal) | Scale 100 → 110 %, linear | R |
| `CP_Black` (gag accent) | 2–4 frames of #000000, hard in/out | R |
| Speed ramps / shake / blur | **None** | O |

## 5. Transitions

| Name | Spec | Label |
|---|---|---|
| `CUT` | Hard cut, 0 frames. Cut 0–2 frames before the noun onset | O / R (offset) |
| All others | Not used | O |

## 6. Colour presets

| Name | Spec | Label |
|---|---|---|
| `CP_Balance` | Per clip: neutral WB, exposure so faces sit 60–70 IRE | R |
| `CP_Finish` (adjustment layer) | `templates/luts/crisp_pop_709.cube` at **80 %** | R (built to hit M stats: mean S ≈ 40 %, V ≈ 46 %, luma σ ≈ 60/255) |
| Sharpen | Unsharp radius 2.5 px, amount 0.9 (FFmpeg `unsharp=5:5:0.9`) · Resolve Sharpen 0.40 · Premiere Unsharp Mask 90 / 2.5 / 2 | O (look) / R (values) |
| Saturation | +5…+15 on top of the LUT if the source is flat | R |
| Upscale | ×2 (Super Scale / Topaz / Real-ESRGAN) **before** sharpening any < 1080p source | O/R |

LUT internals: mid S-curve (k = 0.18), black floor 0.015, soft shoulder from 0.92, saturation × 1.18, skin hues 15–45° protected (× 1.06), foliage/water hues 80–190° × 1.03.

## 7. Audio presets: ALL [R], unverified

| Name | Chain / values |
|---|---|
| `CP_Dialogue` | HPF 80 Hz 12 dB/oct → de-esser 6 kHz −4 dB → comp 3:1, attack 10 ms, release 100 ms, 4–6 dB GR → EQ +2 dB @ 3.5 kHz (Q 1) → limiter −1 dBTP |
| `CP_MusicBed` | HPF 120 Hz under dialogue; sidechain duck −18 dB (range 18–22), attack 50 ms, release 200 ms; ends with a button or hard stop on the last word |
| `CP_Whoosh` | Peak −12 dBFS; starts 4–6 frames before the cut, peaks on the cut; 10–20 % of cuts |
| `CP_Impact` | Peak −8 dBFS; on the punchline / emphasis word |
| `CP_Foley` | −14 to −10 dBFS; only when B-roll implies the sound |
| `CP_Master` | −14 LUFS integrated, −1 dBTP, LRA ≤ 7 LU; 48 kHz |

## 8. Timeline / track naming

`V1 A-ROLL · V2 B-ROLL · V3 B-ROLL_ALT · V4 ADJ_FINISH · V5 CAPTIONS · V6 BRAND_WM`
`A1 DIALOGUE · A2 DIALOGUE_ALT · A3 SFX_HITS · A4 SFX_FOLEY · A5 MUSIC · A6 ROOM`

Clip colour labels: A-roll = **orange**, B-roll literal = **green**, B-roll generic = **teal**, generated/AI = **violet**, gag/black = **red**.

## 9. Export presets

| Name | Spec |
|---|---|
| `CP_Shorts_1080x1920_30p` | H.264 High 4.2, 1080 × 1920, 30 fps CFR, VBR 2-pass 16 / 20 Mbps, GOP 15, 2 B-frames, faststart; AAC-LC 320 kbps 48 kHz; −14 LUFS / −1 dBTP |
| `CP_YouTube_16x9` | H.264 High, 1920 × 1080 (12–16 Mbps) or 3840 × 2160 (45 Mbps), native fps |
| `CP_Master_ProRes` | ProRes 422 HQ, 1080 × 1920, 30 fps, PCM 24-bit 48 kHz, captions **not** burned (ship `.ass` + `.srt`) |

FFmpeg (shipped as `templates/ffmpeg/finish_and_export.sh`):

```bash
ffmpeg -i edit.mp4 -filter_complex "[0:v]split[a][b];[b]lut3d=file=crisp_pop_709.cube[g];\
[a][g]blend=all_expr='A*0.2+B*0.8',unsharp=5:5:0.9,ass=captions.ass,format=yuv420p[v];\
[0:a]loudnorm=I=-14:TP=-1.0:LRA=7[a]" -map "[v]" -map "[a]" -r 30 -c:v libx264 -profile:v high \
-level 4.2 -preset slow -crf 16 -maxrate 20M -bufsize 40M -g 15 -bf 2 -movflags +faststart \
-c:a aac -b:a 320k -ar 48000 short_final.mp4
```
