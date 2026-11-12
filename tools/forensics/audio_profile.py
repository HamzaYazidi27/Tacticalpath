#!/usr/bin/env python3
"""
audio_profile.py — measure the audio mix of a finished Short.

Reports
  * Integrated loudness (LUFS), loudness range (LU), true peak (dBTP)   — ffmpeg ebur128
  * Short-term loudness curve (3 s windows) → intensity progression, first/last-second fades
  * Silence map (gaps > 250 ms at -45 dB)                                — ffmpeg silencedetect
  * Optional: tempo / beat grid (librosa, if installed)
  * Optional: voice-vs-music balance (if you pass stems separated with Demucs:
      demucs --two-stems=vocals short.mp4  →  --vocals path --music path)

Requires: ffmpeg in PATH. Optional: librosa, numpy.
Usage   : python3 audio_profile.py short.mp4 --out reports/short
          python3 audio_profile.py short.mp4 --out reports/short --vocals vocals.wav --music no_vocals.wav
"""
import argparse
import json
import re
import subprocess
from pathlib import Path


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stderr


def ebur128(path):
    log = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-filter_complex",
               "ebur128=peak=true:framelog=verbose", "-f", "null", "-"])
    st_curve = [(float(m.group(1)), float(m.group(2)))
                for m in re.finditer(r"t:\s*([\d.]+)\s+TARGET.*?S:\s*(-?[\d.]+|-inf)", log) if m.group(2) != "-inf"]
    summ = log[log.rfind("Summary:"):]
    g = lambda k: float(re.search(k + r":\s*(-?[\d.]+)", summ).group(1)) if re.search(k + r":\s*(-?[\d.]+)", summ) else None
    return {"integrated_lufs": g("I"), "lra_lu": g("LRA"), "true_peak_dbtp": g("Peak")}, st_curve


def silences(path):
    log = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
               "silencedetect=noise=-45dB:d=0.25", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return [{"start": s, "end": e} for s, e in zip(starts, ends)]


def loudness(path):
    stats, _ = ebur128(path)
    return stats["integrated_lufs"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--vocals", type=Path)
    ap.add_argument("--music", type=Path)
    a = ap.parse_args()
    stats, curve = ebur128(a.media)
    sampled = [(round(t, 1), s) for t, s in curve[::10]]  # ~1 value per second
    rep = {"file": a.media.name, **stats,
           "short_term_lufs_per_second": sampled,
           "silences": silences(a.media)}
    if curve:
        n = len(curve)
        thirds = [curve[k * n // 3:(k + 1) * n // 3] for k in range(3)]
        rep["mean_short_term_lufs_per_third"] = [round(sum(s for _, s in t) / len(t), 1) if t else None for t in thirds]
    try:
        import librosa  # optional
        y, sr = librosa.load(str(a.media), sr=22050, mono=True)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        rep["tempo_bpm_estimate"] = round(float(tempo if not hasattr(tempo, "__len__") else tempo[0]), 1)
        rep["beat_times_s"] = [round(float(b), 2) for b in librosa.frames_to_time(beats, sr=sr)][:200]
        rep["tempo_note"] = "librosa estimate on the full mix — speech-heavy mixes can mislead; verify on the music stem"
    except Exception as e:  # noqa
        rep["tempo_bpm_estimate"] = None
        rep["tempo_note"] = f"librosa not available or failed ({type(e).__name__})"
    if a.vocals and a.music:
        v, m = loudness(a.vocals), loudness(a.music)
        rep["stems"] = {"vocals_lufs": v, "music_lufs": m,
                        "voice_minus_music_lu": round(v - m, 1) if v is not None and m is not None else None}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{a.out}_audio.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps({k: v for k, v in rep.items() if k not in ("short_term_lufs_per_second", "beat_times_s")}, indent=2))


if __name__ == "__main__":
    main()
