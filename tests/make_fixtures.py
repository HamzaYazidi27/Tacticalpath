#!/usr/bin/env python3
"""Build a synthetic but realistic test set (no third-party footage):

  fixtures/raw_podcast.mp4   1920x1080, ~2.5 min "unedited podcast": a real public-domain face
                             (NASA portrait shipped with scikit-image), espeak-ng voice with ums,
                             long pauses and a weak intro before the good story, plus a 4 s cutaway.
  fixtures/broll/            small B-roll library named by subject (cat, rocket, coffee, moon, galaxy…)
  fixtures/raw_stock.mp4     speechless footage for montage mode
Requires: espeak-ng, ffmpeg, scikit-image, pillow, numpy.
"""
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from skimage import data

OUT = Path(__file__).resolve().parent / "fixtures"

SCRIPT = [
    ("Hey everyone, welcome back to the show.", 0.6),
    ("Um, so, today we have a lot to talk about.", 1.4),
    ("Before we start, thanks again for listening, it really means a lot.", 1.8),
    ("Okay. So.", 1.2),
    ("Did you know a cat once flew to space?", 0.5),
    ("In nineteen sixty three, France launched a rocket with a cat named Felicette on board.", 0.5),
    ("She was a stray cat, found on the streets of Paris.", 0.4),
    ("Scientists trained her in a lab, with loud noises and spinning machines.", 0.9),
    ("Um, then the rocket took off from the Sahara desert.", 0.4),
    ("It climbed one hundred and fifty kilometres, way above the clouds, almost to the edge of space.", 0.5),
    ("For five minutes she was weightless.", 0.5),
    ("Then a parachute opened and the capsule fell back to the ground.", 1.6),
    ("And here's the crazy part.", 0.4),
    ("She survived the whole flight.", 0.4),
    ("The first cat in space, and almost nobody remembers her name.", 0.4),
    ("Today there is a bronze statue of her, looking up at the stars.", 1.8),
    ("Anyway, uh, let's talk about something else.", 1.0),
    ("Astronauts on the space station drink coffee from special cups.", 0.5),
    ("The cup uses surface tension, so the coffee climbs the walls and reaches your mouth.", 0.6),
    ("Without it, the coffee would just float away as a ball of liquid.", 1.4),
    ("I tried to explain that to my horse once. He did not care.", 1.2),
    ("And the moon, um, the moon is slowly drifting away from the earth, about four centimetres every year.", 0.8),
    ("So, yeah. That's the show. See you next week.", 1.0),
]


def sh(*cmd):
    subprocess.run([str(c) for c in cmd], check=True, capture_output=True)


def speech(tmp: Path) -> Path:
    parts = []
    for i, (line, gap) in enumerate(SCRIPT):
        w = tmp / f"s{i}.wav"
        sh("espeak-ng", "-v", "en-us+m3", "-s", "158", "-p", "42", "-w", w, line)
        parts.append(w)
        g = tmp / f"g{i}.wav"
        sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono", "-t", f"{gap}", g)
        parts.append(g)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    out = tmp / "voice.wav"
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ar", "48000", "-af",
       "aecho=0.6:0.3:12:0.15,highpass=f=90,volume=1.4", out)
    return out


def studio_frame(face: Image.Image, t: float) -> Image.Image:
    W, H = 1920, 1080
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    r = (48 + 30 * (1 - y) + 10 * x).astype(np.uint8)
    g = (38 + 22 * (1 - y)).astype(np.uint8) * np.ones_like(x, dtype=np.uint8)
    b = (40 + 26 * x).astype(np.uint8) * np.ones_like(y, dtype=np.uint8)
    img = Image.fromarray(np.dstack([r * np.ones_like(x, dtype=np.uint8), g, b]).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 820, W, H], fill=(28, 24, 26))                        # desk
    for k in range(6):                                                     # shelf bokeh
        d.ellipse([90 + 260 * k, 120 + 40 * (k % 2), 150 + 260 * k, 180 + 40 * (k % 2)], fill=(90, 70, 50))
    img = img.filter(ImageFilter.GaussianBlur(6))
    dx = int(14 * np.sin(t * 0.7))
    dy = int(6 * np.sin(t * 1.3))
    img.paste(face, (1080 + dx, 220 + dy))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([980, 560, 1040, 900], radius=20, fill=(14, 14, 16))  # mic
    return img


def podcast(tmp: Path):
    voice = speech(tmp)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", voice],
                               capture_output=True, text=True).stdout)
    face = Image.fromarray(data.astronaut()).resize((560, 560))
    frames = tmp / "frames"
    frames.mkdir()
    fps = 10
    cut_a, cut_b = 92.0, 96.0                 # a 4 s cutaway (no face) inside the weak tail
    gal = Image.fromarray((np.dstack([data.hubble_deep_field()[..., c] for c in range(3)])).astype(np.uint8)).resize((1920, 1080))
    for i in range(int(dur * fps) + 1):
        t = i / fps
        if cut_a <= t < cut_b:
            k = (t - cut_a) / (cut_b - cut_a)
            fr = gal.crop((int(200 * k), 0, int(200 * k) + 1720, 968)).resize((1920, 1080))
        else:
            fr = studio_frame(face, t)
        fr.save(frames / f"{i:05d}.jpg", quality=90)
    OUT.mkdir(exist_ok=True)
    sh("ffmpeg", "-y", "-framerate", fps, "-i", frames / "%05d.jpg", "-i", voice, "-r", "30", "-c:v", "libx264",
       "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", OUT / "raw_podcast.mp4")


def broll():
    lib = OUT / "broll"
    lib.mkdir(parents=True, exist_ok=True)
    imgs = {
        "cat_stray_street.jpg": data.chelsea(),
        "coffee_cup.jpg": data.coffee(),
        "rocket_launch.jpg": data.rocket(),
        "galaxy_stars_space.jpg": data.hubble_deep_field(),
        "moon_surface.jpg": np.dstack([data.moon()] * 3),
        "astronaut_space_station.jpg": data.astronaut(),
        "coins_money.jpg": np.dstack([data.coins()] * 3),
        "horse.jpg": (np.dstack([data.horse()] * 3) * 255).astype(np.uint8),
    }
    for name, arr in imgs.items():
        Image.fromarray(arr.astype(np.uint8)).save(lib / name, quality=92)
    # two moving clips (pan over an image) to exercise the video path
    sh("ffmpeg", "-y", "-loop", "1", "-i", lib / "rocket_launch.jpg", "-t", "6", "-vf",
       "scale=1920:-2,crop=1280:720:'(iw-1280)*t/6':0,fps=30,format=yuv420p", lib / "rocket_takeoff_desert.mp4")
    sh("ffmpeg", "-y", "-loop", "1", "-i", lib / "cat_stray_street.jpg", "-t", "6", "-vf",
       "scale=1920:-2,crop=1280:720:'(iw-1280)*t/6':0,fps=30,format=yuv420p", lib / "cat_lab_scientists.mp4")


def stock():
    """Speechless 'raw stock' reel: several static/moving shots with ambient noise."""
    parts = []
    tmp = Path(tempfile.mkdtemp())
    srcs = [data.chelsea(), data.coffee(), data.rocket(), data.hubble_deep_field(), data.astronaut(), data.immunohistochemistry()]
    for i, arr in enumerate(srcs):
        p = tmp / f"img{i}.png"
        Image.fromarray(arr.astype(np.uint8)).save(p)
        v = tmp / f"v{i}.mp4"
        sh("ffmpeg", "-y", "-loop", "1", "-i", p, "-f", "lavfi", "-i", "anoisesrc=c=pink:a=0.02", "-t", "5", "-vf",
           f"scale=2400:-2,crop=1920:1080:'(iw-1920)*t/5':'(ih-1080)/2',fps=30,format=yuv420p", "-c:a", "aac",
           "-shortest", v)
        parts.append(v)
    lst = tmp / "l.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", OUT / "raw_stock.mp4")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as t:
        podcast(Path(t))
    broll()
    stock()
    print("fixtures written to", OUT)
