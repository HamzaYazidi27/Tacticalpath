# DELIVERABLE 4 — Editing Workflow SOP (Center-Punch Shorts)

Target throughput: **one 35–60 s Short in ~2–3 h** once the source podcast is selected. Each step lists its **input → action → output → done-when**.

---

## 0. Project scaffold

```bash
templates/project/create_project.sh 2026-11-20_octopus-escape ./productions
```

```
PROJECT/
├── 01_PROJECT_FILES/           (.prproj / .drp / CapCut draft, autosave/, timelines/)
├── 02_SOURCE_AROLL/            podcast_raw/ (full episode cams + audio) · selects/
├── 03_BROLL/                   stock/ · original_shot/ · generated_ai/ · licensed/
├── 04_ARCHIVAL_MEDIA/          public-domain / archive material
├── 05_VOICE_AND_TRANSCRIPT/    audio/ (clean dialogue) · transcripts/ (word-level JSON, SRT)
├── 06_MUSIC/
├── 07_SFX/                     whooshes/ · impacts/ · risers/ · foley/ · ui/
├── 08_GRAPHICS/                captions_ass/ · callouts/ · maps/ · crisp_pop_709.cube
├── 09_FONTS/                   Montserrat-Black.otf, Montserrat-ExtraBold.otf
├── 10_PRECOMPS/                reframed_9x16/ · stills_to_clips/
├── 11_EXPORTS/                 review/ · final/ · archive_master/
├── 12_COVERS/                  chosen cover frame(s)
└── 13_LICENSES/                asset_log.csv (one row per external asset)
```

Adapted from the brief:
* `02_RAW_FOOTAGE` → `02_SOURCE_AROLL`, because the A-roll is always a conversation.
* `12_THUMBNAILS` → `12_COVERS`, because Shorts use a frame, not a designed thumbnail.
* `13_LICENSES` is added, because this format lives or dies on rights.

**File naming:** `<shot#>_<type>_<desc>_v<nn>.ext`, e.g. `014_B_octopus-beak-macro_v01.mp4`.

---

## 1. Topic and clip selection (≈ 30 min)

* **Input:** a podcast episode you own or have permission to clip.
* **Action:**
  1. Scan the transcript for **self-contained stories of 35–60 s** that contain a concrete oddity: a number, a "why", a danger, a first-hand encounter.
  2. Each candidate needs ≥ 6 **showable nouns** (animals, objects, places, actions).
  3. Write the **title first**: oddity + voice, e.g. `Why Octopuses Always Escape ft <Guest>`.
* **Output:** in/out timecodes and a title.
* **Done when:** you can say the hook in ≤ 8 words and list ≥ 6 B-roll nouns.

## 2. Dialogue preparation (≈ 15 min)

* Cut the selection **from the first word of the claim**. No greeting, no question set-up unless the question *is* the hook.
* Remove ums, false starts and gaps > 300 ms. Keep natural laughs; they become `*LAUGHS*` tags.
* Clean the audio (see §12) and export `05_VOICE_AND_TRANSCRIPT/audio/dialogue_clean.wav`.
* Transcribe with word timestamps: WhisperX / faster-whisper (`word_timestamps=True`), Premiere Transcript, or CapCut auto captions. Save the JSON.

## 3. Footage research (≈ 30–45 min)

* Build a **noun list** from the transcript. For each noun, find 1–3 clips of 1–3 s each.
* Look in this order:
  1. your own footage
  2. public-domain sources (NOAA, USFWS, NPS, NASA)
  3. free-licence stock (Pexels, Pixabay, Mixkit, Wikimedia Commons CC0/CC-BY)
  4. paid stock (Storyblocks, Artgrid, Pond5)
  5. generated imagery, only for hypothetical or comic beats
* Log every asset in `13_LICENSES/asset_log.csv` **before** it goes on the timeline.

## 4. Asset organisation (≈ 10 min)

* Rename to `<noun>_<source>_<n>`, e.g. `octopus-jar_pexels_1.mp4`.
* Pre-render vertical versions into `10_PRECOMPS/reframed_9x16/`:
  * Horizontal B-roll: `reframe_9x16.sh` (pick the x-centre on the subject).
  * Stills: `still_to_clip.sh`.
  * Low-resolution sources: upscale ×2 first.

## 5. Storyboard (≈ 15 min)

* Paste the transcript into a sheet with one row per caption chunk (1–3 words). Mark each row **A** (speaker) or **B** (noun B-roll).
* **Rules:**
  * The first row is A, already mid-claim.
  * B-roll starts on the first noun (≤ 1.2 s).
  * Return to A every 3–6 s and on every emotional reaction.
  * The last row is A.
* Template: [`demo/storyboard_60s.csv`](../demo/storyboard_60s.csv).

## 6. Rough cut (≈ 20 min)

* Lay the dialogue on A1 and the speaker video (W framing) on V1 for the full length.
* Add **punch-in variants** (P1 112 %, P2 120 %) by blading the speaker track at every sentence boundary and alternating framings.
* Check that the timing works with dialogue only.

## 7. B-roll insertion and fine cut (≈ 40 min)

* Place B-roll on V2 so its first frame lands **0–2 frames before** the noun's first syllable.
* Keep shots 0.7–2.0 s and split longer ones into a second angle. Target ≥ 50 cuts/min and 65–75 % B-roll coverage.
* Watch at 1× with the sound off. Each picture should still "read" the sentence. If a stretch doesn't, replace generic B-roll with literal B-roll.

## 8. Motion graphics (≈ 5 min)

The style has **no** lower thirds, titles or end screens. Only add an explainer callout (green ring) if a fact is invisible otherwise, and keep it ≤ 1.5 s.

## 9. Captions / typography (≈ 15 min)

* Generate the captions:

  ```bash
  python3 templates/captions/make_captions.py words.json 08_GRAPHICS/captions_ass/captions.ass --brand "YOURBRAND"
  ```

  Or apply the `CP_Caption` style in your editor (Blueprint §3–5).
* Proofread every chunk:
  * spelling of names and species
  * numbers as digits (`16FT`)
  * profanity masked
  * non-speech tags in asterisks
* Make sure no chunk covers a face's eyes. If one does, change the shot, not the caption position.

## 10. Colour (≈ 15 min)

1. Neutral balance per clip: white balance and exposure only.
2. Timeline-level finish: `crisp_pop_709.cube` at 80 % + sharpen (unsharp 0.9 / Resolve sharpen 0.40).
3. Check skin on speakers (no orange) and blacks on underwater footage (no crushed blue).

## 11. Sound design (≈ 20 min) [R]

* **Music bed:** one track, starting at 0 s with no fade-in, and ending on the last word (button or hard stop).
* **SFX:**
  * whoosh into 10–20 % of B-roll cuts, the big reveals
  * low impact on the punchline word
  * literal foley where B-roll implies sound (splash, roar, chainsaw)
* Cue SFX 1–2 frames **before** the cut.

## 12. Audio mix (≈ 15 min) [R]

| Element | Treatment |
|---|---|
| Dialogue | HPF 80 Hz → de-ess → comp 3:1 (4–6 dB GR) → presence +2 dB @ 3.5 kHz; dialogue peaks around −6 dBFS |
| Music | Ducked 18–22 dB under dialogue (sidechain, 200 ms release) |
| SFX | Peaks −12 to −8 dBFS; impacts may touch −6 |
| Master | −14 LUFS integrated, ≤ −1 dBTP, LRA ≤ 7 |

## 13. Quality control (≈ 10 min)

| ✓ | Check |
|---|---|
| ▢ | Frame 1 = speaker mid-claim, caption visible |
| ▢ | First B-roll ≤ 1.2 s; cuts/min ≥ 50 (run `tools/forensics/scene_cuts.py` on the export) |
| ▢ | B-roll share 65–75 %; no B-roll > 2 s unrelated to the line |
| ▢ | Captions 100 % coverage, ≤ 16 characters, centre Y = 960, no typos |
| ▢ | Watermark visible the whole time, 56 px under the caption |
| ▢ | Zero dissolves, wipes or zoom transitions |
| ▢ | Eyes never covered by the caption; critical content outside the bottom 20 % / right 15 % UI zones |
| ▢ | Last frame = speaker's last word; loop to frame 1 sounds and reads natural |
| ▢ | −14 LUFS ±1, peaks ≤ −1 dBTP (`tools/forensics/audio_profile.py`) |
| ▢ | Every external asset listed in `asset_log.csv` with a licence |
| ▢ | Watched once on a phone, sound on, at full brightness |

## 14. Export (≈ 5 min)

* Deliver: `11_EXPORTS/final/<date>_<slug>_SHORT.mp4` (Blueprint §6).
* Archive: `11_EXPORTS/archive_master/<slug>_MASTER_ProRes422HQ.mov` + `captions.ass` + `asset_log.csv`.
* Cover: pick a frame where the caption reads as a mini-headline (the channel's covers always show a caption) and save it in `12_COVERS/`.

---

## 15. Asset resources and licences

*Licence terms change. Re-read the licence page on the day you download, and record it in `asset_log.csv`.*

### Stock and archival footage

| Resource | Website | Cost | Licence notes | Best use |
|---|---|---|---|---|
| Pexels Videos | pexels.com | Free | Pexels License: no attribution required; can't resell unmodified clips; check model/brand visibility | General nature, people, cities |
| Pixabay | pixabay.com | Free | Pixabay Content License: similar to Pexels; restrictions on standalone resale | Nature, animals, stills |
| Mixkit | mixkit.co | Free | Mixkit licence per category: read the video licence | Short vertical-friendly clips |
| Coverr | coverr.co | Free | Coverr licence | Lifestyle/nature fillers |
| Wikimedia Commons | commons.wikimedia.org | Free | **Per file** (CC0, CC-BY, CC-BY-SA, PD): attribution often required | Rare species, historical images |
| NOAA Photo Library / Ocean Exploration | photolib.noaa.gov · oceanexplorer.noaa.gov | Free | US-government works are generally public domain; credit requested; check third-party items | Sharks, whales, deep sea |
| USFWS National Digital Library | digitalmedia.fws.gov | Free | Mostly public domain; check each item | US wildlife |
| NPS (US National Park Service) | nps.gov (photo/video galleries) | Free | NPS-created media is generally public domain; check credits | Bears, wolves, parks |
| NASA Image and Video Library | images.nasa.gov | Free | Generally not copyrighted; follow NASA media guidelines (no endorsement implied) | Moon, Earth, space |
| Internet Archive | archive.org | Free | Varies per item; many items are *not* PD | Archival film, if PD is verified |
| Storyblocks | storyblocks.com | Subscription | Royalty-free with subscription | High-volume B-roll |
| Artgrid | artgrid.io | Subscription | Royalty-free, cinematic | Premium nature/cinematic |
| Envato Elements | elements.envato.com | Subscription | Item licence per project registration | Footage + templates + SFX |
| Pond5 | pond5.com | Per clip | Royalty-free per clip; strong archival/wildlife catalogue | Specific wildlife moments |

### Music

| Resource | Website | Cost | Licence notes |
|---|---|---|---|
| YouTube Audio Library | studio.youtube.com → Audio library | Free | Some tracks require attribution in the description |
| Epidemic Sound | epidemicsound.com | Subscription | Clears the channel when registered; widely used for Shorts |
| Artlist | artlist.io | Subscription | Lifetime licence for content made during the subscription |
| Uppbeat | uppbeat.io | Freemium | Free tier requires a credit code |
| Pixabay Music | pixabay.com/music | Free | Pixabay licence; some tracks are Content-ID registered by the uploader: check |
| Free Music Archive | freemusicarchive.org | Free | Per track (CC variants): check NC/ND |

### Sound effects

| Resource | Website | Cost | Licence notes |
|---|---|---|---|
| Freesound | freesound.org | Free | Per sound: CC0 / CC-BY / CC-BY-NC (avoid NC for monetised channels) |
| Zapsplat | zapsplat.com | Free / paid | Free tier requires attribution |
| Pixabay Sound Effects | pixabay.com/sound-effects | Free | Pixabay licence |
| Sonniss GDC bundles | sonniss.com/gameaudiogdc | Free | Royalty-free, commercial use allowed per bundle licence |
| Epidemic Sound SFX | epidemicsound.com | Subscription | Included with the subscription |
| BBC Sound Effects | sound-effects.bbcrewind.co.uk | Free* | *RemArc licence = personal / educational / research only; **not for monetised YouTube** without a commercial licence |

### Typography

| Font | Source | Licence |
|---|---|---|
| **Montserrat** (Black / ExtraBold) | fonts.google.com/specimen/Montserrat | SIL Open Font License: free for commercial video |
| Poppins Black (alt) | fonts.google.com | OFL |
| Gilroy Heavy (alt) | Radomir Tinkov (commercial) | Paid licence for commercial use |

### Motion graphics, maps and tools

| Resource | Website | Cost | Use |
|---|---|---|---|
| Motion Array / Envato Elements | motionarray.com · elements.envato.com | Subscription | Callout rings, map packs (keep them on-style) |
| Natural Earth | naturalearthdata.com | Free, public domain | Clean vector maps |
| OpenStreetMap | openstreetmap.org | Free (ODbL) | Map data; attribution "© OpenStreetMap contributors" |
| Google Earth Studio | earth.google.com/studio | Free | Aerial fly-ins; Google attribution required on screen |
| WhisperX / faster-whisper | github.com/m-bain/whisperX · github.com/SYSTRAN/faster-whisper | Free (open source) | Word timestamps for `make_captions.py` |
| Real-ESRGAN | github.com/xinntao/Real-ESRGAN | Free (open source) | Upscaling low-res B-roll |
| Topaz Video AI | topazlabs.com | Paid | Upscaling / denoise |
| Adobe Firefly | firefly.adobe.com | Freemium | Generated stills for hypothetical/comic beats; Adobe positions it for commercial use |

### Asset acquisition checklist (per asset)
- [ ] The asset shows the noun being spoken (literal), or is a deliberate comic/hypothetical image
- [ ] Licence read today and allows **commercial, monetised** use on YouTube
- [ ] Attribution requirement noted (description text ready)
- [ ] No NC/ND restriction, no editorial-only restriction (unless the use is editorial)
- [ ] Identifiable people: model release, or editorial context only
- [ ] Resolution ≥ 1080 px on the short side after reframing (or upscaled before sharpening)
- [ ] Logged in `13_LICENSES/asset_log.csv` with URL and date
- [ ] Generated imagery labelled per YouTube's altered/synthetic content disclosure when realistic
