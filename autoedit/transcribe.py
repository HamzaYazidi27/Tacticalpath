"""Speech-to-text with word timestamps (faster-whisper). Cached per input."""
from __future__ import annotations

from pathlib import Path

from .util import ffmpeg, load_json, log, save_json


def extract_wav(src: Path, wav: Path) -> Path:
    if not wav.exists():
        ffmpeg("-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav))
    return wav


_MODELS = {}


def _model(size: str):
    from faster_whisper import WhisperModel
    if size not in _MODELS:
        _MODELS[size] = WhisperModel(size, device="auto", compute_type="auto")
    return _MODELS[size]


def transcribe(src: Path, work: Path, model_size: str = "small", language: str | None = None,
               task: str = "transcribe", upgrade: dict | None = None) -> dict:
    """Return {"language": str, "words": [{"word","start","end","prob"}]}.
    task="translate": English words timed on the same audio (used to search English stock footage
    for a talk in Arabic, French, Darija…)."""
    cache = work / ("transcript.json" if task == "transcribe" else "translation_en.json")
    if cache.exists():
        c = load_json(cache)
        if c.get("model") in (None, model_size) or c.get("model") == (upgrade or {}).get(c.get("language")):
            return c
    wav = extract_wav(src, work / "audio16k.wav")
    try:
        import faster_whisper  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise SystemExit("faster-whisper is not installed: pip install faster-whisper") from e
    import wave

    import numpy as np
    with wave.open(str(wav)) as wf:      # decode ourselves: avoids PyAV version issues
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if upgrade and language is None:     # some languages need a bigger model (e.g. Arabic dialects)
        _, probe_info = _model(model_size).transcribe(audio[: 16000 * 30], task="transcribe")   # detection only
        language = probe_info.language
        if upgrade.get(language) and upgrade[language] != model_size:
            log(f"language '{language}' detected → using the more accurate '{upgrade[language]}' model")
            model_size = upgrade[language]
    log(f"{'transcribing' if task == 'transcribe' else 'translating to English (for B-roll searches)'} "
        f"with faster-whisper '{model_size}' (first run downloads the model)…")
    model = _model(model_size)
    segments, info = model.transcribe(
        audio, language=language, task=task, word_timestamps=True, vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300}, beam_size=5,
    )
    words = []
    for seg in segments:
        for w in seg.words or []:
            t = w.word.strip()
            if t:
                words.append({"word": t, "start": round(w.start, 3), "end": round(w.end, 3),
                              "prob": round(float(w.probability), 3)})
    out = {"language": info.language, "duration": info.duration, "words": words, "model": model_size}
    save_json(cache, out)
    log(f"transcript: {len(words)} words, language={info.language}")
    return out
