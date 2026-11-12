# DELIVERABLE 6 — 60-Second Demonstration Storyboard

**"Why Octopuses Always Escape"**: an original concept that validates the Center-Punch system.

* Rendered animatic (placeholder visuals, real timing and real captions): [`demo/animatic_60s.mp4`](../demo/animatic_60s.mp4)
* Machine-readable storyboard: [`demo/storyboard_60s.csv`](../demo/storyboard_60s.csv)
* Rebuild it with `python3 demo/build_animatic.py`

Nothing here is copied from the reference channel. The script is original, the facts are public knowledge, and the animatic uses synthetic slates and a synthetic guide track.

---

## 1. Concept

| | |
|---|---|
| Format | Podcast-clip Short, 9:16, 60.0 s, 30 fps |
| A-roll | Your own podcast: **Guest** (marine-biology enthusiast) on A-cam, **Host** on B-cam |
| Title | `Why Octopuses Always Escape ft <Guest>` (the "why" + counter-intuitive behaviour pattern behind the reference's 2.7 M-view Short) |
| Hook | The first frame is the guest mid-claim: "An octopus once escaped from an aquarium…" |
| Loop | The last line ("…because it would win.") flows back into the first ("An octopus once escaped…") |

### How the demo maps to the measured profile

| Metric | Demo | Reference |
|---|---:|---|
| Shots / cuts per minute | **52 / 51.0** | ≥ 48.8 [M] |
| A-roll share of runtime | **35.9 %** | 23–36 % [M] |
| Caption chunks | **90** | — |
| Words per chunk (mean) | **1.91** | 1.79 [M] |
| Caption centre / cap height | **0.502 / 41 px** (re-measured on the render) | 0.501 / 41 px [M] |

---

## 2. Narration script (original)

| Time | Speaker | Line |
|---|---|---|
| 0.04–5.63 | Guest | An octopus once escaped from an aquarium, crawled across the floor, and slid down a drain pipe into the ocean. |
| 5.79–9.61 | Guest | Nobody saw it happen. They just found the wet trail in the morning. |
| 9.79–12.63 | Guest | And here's the crazy part, that's not even rare. |
| 12.79–16.33 | Guest | Octopuses have no bones. The only hard part of their body is the beak. |
| 16.49–20.13 | Guest | So if the beak fits through a gap, the whole animal fits. |
| 20.29–23.93 | Guest | A five-kilo octopus can squeeze through a hole the size of a coin. |
| 24.09–24.72 | Host | *laughs* |
| 24.89–29.92 | Guest | And they're smart about it. In labs they've learned to unscrew jars from the inside. |
| 30.09–34.71 | Guest | They'll short-circuit the lights by squirting water at them, because they don't like the brightness. |
| 34.89–38.53 | Guest | Two thirds of their neurons are in their arms, so every arm is basically thinking for itself. |
| 38.69–41.73 | Guest | Which means when an octopus escapes, it's not luck. |
| 41.89–47.45 | Guest | It's watching you. It's learning the schedule. |
| 47.69–52.13 | Guest | And it's waiting for the one night somebody forgets to close the lid. |
| 52.29–54.73 | Guest | Honestly? I'd never keep one. |
| 54.89–56.25 | Host | Why? |
| 56.49–59.88 | Guest | Not because it's dangerous. Because it would win. |

**Fact-check notes.** Before publishing, verify each claim against a reliable source and cite it in the description. All of them are widely reported:
* octopus aquarium escape via a drain (New Zealand, 2016)
* the beak is the only hard part
* squeezing through gaps about the size of the beak
* unscrewing jars from inside
* squirting water at lights
* about two-thirds of neurons in the arms

---

## 3. Scene-by-scene storyboard and editing timeline

Hard cut on every row. `A-roll` = speaker, `B-roll` = cutaway.

| # | In → Out | Dur | Type | Framing | Visual | Motion | SFX | Purpose |
|---:|---|---:|---|---|---|---|---|---|
| 1 | 0.00→1.10 | 1.10 | A-roll | A-cam guest MCU, punch 115% | Guest mid-story, eyes to host | static; punched-in crop | none — voice from frame 1 | HOOK: open on the most extreme claim, caption already on screen |
| 2 | 1.10→2.25 | 1.15 | B-roll | B-roll wide | Aquarium tank at night, octopus pressed against glass | push-in 100→106% | soft whoosh (-24 dB) on cut | Illustrate "aquarium" the instant it is spoken |
| 3 | 2.25→3.25 | 1.00 | B-roll | B-roll macro | Arm sliding over the tank rim | static | wet squelch, low | Literal visual of "crawled" |
| 4 | 3.25→4.20 | 0.95 | B-roll | B-roll low angle | Wet trail across a concrete floor | push-in 100→105% | — | Literal visual of "across the floor" |
| 5 | 4.20→4.95 | 0.75 | B-roll | B-roll close | Floor drain grate, water draining | static | drain gurgle | "drain pipe" |
| 6 | 4.95→5.75 | 0.80 | B-roll | B-roll aerial | Harbour at dawn, open sea | slow drift right | whoosh into wide | Payoff of sentence 1: "into the ocean" |
| 7 | 5.75→6.85 | 1.10 | A-roll | A-cam guest MCU 100% | Guest shrugs | static (wide framing = punch-out) | — | Return to speaker = credibility; reset framing |
| 8 | 6.85→8.05 | 1.20 | B-roll | B-roll medium | Empty aquarium corridor, morning light | push-in | room tone | "Nobody saw it" |
| 9 | 8.05→8.90 | 0.85 | B-roll | B-roll insert | Close-up of wet streak ending at the drain | static | — | Evidence shot |
| 10 | 8.90→9.75 | 0.85 | B-roll | B-roll insert — angle 2 | Close-up of wet streak ending at the drain (second angle / tighter) | static | — | Split long B-roll into two angles to hold ~1 s rhythm |
| 11 | 9.75→10.85 | 1.10 | A-roll | B-cam host reaction | Host leans back, eyebrows up | static | — | Reaction = permission for viewer to be surprised; caption keeps guest words |
| 12 | 10.85→12.75 | 1.90 | A-roll | A-cam guest, punch 120% | Guest leans in: "that's not even rare" | static, tightest framing | low impact hit under "rare" | Escalation beat — tightest punch on the key word |
| 13 | 12.75→14.05 | 1.30 | B-roll | B-roll medium | Octopus flowing over reef rocks | tracking with subject | — | Context: the animal itself |
| 14 | 14.05→15.25 | 1.20 | B-roll | Motion graphic | Silhouette of octopus; beak circled in caption-green ring that draws on | ring stroke 0→100% in 8 f | UI tick on ring complete | Explain "only hard part = beak" visually |
| 15 | 15.25→16.45 | 1.20 | B-roll | B-roll macro | Beak close-up (stock/footage) | push-in | — | Proof shot |
| 16 | 16.45→17.85 | 1.40 | A-roll | A-cam guest MCU | Guest gestures a small gap with fingers | static | — | Speaker sells the rule |
| 17 | 17.85→19.05 | 1.20 | B-roll | B-roll close | Octopus squeezing through a rock crack | static | squeeze/stretch foley | Literal |
| 18 | 19.05→20.25 | 1.20 | B-roll | B-roll tighter | Same action, last arm disappearing | static | — | Completion of action (2-shot mini sequence) |
| 19 | 20.25→21.45 | 1.20 | A-roll | A-cam guest wide 100% | Hands show coin size | static | — | Gesture needs the wider framing |
| 20 | 21.45→22.85 | 1.40 | B-roll | B-roll medium | Octopus passing through a narrow tube (lab footage) | static | — | "five-kilo octopus" |
| 21 | 22.85→24.05 | 1.20 | B-roll | Insert | Coin on dark table, top-down | push-in 100→110% | coin clink | Size comparison |
| 22 | 24.05→24.85 | 0.80 | A-roll | B-cam host laughing | Host laughs | static | — | Caption shows *LAUGHS* tag — emotional beat |
| 23 | 24.85→26.05 | 1.20 | A-roll | A-cam guest punch 112% | Guest continues | static | — | Back to story |
| 24 | 26.05→27.35 | 1.30 | B-roll | B-roll wide | Lab tank with jar inside | push-in | — | Setup |
| 25 | 27.35→28.10 | 0.75 | B-roll | B-roll close | Octopus inside jar turning the lid from inside | static | glass creak | Literal "unscrew jars from the inside" |
| 26 | 28.10→28.85 | 0.75 | B-roll | B-roll close — angle 2 | Octopus inside jar turning the lid from inside (second angle / tighter) | static | — | Split long B-roll into two angles to hold ~1 s rhythm |
| 27 | 28.85→30.05 | 1.20 | B-roll | B-roll close | Lid pops off | static | pop + small impact | Micro-payoff |
| 28 | 30.05→31.05 | 1.00 | A-roll | A-cam guest MCU | Guest grinning | static | — | Speaker |
| 29 | 31.05→32.45 | 1.40 | B-roll | B-roll wide | Aquarium lamp glowing above tank at night | static | electrical hum fades in | Setup for next gag |
| 30 | 32.45→33.45 | 1.00 | B-roll | B-roll close | Water jet hits the lamp → flicker → 4 black frames | static; 4-frame black | zap + hum cuts out | Visual gag on "short-circuit lights" |
| 31 | 33.45→34.85 | 1.40 | B-roll | B-roll macro | Single octopus eye in the dark | push-in 100→108% | low drone swell | Creepy "they don't like the brightness" |
| 32 | 34.85→36.05 | 1.20 | A-roll | A-cam guest MCU | Guest taps temple | static | — | Speaker |
| 33 | 36.05→37.45 | 1.40 | B-roll | B-roll overhead | Arms moving independently | static | — | "Two thirds of their neurons are in their arms" |
| 34 | 37.45→38.65 | 1.20 | B-roll | B-roll close | One arm curling around a shell | static | — | Each arm "thinking" |
| 35 | 38.65→40.05 | 1.40 | B-roll | B-roll close | Another arm probing a crevice | static | — | Repetition = proof |
| 36 | 40.05→41.85 | 1.80 | A-roll | A-cam guest punch 115% | "…not luck." | static | low impact on "luck" | Turn of the story: from facts to menace |
| 37 | 41.85→43.05 | 1.20 | B-roll | B-roll ECU | Octopus eye opening | static | — | Menace |
| 38 | 43.05→44.85 | 1.80 | A-roll | B-cam host reaction | Host slowly shakes head | static | — | Reaction holds longer = tension |
| 39 | 44.85→46.15 | 1.30 | B-roll | B-roll medium | Octopus watching a keeper through the glass | rack-focus feel | — | "It's watching you" |
| 40 | 46.15→46.90 | 0.75 | B-roll | Insert | Feeding-schedule whiteboard / wall clock | push-in | clock tick | "learning the schedule" |
| 41 | 46.90→47.65 | 0.75 | B-roll | Insert — angle 2 | Feeding-schedule whiteboard / wall clock (second angle / tighter) | push-in | — | Split long B-roll into two angles to hold ~1 s rhythm |
| 42 | 47.65→48.40 | 0.75 | B-roll | B-roll wide | Keeper leaves, lights switch off | static | light switch clack | Night falls |
| 43 | 48.40→49.15 | 0.75 | B-roll | B-roll wide — angle 2 | Keeper leaves, lights switch off (second angle / tighter) | static | — | Split long B-roll into two angles to hold ~1 s rhythm |
| 44 | 49.15→50.45 | 1.30 | B-roll | B-roll close | Tank lid left slightly open | push-in 100→110% | tension riser starts (2 s) | Setup |
| 45 | 50.45→51.35 | 0.90 | B-roll | B-roll macro | Arm tip slips out of the lid gap | static | — | Payoff |
| 46 | 51.35→52.25 | 0.90 | B-roll | B-roll macro — angle 2 | Arm tip slips out of the lid gap (second angle / tighter) | static | — | Split long B-roll into two angles to hold ~1 s rhythm |
| 47 | 52.25→53.45 | 1.20 | A-roll | A-cam guest wide 100% | Guest laughs, sits back | static | riser stops dead | Release |
| 48 | 53.45→54.85 | 1.40 | A-roll | A-cam guest punch 115% | "I'd never keep one." | static | — | Personal verdict |
| 49 | 54.85→56.45 | 1.60 | A-roll | B-cam host reaction | Host: "why?" | static | — | Set up the punchline |
| 50 | 56.45→57.35 | 0.90 | B-roll | B-roll low angle | Octopus crossing a dark floor toward camera | slow push-in | wet steps foley | Final image of menace |
| 51 | 57.35→58.25 | 0.90 | B-roll | B-roll low angle — angle 2 | Octopus crossing a dark floor toward camera (second angle / tighter) | slow push-in | — | Split long B-roll into two angles to hold ~1 s rhythm |
| 52 | 58.25→60.00 | 1.75 | A-roll | A-cam guest punch 120% | "…because it would win." | static | music button / hard stop on last word | Punchline + seamless loop into "An octopus once…" |

**Structure**

| Stage | Time | Content |
|---|---|---|
| Claim | 0–5.75 | 1 A-roll + 5 literal B-roll |
| Context | 5.75–24.85 | |
| Escalation | 24.85–44.85 | Intelligence → independence → "not luck" |
| Menace | 44.85–53.45 | Watching → schedule → lid |
| Verdict + loop | 53.45–60 | |

The tightest punch-ins (120 %) fall on "rare" (shot 12) and "win" (shot 52); "luck" (shot 36) gets 115 %.

---

## 4. Footage requirements

| Need | Shots | Suggested legal source |
|---|---|---|
| Podcast A/B-cam, 4K or 1080p, 16:9, two speakers | 1, 7, 11–12, 16, 19, 22–23, 28, 32, 36, 38, 47–49, 52 | Your own recording |
| Octopus behaviour (reef, squeezing, arms, eye, jar) | ~18 shots | Pexels / Pixabay / Storyblocks / Pond5; NOAA for wild octopus |
| Aquarium environment (tank at night, corridor, lid, keeper, lights) | ~10 shots | Shoot at a local aquarium with permission, or use stock |
| Inserts (coin, clock/whiteboard, wet floor, drain) | 5 shots | Shoot yourself in 20 minutes on a phone |
| Explainer graphic (beak callout) | Shot 14 | Build in-editor: green ring `#19F464` + shadow |
| Water-jet-on-lamp gag | Shot 30 | Stock, or a staged practical shot. Add 4 black frames |

---

## 5. Text overlays (captions)

* Generated by `make_captions.py` from `demo/words_60s.json`: 90 chunks, every one ≤ 16 characters, centre Y 960.
* Brand watermark `WILD` + `FRAME`, 56 px under the caption, for the full 60 s.
* `*LAUGHS*` appears as a non-speech tag.

| # | In → Out (s) | Caption | # | In → Out (s) | Caption |
|---:|---|---|---:|---|---|
| 1 | 0.04 → 0.54 | `AN OCTOPUS` | 46 | 27.96 → 28.57 | `TO UNSCREW` |
| 2 | 0.54 → 1.16 | `ONCE ESCAPED` | 47 | 28.57 → 29.30 | `JARS FROM THE` |
| 3 | 1.16 → 1.49 | `FROM AN` | 48 | 29.30 → 30.09 | `INSIDE` |
| 4 | 1.49 → 2.16 | `AQUARIUM` | 49 | 30.09 → 30.45 | `THEY'LL` |
| 5 | 2.16 → 2.88 | `CRAWLED ACROSS` | 50 | 30.45 → 31.11 | `SHORT-CIRCUIT` |
| 6 | 2.88 → 3.55 | `THE FLOOR` | 51 | 31.11 → 31.67 | `THE LIGHTS BY` |
| 7 | 3.55 → 3.94 | `AND SLID` | 52 | 31.67 → 32.12 | `SQUIRTING` |
| 8 | 3.94 → 4.28 | `DOWN A` | 53 | 32.12 → 32.48 | `WATER AT` |
| 9 | 4.28 → 4.78 | `DRAIN PIPE` | 54 | 32.48 → 32.89 | `THEM` |
| 10 | 4.78 → 5.17 | `INTO THE` | 55 | 32.89 → 33.45 | `BECAUSE THEY` |
| 11 | 5.17 → 5.79 | `OCEAN` | 56 | 33.45 → 34.06 | `DON'T LIKE THE` |
| 12 | 5.79 → 6.49 | `NOBODY SAW IT` | 57 | 34.06 → 34.89 | `BRIGHTNESS` |
| 13 | 6.49 → 7.13 | `HAPPEN` | 58 | 34.89 → 35.38 | `TWO THIRDS OF` |
| 14 | 7.13 → 7.63 | `THEY JUST` | 59 | 35.38 → 35.91 | `THEIR NEURONS` |
| 15 | 7.63 → 8.14 | `FOUND THE` | 60 | 35.91 → 36.13 | `ARE IN` |
| 16 | 8.14 → 8.78 | `WET TRAIL IN` | 61 | 36.13 → 36.71 | `THEIR ARMS` |
| 17 | 8.78 → 9.79 | `THE MORNING` | 62 | 36.71 → 37.02 | `SO EVERY` |
| 18 | 9.79 → 10.54 | `AND HERE'S THE` | 63 | 37.02 → 37.24 | `ARM IS` |
| 19 | 10.54 → 11.36 | `CRAZY PART` | 64 | 37.24 → 37.64 | `BASICALLY` |
| 20 | 11.36 → 11.92 | `THAT'S NOT` | 65 | 37.64 → 38.13 | `THINKING FOR` |
| 21 | 11.92 → 12.79 | `EVEN RARE` | 66 | 38.13 → 38.69 | `ITSELF` |
| 22 | 12.79 → 13.30 | `OCTOPUSES` | 67 | 38.69 → 39.32 | `WHICH MEANS` |
| 23 | 13.30 → 13.64 | `HAVE NO` | 68 | 39.32 → 39.70 | `WHEN AN` |
| 24 | 13.64 → 14.15 | `BONES` | 69 | 39.70 → 40.83 | `OCTOPUS ESCAPES` |
| 25 | 14.15 → 14.55 | `THE ONLY` | 70 | 40.83 → 41.27 | `IT'S NOT` |
| 26 | 14.55 → 15.12 | `HARD PART OF` | 71 | 41.27 → 41.89 | `LUCK` |
| 27 | 15.12 → 15.74 | `THEIR BODY IS` | 72 | 41.89 → 43.37 | `IT'S WATCHING` |
| 28 | 15.74 → 16.49 | `THE BEAK` | 73 | 43.37 → 44.24 | `YOU` |
| 29 | 16.49 → 16.98 | `SO IF THE` | 74 | 44.24 → 45.72 | `IT'S LEARNING` |
| 30 | 16.98 → 17.53 | `BEAK FITS` | 75 | 45.72 → 47.69 | `THE SCHEDULE` |
| 31 | 17.53 → 18.16 | `THROUGH A` | 76 | 47.69 → 48.21 | `AND IT'S` |
| 32 | 18.16 → 18.64 | `GAP` | 77 | 48.21 → 49.18 | `WAITING FOR THE` |
| 33 | 18.64 → 19.20 | `THE WHOLE` | 78 | 49.18 → 49.78 | `ONE NIGHT` |
| 34 | 19.20 → 20.29 | `ANIMAL FITS` | 79 | 49.78 → 50.90 | `SOMEBODY FORGETS` |
| 35 | 20.29 → 20.96 | `A FIVE-KILO` | 80 | 50.90 → 51.65 | `TO CLOSE THE` |
| 36 | 20.96 → 21.58 | `OCTOPUS CAN` | 81 | 51.65 → 52.29 | `LID` |
| 37 | 21.58 → 22.44 | `SQUEEZE THROUGH` | 82 | 52.29 → 53.25 | `HONESTLY?` |
| 38 | 22.44 → 22.99 | `A HOLE THE` | 83 | 53.25 → 53.89 | `I'D NEVER` |
| 39 | 22.99 → 23.48 | `SIZE OF A` | 84 | 53.89 → 54.89 | `KEEP ONE` |
| 40 | 23.48 → 24.09 | `COIN` | 85 | 54.89 → 56.49 | `WHY?` |
| 41 | 24.09 → 25.09 | `*LAUGHS* AND` | 86 | 56.49 → 57.20 | `NOT BECAUSE` |
| 42 | 25.09 → 25.89 | `THEY'RE SMART` | 87 | 57.20 → 57.49 | `IT'S` |
| 43 | 25.89 → 26.63 | `ABOUT IT` | 88 | 57.49 → 58.42 | `DANGEROUS` |
| 44 | 26.63 → 27.03 | `IN LABS` | 89 | 58.42 → 59.06 | `BECAUSE IT` |
| 45 | 27.03 → 27.96 | `THEY'VE LEARNED` | 90 | 59.06 → 60.13 | `WOULD WIN` |

---

## 6. Transition instructions

* **52 hard cuts.**
* No dissolves, wipes or zooms.
* The only "effect" is 4 black frames at the end of shot 30 (the lights-out gag), as a cut, not a fade.
* B-roll cuts land 0–2 frames before the noun onset.
* Loop: the last frame (shot 52, guest at 120 %) cuts hard; the replay starts on shot 1 (guest at 115 %), so the loop reads as one more jump cut.

---

## 7. Music progression [R]

| Time | Music |
|---|---|
| 0–24.05 | Low mysterious pulse (felt synth + soft pizzicato), ~95–100 BPM, ducked −20 dB under dialogue; starts at full level at frame 1 (no fade) |
| 24.05 | Bed drops out for 0.8 s under the host's laugh (shot 22, comic release), then returns |
| 31–36 | Electrical hum layer, cut dead on the 4 black frames |
| 44.8–52.2 | Tension: add a low drone; 2 s riser from 49.15 s (shot 44, lid) |
| 52.25 | Riser stops dead on the cut to the guest (shot 47, release) |
| 57.35–60 | Bed thins to just the pulse; stops on "win" with a single low button note |

## 8. SFX placement [R]

| Shot | Time (s) | SFX | Level |
|---:|---:|---|---|
| 2 | 1.10 | soft whoosh (-24 dB) on cut | −12 to −14 dBFS |
| 3 | 2.25 | wet squelch, low | −16 to −12 dBFS |
| 5 | 4.20 | drain gurgle | −16 to −12 dBFS |
| 6 | 4.95 | whoosh into wide | −12 to −14 dBFS |
| 8 | 6.85 | room tone | −16 to −12 dBFS |
| 12 | 10.85 | low impact hit under "rare" | −8 dBFS |
| 14 | 14.05 | UI tick on ring complete | −18 dBFS |
| 17 | 17.85 | squeeze/stretch foley | −16 to −12 dBFS |
| 21 | 22.85 | coin clink | −16 to −12 dBFS |
| 25 | 27.35 | glass creak | −16 to −12 dBFS |
| 27 | 28.85 | pop + small impact | −8 dBFS |
| 29 | 31.05 | electrical hum fades in | −16 to −12 dBFS |
| 30 | 32.45 | zap + hum cuts out | −16 to −12 dBFS |
| 31 | 33.45 | low drone swell | −16 to −12 dBFS |
| 36 | 40.05 | low impact on "luck" | −8 dBFS |
| 40 | 46.15 | clock tick | −18 dBFS |
| 42 | 47.65 | light switch clack | −16 to −12 dBFS |
| 44 | 49.15 | tension riser starts (2 s) | −14 → −8 dBFS |
| 47 | 52.25 | riser stops dead | −14 → −8 dBFS |
| 50 | 56.45 | wet steps foley | −16 to −12 dBFS |
| 52 | 58.25 | music button / hard stop on last word | −10 dBFS |

## 9. Colour treatment

1. Per-clip neutral balance.
2. Timeline finish `crisp_pop_709.cube` at 80 % + unsharp 0.9.
3. Underwater shots: protect the blues, lift the shadows +3 %.
4. Night aquarium shots: keep blacks at ~2–3 %, not crushed. The octopus eye must read.

## 10. Export

* Deliver `CP_Shorts_1080x1920_30p` (H.264, 16/20 Mbps, AAC 320 k, −14 LUFS / −1 dBTP).
* Archive `CP_Master_ProRes` + `captions_60s.ass`.
* One-liner: `templates/ffmpeg/finish_and_export.sh edit.mp4 demo/captions_60s.ass final.mp4`.

## 11. Validation performed in this repo

Measured by running the repo's forensic tools on the rendered animatic:

| Check | Tool | Result |
|---|---|---|
| Rhythm | `tools/forensics/scene_cuts.py demo/animatic_60s.mp4` | 51 shots detected (of 52 cut), **50.1 cuts/min**, median shot 1.2 s, 17/17/16 cuts per third. The one undetected cut joins two consecutive A-cam shots with near-identical placeholder slates; real footage would separate them |
| Caption geometry | `tools/forensics/caption_sampler.py demo/animatic_60s.mp4` | Centre **0.502**, cap height **41 px**, matching the reference (0.501 / 41 px) |
| Loudness | `tools/forensics/audio_profile.py` | Guide track normalised to about −16 LUFS (single-pass loudnorm). Two-pass is needed for an exact −14 |
