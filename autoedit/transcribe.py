"""Speech-to-text with word timestamps (faster-whisper). Cached per input."""
from __future__ import annotations

from pathlib import Path

from .util import ffmpeg, load_json, log, save_json


def extract_wav(src: Path, wav: Path) -> Path:
    if not wav.exists():
        ffmpeg("-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav))
    return wav


def transcribe(src: Path, work: Path, model_size: str = "small", language: str | None = None) -> dict:
    """Return {"language": str, "words": [{"word","start","end","prob"}]}."""
    cache = work / "transcript.json"
    if cache.exists():
        return load_json(cache)
    wav = extract_wav(src, work / "audio16k.wav")
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:  # pragma: no cover
        raise SystemExit("faster-whisper is not installed: pip install faster-whisper") from e
    log(f"transcribing with faster-whisper '{model_size}' (first run downloads the model)…")
    model = WhisperModel(model_size, device="auto", compute_type="auto")
    import wave

    import numpy as np
    with wave.open(str(wav)) as wf:      # decode ourselves: avoids PyAV version issues
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    segments, info = model.transcribe(
        audio, language=language, word_timestamps=True, vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300}, beam_size=5,
    )
    words = []
    for seg in segments:
        for w in seg.words or []:
            t = w.word.strip()
            if t:
                words.append({"word": t, "start": round(w.start, 3), "end": round(w.end, 3),
                              "prob": round(float(w.probability), 3)})
    out = {"language": info.language, "duration": info.duration, "words": words}
    save_json(cache, out)
    log(f"transcript: {len(words)} words, language={info.language}")
    return out
