"""Render an EDL to a finished 1080×1920 Short."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import sfx
from .analyze import face_at, face_track
from .util import FPS, H, ROOT, W, ffmpeg, filter_file_args, frames, has_libass, log, probe, run

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus"}
LUT = ROOT / "templates" / "luts" / "crisp_pop_709.cube"
FONTS = ROOT / "fonts"


def fpath(p) -> str:
    """Path safe inside an FFmpeg filter argument (Windows drive colons, backslashes, quotes)."""
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def _captions_module():
    spec = importlib.util.spec_from_file_location("make_captions", ROOT / "templates" / "captions" / "make_captions.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ A-roll cut
def cut_aroll(src: Path, islands: list[dict], out: Path, info: dict) -> Path:
    """Concatenate the kept speech islands of the source (picture + sound) into one file."""
    if out.exists():
        return out
    w, h = info["width"], info["height"]
    scale = min(1.0, 3840 / max(w, h))
    sw, sh = int(w * scale) // 2 * 2, int(h * scale) // 2 * 2
    parts, labels = [], []
    for n, i in enumerate(islands):
        parts.append(f"[0:v]trim=start={i['src_start']}:end={i['src_end']},setpts=PTS-STARTPTS,"
                     f"scale={sw}:{sh},fps={FPS},setsar=1[v{n}];")
        parts.append(f"[0:a]atrim=start={i['src_start']}:end={i['src_end']},asetpts=PTS-STARTPTS,"
                     f"aresample=48000,afade=t=in:d=0.008,afade=t=out:st={max(0, i['src_end'] - i['src_start'] - 0.012):.3f}:d=0.012[a{n}];")
        labels.append(f"[v{n}][a{n}]")
    script = "".join(parts) + "".join(labels) + f"concat=n={len(islands)}:v=1:a=1[v][a]"
    fc = out.with_suffix(".filter.txt")
    fc.write_text(script)
    ffmpeg("-i", str(src), *filter_file_args(fc), "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "pcm_s16le", "-ar", "48000", str(out))
    return out


# ------------------------------------------------------------------ shot renders
ENC = ["-an", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS)]


def _crop_for(sw, sh, zoom, fx, fy, fw):
    """9:16 crop window on a sw×sh frame for a face at (fx, fy) — eyes on the upper third."""
    ch = sh / zoom
    cw = ch * 9 / 16
    if cw > sw:                      # source narrower than 9:16 (already vertical)
        cw = sw / zoom
        ch = cw * 16 / 9
    cx = fx * sw
    cy = fy * sh
    x = min(max(cx - cw / 2, 0), sw - cw)
    y = min(max(cy - ch * 0.36, 0), sh - ch)
    return int(cw) // 2 * 2, int(ch) // 2 * 2, int(x), int(y)


def render_a(aroll: Path, s: dict, out: Path, size, track):
    sw, sh = size
    fx, fy, fw = face_at(track, s["t0"], s["t1"])
    zoom = s.get("zoom", 1.0)
    if sh > sw:                      # source already vertical (already framed by its creator):
        zoom = 1 + (zoom - 1) * 0.6  # gentler punch-ins, and stay close to the original centre
        fx, fy = 0.5 + (fx - 0.5) * 0.3, 0.42 + (fy - 0.42) * 0.3
    cw, ch, x, y = _crop_for(sw, sh, zoom, fx, fy, fw)
    n = frames(s["t1"]) - frames(s["t0"])
    vf = f"crop={cw}:{ch}:{x}:{y},scale={W}:{H}:flags=lanczos"
    if s.get("intro"):               # frame 1: 12 % punch-out eased over 8 frames (supersampled = no jitter)
        vf = (f"crop={cw}:{ch}:{x}:{y},scale={2 * W}:{2 * H}:flags=lanczos,"
              f"zoompan=z='1+0.12*pow(max(0,1-on/8),2)':x='iw/2-(iw/zoom/2)':y='ih*0.4-(ih/zoom*0.4)'"
              f":d=1:s={W}x{H}:fps={FPS}")
    ffmpeg("-ss", f"{s['t0']:.4f}", "-i", str(aroll), "-frames:v", str(n),
           "-vf", f"{vf},setsar=1,format=yuv420p", *ENC, str(out))


def _smooth_push(n: int, amount: float, cx: float = 0.5) -> str:
    """Slow, jitter-free push-in: zoompan on a 2x supersampled frame (sub-pixel steps at output size)."""
    return (f"scale={2 * W}:{2 * H}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={2 * W}:{2 * H}:x='(iw-{2 * W})*{cx}':y='(ih-{2 * H})/2',"
            f"zoompan=z='1+{amount}*on/{max(n, 1)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")


def render_b(s: dict, out: Path):
    """B-roll shot: full-bleed 9:16 crop, native motion kept; static footage gets a slow smooth push-in."""
    a = s["asset"]
    n = frames(s["t1"]) - frames(s["t0"])
    if a["kind"] == "image":
        ffmpeg("-loop", "1", "-framerate", str(FPS), "-i", a["path"], "-frames:v", str(n), "-vf",
               f"{_smooth_push(n, 0.06)},setsar=1,format=yuv420p", *ENC, str(out))
        return
    static = a.get("motion") is not None and a["motion"] < 1.5
    cx = a.get("crop_x", 0.5)                            # subject-aware 9:16 window (CLIP)
    move = f"fps={FPS},{_smooth_push(n, 0.05, cx)}" if static else \
        f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}:x='(iw-{W})*{cx}':y='(ih-{H})/2'"
    loop = [] if a.get("max_len") else ["-stream_loop", "-1"]   # cued shots are long enough: never loop them
    ffmpeg(*loop, "-ss", f"{s.get('in', 0):.3f}", "-i", a["path"], "-frames:v", str(n), "-vf",
           f"{move},setsar=1,format=yuv420p", *ENC, str(out))
    if frames_of(out) < n:                               # source ended early: hold the last frame, never a gap
        tmp = out.with_suffix(".pad.mp4")
        ffmpeg("-i", str(out), "-vf", f"tpad=stop_mode=clone:stop={n},trim=end_frame={n}", *ENC, str(tmp))
        tmp.replace(out)


def frames_of(p: Path) -> int:
    r = run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
             "stream=nb_read_frames", "-of", "csv=p=0", str(p)])
    try:
        return int(r.stdout.strip())
    except ValueError:
        return 0


def render_video(plan: dict, aroll: Path, work: Path) -> Path:
    out = work / "video_track.mp4"
    info = probe(aroll)
    size = (info["width"], info["height"])
    track = face_track(aroll, work, name="faces_aroll") if any(s["kind"] == "A" for s in plan["shots"]) else []
    shots_dir = work / "shots"
    shots_dir.mkdir(exist_ok=True)
    jobs = []
    for i, s in enumerate(plan["shots"]):
        p = shots_dir / f"{i:03d}_{s['kind']}.mp4"
        jobs.append((s, p))

    def do(job):
        s, p = job
        if s["kind"] == "A":
            render_a(aroll, s, p, size, track)
        else:
            render_b(s, p)
        return p

    with ThreadPoolExecutor(max_workers=4) as ex:
        paths = list(ex.map(do, jobs))
    lst = work / "shots.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in paths))
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out))
    log(f"video track: {len(paths)} shots rendered")
    return out


# ------------------------------------------------------------------ audio
def _loudnorm_measure(path: Path, af_prefix: str = "") -> dict:
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
             (af_prefix + "," if af_prefix else "") + "loudnorm=I=-14:TP=-1:LRA=7:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr, re.S)
    return json.loads(m.group(0)) if m else {}


def normalize(mixed: Path, final: Path, cfg) -> Path:
    """Gain to the loudness target + peak limiter, measured and corrected once (deterministic, any material)."""
    m = _loudnorm_measure(mixed)
    if not m or m.get("input_i") in (None, "-inf"):
        ffmpeg("-i", str(mixed), "-ar", "48000", str(final))
        return final
    limit = 10 ** ((cfg.true_peak - 1.0) / 20)          # ceiling with margin for the AAC encode
    gain = cfg.loudness_lufs - float(m["input_i"])
    for _ in range(3):
        ffmpeg("-i", str(mixed), "-af", f"aresample=192000,volume={gain:.2f}dB,"     # 4x oversampling ≈ true-peak limiting
               f"alimiter=limit={limit:.4f}:attack=2:release=60:level=disabled,aresample=48000", "-ar", "48000", str(final))
        got = _loudnorm_measure(final)
        err = cfg.loudness_lufs - float(got["input_i"])
        if abs(err) <= 0.5:
            break
        gain += err
    return final


def pick_music(cfg, seed: str):
    files = []
    for d in cfg.music_dirs:
        root = Path(d).expanduser()
        if root.exists():
            files += [p for p in sorted(root.rglob("*")) if p.suffix.lower() in AUDIO_EXT]
    if not files:
        return None
    return files[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(files)]


def render_audio(plan: dict, aroll: Path, work: Path, cfg) -> Path:
    D = plan["duration"]
    dlg = work / "dialogue.wav"
    ffmpeg("-i", str(aroll), "-vn", "-af",
           "highpass=f=80,deesser=i=0.4,acompressor=threshold=-20dB:ratio=3:attack=10:release=100:makeup=2,"
           "equalizer=f=3500:t=q:w=1:g=2", "-ar", "48000", "-ac", "1", str(dlg))
    # SFX: whoosh on a share of B-roll entrances that follow the speaker, impact under the final line
    events, entrances = [], []
    shots = plan["shots"]
    for i in range(1, len(shots)):
        if shots[i]["kind"] == "B" and shots[i - 1]["kind"] == "A":
            entrances.append(shots[i]["t0"])
    k = max(1, round(len(entrances) / max(1, round(len(entrances) * cfg.whoosh_share * 2.5))))
    events += [(t, "whoosh") for t in entrances[::k]][: max(1, int(len(shots) * cfg.whoosh_share))]
    last_a = next((s for s in reversed(shots) if s["kind"] == "A"), None)
    if last_a:
        events.append((last_a["t0"], "impact"))
    events.append((0.0, "hit"))                                   # frame 1 grabs the ear too
    tD = plan.get("stats", {}).get("teaser") or 0
    if tD:
        events.append((tD, "whoosh"))                             # "rewind" into the story
    sfx_wav = sfx.write_wav(work / "sfx.wav", sfx.track(D, events))
    inputs = ["-i", str(dlg), "-i", str(sfx_wav)]
    music = pick_music(cfg, plan.get("title", "") + str(D))
    if music:
        dl = _loudnorm_measure(dlg).get("input_i", "-20")
        target = max(-40.0, float(dl) + cfg.music_db_under_voice)
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        fo = 0.04 if cfg.loop_ending else 0.25                   # loop: no "the end" fade, the video just restarts
        fc = (f"[2:a]atrim=0:{D:.3f},loudnorm=I={target:.1f}:TP=-6:LRA=11,aresample=48000,"
              f"afade=t=out:st={max(0, D - fo):.3f}:d={fo}[m0];"
              f"[0:a]asplit=2[d][key];[m0][key]sidechaincompress=threshold=0.04:ratio=6:attack=40:release=250[m];"
              f"[d][1:a][m]amix=inputs=3:normalize=0:duration=first[mix]")
        log(f"music: {music.name} (bed at {target:.1f} LUFS, ducked under the voice)")
    else:
        fc = "[0:a][1:a]amix=inputs=2:normalize=0:duration=first[mix]"
    mixed = work / "mix_raw.wav"
    ffmpeg(*inputs, "-filter_complex", fc, "-map", "[mix]", "-ar", "48000", "-ac", "2", "-t", f"{D:.3f}", str(mixed))
    return normalize(mixed, work / "mix_final.wav", cfg)


def render_audio_montage(plan: dict, src: Path, work: Path, cfg) -> Path:
    """Music bed if available, else the footage's own sound per shot; whooshes on a share of cuts."""
    D = plan["duration"]
    shots = plan["shots"]
    events = [(s["t0"], "whoosh") for s in shots[1::max(1, round(1 / max(cfg.whoosh_share, 0.05)))]]
    sfx_wav = sfx.write_wav(work / "sfx.wav", sfx.track(D, events))
    music = pick_music(cfg, str(src) + str(D))
    if music:
        bed = work / "bed.wav"
        ffmpeg("-stream_loop", "-1", "-i", str(music), "-t", f"{D:.3f}", "-af",
               f"afade=t=out:st={max(0, D - 0.4):.3f}:d=0.4", "-ar", "48000", "-ac", "2", str(bed))
        log(f"music: {music.name}")
    else:
        parts, labels = [], []
        for n, s in enumerate(shots):
            d = s["t1"] - s["t0"]
            parts.append(f"[0:a]atrim=start={s['in']}:duration={d:.4f},asetpts=PTS-STARTPTS,aresample=48000,"
                         f"afade=t=in:d=0.01,afade=t=out:st={max(0, d - 0.02):.4f}:d=0.02[a{n}];")
            labels.append(f"[a{n}]")
        fc = work / "nat.filter.txt"
        fc.write_text("".join(parts) + "".join(labels) + f"concat=n={len(shots)}:v=0:a=1[a]")
        bed = work / "bed.wav"
        if probe(src)["has_audio"]:
            ffmpeg("-i", str(src), *filter_file_args(fc), "-map", "[a]", "-ar", "48000", "-ac", "2", str(bed))
        else:
            ffmpeg("-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo", "-t", f"{D:.3f}", str(bed))
    bed_n = work / "bed_norm.wav"                                  # bring the bed up first, then add the SFX on top
    normalize(bed, bed_n, cfg.__class__(**{**cfg.__dict__, "loudness_lufs": cfg.loudness_lufs - 1.5}))
    bed = bed_n
    mixed = work / "mix_raw.wav"
    ffmpeg("-i", str(bed), "-i", str(sfx_wav), "-filter_complex", "[0:a][1:a]amix=inputs=2:normalize=0:duration=first[m]",
           "-map", "[m]", "-t", f"{D:.3f}", "-ar", "48000", str(mixed))
    return normalize(mixed, work / "mix_final.wav", cfg)


# ------------------------------------------------------------------ captions + finish
def brand_split(brand: str, explicit=None) -> tuple[str, int]:
    """'WILD|FRAME' or 'WildFrame' or 'Wild Frame' → ('WILDFRAME', 4). Plain names split in the middle."""
    if explicit is not None:
        return brand.replace("|", ""), explicit
    if "|" in brand:
        return brand.replace("|", ""), brand.index("|")
    if " " in brand.strip():
        b = brand.strip()
        return b.replace(" ", ""), b.rindex(" ")
    caps = [i for i, c in enumerate(brand) if c.isupper() and i > 0]
    if caps and not brand.isupper():
        return brand, caps[-1]
    return brand, len(brand) // 2


# caption fonts per script: (ASS family, ASS size, Pillow file, Pillow size, watermark file)
FONTSET = {"latin": ("Montserrat Black", 82, "Montserrat-Black.otf", 59, "Montserrat-ExtraBold.otf"),
           "arabic": ("Tajawal Black", 100, "Tajawal-Black.ttf", 72, "Tajawal-ExtraBold.ttf")}


def fontset(words) -> tuple:
    from .language import script
    return FONTSET[script(words)]


def write_captions(plan: dict, work: Path, cfg):
    mc = _captions_module()
    brand, split = brand_split(cfg.brand, cfg.brand_accent_split)
    family, size = fontset(plan["words"])[:2]
    ass = mc.build(plan["words"], brand, split, "pop", True, family, size, 0.50, 6, 1.5, True,
                   bool(cfg.brand), 3, duration=plan["duration"])
    p = work / "captions.ass"
    p.write_text(ass, encoding="utf-8")
    srt, chunks = [], mc.chunk_words(plan["words"])

    def st(t):
        h, m = int(t // 3600), int(t % 3600 // 60)
        return f"{h:02d}:{m:02d}:{t % 60:06.3f}".replace(".", ",")
    for n, (s, e, c) in enumerate(chunks, 1):
        srt.append(f"{n}\n{st(s)} --> {st(e)}\n{' '.join(mc.clean(w['word'], True) for w in c)}\n")
    (work / "captions.srt").write_text("\n".join(srt), encoding="utf-8")
    return p


def mixed_lut(mix: float, work: Path) -> Path:
    """Bake the LUT strength into a new .cube (identity·(1-mix) + LUT·mix) — much faster than a blend filter."""
    out = work / f"lut_mix{int(mix * 100)}.cube"
    if out.exists():
        return out
    lines = LUT.read_text().splitlines()
    size = int(next(l for l in lines if l.startswith("LUT_3D_SIZE")).split()[1])
    data = [l for l in lines if l and (l[0].isdigit() or l[0] == "-")]
    res = [l for l in lines if not (l and (l[0].isdigit() or l[0] == "-"))]
    n = 0
    for b in range(size):
        for g in range(size):
            for r in range(size):
                v = [float(x) for x in data[n].split()]
                ident = (r / (size - 1), g / (size - 1), b / (size - 1))
                res.append("%.6f %.6f %.6f" % tuple(i * (1 - mix) + x * mix for i, x in zip(ident, v)))
                n += 1
    out.write_text("\n".join(res) + "\n")
    return out


def caption_overlay(plan: dict, work: Path, cfg) -> Path:
    """Captions + watermark drawn with Pillow (for ffmpeg builds without libass), as a concat list of
    transparent PNG bands. Same measured style: Montserrat Black 82 px, #19F464, 2 px rim, hard shadow
    (+1.5, +6), soft glow, centre at 50 %; watermark 56 px lower."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    mc = _captions_module()
    brand, split = brand_split(cfg.brand, cfg.brand_accent_split)
    band_h, cy = 300, 150                      # band is placed with its centre on the frame centre
    # Pillow sizes are em sizes (cap height = 0.70 em): 59 → 41 px caps, 24 → 17 px caps (= measured reference)
    _, _, ffile, fsize, _ = fontset(plan["words"])
    font = ImageFont.truetype(str(FONTS / ffile), fsize)
    wfont = ImageFont.truetype(str(FONTS / "Montserrat-ExtraBold.otf"), 24)
    base, wbase = cy + 20.5, cy + 56 + 8.5     # baselines: caption caps centred on cy, watermark 56 px lower
    d = work / "caption_png"
    d.mkdir(exist_ok=True)

    def draw_brand(img):
        if not brand:
            return
        dr = ImageDraw.Draw(img)
        parts = [(brand[:split].upper(), (230, 226, 222, 204)), (brand[split:].upper(), (84, 187, 111, 191))]
        widths = [sum(dr.textlength(ch, font=wfont) + 11 for ch in t) for t, _ in parts]
        x = (W - sum(widths) + 11) / 2
        for (t, col), _ in zip(parts, widths):
            for ch in t:
                dr.text((x, wbase), ch, font=wfont, fill=col, anchor="ls")
                x += dr.textlength(ch, font=wfont) + 11

    def band(text):
        img = Image.new("RGBA", (W, band_h), (0, 0, 0, 0))
        if text:
            glow = Image.new("RGBA", (W, band_h), (0, 0, 0, 0))
            ImageDraw.Draw(glow).text((W / 2, base), text, font=font, fill=(25, 244, 100, 110), anchor="ms",
                                      stroke_width=7, stroke_fill=(25, 244, 100, 110))
            img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(12)))
            dr = ImageDraw.Draw(img)
            dr.text((W / 2 + 1.5, base + 6), text, font=font, fill=(10, 61, 22, 255), anchor="ms",
                    stroke_width=2, stroke_fill=(10, 61, 22, 255))
            dr.text((W / 2, base), text, font=font, fill=(25, 244, 100, 255), anchor="ms",
                    stroke_width=2, stroke_fill=(6, 38, 13, 255))
        draw_brand(img)
        return img

    entries, t = [], 0.0
    blank = d / "blank.png"
    band("").save(blank)
    for k, (st, en, c) in enumerate(mc.chunk_words(plan["words"])):
        if st > t + 0.01:
            entries.append((blank, st - t))
        f = d / f"c{k:04d}.png"
        band(" ".join(mc.clean(w["word"], True) for w in c)).save(f)
        entries.append((f, max(en - st, 0.04)))
        t = en
    if plan["duration"] > t:
        entries.append((blank, plan["duration"] - t))
    lst = work / "captions_png.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\nduration {dur:.4f}\n" for p, dur in entries)
                   + f"file '{entries[-1][0].resolve()}'\n", encoding="utf-8")
    return lst


HOOK_Y = 290                                  # top of the hook card: below the platform's top bar, above the captions


def hook_card(text: str, out: Path) -> Path | None:
    """On-screen hook title for the first seconds: white rounded line boxes, black Montserrat Black,
    one key word on a brand-green chip, soft drop shadow. Transparent PNG, full frame width."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    from . import viral
    from .language import is_arabic
    rtl = is_arabic(text)
    text = " ".join(text.split()) if rtl else " ".join(text.split()).upper()
    if not text:
        return None
    hi = viral.highlight_word(text)
    toks = text.split()
    for size in ((80, 72, 64, 56) if rtl else (68, 60, 52, 46)):
        font = ImageFont.truetype(str(FONTS / ("Tajawal-Black.ttf" if rtl else "Montserrat-Black.otf")), size)
        meas = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
        sp = meas.textlength(" ", font=font)
        lines, cur, wsum = [], [], 0.0
        for i, t in enumerate(toks):
            tw = meas.textlength(t, font=font)
            if cur and wsum + sp + tw > 880:
                lines.append(cur)
                cur, wsum = [], 0.0
            wsum += (sp if cur else 0) + tw
            cur.append((i, t, tw))
        lines.append(cur)
        if len(lines) <= 3:
            break
    pad_x, pad_y, lh = 30, 16, int(size * 1.22)
    hgt = len(lines) * lh + 2 * pad_y + 40
    img = Image.new("RGBA", (W, hgt), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, hgt), (0, 0, 0, 0))
    sd, boxes = ImageDraw.Draw(shadow), []
    for li, ln in enumerate(lines):
        lw = sum(tw for _, _, tw in ln) + sp * (len(ln) - 1)
        x0, y0 = (W - lw) / 2 - pad_x, 10 + li * lh
        box = (x0, y0, x0 + lw + 2 * pad_x, y0 + lh + 2 * pad_y - 6)
        boxes.append((box, ln, (W - lw) / 2))
        sd.rounded_rectangle((box[0], box[1] + 8, box[2], box[3] + 8), radius=20, fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(10)))
    dr = ImageDraw.Draw(img)
    for box, _, _ in boxes:
        dr.rounded_rectangle(box, radius=20, fill=(255, 255, 255, 255))
    for box, ln, x in boxes:
        base = box[1] + pad_y + size * (0.80 if rtl else 0.86)
        for i, t, tw in (reversed(ln) if rtl else ln):         # right-to-left scripts: first word on the right
            if i == hi:
                dr.rounded_rectangle((x - 10, box[1] + 9, x + tw + 10, box[3] - 9), radius=14, fill=(25, 244, 100, 255))
                dr.text((x, base), t, font=font, fill=(6, 38, 13, 255), anchor="ls")
            else:
                dr.text((x, base), t, font=font, fill=(12, 12, 12, 255), anchor="ls")
            x += tw + sp
    img.save(out)
    return out


def finish(video: Path, audio: Path, ass: Path, out: Path, cfg, plan: dict | None = None) -> Path:
    lut = mixed_lut(cfg.lut_mix, ass.parent)
    grade = f"lut3d=file='{fpath(lut)}',unsharp=5:5:{cfg.sharpen}:5:5:0"
    if has_libass() or plan is None:
        inputs = ["-i", str(video), "-i", str(audio)]
        vf = f"[0:v]{grade},ass='{fpath(ass)}':fontsdir='{fpath(FONTS)}'[base]"
    else:                                     # no libass in this ffmpeg: overlay Python-drawn caption bands
        lst = caption_overlay(plan, ass.parent, cfg)
        inputs = ["-i", str(video), "-i", str(audio), "-f", "concat", "-safe", "0", "-i", str(lst)]
        vf = (f"[0:v]{grade}[g];[2:v]fps={FPS},format=rgba[c];"
              f"[g][c]overlay=x=0:y=(main_h-overlay_h)/2:format=auto[base]")
    card = hook_card(plan.get("hook", ""), ass.parent / "hook.png") if plan else None
    if card:                                  # hook title: slides in on frame 1, fades out after hook_secs
        hs = float(plan.get("hook_secs") or cfg.hook_secs)
        k = len(inputs) // 2 if "-f" not in inputs else 3
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{hs:.2f}", "-i", str(card)]
        vf += (f";[{k}:v]format=rgba,fade=t=out:st={hs - 0.18:.2f}:d=0.18:alpha=1[hk];"
               f"[base][hk]overlay=x=0:y='{HOOK_Y}-36*pow(max(0,1-t/0.16),2)':eof_action=pass:format=auto,format=yuv420p[v]")
    else:
        vf += ";[base]format=yuv420p[v]"
    ffmpeg(*inputs, "-filter_complex", vf, "-map", "[v]", "-map", "1:a",
           "-r", str(FPS), "-c:v", "libx264", "-profile:v", "high", "-level", "4.2", "-preset", "medium", "-crf", "17",
           "-maxrate", "20M", "-bufsize", "40M", "-g", "15", "-bf", "2", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-shortest", str(out))
    return out


def cover(final: Path, t: float, out: Path, card: Path | None = None) -> Path:
    """Thumbnail: a strong frame, with the hook title on it when there is one."""
    if card and card.exists():
        ffmpeg("-ss", f"{t:.2f}", "-i", str(final), "-i", str(card), "-filter_complex",
               f"[0:v][1:v]overlay=x=0:y={HOOK_Y}", "-frames:v", "1", "-q:v", "2", str(out))
    else:
        ffmpeg("-ss", f"{t:.2f}", "-i", str(final), "-frames:v", "1", "-q:v", "2", str(out))
    return out
