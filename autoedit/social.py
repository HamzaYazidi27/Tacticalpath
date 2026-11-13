"""Real-footage B-roll from the web, legally reusable, cut to the exact moment that shows the spoken word.

Providers (each returns short local clips already trimmed to the matching moment):
  * YouTubeCC       — YouTube search restricted to Creative Commons (CC BY) videos; license re-checked per video;
                       the video's own captions give a time hint ("the word is said here"), CLIP confirms it on screen.
  * Wikimedia       — Wikimedia Commons videos under CC0 / Public Domain / CC BY.
  * InternetArchive — archive.org films marked CC0 / Public Domain / CC BY (metadata can be wrong: CLIP + credits).
  * UrlLibrary      — links YOU provide (YouTube, TikTok, Instagram… anything yt-dlp opens) for footage you own or
                       have permission to use. Downloaded once, then searched visually like a local library.

Licences excluded on purpose: NC (non-commercial — conflicts with monetised channels), ND (no derivatives),
SA (share-alike would force your whole Short under CC BY-SA).
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from . import vision
from .util import log, probe, proc_env

UA = {"User-Agent": "AutoeditClipFinder/1.0 (open-source video editing tool)"}
OK_LICENSE = re.compile(r"(\bcc0\b|public ?domain|publicdomain|\bcc[ -]by[ -]?\d|creativecommons\.org/licenses/by/\d|"
                        r"creative commons attribution license)", re.I)
BAD_LICENSE = re.compile(r"(\bby[ -](nc|nd|sa)\b|/by-(nc|nd|sa)/|non-?commercial|no ?deriv|share-?alike)", re.I)
SEG = 4.5   # seconds kept around the matching moment
JS = {"deno": {}, "node": {}}   # yt-dlp needs a JavaScript runtime for YouTube: whichever is installed


def license_ok(text: str) -> bool:
    t = (text or "").lower()
    return bool(OK_LICENSE.search(t)) and not BAD_LICENSE.search(t)


_CACHE_DIR: Path | None = None
_LOCKS: dict = {}
_LAST: dict = {}


def set_cache(path: Path) -> None:
    """API answers are cached on disk: re-runs and repeated words cost no extra requests."""
    global _CACHE_DIR
    _CACHE_DIR = path / "api"
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_json(url: str, tries: int = 5, min_interval: float = 1.0) -> dict:
    """GET JSON: disk cache, one request at a time per host (spaced), retries on 429/5xx honouring Retry-After."""
    import hashlib
    import threading
    import time
    import urllib.error
    cf = _CACHE_DIR / (hashlib.md5(url.encode()).hexdigest() + ".json") if _CACHE_DIR else None
    if cf and cf.exists():
        return json.loads(cf.read_text(encoding="utf-8"))
    host = urllib.parse.urlparse(url).netloc
    lock = _LOCKS.setdefault(host, threading.Lock())
    for n in range(tries):
        with lock:
            wait = _LAST.get(host, 0) + min_interval - time.time()
            if wait > 0:
                time.sleep(wait)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                    data = json.loads(r.read().decode("utf-8"))
                _LAST[host] = time.time()
                if cf:
                    cf.write_text(json.dumps(data), encoding="utf-8")
                return data
            except urllib.error.HTTPError as e:
                _LAST[host] = time.time()
                if e.code not in (429, 500, 502, 503, 504) or n == tries - 1:
                    raise
                ra = e.headers.get("Retry-After")
                pause = min(float(ra) if ra and ra.isdigit() else 2 * 2 ** n, 30)
        time.sleep(pause)
    raise RuntimeError("unreachable")


def url_duration(url: str) -> float:
    """Duration of a remote media file (ffprobe with a proper User-Agent; Wikimedia rejects anonymous clients)."""
    p = subprocess.run(["ffprobe", "-v", "error", "-user_agent", UA["User-Agent"], "-show_entries", "format=duration",
                        "-of", "csv=p=0", url], capture_output=True, text=True, timeout=60, env=proc_env())
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def _hdr(headers: dict | None) -> str | None:
    return "".join(f"{k}: {v}\r\n" for k, v in (headers or {}).items()) or None


def cut_segment(src: str, t: float, out: Path, length: float = SEG, headers: str | None = None) -> Path | None:
    """Copy [t, t+length] of a local file or URL into a small H.264 clip (no audio)."""
    if out.exists() and out.stat().st_size > 0:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if src.startswith("http"):
        cmd += ["-user_agent", UA["User-Agent"]]
    if headers:
        cmd += ["-headers", headers]
    cmd += ["-ss", f"{max(t, 0):.2f}", "-i", src, "-t", f"{length:.2f}", "-an", "-vf", "scale='min(1920,iw)':-2",
            "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(out)]
    p = subprocess.run(cmd, capture_output=True, timeout=180, env=proc_env())
    return out if p.returncode == 0 and out.exists() and out.stat().st_size > 1000 else None


def _asset(path: Path, query: str, credit: str, license_: str, m: dict, source: str) -> dict | None:
    """Video asset trimmed to the single continuous shot that shows the query (None if that shot is too short)."""
    t = max(0.0, m.get("t_local", 0.3))
    sh = vision.clean_shot(str(path), t + 0.2)
    span = sh["end"] - max(sh["start"], t - 0.3)
    if span < 0.9:
        return None
    start = max(sh["start"], t - 0.3)
    return {"path": str(path), "kind": "video", "source": source, "query": query, "credit": credit,
            "license": license_, "in": round(start, 3), "max_len": round(span, 3), "dur": sh["total"] or SEG,
            "motion": sh["motion"], "match": round(m["prob"], 3), "sim": round(m["sim"], 3),
            "crop_x": vision.best_crop(str(path), t + 0.2, query)}


# ---------------------------------------------------------------- YouTube (Creative Commons only)
class YouTubeCC:
    SEARCH = "https://www.youtube.com/results?search_query={q}&sp=EgIwAQ%253D%253D"   # sp = Creative Commons filter

    def __init__(self, cache: Path, candidates: int = 4):
        self.cache, self.candidates = cache / "youtube_cc", candidates
        self.failures, self.disabled = 0, False          # circuit breaker: stop hammering a blocked network

    def _fail(self, hard: bool = False):
        self.failures += 1
        if hard or self.failures >= 3:
            if not self.disabled:
                log("youtube-cc: paused for the rest of this edit (network blocked by YouTube). "
                    "It works from a normal home/office connection.")
            self.disabled = True

    @staticmethod
    def _ydl(opts):
        from yt_dlp import YoutubeDL
        return YoutubeDL({"quiet": True, "no_warnings": True, "noprogress": True, "js_runtimes": JS, **opts})

    def _download(self, vid: str, t0: float, t1: float, fmt: str, name: str) -> Path | None:
        """Download only [t0, t1] of a video with yt-dlp (handles YouTube's chunked streaming)."""
        from yt_dlp.utils import download_range_func
        self.cache.mkdir(parents=True, exist_ok=True)
        done = list(self.cache.glob(name + ".*"))
        if done:
            return done[0]
        try:
            with self._ydl({"format": fmt, "outtmpl": str(self.cache / (name + ".%(ext)s")),
                            "download_ranges": download_range_func(None, [(t0, t1)]),
                            "force_keyframes_at_cuts": False}) as y:
                y.download([f"https://www.youtube.com/watch?v={vid}"])
        except Exception as e:
            log(f"youtube-cc: download of {vid} failed ({type(e).__name__})")
            self._fail(hard="confirm you" in str(e) or "403" in str(e))
            return None
        done = [p for p in self.cache.glob(name + ".*") if p.suffix not in (".part", ".ytdl")]
        return done[0] if done else None

    @staticmethod
    def caption_hint(info: dict, query: str) -> float | None:
        """Time (s) at which the video's own captions say the query word, if they do."""
        words = [w for w in re.findall(r"[a-z']+", query.lower()) if len(w) > 2]
        if not words:
            return None
        tracks = (info.get("subtitles") or {}).get("en") or (info.get("automatic_captions") or {}).get("en") or []
        j3 = next((t for t in tracks if t.get("ext") == "json3"), None)
        if not j3:
            return None
        try:
            data = _get_json(j3["url"])
        except Exception:
            return None
        for ev in data.get("events", []):
            t0 = ev.get("tStartMs", 0)
            for sg in ev.get("segs", []) or []:
                if any(w in sg.get("utf8", "").lower() for w in words):
                    return (t0 + sg.get("tOffsetMs", 0)) / 1000.0
        return None

    def find(self, query: str, limit: int = 1, verify: str | None = None) -> list[dict]:
        vq = verify or query          # search with `query`, require that the picture shows `vq`
        if self.disabled:
            return []
        try:
            with self._ydl({"extract_flat": True, "skip_download": True, "playlistend": 15}) as y:
                res = y.extract_info(self.SEARCH.format(q=urllib.parse.quote(query)), download=False)
        except Exception as e:
            log(f"youtube-cc: search failed for '{query}' ({type(e).__name__})")
            return []
        entries = [e for e in (res.get("entries") or []) if e and 8 <= (e.get("duration") or 0) <= 900
                   and not UNSAFE.search(e.get("title") or "")]
        out = []
        for e in entries[: self.candidates]:
            vid = e.get("id")
            try:
                with self._ydl({"skip_download": True, "format": "bv*[height<=1080][protocol^=http]/b[protocol^=http]"}) as y:
                    info = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            except Exception as ex:
                if "confirm you" in str(ex) and "bot" in str(ex):
                    self._fail(hard=True)
                    return out
                log(f"youtube-cc: {vid} unavailable ({type(ex).__name__})")
                continue
            lic = info.get("license") or ""
            if not license_ok(lic):
                continue                                    # the search filter is not proof: re-check every video
            dur = float(info.get("duration") or 0)
            hint = self.caption_hint(info, query)
            # 1) low-res preview of the useful part only (around the caption hit, else the first 5 min)
            w0, w1 = (max(0.0, hint - 10), min(dur, hint + 15)) if hint is not None else (0.0, min(dur, 300.0))
            scan = self._download(vid, w0, w1, "bv*[height<=360]/bv*[height<=480]/b[height<=480]", f"{vid}_scan_{int(w0)}")
            if not scan:
                if self.disabled:
                    return out
                continue
            m = vision.best_moment(str(scan), w1 - w0, vq, hint=(hint - w0) if hint is not None else None)
            if not m:
                continue
            # 2) only the matching seconds in full quality
            t = w0 + m["t"] - 0.3
            hq = self._download(vid, max(0.0, t), min(dur, t + SEG + 0.5), "bv*[height<=1080]/b[height<=1080]",
                                f"{vid}_hq_{int(t * 10)}") or scan
            seg = cut_segment(str(hq), 0.0 if hq != scan else m["t"] - 0.3, self.cache / f"{vid}_{int(t * 10)}.mp4")
            if seg:
                credit = f"\"{info.get('title', '')}\" by {info.get('uploader', '?')} — {info.get('webpage_url')} — {lic}"
                a = _asset(seg, query, credit, lic, {**m, "t_local": 0.3}, "youtube_cc")
                if a:
                    out.append(a)
            if len(out) >= limit:
                break
        return out


# ---------------------------------------------------------------- Wikimedia Commons
class Wikimedia:
    API = "https://commons.wikimedia.org/w/api.php"

    def __init__(self, cache: Path, candidates: int = 4):
        self.cache, self.candidates = cache / "wikimedia", candidates

    def find(self, query: str, limit: int = 1, verify: str | None = None) -> list[dict]:
        vq = verify or query          # search with `query`, require that the picture shows `vq`
        url = self.API + "?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": f"filetype:video {query}", "gsrlimit": 40, "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata", "iiextmetadatafilter": "LicenseShortName|Artist|ObjectName"})
        try:
            pages = list((_get_json(url).get("query") or {}).get("pages", {}).values())
        except Exception as e:
            log(f"wikimedia: '{query}' failed ({type(e).__name__})")
            return []
        out = []

        def lic_of(pg):
            return ((pg.get("imageinfo") or [{}])[0].get("extmetadata", {}).get("LicenseShortName") or {}).get("value", "")
        usable = [pg for pg in sorted(pages, key=lambda p: p.get("index", 0))
                  if license_ok(lic_of(pg)) and (pg.get("imageinfo") or [{}])[0].get("url")]
        for pg in usable[: self.candidates]:
            ii = pg["imageinfo"][0]
            meta = ii.get("extmetadata", {})
            lic = lic_of(pg)
            dur = url_duration(ii["url"])
            if dur <= 0:
                continue
            m = vision.best_moment(ii["url"], dur, vq)
            if not m:
                continue
            seg = cut_segment(ii["url"], m["t"] - 0.3, self.cache / f"{pg['pageid']}_{int(m['t'])}.mp4")
            if seg:
                artist = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "unknown"))
                credit = f"\"{pg['title']}\" by {artist} — https://commons.wikimedia.org/?curid={pg['pageid']} — {lic}"
                a = _asset(seg, query, credit, lic, {**m, "t_local": 0.3}, "wikimedia")
                if a:
                    out.append(a)
            if len(out) >= limit:
                break
        return out


# ---------------------------------------------------------------- Internet Archive
class InternetArchive:
    def __init__(self, cache: Path, candidates: int = 3):
        self.cache, self.candidates = cache / "archive", candidates

    def find(self, query: str, limit: int = 1, verify: str | None = None) -> list[dict]:
        vq = verify or query          # search with `query`, require that the picture shows `vq`
        q = f'({query}) AND mediatype:movies AND (licenseurl:*publicdomain* OR licenseurl:*creativecommons*)'
        url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
            {"q": q, "fl[]": ["identifier", "title", "licenseurl"], "rows": 10, "output": "json",
             "sort[]": "downloads desc"}, doseq=True)
        try:
            docs = _get_json(url)["response"]["docs"]
        except Exception as e:
            log(f"archive: '{query}' failed ({type(e).__name__})")
            return []
        out = []
        for d in docs[: self.candidates]:
            lic = d.get("licenseurl", "")
            if not license_ok(lic):
                continue
            try:
                files = _get_json(f"https://archive.org/metadata/{d['identifier']}")["files"]
            except Exception:
                continue
            vids = [f for f in files if f.get("format") in ("h.264", "MPEG4", "512Kb MPEG4", "h.264 IA")
                    and float(f.get("length") or 0) > 5]
            if not vids:
                continue
            scan = min(vids, key=lambda f: int(f.get("size") or 1e12))          # small file for scanning
            best = max(vids, key=lambda f: int(f.get("size") or 0))             # best quality for the cut
            base = f"https://archive.org/download/{d['identifier']}/"
            m = vision.best_moment(base + urllib.parse.quote(scan["name"]), float(scan["length"]), vq, samples=20)
            if not m:
                continue
            seg = cut_segment(base + urllib.parse.quote(best["name"]), m["t"] - 0.3,
                              self.cache / f"{d['identifier']}_{int(m['t'])}.mp4")
            if seg:
                credit = f"\"{d.get('title', d['identifier'])}\" — https://archive.org/details/{d['identifier']} — {lic}"
                a = _asset(seg, query, credit, lic, {**m, "t_local": 0.3}, "archive")
                if a:
                    out.append(a)
            if len(out) >= limit:
                break
        return out


UNSAFE = re.compile(r"\b(sexy|sensual|seductive|erotic|lingerie|naked|nude|stripper|twerk\w*|provocative|"
                    r"blood|gore|corpse|dead body)\b", re.I)   # never auto-insert these as B-roll

PEOPLE_WORDS = set("""man men woman women person people guy girl boy kid kids child children baby babies family crowd
doctor scientist soldier diver divers farmer hunter tourist teenager athlete player worker face selfie portrait""".split())


def face_prominent(img) -> bool:
    """True when a human face dominates the picture (>12 % of its width). Strangers' faces are not used as
    illustrations for unrelated words (likeness / consent), unless the word itself is about people."""
    try:
        import cv2
        import numpy as np
        g = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
        det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = det.detectMultiScale(g, 1.1, 5, minSize=(30, 30))
        return any(w > 0.12 * g.shape[1] for (_, _, w, _) in faces)
    except Exception:
        return False


# ---------------------------------------------------------------- Mixkit (free stock VIDEO, no key)
class Mixkit:
    """mixkit.co free stock videos — Mixkit Stock Video Free License: commercial use allowed, no attribution
    required (credit written anyway). Searched through the public site, politely (cache + spacing)."""
    SITE = "https://mixkit.co/free-stock-video/discover/{slug}/"
    ASSET = "https://assets.mixkit.co/videos/{id}/{id}-{res}.mp4"
    BROWSER = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/124.0 Safari/537.36"}

    def __init__(self, cache: Path, candidates: int = 4):
        self.cache, self.candidates = cache / "mixkit", candidates

    def _search(self, query: str) -> list[tuple[str, str]]:
        import hashlib
        slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
        cf = self.cache / f"search_{hashlib.md5(slug.encode()).hexdigest()[:12]}.json"
        if cf.exists():
            return [tuple(x) for x in json.loads(cf.read_text())]
        self.cache.mkdir(parents=True, exist_ok=True)
        try:
            req = urllib.request.Request(self.SITE.format(slug=slug), headers=self.BROWSER)
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode("utf-8", "ignore")
        except Exception as e:
            log(f"mixkit: '{query}' failed ({type(e).__name__})")
            return []
        items = list(dict.fromkeys(re.findall(r'href="/free-stock-video/([a-z0-9-]+)-(\d+)/"', html)))
        cf.write_text(json.dumps(items))
        return items

    def find(self, query: str, limit: int = 1, verify: str | None = None) -> list[dict]:
        vq = verify or query          # search with `query`, require that the picture shows `vq`
        items = self._search(query)
        words = set(re.findall(r"[a-z]{3,}", query.lower()))
        # rank by how many query words appear in the clip title, keep the site order otherwise
        items = [it for it in items if not UNSAFE.search(it[0].replace("-", " "))]
        items = sorted(items, key=lambda it: -len(words & set(it[0].split("-"))))
        out = []
        for title, vid in items[: self.candidates]:
            dest = self.cache / f"{vid}.mp4"
            if not dest.exists():
                for res in ("1080", "720"):
                    try:
                        req = urllib.request.Request(self.ASSET.format(id=vid, res=res), headers=self.BROWSER)
                        with urllib.request.urlopen(req, timeout=60) as r:
                            dest.write_bytes(r.read())
                        break
                    except Exception:
                        continue
            if not dest.exists():
                continue
            dur = probe(dest)["duration"]
            m = vision.best_moment(str(dest), dur, vq, samples=10)
            if not m:
                continue
            need = set(re.findall(r"[a-z]{3,}", vq.lower())) - {"the", "and", "with"}
            if len(need) >= 2 and not need <= set(title.split("-")) and m["prob"] < 0.985:
                continue                    # phrase only half in the title: demand a near-certain visual match
            a = _asset(dest, query, f"\"{title.replace('-', ' ')}\" — https://mixkit.co/free-stock-video/{title}-{vid}/ "
                       "— Mixkit Stock Video Free License", "Mixkit Free License", {**m, "t_local": m["t"]}, "mixkit")
            if a:
                out.append(a)
            if len(out) >= limit:
                break
        return out


# ---------------------------------------------------------------- Openverse (real CC photos: Flickr, museums…)
class Openverse:
    """Real photographs under CC BY / CC0 / Public Domain Mark, CLIP-checked; animated with a slow push-in."""
    API = "https://api.openverse.org/v1/images/"

    def __init__(self, cache: Path, candidates: int = 6):
        self.cache, self.candidates = cache / "openverse", candidates

    def find(self, query: str, limit: int = 1, verify: str | None = None) -> list[dict]:
        vq = verify or query          # search with `query`, require that the picture shows `vq`
        url = self.API + "?" + urllib.parse.urlencode({"q": query, "license": "by,cc0,pdm", "page_size": 20,
                                                       "mature": "false"})
        try:
            results = _get_json(url).get("results", [])
        except Exception as e:
            log(f"openverse: '{query}' failed ({type(e).__name__})")
            return []
        results = [r for r in results if (r.get("width") or 0) >= 640 and (r.get("height") or 0) >= 480
                   and license_ok(f"cc {r.get('license')} {r.get('license_version', '')}".replace("cc pdm", "public domain")
                                  .replace("cc cc0", "cc0").replace("cc by ", "cc by "))]
        from PIL import Image
        paths, metas = [], []
        self.cache.mkdir(parents=True, exist_ok=True)
        for r in results[: self.candidates]:
            dest = self.cache / f"{r['id']}.jpg"
            try:
                if not dest.exists():
                    with urllib.request.urlopen(urllib.request.Request(r["url"], headers=UA), timeout=30) as resp:
                        dest.write_bytes(resp.read())
                Image.open(dest).verify()
                paths.append(dest)
                metas.append(r)
            except Exception:
                continue
        if not paths:
            return []
        imgs = [Image.open(p).convert("RGB") for p in paths]
        if not (set(query.lower().split()) & PEOPLE_WORDS):
            keep = [i for i, im in enumerate(imgs) if not face_prominent(im)]
            imgs, paths, metas = [imgs[i] for i in keep], [paths[i] for i in keep], [metas[i] for i in keep]
            if not imgs:
                return []
        emb = vision.embed_images(imgs)
        prob, sim = vision.score(emb, vq)
        bad = vision.unsafe_mask(emb, sim)
        order = [i for i in sorted(range(len(paths)), key=lambda i: -(prob[i] + sim[i])) if not bad[i]]
        out = []
        for i in order:
            if prob[i] < vision.MIN_PROB or sim[i] < vision.MIN_SIM:
                continue
            r = metas[i]
            lic = f"{r.get('license', '').upper()} {r.get('license_version', '')}".strip()
            credit = f"Photo \"{r.get('title') or ''}\" by {r.get('creator') or 'unknown'} — {r.get('foreign_landing_url')} — {lic}"
            out.append({"path": str(paths[i]), "kind": "image", "source": "openverse", "query": query, "credit": credit,
                        "license": lic, "in": 0.0, "match": round(float(prob[i]), 3), "sim": round(float(sim[i]), 3)})
            if len(out) >= limit:
                break
        return out


# ---------------------------------------------------------------- your own links (any platform)
def fetch_urls(urls: list[str], cache: Path, max_len: int = 600) -> list[dict]:
    """Download the clips behind the links you provide (YouTube, TikTok, Instagram, X…) once, ≤1080p.
    Only use links to footage you own or have permission to reuse."""
    out = []
    if not urls:
        return out
    from yt_dlp import YoutubeDL
    d = cache / "urls"
    d.mkdir(parents=True, exist_ok=True)
    opts = {"quiet": True, "no_warnings": True, "noprogress": True, "js_runtimes": JS, "outtmpl": str(d / "%(extractor)s_%(id)s.%(ext)s"),
            "format": "bv*[height<=1080]+ba/b[height<=1080]/b", "merge_output_format": "mp4",
            "match_filter": lambda info, *_: None if (info.get("duration") or 0) <= max_len else "too long"}
    for u in urls:
        try:
            with YoutubeDL(opts) as y:
                info = y.extract_info(u, download=True)
                path = Path(y.prepare_filename(info)).with_suffix(".mp4")
                if not path.exists():
                    path = Path(y.prepare_filename(info))
            if path.exists():
                out.append({"path": str(path), "kind": "video", "source": "your-link",
                            "credit": f"\"{info.get('title', '')}\" — {info.get('webpage_url', u)} (used with permission)"})
        except Exception as e:
            log(f"link skipped: {u} ({type(e).__name__}: {str(e)[:80]})")
    log(f"your links: {len(out)}/{len(urls)} clip(s) available")
    return out


def read_url_list(items: list[str]) -> list[str]:
    urls = []
    for it in items:
        p = Path(it).expanduser()
        if p.exists():
            urls += [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
                     if ln.strip().startswith("http")]
        elif it.startswith("http"):
            urls.append(it)
    return urls
