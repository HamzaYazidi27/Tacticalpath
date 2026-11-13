"""Retention layer: virality score, cold-open teaser, on-screen hook title, loop-friendly endings.

Everything here is explainable heuristics (no ML), so a score can be shown to the user part by part.
The signals are the ones short-form retention depends on: a strong first line, a payoff, a clip that
stands on its own, pace, things to show, vocal energy, and an ending that flows back into the start.
"""
from __future__ import annotations

import re

import numpy as np

from . import language as L

# weights (sum = 100) — shown in the Studio as the score breakdown
PARTS = {"hook": 25, "payoff": 15, "standalone": 15, "visual": 15, "pace": 10, "energy": 10, "loop": 10}
LABELS = {"hook": "Accroche", "payoff": "Chute", "standalone": "Compréhensible seul", "visual": "Visuel",
          "pace": "Rythme", "energy": "Énergie", "loop": "Boucle"}

DANGLING = {"and", "but", "so", "then", "because", "or", "also", "et", "mais", "donc", "puis", "parce", "aussi"}
PRONOUN_START = {"he", "she", "they", "it", "this", "that", "these", "those", "him", "her", "them",
                 "il", "elle", "ils", "elles", "ça", "cela", "ce"}
CLOSERS = ("that's it", "that's all", "anyway", "so yeah", "voilà", "bref", "c'est tout")


def _clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def _first_tok(text: str) -> str:
    t = text.split()
    return L.bare(t[0]) if t else ""


def score(words, sents, a: int, b: int, dur: float, cfg, env_db=None, hop: float = 0.1) -> dict:
    """0–100 virality estimate of sentences a..b, with a 0–1 value per part."""
    body = sents[a:b + 1]
    first, last = body[0]["text"], body[-1]["text"]
    i0, i1 = body[0]["i0"], body[-1]["i1"]
    p = {}
    p["hook"] = _clip01((L.hook_score(first) + 1.0) / 6.0)
    pay = max(L.hook_score(x["text"]) for x in body[-2:])
    p["payoff"] = _clip01((pay + 1.0) / 5.0 + (0.25 if last.strip()[-1:] in ".!?" else 0.0)
                          - (0.4 if any(c in last.lower() for c in CLOSERS) else 0.0))
    st = 1.0
    st -= 0.35 if _first_tok(first) in DANGLING else 0.0
    st -= 0.25 if _first_tok(first) in PRONOUN_START else 0.0
    st -= 0.3 * sum(1 for x in body if L.is_meta(x["text"]))
    nxt = sents[b + 1]["text"] if b + 1 < len(sents) else ""
    st -= 0.3 if nxt and _first_tok(nxt) in DANGLING else 0.0
    p["standalone"] = _clip01(st)
    kws = L.keywords(words, i0, i1)
    visual = sum(1 for k in kws if k["score"] >= 3)
    p["visual"] = _clip01(visual / max(dur / 10.0, 1.0) / 2.5)
    wps = (i1 - i0 + 1) / max(dur, 1e-6)
    p["pace"] = _clip01(1.0 - max(0.0, 2.4 - wps, wps - 3.8) / 1.2)
    p["energy"] = 0.5
    if env_db is not None and len(env_db):
        seg = env_db[int(body[0]["start"] / hop): int(body[-1]["end"] / hop) + 1]
        if len(seg) > 5:
            lift = float(np.median(seg)) - float(np.median(env_db))         # louder than the rest of the talk
            spread = float(np.percentile(seg, 90) - np.percentile(seg, 30))  # dynamic, not monotone
            p["energy"] = _clip01(0.5 + lift / 8.0 + (spread - 12.0) / 30.0)
    loop = 0.0
    loop += 0.5 if ("?" in first or _first_tok(first) in {"why", "how", "what", "pourquoi", "comment"}) else 0.0
    loop += 0.3 if len(last.split()) <= 12 else 0.0
    loop += 0.2 if not any(c in last.lower() for c in CLOSERS) else 0.0
    p["loop"] = _clip01(loop)
    total = sum(PARTS[k] * p[k] for k in PARTS)
    total -= min(15.0, abs(dur - cfg.target_dur) / max(cfg.target_dur, 1) * 20)   # far from the ideal length
    return {"total": int(round(max(0.0, min(100.0, total)))), "parts": {k: round(v, 2) for k, v in p.items()}}


def auto_count(speech_s: float, cfg) -> int:
    """How many Shorts to aim for when count = 0 (auto): about one per 75 s of talk, 1–8."""
    return int(min(8, max(1, round(speech_s / 75.0))))


def teaser(words, sents, a: int, b: int, dur: float, cfg, est) -> list[int] | None:
    """Cold open: a punchy line from later in the clip, played first ("flash-forward"), then the story.
    Only when it is clearly stronger than the opening line and short enough not to bloat the clip."""
    if not cfg.cold_open or b - a < 3:
        return None
    base = L.hook_score(sents[a]["text"])
    best = None
    for si in range(a + 2, b):                                  # never the payoff line, never the opening
        s = sents[si]
        k0 = s["i0"] + (1 if _first_tok(s["text"]) in DANGLING else 0)     # "Then the biggest…" → "The biggest…"
        n = s["i1"] - k0 + 1
        text = " ".join(words[k]["word"] for k in range(k0, s["i1"] + 1))
        if not 3 <= n <= 14 or L.is_meta(text) or _first_tok(text) in DANGLING | PRONOUN_START:
            continue
        d = est(words, k0, s["i1"], cfg.gap_trim)
        if not 1.0 <= d <= 3.6 or dur + d > cfg.max_dur + 1:
            continue
        hs = L.hook_score(text)
        if hs >= max(2.5, base + 1.5) and (best is None or hs > best[0]):
            best = (hs, [k0, s["i1"]])
    return best[1] if best else None


def hook_text(sents, a: int, b: int, teaser_range=None, max_words: int = 12) -> str:
    """Short on-screen title for the first seconds (Claude writes a better one when available)."""
    def clean(t):
        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r"^(so|and|but|well|okay|ok|yeah|um|uh|donc|et|mais|bon|euh)[, ]+", "", t, flags=re.I)
        return t.strip(" ,;:-")
    pool = []
    for si in range(a, min(b + 1, a + 4)):                      # questions near the top make the best hooks
        if "?" in sents[si]["text"]:
            pool.append(sents[si]["text"])
    pool.append(sents[a]["text"])
    if teaser_range:
        pool += [s["text"] for s in sents[a:b + 1] if s["i0"] == teaser_range[0]]
    for t in pool:
        t = clean(t)
        if 3 <= len(t.split()) <= max_words:
            return t
        for clause in re.split(r"(?<=[,;:])\s+", t):            # a short clause of a long line
            c = clean(clause)
            if 4 <= len(c.split()) <= max_words and not L.is_meta(c):
                return c
    return ""


def highlight_word(text: str) -> int | None:
    """Index of the word to colour in the hook title (number, superlative, showable noun)."""
    best, bi = 0.0, None
    for i, w in enumerate(text.split()):
        b = L.bare(w)
        s = (3 if re.search(r"\d", b) else 0) + (2 if b in L.HOOK_WORDS else 0) + (1.5 if b in L.VISUAL else 0)
        s += 0.5 if len(b) >= 6 and b not in L.STOP else 0
        if s > best:
            best, bi = s, i
    return bi
