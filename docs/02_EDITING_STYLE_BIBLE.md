# DELIVERABLE 2 — Editing Style Bible: "CENTER-PUNCH"

*A reproducible editing system reverse-engineered from @Tacticalpath. The name "Center-Punch" is ours, not the channel's.*

> Labels: **[M]** measured · **[O]** observed · **[I]** inferred · **[R]** recommendation (unverifiable with available access).
> Evidence: [`01_CHANNEL_ANALYSIS_REPORT.md`](01_CHANNEL_ANALYSIS_REPORT.md) · numbers: [`evidence/measurements.json`](../evidence/measurements.json)

---

## A. Editing identity

| | |
|---|---|
| **Core philosophy** | *"Never let the eye rest; never let the ear lose the story."* One voice tells a story without interruption. The picture changes about every second to illustrate exactly what is being said, and one fixed caption at the optical centre ties the two together. |
| **Format** | Vertical 9:16 Shorts, about 35–60 s (43 s measured on the reference) [M/I] |
| **Visual identity** | Full-bleed vertical images, a crisp/over-sharpened finish, and **one neon-green centre caption with a branded watermark locked under it** [M] |
| **Narrative identity** | Expert or podcast storytelling about wild animals: danger, rarity, "who would win", strange facts [O] |
| **Intensity** | High: ≥ 49 cuts/min, ~1 s shots, hard cuts only [M] |
| **Emotional atmosphere** | Awe + dread + humour. The awe comes from B-roll spectacle, the dread from the danger stories, the humour from guest reactions and absurd AI composites [O] |
| **Dominant techniques** | (1) word-to-picture B-roll · (2) centre-locked 1–3-word captions · (3) punch-in jump framing on the speaker · (4) hard cuts · (5) cold open mid-story · (6) loopable hard ending |
| **Distinctive marks** | Caption at **exactly 50 % height** (most channels caption at ~65–75 %) · **green #19F464** fill + dark-green drop-shadow · **two-tone wide-tracked watermark 55 px under the caption** [M] |

---

## B. Quantitative editing profile

| Parameter | Typical value | Observed range | Confidence |
|---|---:|---:|---|
| Cuts per minute | **≥ 49** (target 50–60) | lower bound 48.8 (1 video, 1 fps) | Medium: bound measured, exact value unknown |
| Median shot duration | **≈ 1.0 s** | B-roll 0.7–2 s; speaker 1–2 s | Medium |
| Mean shot duration | **≤ 1.2 s** | — | Medium |
| B-roll share of runtime | **65–77 %** | 64 % (162 frames / 54 videos), 77 % (1 video) | High |
| Speaker (A-roll) share | 23–35 % | — | High |
| Punch-in frequency | Every 2nd–3rd speaker shot changes framing | 3 framings in one sampled video | Medium (O) |
| Transitions other than hard cut | ~0 per minute | 0 in 206 frames | High |
| Text overlay frequency | **100 % of runtime** (continuous captions) | 206/206 frames | High |
| Words per caption | **1.8 mean**; 1–3 | 1–4 | High |
| Caption chunk duration | ≈ 0.3–0.7 s | — | Low (I, from ~2.8–3.2 words/s typical podcast speech) |
| Other graphics | none | 0 lower thirds / maps / arrows in 206 frames | High |
| Music intensity | Unknown | — | **Unverified** |
| Duration | 43 s measured | n = 1 | Low |

---

## C. Visual specification

### C1. Typography system: "Center-Punch caption"

| Token | Value | Label |
|---|---|---|
| Font | **Montserrat Black** (OFL, free). Alternatives: Gilroy Heavy, Poppins Black | M (calibrated) |
| Size | **82 px on a 1080 × 1920 canvas** → 41–42 px cap height | M |
| Case | UPPERCASE | M |
| Tracking | 0 | O |
| Lines | 1 line; max ~16 characters (observed max 15) | M |
| Position | Centre X; **centre Y = 960 px (50 %)** | M |
| Fill | `#19F464` (hi-light `#30FF7D`) | M |
| Outline | 2 px, `#06260D` | I |
| Drop shadow | Hard (0 blur), colour `#0A3D16`, offset **x +1.5, y +6 px** | M/I |
| Glow | Same green, ~10 px spread, blur 12, ~40 % opacity | O |
| Watermark | Brand in Montserrat ExtraBold 33 px, tracking +11, two tones: light `#E6E2DE` at ~80 % opacity + accent `#54BB6F` at ~75 %. **Centre 56 px below the caption centre**, visible for the whole video | M |
| Profanity | Mask vowels: `F***`, `S***` | O |
| Non-speech | `*SOUNDS*`, `*LAUGHS*`, `*IN SHOCK*` | O |

### C2. Graphic system
* **Only one graphic family: the caption plus its watermark.** No lower thirds, name supers, maps, arrows, cards or progress bars [O].
* If an explainer graphic is unavoidable (an anatomy callout, a size comparison), build it in the **same green with the same dark shadow** and keep it on screen for ≤ 1.5 s [R].

### C3. Colour palette

| Role | HEX | Source |
|---|---|---|
| Caption fill | `#19F464` | M (median of 44 frames) |
| Caption highlight | `#30FF7D` | M (p90) |
| Caption shadow | `#0A3D16` (core) / `#04651C` (mean incl. bleed) | I / M |
| Caption rim | `#06260D` | I |
| Watermark light | `#E6E2DE` @ 80 % (renders ≈ `#C6C2BE` over footage) | M/I |
| Watermark accent | `#54BB6F` | M |

### C4. Image treatment
* **No forced unified grade.** Each clip keeps its native look [O].
* Every clip gets the same **finish**: moderate saturation lift (target mean S ≈ 40 %), mid-contrast S-curve, and **visible sharpening / clarity** [M/O].
* Low-resolution sources are upscaled and then sharpened. The slightly crunchy result is part of the look [O].
* Preset: `templates/luts/crisp_pop_709.cube` at 60–100 % + unsharp 5×5 at 0.9 [R, built to hit the measured statistics].

### C5. Motion language
* Movement comes from the **cuts**, not from camera moves.
* The speaker's framing jumps between ~100 %, ~112 % and ~120 % on alternate shots [O].
* B-roll keeps its native motion (drone, tracking, handheld) [O].
* Stills and AI images get a slow push-in, 100 → 106 % over the shot, linear [R].

### C6. Transition library

| Use | Transition |
|---|---|
| Every edit | **Hard cut** (O) |
| Optional gag beat | 2–4 frames of black (cut, not fade) when a "lights-out"-type gag needs it [R] |
| Never | Dissolves, whips, zoom transitions, glitch, light leaks [O: absent] |

### C7. Composition rules
1. Fill the whole 9:16 frame. Use blur-fill only when the source can't be cropped (≤ 2 % of runtime) [M].
2. Eyes on the upper third (≈ 30–38 % height). The caption then lands at mouth/chest level and never covers the eyes [O].
3. Centre animal heads and faces horizontally. The caption sits under the subject, never across its eyes [O].
4. Split-stack (two 1080 × 960 halves) only for a two-speaker exchange or a footage + reaction pairing (≈ 1 %) [M].
5. Keep the bottom 20 % and the right 15 % free of essential content: the Shorts UI covers them [R].

---

## D. Audio specification: ALL [R], unverified

The reference audio was not accessible. These are production choices consistent with the observed format, a voice-led podcast clip with continuous captions. Replace them with measured values from `tools/forensics/audio_profile.py`.

| Element | Specification |
|---|---|
| Narration | The source speaker is the narrator. No separate voice-over [O: captions follow conversational speech, including non-speech tags]. Keep natural pauses short; tighten gaps > 300 ms in the rough cut |
| Voice chain | High-pass 80 Hz → de-ess (5–8 kHz, −3 to −5 dB) → compressor 3:1, 10 ms / 100 ms, 4–6 dB GR → gentle presence lift +2 dB at 3–4 kHz → limiter −1 dBTP |
| Music | One instrumental bed per Short, mood-matched (mystery/tension for danger stories, playful pizzicato for comedic animals). Ducked **18–22 dB under the voice** |
| SFX | Sparse and literal. Whoosh on 10–20 % of cuts, mainly into big B-roll. Low impact on the punchline word. Nature foley (splash, roar, chainsaw) when the B-roll implies it. No UI clicks |
| Transitions | Music hard-starts at 0 s (no fade-in). On the last word: hard stop or a short button, so the loop restarts cleanly |
| Delivery loudness | −14 LUFS integrated, ≤ −1 dBTP, LRA ≤ 7 |

---

## E. Storytelling specification

**Hook formula** [O/I]
> TITLE = concrete oddity + credible voice ("Why Never Cut Trees on a New Moon"). FRAME 1 = speaker already mid-claim + caption on screen. By 1 s the first literal B-roll lands.

**Narrative structure** [O/I]
1. **Claim (0–6 s):** the strangest statement, with a matching picture for each noun.
2. **Context (6–20 s):** how/why. Alternate B-roll (65–75 %) with speaker (25–35 %).
3. **Escalation (20–40 s):** a bigger number, a worse danger, a twist. Tightest punch-ins sit on emphasis words.
4. **Verdict / punchline (last 3–5 s):** on the speaker. Hard end, no CTA, loops to frame 1.

**Pacing:** one picture idea per caption chunk (~1 s). A speaker shot every 3–6 s. Never more than ~13 s of continuous B-roll (the longest run observed was 13 samples) [M].

**Information density:** one fact per 4–6 s; keep every sentence that adds a noun you can show [I].

**Suspense patterns:** withhold the payoff noun until the B-roll can show it. Use reaction shots as "permission to be shocked" [O].

**Ending formula:** the final line returns to the speaker. Cut on the last syllable, with no end card [M/O]. Write the last line so it leads back into the first.

---

## F. Editing rules

### DO
1. Cut on every new noun or idea: aim for **≈ 1 s shots, ≥ 50 cuts/min**.
2. Show the literal thing being said whenever footage exists (word-to-picture sync).
3. Keep captions on screen 100 % of the time: 1–3 words, UPPERCASE, centred at **50 %**, `#19F464` + dark-green hard shadow.
4. Lock the brand watermark directly under the caption for the whole video.
5. Alternate the speaker's framing (wide → punch-in → wide) on consecutive speaker shots.
6. Open on the speaker mid-claim with the caption already visible. No intro.
7. End on the speaker's last word with a hard cut, so it loops.
8. Fill the 9:16 frame and finish every clip with the crisp/sharpen pass.

### DON'T
1. No dissolves, whips, zoom transitions, glitches or light leaks.
2. No lower thirds, name tags, title cards, end screens or subscribe animations.
3. Don't move the caption: no bottom-third captions, no per-shot repositioning.
4. No karaoke colour highlighting inside the chunk. The whole chunk is one colour.
5. Don't hold B-roll unrelated to the spoken line for more than 2 s.
6. Don't use footage, music or podcast audio you have no rights to.

### OPTIONAL
* Blur-fill letterbox for a source that can't be cropped (≤ 2 % of runtime).
* Split-stack for a two-speaker exchange or a footage + reaction pairing (≈ 1 %).
* AI-generated stills for comic or hypothetical beats ("an elephant vs a polar bear"). Label them where platform policy requires.
* A repurposed vertical social clip, keeping its own text, only with a licence.
* 2–4 black frames as a gag accent.
