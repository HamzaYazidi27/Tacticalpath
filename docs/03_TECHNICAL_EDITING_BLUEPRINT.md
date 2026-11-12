# DELIVERABLE 3 — Technical Editing Blueprint

How to recreate every Center-Punch technique, in three editors and in a software-independent FFmpeg pipeline that ships with this repo and has been tested.

> Menu names change between versions. Where a path is version-dependent it is marked *(≈)*. Numbers come from [`05_PRESET_SPECIFICATION.md`](05_PRESET_SPECIFICATION.md).

---

## 0. Which software?

| Need | CapCut Desktop | Premiere Pro | DaVinci Resolve | Repo FFmpeg pipeline |
|---|---|---|---|---|
| Word-chunk auto-captions with glow + shadow | ★★★ native | ★★ Speech-to-Text + styles (glow needs a workaround) | ★★ Studio auto-subtitles; Text+ for glow | ★★★ pixel-calibrated (`make_captions.py`) |
| Fast 1 s cutting, jump framing | ★★★ | ★★★ | ★★★ | ★ (scripted) |
| Grade / sharpen finish | ★ | ★★ Lumetri | ★★★ | ★★ LUT + unsharp |
| Team / pro handoff | ★ | ★★★ | ★★★ | ★★ |
| Cost | Free / Pro | Subscription | Free / Studio | Free |

**Recommendation.**
* **Premiere Pro** as the primary professional platform. Speech-to-Text gives editable caption tracks, Essential Graphics templates make the caption reusable, Auto Reframe handles 9:16, and it has the best team interchange.
* **CapCut Desktop** when speed matters more than control: its caption styling reproduces the look in minutes.
* **Resolve** if you grade a lot or work with the free tier.
* Whichever editor you use, the repo's **ASS caption file is the pixel-accurate reference**. Burn it in at the end, or use it as a visual target for the native caption style.

---

## 1. Timeline setup (all editors)

| Setting | Value |
|---|---|
| Resolution | 1080 × 1920 (9:16), square pixels |
| Frame rate | **30 fps** (measured on the reference) |
| Audio | 48 kHz, stereo |
| Colour | Rec.709 / gamma 2.4, SDR |

**Video tracks (bottom → top)**

| Track | Name | Content |
|---|---|---|
| V1 | `A-ROLL` | Reframed speaker cams. Punch-in variants alternate |
| V2 | `B-ROLL` | Cutaways (≈ 70 % coverage) |
| V3 | `B-ROLL_ALT` | Stacked layouts, gag inserts, black frames |
| V4 | `ADJ_FINISH` | Adjustment layer: LUT + sharpen, full length |
| V5 | `CAPTIONS` | Caption chunks |
| V6 | `BRAND_WM` | Watermark, full length |

**Audio tracks**

| Track | Name | Content |
|---|---|---|
| A1 | `DIALOGUE` | Source speaker |
| A2 | `DIALOGUE_ALT` | Host / second speaker |
| A3 | `SFX_HITS` | Whooshes, impacts |
| A4 | `SFX_FOLEY` | Nature / foley |
| A5 | `MUSIC` | Music bed |
| A6 | `ROOM` | Room tone fills |
| Bus | `MIX` | Loudness limiter |

---

## 2. Recreating each technique

### 2.1 Vertical A-roll from a horizontal podcast (observed: 33 % of frames)
1. Nest each camera angle. Set the crop to 9:16 with the eyes at about 33 % from the top.
2. Make **three framing presets per speaker**:

   | Preset | Scale | Framing |
   |---|---:|---|
   | `W` | 100 % | full-height crop, chest-up |
   | `P1` | 112 % | |
   | `P2` | 120 % | face fills the width |

3. Alternate them on consecutive speaker shots: W → P1 → W → P2. Use P2 on emphasis words and on reactions.
4. Repo equivalent:

   ```bash
   templates/ffmpeg/reframe_9x16.sh podcast.mp4 a_P1.mp4 0.62 1.12 0.45 83.40 2.1
   ```

   Arguments: x-centre 0.62, zoom 1.12, y-centre 0.45, start 83.40 s, duration 2.1 s.

### 2.2 Word-to-picture B-roll (observed: 64–77 % of runtime)
1. Run Speech-to-Text and export the transcript.
2. Highlight every **concrete noun, number or verb of action**: those are the B-roll slots.
3. Lay B-roll on V2 so that its **first frame lands on the first syllable of the noun**: cut 0–2 frames *before* the word.
4. Keep each B-roll shot 0.7–2.0 s. Split anything longer into a second angle.
5. Return to A-roll every 3–6 s, or whenever the speaker's face carries emotion (laugh, grimace, disbelief).

### 2.3 Hard-cut grammar
* Use no transitions at all. If an edit feels jarring, fix it by **cutting on the word** (0–2 frames early), not by adding a dissolve.
* Gag accent: drop 2–4 frames of pure black on V3 (a cut, not a fade).

### 2.4 Stills / AI images as B-roll [R]
* Apply a linear scale of 100 % → 106 % over the clip, anchored at centre, without easing.
* Repo:

  ```bash
  templates/ffmpeg/still_to_clip.sh image.png still.mp4 1.2 1.06
  ```

### 2.5 Blur-fill and split-stack (occasional)
* **Blur-fill.** Duplicate the clip:
  * Bottom copy: scale to fill, Gaussian blur ~40, brightness −6.
  * Top copy: fit to width, aligned to the top.

  Repo: `templates/ffmpeg/blurfill_9x16.sh`.
* **Split-stack.** Two 1080 × 960 crops, top and bottom; audio comes from the speaking half. Repo: `templates/ffmpeg/stack_9x16.sh`.

### 2.6 Finish
* Adjustment layer: LUT `crisp_pop_709.cube` at 80 % + sharpen (unsharp radius 2.5 px / amount 90 %, or Premiere *Sharpen* 30–40).
* Upscale low-resolution sources **before** sharpening, using Resolve Super Scale ×2, Topaz or Real-ESRGAN.

---

## 3. Adobe Premiere Pro: implementation

### 3.1 Sequence
New Sequence → Settings:
* Editing Mode: Custom
* Frame size: 1080 × 1920
* Timebase: 30 fps
* Pixel aspect: Square
* Audio: 48 kHz

Name the tracks as in §1.

### 3.2 Captions (Center-Punch)
1. Run **Window → Text → Transcript → Transcribe**.
2. Choose **Create captions** with these settings:

   | Setting | Value |
   |---|---|
   | Maximum length in characters | **16** |
   | Minimum duration | **0.20 s** |
   | Gap between captions | **0 frames** |
   | Lines | **Single** |

3. Select all captions and open **Essential Graphics → Edit**:

   | Property | Value |
   |---|---|
   | Font | Montserrat Black |
   | Size | **82** *(≈ in 1080-wide seq; check the cap height ≈ 41 px with a ruler guide)* |
   | Alignment | centre |
   | Position Y | **960** |
   | Case | Text → All Caps |
   | Fill | `#19F464` |
   | Stroke | Outer, 2, `#06260D` |
   | Shadow | `#0A3D16`, opacity 100 %, distance 6, size 0, blur 0; angle set so the shadow falls straight down *(≈ 95–100° on Premiere's dial — confirm in preview)* |

4. **Create Style…** and name it `CP_Caption`.
5. **Glow.** Native caption tracks have no glow. Either:
   * **a)** Upgrade captions to graphics (Graphics and Titles → *Upgrade Caption to Graphic*), duplicate to the track below, and add *Gaussian Blur 18* + *Opacity 45 %*; or
   * **b)** Burn the repo's ASS file in at export (best fidelity).
6. **Pop.** Premiere captions don't animate per chunk. If you want the pop:
   * Use graphics + a scale keyframe preset: 85 % → 106 % (frame 2) → 100 % (frame 4); or
   * Use the ASS burn-in.

### 3.3 Watermark (MOGRT)
1. Use the Type tool to write `YOURBRAND`.
2. Set Montserrat ExtraBold 33, tracking +330 (Premiere tracking units ≈ 1/1000 em), fill `#E6E2DE` at 80 %.
3. Recolour the last word to `#54BB6F`.
4. Position: centre, Y = 1016.
5. Save it as a Motion Graphics Template (`CP_Watermark.mogrt`) and lay it over the full length on V6.

### 3.4 Punch-in presets
1. On a nested A-roll clip, set Effect Controls → Motion → Scale to 112 and save as preset `CP_P1`.
2. Do the same at Scale 120 and save `CP_P2`.
3. Apply with a drag; adjust Position Y so the eyes stay at ~33 %.

### 3.5 Still push-in preset
1. Keyframe Motion → Scale: 100 at the in-point, 106 at the out-point, linear.
2. Save it as `CP_PushIn` with "Anchor to In Point" + "Scale to clip duration".

### 3.6 Finish
Adjustment layer on V4, with:
* Lumetri → Creative → Look = `crisp_pop_709.cube`, Intensity 80
* Lumetri Basic: Saturation 105–115
* Effect *Unsharp Mask*: Amount 90, Radius 2.5, Threshold 2

### 3.7 Audio [R]
* **Essential Sound.** Tag A1/A2 as **Dialogue** (Loudness: Auto-Match, Reduce Noise ≤ 3, Enhance Speech if needed). Tag A5 as **Music** with Ducking on: duck against Dialogue, sensitivity 6, amount −18 dB, fades 200 ms.
* **Mix bus.** Multiband Compressor (Broadcast) + Hard Limiter at −1 dB. Loudness Radar target −14 LUFS.

### 3.8 Export: see §6

---

## 4. DaVinci Resolve: implementation

### 4.1 Project and timeline
* Project settings: 1080 × 1920, 30 fps, Rec.709 Gamma 2.4. Use vertical resolution on the timeline.
* Track names as in §1.

### 4.2 Captions
* **Studio.** Timeline → **Create Subtitles from Audio** *(≈)*:
  * Max characters per line **16**
  * Lines **single**
  * Gap **0**
* Subtitle track **Track Style**:

  | Property | Value |
  |---|---|
  | Font | Montserrat Black, size ~82 *(≈ verify cap height 41 px)* |
  | Colour | `#19F464` |
  | Stroke | `#06260D`, size 2 |
  | Drop shadow | `#0A3D16`, offset X 1.5 / Y −6 (Resolve's Y is up-positive), strength 100, no blur |
  | Position | centre, Y offset so the centre is at 960 |

  Then set UPPER CASE on the transcript text: select all → Change Case *(≈)*.
* **Free version / glow + pop.** Import the repo's `.ass` as a reference, or build a **Text+** Fusion title:
  * Shading element 1: fill `#19F464`
  * Element 2: outline `#06260D` 2 px
  * Element 3: shadow `#0A3D16`, offset (0.001, −0.006)
  * Element 4: glow via a Soft Glow node, gain 0.6, threshold 0.4

  Save it as a macro `CP_Caption` and keyframe Size 0.85 → 1.06 → 1.0 over 4 frames.

### 4.3 Watermark
Text+ macro `CP_Watermark`:
* Montserrat ExtraBold, character spacing 1.35, two-colour via a *Character Level Styling* modifier
* Y = 1016 px

### 4.4 Punch-ins and push-ins
* Inspector → Transform → Zoom 1.12 / 1.20. Save as **Inspector presets** *(≈ "Save Preset" in the Inspector menu)*.
* Push-in: Dynamic Zoom with start 1.00 and end 1.06, linear.

### 4.5 Colour page
Node tree: `N1 Balance (per clip)` → `N2 Super Scale/NR (if low-res)` → `N3 LUT crisp_pop_709.cube (Key output gain 0.8)` → `N4 Sharpen: Blur/Sharpen Radius 0.40, H/V ratio 1`, Mid-Detail +25.

Put N3/N4 on a **timeline-level** node graph so every clip gets the finish.

### 4.6 Fairlight [R]
* Dialogue: EQ HPF 80 Hz, Dynamics comp 3:1, −18 dB threshold.
* Music bus: sidechain ducking from dialogue, −18 dB.
* Main bus limiter at −1 dBTP. Loudness meter set to the YouTube −14 standard.

---

## 5. CapCut Desktop: implementation (fastest route)

1. **New project → Ratio 9:16 → 1080p / 30 fps.**
2. **Text → Auto captions → English.** After generation, open the caption settings *(≈ "Captions → Style / Layout")*:

   | Setting | Value |
   |---|---|
   | Max characters per line | **16** (or "words per line: 3") |
   | Lines | 1 |
   | Font | **Montserrat Black** (import the OTF) |
   | Case | Aa → UPPERCASE |
   | Fill | `#19F464` |
   | Stroke | `#06260D`, thickness ~10 *(CapCut units)* |
   | Shadow | `#0A3D16`, opacity 100, blur 0, distance ~6, angle −90° (down) *(≈)* |
   | Glow *(text effect)* | colour `#19F464`, intensity low |
   | Position | drag to the canvas **centre**; Y = 0 in CapCut's centred coordinates |
   | Animation In | *Pop* or *Bounce*, 0.10–0.15 s |

   Save it as **"Center-Punch" preset** *(≈ Text → "Save as preset")*.
3. **Watermark.**
   * Add a Text layer `YOURBRAND`, Montserrat ExtraBold, letter-spacing ~8.
   * Colour the light part `#E6E2DE` at 80 % and the accent part `#54BB6F` (select letters → colour).
   * Set Y ≈ −56 px below the caption *(CapCut Y is up-positive)* and stretch it over the full timeline.
4. **Punch-ins.** Select an A-roll clip → Basic → Scale 112 % / 120 %.
5. **Finish.** Adjustment → *Filters* or import the `.cube` (Adjust → LUT); Sharpen 25–35; Saturation +10.
6. **Audio [R].**
   * Enhance voice ON.
   * Music volume about −18 dB relative to voice. Use auto-ducking ("Reduce music when speaking") if available.
   * Loudness normalise on export, or run the repo's `finish_and_export.sh`.

---

## 6. Export settings

| Preset | Container / codec | Settings | Use |
|---|---|---|---|
| **Shorts delivery** | MP4 H.264 High @ 4.2 | 1080 × 1920, 30 fps CFR, VBR 2-pass target 16 Mbps / max 20 Mbps, GOP 15, B-frames 2, `+faststart`. AAC-LC 320 kbps 48 kHz. −14 LUFS, −1 dBTP | YouTube Shorts / TikTok / Reels |
| **Standard YouTube (16:9)** — not used by the channel | MP4 H.264 High | 1920 × 1080 (or 3840 × 2160), native fps, 12–16 Mbps (45 Mbps for 4K) | Long-form re-cut, if ever needed |
| **Archival master** | MOV ProRes 422 HQ (or DNxHR HQX) | 1080 × 1920, 30 fps, PCM 24-bit 48 kHz, **no burned captions** + a separate `.ass`/`.srt` | Re-editing, re-captioning, translations |

Repo one-liner (grade + sharpen + captions + loudness + Shorts encode):

```bash
templates/ffmpeg/finish_and_export.sh edit.mp4 captions.ass short_final.mp4
```

> `loudnorm` in the script is single-pass (±1–2 LU). For exact −14 LUFS, run it as two-pass: measure first, then pass the `measured_*` values.

---

## 7. Reusable motion-graphics templates

| Template | Status | Build |
|---|---|---|
| **Caption (Center-Punch)** | ✅ shipped: `templates/captions/make_captions.py` (ASS) | Premiere style `CP_Caption` / Resolve Text+ macro / CapCut preset (§3–5) |
| **Watermark** | ✅ shipped inside the ASS output (`--brand`) | MOGRT / Text+ macro / CapCut text preset |
| Opening title | ❌ not part of the style: the channel has none | Don't build one |
| Lower thirds / headlines / labels / info cards | ❌ not part of the style | Don't build them |
| Callout ring (optional explainer) | [R] | Ellipse stroke 8 px `#19F464` + same shadow; stroke draws on 0 → 100 % over 8 frames; on screen ≤ 1.5 s |
| Map | [R], only if a story needs location | Flat dark map (Natural Earth), one green pin `#19F464`, push-in 100 → 115 % in 1.5 s, hard cut out |
