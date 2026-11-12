# DELIVERABLE 1 — Channel Analysis Report: @Tacticalpath

> **Evidence labels used everywhere in this repo**
> **[M] Measured**: computed from pixels or metadata · **[O] Observed**: seen by eye on real frames ·
> **[I] Inferred**: logical deduction from M/O evidence · **[R] Recommendation**: not verifiable with the access we had; a production choice consistent with the evidence.
> Raw data: [`evidence/measurements.json`](../evidence/measurements.json) · access limits: [`evidence/ACCESS_LOG.md`](../evidence/ACCESS_LOG.md)

---

## 0. Executive summary

1. **The channel is not a military/tactical channel.** Despite the name, `@Tacticalpath` (ID `UCF89JkC5qAzp8jI66J6G2yw`, ~55 K subscribers) is a **Shorts-only wildlife-podcast clip channel** [M]. The "Videos" and "Live" tabs do not exist [M]. Its titles credit the source podcasts or guests: "ft Forrest Galante", "ft@Wild Times Podcast", "ft Paul Rosolie", "@Junglekeeper" (46 of 55 titles carry "ft"/"@") [M].
2. **Format = podcast A-roll + heavy literal B-roll + centre captions.** A vertical crop of a podcast speaker is intercut with wildlife B-roll so often that **64 % of the 162 sampled mid-video frames are B-roll** [M]. In the one video with a full storyboard, it is **77 %** [M].
3. **Very fast cutting.** The fully sampled video (43 s) shows **≥ 35 visual changes, so ≥ 49 cuts/min, with a mean shot length ≤ 1.2 s**. Both figures are lower bounds, because the sampling is 1 fps [M].
4. **One dominant graphic system: the "Center-Punch" caption.** Every sampled frame (206/206) carries it [M]:
   * 1–3 UPPERCASE words, mean 1.79 words, median 9 characters [M].
   * Heavy geometric sans: closest match **Montserrat Black**, calibrated to within 3 % [M].
   * **Neon-green fill #19F464**, a dark-green hard drop shadow pushed downward, and a soft glow [M].
   * The block is centred at **50.1 % of frame height** [M].
   * A persistent two-tone, wide-tracked **watermark** sits 55 px below it [M].
5. **Word-to-picture sync.** At least 27 of the 104 sampled B-roll frames (26 %) show the exact noun that the caption displays at that instant ("BELUGA WHALES" over a beluga, "BEAR SPRAY" over bear spray) [M/O]. The rest illustrate the topic more loosely.
6. **Hard cuts only.** No dissolve, whip or zoom transition appears in any of the 206 frames [O]. Section 2.4 explains statistically why that rules them out as a recurring device [I].
7. **Audio could not be inspected at all.** YouTube's bot wall blocked streams and transcripts from this cloud IP, and it was not circumvented. Every audio value in this repo is therefore labelled [R]. [`tools/forensics/`](../tools/forensics) measures audio automatically once you supply files.

---

## 1. Phase 1 — Channel reconnaissance

### 1.1 Identity and positioning

| Item | Finding | Label |
|---|---|---|
| Channel name / handle | Tacticalpath / `@Tacticalpath` | M |
| Channel ID | `UCF89JkC5qAzp8jI66J6G2yw` | M |
| Subscribers | ~55,000 (rounded display) | M |
| Description | A disclaimer, not a positioning statement: *"This content does not belong to TacticalPath; it is edited and shared solely for entertainment and educational purposes…"* plus a "Section 107 fair use" notice | M |
| Category (de facto) | Animals / wildlife facts and stories, told through clips of podcast guests (wildlife biologists, jungle conservationists, podcast hosts, comedians) | O |
| Target audience | English-speaking, broad, curiosity-driven Shorts viewers. The topics are danger, rare animals and "who would win" debates | I |
| Primary language | English (en-US original audio track). YouTube auto-dubbing adds 13 dubbed tracks (de, es, fr, hi, id, it, he, ml, nl, pl, pt-BR, ru, uk) | M |
| Publishing format | 100 % vertical Shorts. No long-form videos and no lives | M |
| Shorts listed | ≥ 55. The continuation page returned 403, so the true total is unknown | M |
| Duration distribution | Only one duration is measurable: 43 s (`oB518y0L7fI`) | M (n = 1) |
| Publishing frequency | Not measurable: only one upload date (2026-10-21) is known. Nine Shorts listed above it were posted after that date, so ≥ 9 uploads in ≤ 22 days (≈ 3/week recently) | I |

> ⚠️ **Rights note (business-critical, not legal advice).** The channel's own description says it reposts footage it does not own. A "fair use" disclaimer has no legal effect on its own. This repo reconstructs the **editing grammar** for use on footage **you own, licence or have permission for**: your own podcast, a guest who grants clip rights, or licensed and public-domain B-roll. None of the reference channel's footage, audio, scripts or branding is reused here.

### 1.2 Inventory and performance

The full 55-row table, with a URL, views and per-frame content for every Short, is in [`evidence/channel_inventory.md`](../evidence/channel_inventory.md).

| Statistic (first 55 Shorts) | Value [M] |
|---|---|
| Total views | 21.1 M |
| Median / mean | 58 K / 384 K (heavily right-skewed) |
| Q1 / Q3 | 40 K / 250 K |
| ≥ 1 M views | 6 Shorts |
| 100 K – 1 M | 16 Shorts |
| < 100 K | 33 Shorts |

**Top performers** [M]

| Video | Views | Hook type |
|---|---:|---|
| [New Shark Species Discovered ft.Forrest Galante](https://www.youtube.com/shorts/7nFyBuaKkTc) | 3.2 M | discovery / novelty |
| [Creepiest Camping Alone Story ft@Junglekeeper](https://www.youtube.com/shorts/5gi88teXjOI) | 3.1 M | first-person fear story |
| [Why Never Cut Trees on a New Moon](https://www.youtube.com/shorts/oB518y0L7fI) | 2.7 M | "why" + counter-intuitive rule |
| [@Forrest Galante on How to Save the Ocean](https://www.youtube.com/shorts/dWXChlEX888) | 2.7 M | authority + big topic |
| [This Bird Sleeps 10,000 Times a Day ft@Wild Times Podcast](https://www.youtube.com/shorts/59v9T5CsPDg) | 2.0 M | absurd number |
| [White Sharks Roaming Lakes Now?? ft Forrest Galante](https://www.youtube.com/shorts/gYr5TjFjp3g) | 1.6 M | alarming question |

**Title grammar** [M]:
* 46/55 credit the guest or podcast.
* 16/55 use superlatives or danger words (most, rarest, deadliest, worst, terrifying).
* 11/55 contain a number ("16-Foot", "110 ft", "10,000 Times").
* 5/55 are questions.

The breakout titles combine a **concrete, checkable oddity** (a number, a "why", a new species) with a credible voice.

### 1.3 Representative sample analysed

The channel has ≥ 55 uploads, so 11 were prioritised following the brief. Sequential evidence exists for one of them; the others have 3–4 real frames each.

| Role | Video | Evidence available |
|---|---|---|
| Most viewed | `7nFyBuaKkTc`: New Shark Species Discovered (3.2 M) | 3 mid-frames + cover |
| Most recent | `3_z-hemLYEg`: River otters bullying a 16ft croc | 3 mid-frames |
| Median performer | `qPQQJ_CLhZ0`: The most Terrifying Animal (58 K) | 3 mid-frames + cover |
| Full sequential reference | `oB518y0L7fI`: Why Never Cut Trees on a New Moon (2.7 M) | **44-frame 1 fps storyboard**, player metadata, 3 mid-frames, cover |
| Variant: all-B-roll samples | `hL1CJ4qplqk`: New Zealand's "Extinct" Moose | 3 mid-frames + cover |
| Variant: podcast-only, punch-ins | `z1BGPB46LUI`: A Deadly Taipan Licked His Neck | 3 mid-frames + cover |
| Variant: split-screen stack | `b6qEwIQHqAI`: NYC Man Became Rich using Crows | 3 mid-frames + cover |
| Variant: blur-fill letterbox | `KD566jCAu4w`: How Crocodiles Survived the Extinction Event | 3 mid-frames + cover |
| Variant: repurposed social clip | `jCG3oVDFBuM`: Jason Derulo's Shark Scandal (968 K) | 3 mid-frames + cover |
| Variant: AI composite B-roll | `DtCh-oP9kg0`: What Wild Animal Would you Have as Sidekick | 3 mid-frames + cover |
| Variant: film footage over podcast | `1_WnsTGwdgI`: A bear Passed 18 Inches From his Head | 3 mid-frames + cover |

In total, **206 real frames** were inspected:
* 162 auto mid-frames at ≈ 25/50/75 % of runtime
* 44 full-resolution 1080 × 1920 cover frames
* 44 storyboard frames (50 × 90 px)

Cover-frame numbers in this report come from the 44 cover frames only.

---

## 2. Phase 2 — Visual editing forensics

### 2.1 Rhythm and pacing

| Parameter | Value | Label / method |
|---|---|---|
| Visual segments in `oB518y0L7fI` (43 s) | 36 (35 changes) | M: HSV-histogram distance between 1 fps storyboard frames > 0.25, verified by eye |
| Cuts per minute | **≥ 48.8** | M, lower bound. Shots under 1 s fall between samples |
| Mean shot length | **≤ 1.19 s** | M, upper bound |
| Median shot length | ≈ 1 s (sampling floor) | M/I |
| Shots holding ≥ 2 samples (≥ ~2 s) | 7 of 36 | M |
| First 3 / 5 / 10 s | 3 / 5 / 10 visual changes (one per sampled second) | M |
| First 30 s | 27 changes | M |
| Opening vs middle vs end | Steady density throughout. The 1–2 s runs of continuous B-roll are spread evenly, and the last 3 s hold on the speaker | M/O |
| Jump cuts on the speaker | Yes: frames 41→42→43 are the same take reframed. Mid-frames show the same guest at 3 framings in `z1BGPB46LUI` | O |
| B-roll insertion frequency | 77 % of sampled seconds (`oB518y0L7fI`), 64 % of 162 mid-frames (54 Shorts) | M |

**Classification.** This is fast-paced retention editing applied to a documentary information structure. Call it a *"podcast-clip documentary montage"*. It is not news-report or tactical-doc editing: there are no lower thirds, no maps, no date stamps and no archival-style treatments [O].

### 2.2 Scene composition [O, counts M]

| Layout | Share of 162 mid-frames | Description |
|---|---:|---|
| Full-bleed 9:16 crop of a podcast camera | 32.7 % | Speaker centred. Eyes sit on the upper third (≈ 30–38 % of height). Mic often in the lower-left or lower-right. Framing alternates between medium close-up and tight close-up |
| Full-bleed 9:16 B-roll | 64.2 % | Subject centred, often filling the frame. Low angles, aerials, macro. Many sources are natively vertical: phone, vlog and social clips |
| Blur-fill letterbox | 1.9 % | A horizontal or 4:5 podcast frame placed in the top ~80 %, over a blurred copy |
| Split-stack (top/bottom) | 1.2 % | Two podcast speakers stacked, or film/footage on top with the speaker reacting below |

Composition rules that recur [O]:
* The subject's face or the animal's head sits **above** the caption band.
* The caption sits roughly at mouth or chest height of the speaker.
* No picture-in-picture, no rounded "cards" and no floating screenshots were seen.

One social clip (`jCG3oVDFBuM`) keeps its **original platform text overlay** at the top.

### 2.3 Camera movement and image animation

| Technique | Evidence | Frequency | Label |
|---|---|---|---|
| Static podcast crop | Most podcast frames | Dominant | O |
| **Digital punch-in / punch-out on the same take** (jump framing) | Storyboard 41→42→43. `z1BGPB46LUI` wide → close → medium. `oB518y0L7fI` mid-frames 25 % vs 50 % | Recurring | O |
| Native camera motion inside B-roll (aerials, tracking, handheld) | Drone shots (moose, croc), underwater tracking (whale shark) | Recurring, inherited from source footage | O |
| Slow push-in / Ken Burns on stills and AI images | Many stills are present (AI composites, illustrations), but motion cannot be seen in single frames | Unknown | **R**: 100→106 % over the shot |
| Speed ramps, camera shake, freeze frames, motion blur | Not seen in 206 frames. Shake and blur would leave visible smeared frames | Absent / rare | O/I |

### 2.4 Transitions

| Transition | Frequency | Duration | Purpose | Label |
|---|---|---|---|---|
| **Hard cut** | ≈ 100 % | 0 frames | Rhythm; word-to-picture sync | O |
| Cross dissolve | Not observed | — | — | O |
| Fade to black/white | Not observed (the storyboard's black final tile is padding) | — | — | O |
| Whip / zoom / speed transition | Not observed | — | — | O |

**Why the absence is meaningful** [I]: at ~50 cuts per minute, a 10-frame dissolve on every cut would cover about 28 % of runtime. Across 206 frames we would then expect to catch dozens of blended frames. We caught **zero**. Dissolves and whips may exist as rare one-offs, but they are not part of the grammar.

---

## 3. Phase 3 — Typography and motion graphics

The caption is the channel's only graphic system. Full specification and presets: [`05_PRESET_SPECIFICATION.md §1`](05_PRESET_SPECIFICATION.md).

| Attribute | Finding | Label |
|---|---|---|
| Typeface category | Heavy geometric grotesque. Straight-leg R, near-circular O, tight apertures | O |
| Closest free match | **Montserrat Black**. Rendering "RESPONSIBLE" at size 82/1080 gives a 42 px cap height and 431 px width vs a 41 px / ~442 px reference | M (calibration) |
| Exact font | Not identifiable with certainty. Alternatives: Gilroy Heavy, Poppins Black, "The Bold Font" | — |
| Case / length | ALL CAPS. 1–3 words (60 × 1, 78 × 2, 22 × 3, 2 × 4). Median 9 characters, max 15 | M |
| Position | Horizontally centred. Vertical centre **961 px / 1920 (0.501)** | M |
| Cap height | Median 41 px (range 33–68) | M |
| Fill | **#19F464** median; #30FF7D at the 90th percentile. Bottom quarter is slightly brighter (#24F577) than the top quarter (#18C34A) | M |
| Shadow | Hard, dark green, falling ~6 px straight down (sampled mean incl. edge bleed #04651C; core ≈ #0A3D16) | M/I |
| Glow / outline | Soft green outer glow and a thin dark rim | O |
| Punctuation | Keeps "?" and apostrophes; drops commas and periods | O |
| Censorship | `THE F***` | O |
| Non-speech tags | `*SOUNDS*`, `*IN SHOCK*` (asterisk-wrapped) | O |
| Watermark | Persistent. Brand name in wide-tracked bold caps, split two-tone: first part light grey-white (#C6C2BE sampled over footage), last part green (#54BB6F, semi-transparent). Cap height ≈ 17 px, ≈ 424 px wide, centred **55 px below the caption centre**, so it travels with the caption block and sits where cropping would destroy the frame | M |
| Other graphics (lower thirds, maps, arrows, labels, timelines) | None in 206 frames | O |
| Entry/exit animation | Not observable from still frames | R: 85→106→100 % "pop" in ~130 ms |

---

## 4. Phase 4 — Colour and image treatment

| Item | Finding | Label |
|---|---|---|
| Global grade | Footage from many sources is **not** matched to one look. Warm studio podcasts sit next to cold underwater and green jungle shots | O |
| Saturation | Mean 101/255 (≈ 40 %), punchy but not neon, measured on cover frames | M |
| Exposure | Mean V 118/255, mid-key | M |
| Contrast | Luma σ ≈ 60 | M |
| Sharpness | **Visible over-sharpening halos and crunchy micro-contrast** on many frames, typical of upscaling plus sharpening of low-resolution sources | O |
| Grain / vignette | Not observed | O |
| Upload resolution | The unauthenticated client was offered at most 480 × 854 for `oB518y0L7fI`, but a JS challenge failed, so formats may be missing. The upload resolution is therefore **undetermined** | M/I |

**Conclusion.** "Mixed grading by footage," unified by two constants: a **crisp/sharpened finish** and the **neon-green caption** drawn over everything.

---

## 5. Phase 5 — Sound design

**Not inspected: no audio was accessible** (see ACCESS_LOG). Only two facts are measured:
* The original track is English, with 13 YouTube auto-dubs.
* The captions transcribe non-speech moments (`*SOUNDS*`), so the source audio, including a speaker imitating animal sounds, is kept audible [O].

Everything in the audio specification ([`02 §D`](02_EDITING_STYLE_BIBLE.md), [`05 §6`](05_PRESET_SPECIFICATION.md)) is labelled **[R]** and should be replaced by the output of `tools/forensics/audio_profile.py`.

---

## 6. Phase 6 — Storytelling and retention

| Stage | Finding | Label |
|---|---|---|
| First frame | The speaker is already talking and the caption is already on screen. No title card, logo sting or intro | M (storyboard f0) |
| First sentence | Mid-story or a claim. The title carries the hook ("Why Never Cut Trees on a New Moon") and the speaker begins inside the answer | I |
| Visual stimulation | A cut roughly every second from frame 1. The first B-roll arrives within ~1 s | M |
| Main body | Information is told by the guest. **B-roll literalises nouns** (≥ 27 of 104 B-roll frames show the exact caption noun). Cutaways return to the speaker every 3–6 s for credibility and emotion: reaction shots, grimaces, laughs | M/O |
| Ending | Ends on the speaker, with no end card, CTA or fade in the storyboard. The last frames are a reaction, so the Short can loop | M/O |
| Thumbnails | None designed: covers are video frames with the caption visible (44/44) | M |

```
TITLE (hook claim) ─► 0 s: speaker mid-story + caption ─► ~1 s cut cadence
   ├─ noun spoken ─► literal B-roll (1–2 s) ─► back to speaker (reaction / punch-in)
   ├─ every 3–6 s: speaker beat (credibility, emotion, *NON-SPEECH* tag)
   └─ last line (twist / verdict) on the speaker ─► hard end ─► loop to frame 1
Captions: continuous, 1–3 words, centred 50 % ─ watermark locked under caption
```

---

## 7. Phase 7 — Frame-by-frame breakdowns

### 7.1 `oB518y0L7fI`: "Why Never Cut Trees on a New Moon" (43 s, 2.7 M views): full 1 fps storyboard

| Frame | t (s) | Class | Hist Δ | New shot | Visual |
|---:|---:|---|---:|---|---|
| 0 | 0.0 | P |  | yes | guest talking head, medium close-up, cropped 9:16 from 16:9 podcast |
| 1 | 0.98 | B | 0.68 | yes | forest path/staircase landscape (stylised, possibly AI) |
| 2 | 1.95 | P | 0.67 | yes | guest, tighter framing (punch-in) |
| 3 | 2.93 | B | 0.62 | yes | logger at tree base |
| 4 | 3.91 | B | 0.6 | yes | hollow trunk close-up |
| 5 | 4.89 | B | 0.51 | yes | giant trunk low angle |
| 6 | 5.86 | B | 0.6 | yes | felled tree stump in forest |
| 7 | 6.84 | B | 0.64 | yes | logs on grass clearing |
| 8 | 7.82 | B | 0.77 | yes | worker on forest track |
| 9 | 8.8 | P | 0.56 | yes | guest reaction |
| 10 | 9.77 | B | 0.42 | yes | forest fire |
| 11 | 10.75 | P | 0.41 | yes | guest, close-up |
| 12 | 11.73 | P | 0.31 | yes | guest, arms crossed (different framing) |
| 13 | 12.7 | B | 0.78 | yes | lone tree in fog by water |
| 14 | 13.68 | B | 0.45 | yes | lone tree in misty field |
| 15 | 14.66 | B | 0.73 | yes | chainsaw cutting log |
| 16 | 15.64 | B | 0.14 | no | same shot (continuation) |
| 17 | 16.61 | B | 0.32 | yes | split log macro |
| 18 | 17.59 | B | 0.73 | yes | moon / eclipse ring on black |
| 19 | 18.57 | P | 0.68 | yes | guest grimace (reaction) |
| 20 | 19.55 | B | 0.7 | yes | moon over tree-ring composite (graphic/AI) |
| 21 | 20.52 | B | 0.22 | no | same shot (continuation) |
| 22 | 21.5 | B | 0.55 | yes | hand holding bored wood |
| 23 | 22.48 | B | 0.67 | yes | city street under suspension bridge |
| 24 | 23.45 | B | 0.16 | no | same shot (continuation) |
| 25 | 24.43 | B | 0.44 | yes | forestry harvester |
| 26 | 25.41 | B | 0.31 | yes | chainsaw on wood |
| 27 | 26.39 | P | 0.53 | yes | guest |
| 28 | 27.36 | B | 0.61 | yes | indigenous community archival/doc footage |
| 29 | 28.34 | B | 0.62 | yes | figure in dark jungle |
| 30 | 29.32 | B | 0.73 | yes | golden misty canopy |
| 31 | 30.3 | B | 0.16 | no | same shot (continuation) |
| 32 | 31.27 | B | 0.86 | yes | night sky / moon |
| 33 | 32.25 | B | 0.68 | yes | insect larvae in wood |
| 34 | 33.23 | B | 0.21 | no | same shot (continuation) |
| 35 | 34.2 | B | 0.71 | yes | stump close-up |
| 36 | 35.18 | B | 0.37 | yes | felled trunk |
| 37 | 36.16 | B | 0.53 | yes | larva macro |
| 38 | 37.14 | B | 0.31 | yes | termites/borers in wood |
| 39 | 38.11 | B | 0.72 | yes | bamboo stand with grey on-screen label |
| 40 | 39.09 | B | 0.19 | no | same shot (continuation) |
| 41 | 40.07 | P | 0.72 | yes | guest, medium close-up |
| 42 | 41.05 | P | 0.23 | no | guest, tighter (punch-in on same take) |
| 43 | 42.02 | P | 0.16 | no | guest, head turned — final frame |

**Reading the table.** Δ ≥ 0.25 is a new shot. Low-Δ pairs with a visible scale change (41→42) are punch-ins on the same take. Unbroken B-roll runs of 6 (f3–f8), 6 (f13–f18), 7 (f20–f26) and 13 samples (f28–f40) track the speaker's argument: trees, cutting, moon, insects. The speaker only returns for emphasis and reaction.

### 7.2 Three-point samples for the other representative videos

| Video | ≈ 25 % | ≈ 50 % | ≈ 75 % | What it shows |
|---|---|---|---|---|
| `7nFyBuaKkTc` (most viewed) | B-roll: diver + giant crab, `CANNOT` | B-roll: whale shark + freediver, `DIVERS` | B-roll: diver close-up, `THIS IS A` | B-roll-dominant discovery story; caption noun matches the picture (`DIVERS`) |
| `3_z-hemLYEg` (recent) | Podcast, `I'VE NEVER SEEN` | Podcast, `ALL OF A SUDDEN` | B-roll: croc top-down, `16FT` | Story → literal number shot |
| `qPQQJ_CLhZ0` (median) | B-roll: dolphin, `HUMAN LEVEL` | Podcast, `THE WORLD` | B-roll: mantis eating cricket, `THEIR SIZE` | Claim → proof shots |
| `hL1CJ4qplqk` | B-roll aerial moose, `AND THEY LET` | B-roll moose in pond, `PRESUMED` | B-roll moose, `SEEN A` | Long B-roll run while the speaker narrates |
| `z1BGPB46LUI` | Podcast wide, `OVER` | Podcast tight, `DOWN` | Podcast medium, `LIKE IT` | Three framings of one take = punch-in grammar |
| `b6qEwIQHqAI` | B-roll: man with gold props, `RICH` | B-roll: crow at table, `OR SOMETHING` | **Split-stack** of two speakers, `THAT HE` | Occasional split layout |
| `KD566jCAu4w` | B-roll croc underwater, `PERFECTLY` | Same shot, tighter, `ENVIRONMENT` | **Blur-fill** podcast, `THEY'RE VERY` | Blur-fill for a non-vertical speaker cam |
| `jCG3oVDFBuM` | Celebrity street clip, `DERULO` | Vlog clip, `GOES OVER TO` | Social clip with **original text overlay**, `YEAH I PUT` | Repurposed social footage as B-roll |
| `DtCh-oP9kg0` | Podcast with dog, `WHAT ANIMAL` | **AI-style composite** (person riding dolphins), `AROUND` | B-roll bear, `BEAR` | Generated imagery used as comic B-roll |
| `1_WnsTGwdgI` | **Stack**: film footage over the podcast, `CAME IN` | Podcast, `AND A` | B-roll: man with bear spray, `BEAR SPRAY` | Literal noun shot |

---

## 8. Limitations and how to remove them

1. **Pacing values are bounds, not exact numbers.** Run `tools/forensics/scene_cuts.py` on 6–10 locally downloaded Shorts to get exact cuts/min, median shot length and opening density.
2. **Audio is unverified.** Run `tools/forensics/audio_profile.py`, with Demucs stems if possible, to get LUFS, music/voice balance and BPM.
3. **Caption animation is unverified.** Step through any Short frame by frame (in a browser: pause, then `,` and `.`). The JSON profile marks this field `"status": "unverified"`.
4. **Upload resolution and dates.** Read them from YouTube Studio if you have access, or from player metadata with a signed-in client.
