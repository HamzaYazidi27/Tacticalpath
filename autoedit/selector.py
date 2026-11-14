"""Pick the best 30–60 s story(ies) in a long recording. Heuristic scoring, optionally re-ranked by Claude."""
from __future__ import annotations

import json
import os
import re

import numpy as np

from . import language as L
from . import viral
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
                    "hook": {"type": "string"},
                    "virality": {"type": "integer"},
                    "teaser_sentence": {"type": "integer"},
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
                "required": ["start_sentence", "end_sentence", "title", "hook", "virality", "teaser_sentence", "why", "broll"],
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
"hook": the text shown big on screen during the first 3 seconds — 3 to 8 words, in the transcript's language, a
curiosity gap that makes people stay (e.g. "Why Americans got it right"), never clickbait the clip doesn't pay off.
"virality": your 0–100 estimate of how well this clip would retain viewers and get shared.
"teaser_sentence": the number of one short, striking sentence from the middle of the clip worth playing first as a
cold open (1–3 seconds, not the final payoff line), or -1 if the opening line is already the strongest.
Order the clips best first.

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
        ts = int(c.get("teaser_sentence", -1))
        tz = None
        if a < ts < b:
            td = est_out(words, sents[ts]["i0"], sents[ts]["i1"], cfg.gap_trim)
            if 0.8 <= td <= 3.2 and d + td <= cfg.max_dur + 1:
                tz = [sents[ts]["i0"], sents[ts]["i1"]]
        clips.append({"s0": a, "s1": b, "start": sents[a]["start"], "end": sents[b]["end"], "dur": round(d, 2),
                      "score": None, "title": c["title"], "why": c.get("why", ""), "queries": q, "source": "claude",
                      "priority": list(q.keys()), "hook": str(c.get("hook", "")).strip(),
                      "llm_virality": c.get("virality"), "teaser": tz})
    log(f"llm: Claude proposed {len(clips)} clip(s)")
    return non_overlapping(clips, n) or None


def _translated_queries(words, en_words, i0, i1):
    """English B-roll keywords for words[i0..i1], each anchored on the spoken word closest in time."""
    t0, t1 = words[i0]["start"] - 0.3, words[i1]["end"] + 0.3
    idx = [k for k, w in enumerate(en_words) if t0 <= w["start"] <= t1]
    if not idx:
        return {}
    q = {}
    for kw in L.keywords(en_words, idx[0], idx[-1]):
        t = en_words[kw["idx"]]["start"]
        k = min(range(i0, i1 + 1), key=lambda j: abs(words[j]["start"] - t))
        q.setdefault(k, kw["query"])
    return q


def on_topic(queries: dict, topic: str | None) -> dict:
    """In a talk about e.g. finance, abstract keywords get on-topic footage instead of a literal mismatch
    ('buy' → not someone buying diapers; 'balance' → not a gymnast). Concrete things keep their query."""
    if not topic:
        return queries
    words, pool = L.TOPICS[topic]
    concrete = set(L.EXPAND.values())
    out, n = {}, 0
    for k in sorted(queries):
        q = queries[k]
        toks = [re.sub(r"'s$", "", L.bare(x)) for x in q.split()]
        hit = next((L.EXPAND[t] for t in toks if t in L.EXPAND), None)
        if q in concrete:
            out[k] = q
        elif hit:
            out[k] = hit                    # "broker's wife wanted" → the broker's footage
        elif any(t in L.VISUAL or t.rstrip("s") in L.VISUAL for t in toks):
            out[k] = q
        else:
            out[k] = pool[n % len(pool)]
            n += 1
    return out


def select(words, cfg, env_db=None, en_words=None, file_title=""):
    sents = L.sentences(words)
    auto = cfg.count <= 0
    n = viral.auto_count(est_out(words, 0, len(words) - 1, cfg.gap_trim), cfg) if auto else cfg.count
    if auto:
        log(f"count: auto → up to {n} Short(s) for this recording")
    clips = llm_rerank(words, sents, cfg, n)
    if not clips:
        clips = non_overlapping(candidates(words, sents, cfg, env_db), n)
        for c in clips:
            c["source"] = "heuristic"
            c["title"] = sents[c["s0"]]["text"][:70]
    for c in clips:                                  # retention layer: score, cold open, on-screen hook
        v = viral.score(words, sents, c["s0"], c["s1"], c["dur"], cfg, env_db)
        if c.get("llm_virality") is not None:
            v["claude"] = int(c["llm_virality"])
            v["total"] = int(round(0.6 * v["claude"] + 0.4 * v["total"]))
        c["virality"] = v
        if "teaser" not in c:
            c["teaser"] = viral.teaser(words, sents, c["s0"], c["s1"], c["dur"], cfg, est_out)
        if not cfg.cold_open:
            c["teaser"] = None
        if cfg.hook_title == "off":
            c["hook"] = ""
        elif cfg.hook_title not in ("", "auto"):
            c["hook"] = cfg.hook_title
        elif not c.get("hook"):
            # a short line from the talk, else the creator's own title (file name), else a longer line
            c["hook"] = (viral.hook_text(sents, c["s0"], c["s1"], c["teaser"], max_words=8)
                         or (file_title if len(clips) == 1 else "")
                         or viral.hook_text(sents, c["s0"], c["s1"], c["teaser"], max_words=12))
    clips.sort(key=lambda c: -c["virality"]["total"])           # Short 1 = the most promising
    if auto and len(clips) > 1:
        keep = [c for c in clips if c["virality"]["total"] >= cfg.min_virality]
        if len(keep) < len(clips):
            log(f"virality: {len(clips) - len(keep)} weak clip(s) dropped (score < {cfg.min_virality})")
        clips = keep or clips[:1]
    for c in clips:  # fill keyword queries for anything Claude didn't cover
        i0, i1 = sents[c["s0"]]["i0"], sents[c["s1"]]["i1"]
        c["i0"], c["i1"] = i0, i1
        if en_words and c.get("source") != "claude":
            for k, q in _translated_queries(words, en_words, i0, i1).items():
                c["queries"].setdefault(k, q)
            t0, t1 = words[i0]["start"] - 0.3, words[i1]["end"] + 0.3
            ix = [k for k, w in enumerate(en_words) if t0 <= w["start"] <= t1]
            topic = L.topic_of(en_words, ix[0], ix[-1]) if ix else None
        else:
            for k in L.keywords(words, i0, i1):
                c["queries"].setdefault(k["idx"], k["query"])
            topic = L.topic_of(words, i0, i1)
        if c.get("source") != "claude":
            c["queries"] = on_topic(c["queries"], topic)
            if topic:
                log(f"topic: {topic} → abstract words illustrated with on-topic footage")
        c["queries"] = {int(k): v for k, v in c["queries"].items()}
    return clips, sents
