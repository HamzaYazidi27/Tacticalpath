#!/usr/bin/env python3
"""
build_animatic.py — render the 60-second demonstration storyboard as a timed animatic.

It proves the template pipeline end-to-end with ORIGINAL placeholder visuals (no third-party footage):
  storyboard_60s.csv  ─┐
  narration lines     ─┼─► slates (PIL) ─► clips with motion (ffmpeg zoompan) ─► concat
                       └─► word timings ─► make_captions.py (ASS) ─► burned captions
  + cut-tick / riser / drone guide track (synthesised) so the rhythm is audible.

Outputs: demo/words_60s.json, demo/captions_60s.ass, demo/animatic_60s.mp4
Requires: ffmpeg (libass), pillow, Montserrat font installed.
"""
import csv
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
W, H = 1080, 1920

# Narration mapped to ORIGINAL shot numbers (column _orig in the CSV). Original script — see docs/06.
LINES = [
    ((1, 6), "An octopus once escaped from an aquarium, crawled across the floor, and slid down a drain pipe into the ocean."),
    ((7, 9), "Nobody saw it happen. They just found the wet trail in the morning."),
    ((10, 11), "And here's the crazy part, that's not even rare."),
    ((12, 14), "Octopuses have no bones. The only hard part of their body is the beak."),
    ((15, 17), "So if the beak fits through a gap, the whole animal fits."),
    ((18, 20), "A five-kilo octopus can squeeze through a hole the size of a coin."),
    ((21, 21), "*laughs*"),
    ((22, 25), "And they're smart about it. In labs they've learned to unscrew jars from the inside."),
    ((26, 29), "They'll short-circuit the lights by squirting water at them, because they don't like the brightness."),
    ((30, 32), "Two thirds of their neurons are in their arms, so every arm is basically thinking for itself."),
    ((33, 34), "Which means when an octopus escapes, it's not luck."),
    ((35, 38), "It's watching you. It's learning the schedule."),
    ((39, 41), "And it's waiting for the one night somebody forgets to close the lid."),
    ((42, 43), "Honestly? I'd never keep one."),
    ((44, 44), "Why?"),
    ((45, 46), "Not because it's dangerous. Because it would win."),
]

FONT_B = "/usr/share/fonts/opentype/montserrat/Montserrat-Black.otf"
FONT_M = "/usr/share/fonts/opentype/montserrat/Montserrat-SemiBold.otf"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def load_rows():
    return list(csv.DictReader(open(HERE / "storyboard_60s.csv")))


def word_timings(rows):
    """Spread each line's words over its shots, weighting by word length (+ pause on punctuation)."""
    spans = {}
    for r in rows:
        o = int(r["_orig"])
        s, e = float(r["start_s"]), float(r["end_s"])
        a, b = spans.get(o, (s, e))
        spans[o] = (min(a, s), max(b, e))
    words = []
    for (o0, o1), text in LINES:
        t0, t1 = spans[o0][0] + 0.04, spans[o1][1] - 0.08
        toks = text.split()
        weights = [max(2, len(w)) + (3 if w[-1] in ",.?!" else 0) for w in toks]
        tot = sum(weights)
        t = t0
        for w, k in zip(toks, weights):
            d = (t1 - t0) * k / tot
            words.append({"word": w, "start": round(t, 3), "end": round(t + d * 0.92, 3)})
            t += d
    return words


def slate(r, path):
    is_p = r["type"] == "P"
    import colorsys
    n = int(r["shot"])
    if is_p:   # A-cam guest = warm studio, B-cam host = cooler studio
        hue = 0.06 if "A-cam" in r["framing"] else 0.72
        top = tuple(int(255 * c) for c in colorsys.hsv_to_rgb(hue, 0.45, 0.30))
        bot = tuple(int(255 * c) for c in colorsys.hsv_to_rgb(hue, 0.40, 0.08))
    else:      # every B-roll shot gets its own palette so cuts read like real footage changes
        hue = (n * 0.137) % 1.0
        top = tuple(int(255 * c) for c in colorsys.hsv_to_rgb(hue, 0.55, 0.42))
        bot = tuple(int(255 * c) for c in colorsys.hsv_to_rgb((hue + 0.08) % 1, 0.50, 0.10))
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        k = y / H
        c = tuple(int(top[i] * (1 - k) + bot[i] * k) for i in range(3))
        for x in range(W):
            px[x, y] = c
    d = ImageDraw.Draw(img)
    if is_p:
        # head-and-shoulders silhouette, scaled by the punch-in value in the framing text
        z = 1.0
        for tok in r["framing"].replace("%", " ").split():
            if tok.isdigit() and 100 <= int(tok) <= 140:
                z = int(tok) / 100
        cx, cy = W // 2, int(H * 0.36)
        hr = int(150 * z)
        d.ellipse([cx - hr, cy - int(hr * 1.25), cx + hr, cy + int(hr * 1.25)], fill=(92, 74, 64))
        d.rounded_rectangle([cx - int(330 * z), cy + int(hr * 1.1), cx + int(330 * z), H + 200], radius=int(220 * z), fill=(30, 30, 34))
        # mic
        d.rectangle([cx + int(170 * z), cy + int(160 * z), cx + int(215 * z), cy + int(420 * z)], fill=(12, 12, 14))
        img = img.filter(ImageFilter.GaussianBlur(1.2))
        d = ImageDraw.Draw(img)
    else:
        f = font(FONT_M, 46)
        words, lines, cur = r["visual"].split(), [], ""
        for w in words:
            if len(cur) + len(w) > 26:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        y = int(H * 0.68)
        for ln in lines:
            tw = d.textlength(ln, font=f)
            d.text(((W - tw) / 2, y), ln, font=f, fill=(170, 200, 210))
            y += 60
        # simple framing guides
        d.rectangle([90, 260, W - 90, H - 300], outline=(60, 90, 100), width=3)
    lab = font(FONT_B, 34)
    tag = f"SHOT {int(r['shot']):02d}  ·  {'A-ROLL' if is_p else 'B-ROLL'}  ·  {float(r['dur_s']):.2f}s"
    d.rounded_rectangle([60, 70, 60 + d.textlength(tag, font=lab) + 40, 132], radius=14, fill=(0, 0, 0))
    d.text((80, 80), tag, font=lab, fill=(25, 244, 100) if not is_p else (240, 236, 230))
    sub = font(FONT_M, 30)
    d.text((62, 150), r["framing"][:60], font=sub, fill=(200, 200, 200))
    d.text((62, 192), f"motion: {r['motion'][:48]}", font=sub, fill=(150, 150, 150))
    img.save(path)


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    rows = load_rows()
    words = word_timings(rows)
    (HERE / "words_60s.json").write_text(json.dumps(words, indent=1))
    run(["python3", str(ROOT / "templates/captions/make_captions.py"), str(HERE / "words_60s.json"),
         str(HERE / "captions_60s.ass"), "--brand", "WILDFRAME", "--accent-split", "4"])
    tmp = Path(tempfile.mkdtemp())
    clips = []
    for r in rows:
        png = tmp / f"s{int(r['shot']):02d}.png"
        slate(r, png)
        dur = float(r["dur_s"])
        fr = max(1, round(dur * 30))
        push = "push" in r["motion"] or "drift" in r["motion"]
        zexpr = f"1+0.07*on/{fr}" if push else "1"
        out = tmp / f"c{int(r['shot']):02d}.mp4"
        vf = (f"scale=2160:3840,zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fr}:s={W}x{H}:fps=30,"
              "setsar=1,format=yuv420p")
        if "black" in r["motion"]:
            vf += ",fade=t=out:st=%.3f:d=0.01:color=black" % max(0, dur - 4 / 30)
        run(["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-frames:v", str(fr), "-vf", vf,
             "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", str(out)])
        clips.append(out)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(tmp / "video.mp4")])
    # guide audio: soft tick on every cut + low drone + riser on the "lid" sequence (numpy → WAV)
    import wave
    import numpy as np
    sr, total = 48000, float(rows[-1]["end_s"])
    t = np.arange(int(sr * total)) / sr
    y = 0.05 * np.sin(2 * np.pi * 55 * t) + 0.03 * np.sin(2 * np.pi * 82.5 * t)
    for c in [float(r["start_s"]) for r in rows][1:]:
        m = (t >= c) & (t < c + 0.08)
        y[m] += 0.35 * np.sin(2 * np.pi * 1800 * t[m]) * np.exp(-60 * (t[m] - c))
    rs = next(float(r["start_s"]) for r in rows if "riser starts" in r["sfx"])
    m = (t >= rs) & (t < rs + 2)
    y[m] += 0.10 * ((t[m] - rs) / 2) * np.sin(2 * np.pi * (200 + 150 * (t[m] - rs)) * (t[m] - rs))
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(str(tmp / "guide.wav"), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    run(["ffmpeg", "-y", "-i", str(tmp / "guide.wav"), "-af", "loudnorm=I=-14:TP=-1", "-ar", "48000",
         "-c:a", "aac", "-b:a", "192k", str(tmp / "guide.m4a")])
    run(["ffmpeg", "-y", "-i", str(tmp / "video.mp4"), "-i", str(tmp / "guide.m4a"),
         "-vf", f"ass={HERE / 'captions_60s.ass'}", "-c:v", "libx264", "-crf", "22", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(HERE / "animatic_60s.mp4")])
    shutil.rmtree(tmp)
    print("wrote", HERE / "animatic_60s.mp4")


if __name__ == "__main__":
    main()
