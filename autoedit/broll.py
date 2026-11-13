"""B-roll sourcing: local library → Pexels → Pixabay → cutaways found inside the input video."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from . import language as L
from .util import log, probe

VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
UA = {"User-Agent": "autoedit/1.0 (+video editing pipeline)"}


def _tokens(text: str) -> set[str]:
    out = set()
    for t in re.split(r"[^a-zA-Zà-ÿÀ-ß0-9]+", text.lower()):
        if len(t) >= 3 and t not in L.STOP:
            out.add(t)
            if t.endswith("s") and len(t) > 4:
                out.add(t[:-1])
            if t.endswith("es") and len(t) > 5:
                out.add(t[:-2])
    return out


class LocalLibrary:
    """Any folder of clips/images. Matching uses file name, folder names and an optional sidecar .txt of tags."""

    def __init__(self, dirs: list[str]):
        self.items = []
        for d in dirs:
            root = Path(d).expanduser()
            if not root.exists():
                log(f"b-roll folder not found: {root}")
                continue
            for p in sorted(root.rglob("*")):
                ext = p.suffix.lower()
                if ext not in VIDEO_EXT | IMAGE_EXT:
                    continue
                tags = " ".join([p.stem] + [x.name for x in p.relative_to(root).parents if x.name])
                side = p.with_suffix(".txt")
                if side.exists():
                    tags += " " + side.read_text(encoding="utf-8", errors="ignore")
                self.items.append({"path": str(p), "kind": "video" if ext in VIDEO_EXT else "image",
                                   "tokens": _tokens(tags), "source": "local", "credit": ""})
        if dirs:
            log(f"b-roll library: {len(self.items)} files")

    def find(self, query: str, limit: int = 2) -> list[dict]:
        q = _tokens(query)
        if not q:
            return []
        scored = [(len(q & it["tokens"]), it) for it in self.items]
        scored = [s for s in scored if s[0] > 0]
        scored.sort(key=lambda s: -s[0])
        return [{**{k: v for k, v in it.items() if k != "tokens"}, "query": query} for _, it in scored[:limit]]


def _get_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers={**UA, **headers})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def _download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
    tmp.rename(dest)
    return dest


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "clip"


class Pexels:
    def __init__(self, key: str, cache: Path):
        self.key, self.cache = key, cache / "pexels"

    def find(self, query: str, limit: int = 2) -> list[dict]:
        out = []
        for orient in ("portrait", "landscape"):
            url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
                {"query": query, "orientation": orient, "per_page": 8, "size": "medium"})
            try:
                data = _get_json(url, {"Authorization": self.key})
            except Exception as e:  # network / quota
                log(f"pexels: '{query}' failed ({type(e).__name__})")
                return out
            for v in data.get("videos", []):
                files = [f for f in v.get("video_files", []) if f.get("link") and f.get("height")]
                if not files:
                    continue
                files.sort(key=lambda f: (abs(max(f["height"], f["width"]) - 1920), -f["height"]))
                f = files[0]
                dest = self.cache / f"{_slug(query)}_{v['id']}.mp4"
                try:
                    _download(f["link"], dest)
                except Exception as e:
                    log(f"pexels: download failed ({type(e).__name__})")
                    continue
                out.append({"path": str(dest), "kind": "video", "source": "pexels", "query": query,
                            "credit": f"Video by {v.get('user', {}).get('name', 'unknown')} on Pexels — {v.get('url', '')}"})
                if len(out) >= limit:
                    return out
            if out:
                return out
        return out


class Pixabay:
    def __init__(self, key: str, cache: Path):
        self.key, self.cache = key, cache / "pixabay"

    def find(self, query: str, limit: int = 2) -> list[dict]:
        url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": self.key, "q": query, "per_page": 8})
        try:
            data = _get_json(url, {})
        except Exception as e:
            log(f"pixabay: '{query}' failed ({type(e).__name__})")
            return []
        out = []
        for h in data.get("hits", []):
            vids = h.get("videos", {})
            f = vids.get("large") or vids.get("medium") or vids.get("small")
            if not f or not f.get("url"):
                continue
            dest = self.cache / f"{_slug(query)}_{h['id']}.mp4"
            try:
                _download(f["url"], dest)
            except Exception as e:
                log(f"pixabay: download failed ({type(e).__name__})")
                continue
            out.append({"path": str(dest), "kind": "video", "source": "pixabay", "query": query,
                        "credit": f"Video by {h.get('user', 'unknown')} on Pixabay — {h.get('pageURL', '')}"})
            if len(out) >= limit:
                break
        return out


def internal_cutaways(src: Path, scene_list: list[dict], clip_start: float, clip_end: float) -> list[dict]:
    """Shots of the input itself that look like inserts (no face, sharp, some motion), outside the clip."""
    pool = []
    for s in scene_list:
        if s["end"] - s["start"] < 1.0 or s["faces"] > 0.2 or s["bright"] < 25:
            continue
        if s["start"] < clip_end and s["end"] > clip_start:
            continue
        pool.append({"path": str(src), "kind": "video", "source": "input", "query": "cutaway", "credit": "",
                     "in": s["start"] + 0.15, "max_len": s["end"] - s["start"] - 0.3,
                     "q": s["sharp"] * (1 + s["motion"])})
    pool.sort(key=lambda x: -x["q"])
    return pool


def _verify_local(assets: list[dict], query: str) -> list[dict]:
    """CLIP check of downloaded stock clips: keep only those that show the query, cued to the right second."""
    from . import vision
    out = []
    for a in assets:
        try:
            dur = probe(Path(a["path"]))["duration"]
        except Exception:
            continue
        m = vision.best_moment(a["path"], dur, query, samples=8)
        if m:
            out.append({**a, "in": max(0.0, m["t"] - 0.3), "dur": dur, "match": round(m["prob"], 3)})
    return out


def resolve(queries: dict[int, str], cfg, cache: Path, src: Path, scene_list, clip, needed: int):
    """Map word index → list of assets (best first). Sources are tried in `cfg.broll_sources` order:
    library / your links (searched visually with CLIP when available) → Pexels → Pixabay → Wikimedia →
    YouTube Creative Commons → Internet Archive. Also returns a pool of internal cutaways."""
    from concurrent.futures import ThreadPoolExecutor

    from . import social, vision
    social.set_cache(cache)
    use_vision = cfg.vision != "off" and vision.available()
    if cfg.vision == "on" and not use_vision:
        log("⚠ vision requested but torch/transformers are not installed: pip install -r requirements-vision.txt")
    sources = list(cfg.broll_sources)
    lib = LocalLibrary(cfg.broll_dirs) if cfg.broll_dirs and "library" in sources else None
    url_clips = social.fetch_urls(social.read_url_list(cfg.broll_urls), cache) if cfg.broll_urls and "urls" in sources else []
    index = None
    if use_vision and ((lib and lib.items) or url_clips):
        files = [{k: v for k, v in it.items() if k != "tokens"} for it in (lib.items if lib else [])] + url_clips
        index = vision.VisualIndex(files, cache / "vision")
    remote = []
    for name in sources:
        if not cfg.online_broll:
            break
        if name == "pexels" and cfg.pexels_key:
            remote.append(("pexels", Pexels(cfg.pexels_key, cache)))
        elif name == "pixabay" and cfg.pixabay_key:
            remote.append(("pixabay", Pixabay(cfg.pixabay_key, cache)))
        elif name in ("wikimedia", "youtube_cc", "archive", "openverse") and use_vision:   # needs the visual check
            cls = {"wikimedia": social.Wikimedia, "youtube_cc": social.YouTubeCC, "archive": social.InternetArchive,
                   "openverse": social.Openverse}[name]
            remote.append((name, cls(cache)))
    if remote:
        log("b-roll sources: " + " → ".join(["library/links" if (lib or url_clips) else ""] * bool(lib or url_clips)
                                             + [n for n, _ in remote]))

    def lookup(q: str) -> list[dict]:
        if index:
            r = index.search(q, top=2)
            if r:
                return r
        elif lib:
            r = lib.find(q, limit=2)
            if r:
                return r
        for name, prov in remote:
            try:
                r = prov.find(q, limit=2 if name in ("pexels", "pixabay") else 1)
            except Exception as e:  # a provider failing must never stop the edit
                log(f"{name}: '{q}' error ({type(e).__name__})")
                continue
            if r and use_vision and name in ("pexels", "pixabay"):
                r = _verify_local(r, q)
            if r:
                return r
        return []

    order = sorted(queries.items(), key=lambda kv: (kv[0] not in clip.get("priority", []), kv[0]))
    uniq = []
    for _, q in order:
        if q not in uniq:
            uniq.append(q)
    uniq = uniq[: max(needed, 1)]
    with ThreadPoolExecutor(max_workers=3 if remote else 1) as ex:
        by_query = dict(zip(uniq, ex.map(lookup, uniq)))
    found = {idx: by_query[q] for idx, q in order if by_query.get(q)}
    for lst in found.values():
        for a in lst:
            if a["kind"] == "video" and "dur" not in a:
                try:
                    a["dur"] = probe(Path(a["path"]))["duration"]
                except Exception:
                    a["dur"] = 0
    hits = sum(1 for q in uniq if by_query.get(q))
    generic = internal_cutaways(src, scene_list, clip["start"], clip["end"]) if scene_list else []
    log(f"b-roll: {hits}/{len(uniq)} keyword(s) illustrated, {len(generic)} internal cutaway(s)")
    return found, generic
