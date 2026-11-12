"""Procedural sound effects (no licensing issues): whoosh and low impact, plus WAV helpers."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 48000


def whoosh(length: float = 0.55, peak_at: float = 0.38, seed: int = 0) -> np.ndarray:
    """Filtered-noise whoosh whose energy peaks at `peak_at` seconds (place the peak on the cut)."""
    rng = np.random.default_rng(seed)
    n = int(SR * length)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    # cutoff sweeps up to the peak then down: 300 Hz → 5 kHz → 800 Hz
    sweep = np.where(t < peak_at, 300 + 4700 * (t / peak_at) ** 2, 5000 - 4200 * ((t - peak_at) / (length - peak_at)))
    alpha = 1 - np.exp(-2 * np.pi * sweep / SR)
    y = np.empty(n)
    acc = 0.0
    for i in range(n):              # one-pole low-pass with moving cutoff
        acc += alpha[i] * (noise[i] - acc)
        y[i] = acc
    env = np.where(t < peak_at, (t / peak_at) ** 2.2, np.exp(-(t - peak_at) / 0.07))
    y = y * env
    return (y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def impact(length: float = 0.6) -> np.ndarray:
    t = np.arange(int(SR * length)) / SR
    body = np.sin(2 * np.pi * (70 - 25 * t) * t) * np.exp(-t / 0.18)
    click = np.random.default_rng(1).standard_normal(len(t)) * np.exp(-t / 0.012) * 0.35
    y = body + click
    return (y / np.abs(y).max()).astype(np.float32)


def track(duration: float, events: list[tuple[float, str]], whoosh_db: float = -14.0, impact_db: float = -10.0) -> np.ndarray:
    """Build a mono SFX track. events: (time_of_cut, 'whoosh'|'impact')."""
    out = np.zeros(int(SR * (duration + 1.0)), dtype=np.float32)
    w = whoosh() * 10 ** (whoosh_db / 20)
    imp = impact() * 10 ** (impact_db / 20)
    for i, (t, kind) in enumerate(events):
        if kind == "whoosh":
            s = int((t - 0.38) * SR)
            snd = whoosh(seed=i) * 10 ** (whoosh_db / 20) if i % 3 else w
        else:
            s, snd = int(t * SR), imp
        s = max(0, s)
        e = min(len(out), s + len(snd))
        out[s:e] += snd[: e - s]
    return out[: int(SR * duration)]


def write_wav(path: Path, y: np.ndarray, sr: int = SR) -> Path:
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path
