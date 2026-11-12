"""Pick the best 30–60 s story(ies) in a long recording. Heuristic scoring, optionally re-ranked by Claude."""
from __future__ import annotations

import json
import os

import numpy as np

from . import language as L
from .util import log


def est_out(words, i0, i1, gap_trim):
    """Duration after pauses are trimmed (what the viewer will actually see)."""
    d = sum(words[k]["end"] - words[k]["start"] for k in range(i0, i1 + 1) if L.bare(words[k]["word"]) not in L.FILLERS)
    d += sum(min(max(words[k + 1]["start"] - words[k]["end"], 0), gap_trim) for k in range(i0, i1))
    return d


def candidates(words, sents, cfg, env_db=None, hop=0.1):
    """Score every sentence-aligned window whose *edited* duration fits [min_dur, max_dur]."""
    out = []
    for a in range(len(sents)):
        for b in range(a, len(sents)):
            d = est_out(words, sents[a]["i0"], sents[b]["i1"], cfg.gap_trim)
            if d < cfg.min_dur:
                continue
            if d > cfg.max_dur:
                break
            out.append((a, b, d))
    if not out and sents:  # recording too short: keep the longest window that fits
        best = None
        for a in range(len(sents)):
            for b in range(a, len(sents)):
                d = est_out(words, sents[a]["i0"], sents[b]["i1"], cfg.gap_trim)
                if d <= cfg.max_dur and (best is None or d > best[2]):
                    best = (a, b, d)
        out = [best] if best else []
    scored = []
    for a, b, d in out:
        i0, i1 = sents[a]["i0"], sents[b]["i1"]
        ws = words[i0:i1 + 1]
        fillers = sum(1 for w in ws if L.bare(w["word"]) in L.FILLERS)
        kws = L.keywords(words, i0, i1)
        visual = sum(1 for k in kws if k["score"] >= 3)
        wps = len(ws) / max(d, 1e-6)
        body = sents[a:b + 1]
        s = 2.0 * L.hook_score(sents[a]["text"])                              # opening line
        s += 1.0 * max(L.hook_score(x["text"]) for x in body[-3:])            # payoff near the end
        s -= 3.0 * sum(1 for x in body if L.is_meta(x["text"]))               # greetings / topic switches inside
        nxt = sents[b + 1]["text"].lower() if b + 1 < len(sents) else ""
        if not nxt or L.is_meta(nxt):
            s += 2.0                                                          # ends where the story ends
        elif nxt.split()[0].strip(",") in {"and", "but", "so", "then", "because", "et", "mais"}:
            s -= 1.5                                                          # cuts a continuing story short
        s += 1.0 * min(visual / max(d / 10, 1), 3)
        s += 0.8 if 2.2 <= wps <= 3.8 else -0.8
        s -= 0.4 * fillers
        s += 0.5 if sents[b]["text"].strip()[-1:] in ".!?" else 0.0
        s -= abs(d - cfg.target_dur) / 12.0
        if env_db is not None and len(env_db):
            seg = env_db[int(sents[a]["start"] / hop): int(sents[b]["end"] / hop) + 1]
            if len(seg):
                s += 0.05 * (float(np.median(seg)) - float(np.median(env_db)))
        scored.append({"s0": a, "s1": b, "start": sents[a]["start"], "end": sents[b]["end"], "dur": round(d, 2),
                       "score": round(s, 3), "title": "", "queries": {}})
    scored.sort(key=lambda c: -c["score"])
    return scored


def non_overlapping(cands, n):
    chosen = []
    for c in cands:
        if all(c["end"] <= x["start"] or c["start"] >= x["end"] for x in chosen):
            chosen.append(c)
        if len(chosen) >= n:
            break
    return chosen


SCHEMA = {
    "type": "object",
    "properties": {
        "clips": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_sentence": {"type": "integer"},
                    "end_sentence": {"type": "integer"},
                    "title": {"type": "string"},
                    "why": {"type": "string"},
                    "broll": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sentence": {"type": "integer"},
                                "word": {"type": "string"},
                                "query": {"type": "string"},
                            },
                            "required": ["sentence", "word", "query"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["start_sentence", "end_sentence", "title", "why", "broll"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["clips"],
    "additionalProperties": False,
}

PROMPT = """You are the story editor of a vertical short-video channel. The format: a podcast/interview speaker tells one
self-contained story, cut to {min_dur:.0f}–{max_dur:.0f} seconds, intercut with literal stock B-roll of whatever is being
said, with big centred captions.

Below is a timestamped transcript split into numbered sentences. Choose the {n} best non-overlapping clips.
A good clip:
- starts directly on a strong, concrete claim (a number, a danger, a "why", a first-hand moment) — never on filler,
  a greeting or a dangling "and so…";
- is understandable on its own, and ends on a payoff, twist or verdict line;
- lasts between {min_dur:.0f} and {max_dur:.0f} seconds (use the timestamps);
- contains many showable things (animals, objects, places, actions).

For each clip list 6–20 B-roll moments: the sentence number, the exact word in that sentence the picture should land on,
and a short English stock-footage search query (2–4 words, concrete and filmable, e.g. "octopus squeezing through gap").
Write the title like a Shorts title: a concrete oddity, under 60 characters, in the transcript's language.

Transcript:
{transcript}"""


def llm_rerank(words, sents, cfg, n):
    """Ask Claude to choose clips. Returns a list of clip dicts, or None if unavailable."""
    if cfg.llm == "off":
        return None
    if cfg.llm == "auto" and not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return None
    try:
        import anthropic
    except ImportError:
        log("llm: 'anthropic' package not installed — using heuristic selection")
        return None
    lines = [f"[{i}] ({s['start']:.1f}–{s['end']:.1f}s) {s['text']}" for i, s in enumerate(sents)]
    prompt = PROMPT.format(min_dur=cfg.min_dur, max_dur=cfg.max_dur, n=n, transcript="\n".join(lines))
    try:
        client = anthropic.Anthropic()
        resp = client.beta.messages.create(
            model=cfg.llm_model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as e:
        log(f"llm: API error {e.status_code} — using heuristic selection")
        return None
    except anthropic.APIConnectionError:
        log("llm: cannot reach the API — using heuristic selection")
        return None
    if resp.stop_reason == "refusal":
        log("llm: request declined — using heuristic selection")
        return None
    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        log("llm: unreadable answer — using heuristic selection")
        return None
    clips = []
    for c in data.get("clips", []):
        a, b = int(c["start_sentence"]), int(c["end_sentence"])
        if not (0 <= a <= b < len(sents)):
            continue
        d = est_out(words, sents[a]["i0"], sents[b]["i1"], cfg.gap_trim)
        if d < cfg.min_dur * 0.8 or d > cfg.max_dur * 1.1:
            continue
        q = {}
        for m in c.get("broll", []):
            si = int(m["sentence"])
            if not (a <= si <= b):
                continue
            target = L.bare(m["word"])
            for k in range(sents[si]["i0"], sents[si]["i1"] + 1):
                if L.bare(words[k]["word"]) == target:
                    q[k] = m["query"]
                    break
        clips.append({"s0": a, "s1": b, "start": sents[a]["start"], "end": sents[b]["end"], "dur": round(d, 2),
                      "score": None, "title": c["title"], "why": c.get("why", ""), "queries": q, "source": "claude",
                      "priority": list(q.keys())})
    log(f"llm: Claude proposed {len(clips)} clip(s)")
    return non_overlapping(clips, n) or None


def select(words, cfg, env_db=None):
    sents = L.sentences(words)
    n = max(1, cfg.count)
    clips = llm_rerank(words, sents, cfg, n)
    if not clips:
        clips = non_overlapping(candidates(words, sents, cfg, env_db), n)
        for c in clips:
            c["source"] = "heuristic"
            c["title"] = sents[c["s0"]]["text"][:70]
    for c in clips:  # fill keyword queries for anything Claude didn't cover
        i0, i1 = sents[c["s0"]]["i0"], sents[c["s1"]]["i1"]
        c["i0"], c["i1"] = i0, i1
        for k in L.keywords(words, i0, i1):
            c["queries"].setdefault(k["idx"], k["query"])
        c["queries"] = {int(k): v for k, v in c["queries"].items()}
    return clips, sents
