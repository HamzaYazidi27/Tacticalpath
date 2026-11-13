"""Turn a selected clip into an edit decision list (EDL) following the Center-Punch rules.

Output timeline facts enforced here (see docs/02_EDITING_STYLE_BIBLE.md §F):
  * pauses > gap_trim and filler words are cut out (jump cuts)
  * frame 1 = speaker; first B-roll by ~1 s; last `end_on_speaker` seconds = speaker
  * B-roll lands 2 frames before its keyword, 0.8–1.8 s long, runs <= max_broll_run
  * speaker shots 0.8–1.6 s, alternating punch-in scales
"""
from __future__ import annotations

from . import language as L
from .util import FPS


def _q(t: float) -> float:
    """Quantise to the frame grid."""
    return round(round(t * FPS) / FPS, 4)


def islands(words, i0, i1, gap_trim):
    """Source ranges to keep (speech islands), with fillers and long pauses removed."""
    keep = [k for k in range(i0, i1 + 1) if L.bare(words[k]["word"]) not in L.FILLERS]
    out, cur = [], None
    for n, k in enumerate(keep):
        w = words[k]
        prev_k = keep[n - 1] if n else None
        contiguous = prev_k is not None and (k == prev_k + 1) and (w["start"] - words[prev_k]["end"] <= gap_trim)
        if cur and contiguous:
            cur["k1"] = k
        else:
            if cur:
                out.append(cur)
            cur = {"k0": k, "k1": k}
    if cur:
        out.append(cur)
    res, t_out = [], 0.0
    for n, isl in enumerate(out):
        s = words[isl["k0"]]["start"] - 0.06
        e = words[isl["k1"]]["end"] + 0.10
        if n > 0:
            s = max(s, res[-1]["src_end"])
        if n + 1 < len(out):
            e = min(e, words[out[n + 1]["k0"]]["start"] - 0.02)
        s, e = max(0.0, s), max(s + 0.1, e)
        dur = _q(e - s)
        res.append({"src_start": round(s, 3), "src_end": round(s + dur, 3), "out_start": round(t_out, 4),
                    "k0": isl["k0"], "k1": isl["k1"]})
        t_out += dur
    return res, _q(t_out)


def remap_words(words, isl):
    out = []
    for i in isl:
        for k in range(i["k0"], i["k1"] + 1):
            w = words[k]
            if L.bare(w["word"]) in L.FILLERS:
                continue
            s = w["start"] - i["src_start"] + i["out_start"]
            e = w["end"] - i["src_start"] + i["out_start"]
            out.append({"word": w["word"], "start": round(s, 3), "end": round(e, 3), "src_idx": k})
    return out


def _next_word_start(ow, t):
    for w in ow:
        if w["start"] > t + 1e-3:
            return w["start"]
    return None


def plan(words, clip, found, generic, cfg):
    isl, D = islands(words, clip["i0"], clip["i1"], cfg.gap_trim)
    ow = remap_words(words, isl)
    by_src = {w["src_idx"]: w for w in ow}
    lead = 2 / FPS
    end_limit = D - cfg.end_on_speaker
    min_start = max(0.8, cfg.first_broll_by - 0.35)

    # --- 1. B-roll shots from keyword anchors
    anchors = sorted((by_src[k]["start"], k) for k in found if k in by_src)
    b_shots, run_start, last_end, uses = [], None, 0.0, {}
    for n, (t, k) in enumerate(anchors):
        if t - lead < min_start - 0.25:
            continue                        # said too early for B-roll: never shift a picture onto another word
        start = _q(max(t - lead, min_start))
        if b_shots and start < last_end:
            if last_end - start > 0.35:
                continue
            start = _q(last_end)            # word still being spoken: chain straight after the previous picture
        if b_shots and start - last_end < 0.75 and start - last_end > 1e-3:
            start = _q(last_end)            # avoid a sub-0.75 s speaker flash: make the run contiguous
        contiguous = bool(b_shots) and abs(start - last_end) < 1e-3
        if contiguous and run_start is not None and start - run_start >= cfg.max_broll_run:
            continue                        # run too long: let the speaker come back
        if not contiguous:
            run_start = start
        nxt = anchors[n + 1][0] - lead if n + 1 < len(anchors) else None
        if nxt is not None and cfg.broll_shot_min <= nxt - start <= cfg.broll_shot_max:
            end = nxt
        else:
            target = start + 1.3
            ns = _next_word_start(ow, target - 0.25)
            end = ns - lead if ns and ns - lead <= start + cfg.broll_shot_max else start + 1.3
        end = min(end, start + cfg.broll_shot_max, end_limit, run_start + cfg.max_broll_run)
        if end - start < cfg.broll_shot_min * 0.9:
            continue
        prev_paths = {x["path"] for x in b_shots[-1]["assets"][:2]} if b_shots and contiguous else set()

        def ok(a):
            u = uses.get(a["path"], [])
            return (a["path"] not in prev_paths and len(u) < (2 if a["kind"] == "image" else 3)
                    and all(abs(start - x) >= 6.0 for x in u))
        cands = [a for a in found[k] if ok(a)]
        if not cands:
            continue                        # never the same picture twice in a row, nor too often
        if cands[0].get("max_len"):                     # never run past the end of the continuous source shot
            end = min(end, start + cands[0]["max_len"])
            if end - start < cfg.broll_shot_min * 0.9:
                continue
        uses.setdefault(cands[0]["path"], []).append(start)
        b_shots.append({"t0": start, "t1": _q(end), "kind": "B", "key": k, "query": clip["queries"].get(k, ""),
                        "word": by_src[k]["word"], "assets": cands})
        last_end = _q(end)

    # --- 2. top up with generic cutaways where the speaker holds too long
    def b_share():
        return sum(s["t1"] - s["t0"] for s in b_shots) / max(D, 1e-6)
    gi = 0
    while generic and b_share() < cfg.broll_share and gi < len(generic):
        bounds = [0.0] + [x for s in sorted(b_shots, key=lambda s: s["t0"]) for x in (s["t0"], s["t1"])] + [end_limit]
        gaps = [(bounds[i], bounds[i + 1]) for i in range(0, len(bounds) - 1, 2)]
        gaps = [(a, b) for a, b in gaps if b - a >= 2.8 and b > min_start + 1]
        if not gaps:
            break
        a, b = max(gaps, key=lambda g: g[1] - g[0])
        mid = (max(a, min_start) + b) / 2
        s0 = _q(mid - 0.6)
        b_shots.append({"t0": s0, "t1": _q(s0 + 1.2), "kind": "B", "key": None, "query": "cutaway",
                        "assets": [generic[gi]]})
        gi += 1

    b_shots.sort(key=lambda s: s["t0"])

    # --- 3. split long B shots into two angles when a second asset exists
    final_b = []
    for s in b_shots:
        assets = s.pop("assets")
        d = s["t1"] - s["t0"]
        if d > 1.55 and len(assets) > 1:
            m = _q(s["t0"] + d / 2)
            final_b += [dict(s, t1=m, asset=assets[0]), dict(s, t0=m, asset=assets[1], angle=2)]
        else:
            final_b.append(dict(s, asset=assets[0]))

    # --- 4. speaker shots fill the gaps, cut on word starts, alternating punch-ins
    shots, t, pi = [], 0.0, 0
    word_starts = [w["start"] - lead for w in ow if w["start"] - lead > 0]

    def add_a(a, b):
        nonlocal pi
        cur = a
        while b - cur > 1e-3:
            remaining = b - cur
            if remaining <= cfg.aroll_shot_max:
                cut = b
            else:
                cands = [x for x in word_starts if cur + cfg.aroll_shot_min <= x <= cur + cfg.aroll_shot_max]
                cut = _q(max(cands)) if cands else _q(cur + min(cfg.aroll_shot_max, remaining / 2))
                if b - cut < cfg.aroll_shot_min * 0.75:
                    cut = b
            shots.append({"t0": _q(cur), "t1": _q(cut), "kind": "A", "zoom": cfg.punch_scales[pi % len(cfg.punch_scales)]})
            pi += 1
            cur = cut

    for s in final_b:
        if s["t0"] - t > 1e-3:
            add_a(t, s["t0"])
        shots.append(s)
        t = s["t1"]
    if D - t > 1e-3:
        add_a(t, D)
    # the final line gets the tightest framing (verdict / punchline)
    a_idx = [i for i, s in enumerate(shots) if s["kind"] == "A"]
    if a_idx:
        shots[a_idx[-1]]["zoom"] = max(cfg.punch_scales)
        if len(a_idx) > 1 and a_idx[-2] == a_idx[-1] - 1:
            shots[a_idx[-2]]["zoom"] = min(cfg.punch_scales)      # keep the jump visible
    # merge micro shots (< 0.35 s) into their predecessor
    merged = []
    for s in shots:
        if merged and s["t1"] - s["t0"] < 0.35:
            merged[-1]["t1"] = s["t1"]
        else:
            merged.append(s)
    shots = merged

    # --- 5. asset in-points (don't reuse the same source range twice)
    used = {}
    for s in shots:
        if s["kind"] != "B":
            continue
        a, d = s["asset"], s["t1"] - s["t0"]
        if a["kind"] == "image":
            s["in"] = 0.0
            continue
        base = a.get("in", min(0.5, a.get("dur", 0) * 0.1))
        if a.get("max_len"):                            # cued to the matching shot: no offsets, no reuse drift
            s["in"] = round(base, 3)
            continue
        off = used.get(a["path"], 0.0)
        span = a.get("max_len") or max(a.get("dur", 0) - base, 0)
        s["in"] = round(base + (off if span - off >= d else 0.0), 3)
        used[a["path"]] = off + d

    n_cuts = len(shots) - 1
    stats = {
        "duration": D, "shots": len(shots), "cuts_per_min": round(n_cuts / D * 60, 1) if D else 0,
        "broll_share": round(sum(s["t1"] - s["t0"] for s in shots if s["kind"] == "B") / max(D, 1e-6), 3),
        "first_broll_at": next((s["t0"] for s in shots if s["kind"] == "B"), None),
        "jump_cuts_removed_s": round(sum(words[k]["end"] - words[k]["start"] for k in range(clip["i0"], clip["i1"] + 1)
                                         if L.bare(words[k]["word"]) in L.FILLERS), 2),
    }
    return {"duration": D, "islands": isl, "words": ow, "shots": shots, "stats": stats,
            "title": clip.get("title", ""), "clip": {k: clip[k] for k in ("start", "end", "dur", "source") if k in clip}}
