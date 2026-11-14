"""autoedit Studio — local web interface for the autoedit pipeline.

Run:  python -m webui            (opens http://127.0.0.1:8765)
      python -m webui --host 0.0.0.0 --port 8765   (other devices on your network; no authentication!)

Everything runs on this computer. Edits are executed by the same command-line pipeline in a subprocess,
one at a time (they are CPU/memory heavy); searches for alternative B-roll run in a second lane.
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

ROOT = Path(__file__).resolve().parent.parent
WS = Path(os.environ.get("AUTOEDIT_WORKSPACE", ROOT / "workspace")).resolve()
UPLOADS, OUT, ASSETS, THUMBS = WS / "uploads", WS / "outbox", WS / "assets", WS / "thumbs"
JOBS_FILE, SECRETS = WS / "jobs.json", WS / "secrets.json"
CONFIG = ROOT / "autoedit.config.json"
LIB = {"broll": ROOT / "broll", "music": ROOT / "music"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
for d in (UPLOADS, OUT, ASSETS, THUMBS, *LIB.values()):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))
from autoedit.util import fix_path, has_libass  # noqa: E402  (repairs PATH for Finder/Explorer launches)

fix_path()
app = FastAPI(title="autoedit Studio")

# ------------------------------------------------------------------ persistence
_lock = threading.RLock()
JOBS: dict[str, dict] = {}
if JOBS_FILE.exists():
    try:
        JOBS = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        for j in JOBS.values():                       # a job cannot survive a server restart
            if j["status"] in ("queued", "running"):
                j.update(status="failed", error="Interrompu (serveur redémarré)")
    except Exception:
        JOBS = {}


def save_jobs():
    with _lock:
        tmp = JOBS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(JOBS, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(JOBS_FILE)


def secrets() -> dict:
    try:
        return json.loads(SECRETS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def sub_env() -> dict:
    env = dict(os.environ)
    s = secrets()
    for k, var in (("pexels", "PEXELS_API_KEY"), ("pixabay", "PIXABAY_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY")):
        if s.get(k):
            env[var] = s[k]
    env["PYTHONUNBUFFERED"] = "1"
    return env


def inside(p: Path, *roots: Path) -> bool:
    p = p.resolve()
    return any(p == r.resolve() or r.resolve() in p.parents for r in roots)


# ------------------------------------------------------------------ job runner
STAGES = [  # (log pattern, stage label, progress %)
    (r"input:", "Préparation", 3), (r"transcribing", "Transcription", 8), (r"transcript:", "Transcription", 18),
    (r"scenes:", "Analyse des plans", 24), (r"PODCAST-CLIP mode|MONTAGE mode", "Analyse", 27),
    (r"clip \d+:", "Choix de l'histoire", 30), (r"b-roll: videos from", "Recherche B-roll", 33),
    (r"→ photo|mixkit|wikimedia|openverse|youtube-cc", "Recherche B-roll", None),
    (r"keyword\(s\) illustrated", "Plan de montage", 60), (r"plan \d+:", "Plan de montage", 63),
    (r"face track", "Rendu des plans", 68), (r"video track", "Rendu des plans", 78), (r"re-render:", "Rendu", 10),
    (r"final grade", "Étalonnage, sous-titres, encodage", 86), (r"✔", "Contrôle qualité", 98),
]
EDIT_Q: "queue.Queue[str]" = queue.Queue()
PROCS: dict[str, subprocess.Popen] = {}


def _update_from_line(job: dict, line: str):
    for pat, label, pct in STAGES:
        if re.search(pat, line):
            job["stage"] = label
            if pct is not None:
                job["progress"] = max(job.get("progress", 0), pct)
            elif job.get("progress", 0) < 58:
                job["progress"] = min(58, job.get("progress", 33) + 1)
    m = re.search(r"b-roll \[(\d+)/(\d+)\]", line)
    if m:
        k, n = int(m.group(1)), int(m.group(2))
        job["stage"] = f"Recherche B-roll ({k}/{n})"
        job["progress"] = max(job.get("progress", 0), 33 + int(25 * k / max(n, 1)))
    m = re.search(r"✔ (\S+_short(\d+)\.mp4)", line)
    if m:
        job.setdefault("outputs", []).append(m.group(1))


def run_job(jid: str):
    job = JOBS[jid]
    job.update(status="running", started=time.time(), stage="Démarrage", progress=1, log=[])
    save_jobs()
    try:
        p = subprocess.Popen(job["cmd"], cwd=ROOT, env=sub_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, bufsize=1)
        PROCS[jid] = p
        for line in p.stdout:
            line = line.rstrip()
            if not line or "Loading weights" in line or line.startswith("Warning: You are sending"):
                continue
            with _lock:
                job["log"] = (job.get("log", []) + [line])[-400:]
                _update_from_line(job, line)
        p.wait()
        if job.get("status") == "cancelled":
            pass
        elif p.returncode == 0:
            job.update(status="done", progress=100, stage="Terminé")
        else:
            job.update(status="failed", error=failure_reason(job["log"], p.returncode))
    except Exception as e:  # never kill the worker
        job.update(status="failed", error=str(e))
    finally:
        PROCS.pop(jid, None)
        job["finished"] = time.time()
        save_jobs()


def failure_reason(log: list[str], code: int) -> str:
    """The most useful line(s) explaining why a run stopped, in plain words when we recognise it."""
    tail = [l for l in log if l.strip()][-12:]
    text = "\n".join(tail)
    if "ffmpeg not found" in text:
        return next(l for l in tail if "ffmpeg not found" in l).replace("ERROR: ", "")
    if "No module named" in text:
        mod = re.search(r"No module named '([^']+)'", text)
        return (f"Module Python manquant : {mod.group(1) if mod else '?'} — relancez le script d'installation "
                "(ou pip install -r requirements.txt)")
    if "No space left" in text:
        return "Disque plein — libérez de l'espace."
    if "MemoryError" in text or code in (-9, 137):
        return "Mémoire insuffisante — fermez d'autres applications ou utilisez la transcription « small »."
    errs = [l for l in tail if re.search(r"(Error|ERROR|error:|failed|✖)", l)]
    raw = [l for l in tail if not l.startswith("[autoedit")]
    pick = errs[-1:] or raw[-2:] or tail[-1:]
    return " · ".join(x.strip()[:300] for x in pick) or f"code {code}"


def worker():
    while True:
        jid = EDIT_Q.get()
        if jid in JOBS and JOBS[jid]["status"] == "queued":
            run_job(jid)


threading.Thread(target=worker, daemon=True).start()


def new_job(kind: str, title: str, cmd: list[str], meta: dict | None = None) -> dict:
    jid = uuid.uuid4().hex[:10]
    job = {"id": jid, "kind": kind, "title": title, "cmd": cmd, "status": "queued", "stage": "En attente",
           "progress": 0, "created": time.time(), "log": [], "outputs": [], **(meta or {})}
    with _lock:
        JOBS[jid] = job
    save_jobs()
    EDIT_Q.put(jid)
    return job


def public(job: dict, full: bool = False) -> dict:
    j = {k: v for k, v in job.items() if k not in ("cmd", "log")}
    j["queue_pos"] = (sum(1 for x in JOBS.values() if x["status"] == "queued" and x["created"] < job["created"])
                      if job["status"] == "queued" else 0)
    if full:
        j["log"] = job.get("log", [])[-200:]
    return j


# ------------------------------------------------------------------ pages / media
@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/media/{rel:path}")
def media(rel: str):
    p = (WS / rel).resolve()
    if not inside(p, WS) or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/fonts/{name}")
def fonts(name: str):
    p = (ROOT / "fonts" / name).resolve()
    if not inside(p, ROOT / "fonts") or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/libmedia/{kind}/{name}")
def libmedia(kind: str, name: str):
    if kind not in LIB:
        raise HTTPException(404)
    p = (LIB[kind] / name).resolve()
    if not inside(p, LIB[kind]) or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p)


_KNOWN: dict = {"t": 0.0, "paths": set()}


def known_asset(p: Path) -> bool:
    """Assets referenced by any EDL in the outbox (they may live in an older cache folder)."""
    if time.time() - _KNOWN["t"] > 10:
        paths = set()
        for e in OUT.glob("*/*_short*_edl.json"):
            try:
                d = json.loads(e.read_text(encoding="utf-8"))
                paths |= {str(Path(sh["asset"]["path"]).resolve()) for sh in d["shots"] if sh.get("asset")}
                if d.get("source"):
                    paths.add(str(Path(d["source"]).resolve()))
            except Exception:
                continue
        _KNOWN.update(t=time.time(), paths=paths)
    return str(p) in _KNOWN["paths"]


@app.get("/api/thumb")
def thumb(path: str, t: float = 0.5, w: int = 270):
    """JPEG frame of any video/image the studio knows about (workspace, library, B-roll cache, EDL assets)."""
    p = Path(path).resolve()
    if not (inside(p, WS, *LIB.values(), ROOT / "autoedit_out") or known_asset(p)) or not p.is_file():
        raise HTTPException(404)
    key = re.sub(r"[^A-Za-z0-9]", "_", f"{p.stem}_{p.stat().st_mtime:.0f}_{t:.2f}_{w}")[-120:]
    out = THUMBS / f"{key}.jpg"
    if not out.exists():
        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        if p.suffix.lower() not in IMAGE_EXT:
            args += ["-ss", f"{max(t, 0):.2f}"]
        subprocess.run(args + ["-i", str(p), "-frames:v", "1", "-vf", f"scale={w}:-2", "-q:v", "4", str(out)],
                       capture_output=True, timeout=60)
    if not out.exists():
        raise HTTPException(404)
    return FileResponse(out, media_type="image/jpeg")


# ------------------------------------------------------------------ uploads + edits
@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    out = []
    for f in files:
        ext = Path(f.filename or "video.mp4").suffix.lower()
        if ext not in VIDEO_EXT:
            raise HTTPException(400, f"Format non supporté : {f.filename}")
        fid = uuid.uuid4().hex[:8]
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(f.filename).stem)[:60] or "video"
        dest = UPLOADS / f"{safe}_{fid}{ext}"
        with open(dest, "wb") as fh:
            shutil.copyfileobj(f.file, fh, 1 << 20)
        out.append({"file_id": dest.name, "name": f.filename, "size": dest.stat().st_size})
    return out


@app.post("/api/jobs")
async def create_job(req: Request):
    b = await req.json()
    src = UPLOADS / b.get("file_id", "")
    if not src.is_file() or not inside(src, UPLOADS):
        raise HTTPException(400, "Fichier introuvable — renvoyez la vidéo.")
    o = b.get("options", {})
    cmd = [sys.executable, "-m", "autoedit", str(src), "--out", str(OUT)]
    for flag, key in (("--brand", "brand"), ("--count", "count"), ("--min-dur", "min_dur"), ("--max-dur", "max_dur"),
                      ("--target", "target"), ("--language", "language"), ("--whisper-model", "whisper_model"),
                      ("--text", "text")):
        if o.get(key) not in (None, ""):
            cmd += [flag, str(o[key])]
    if o.get("sources"):
        cmd += ["--sources", ",".join(o["sources"])]
    if o.get("photos") is False:
        cmd.append("--no-photos")
    if o.get("llm") in ("on", "off"):
        cmd += ["--llm", o["llm"]]
    job = new_job("edit", b.get("name") or src.name, cmd, {"file_id": src.name, "slug": slug_of(src)})
    return public(job)


def slug_of(src: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", src.stem)[:60].strip("_") or "video"


@app.get("/api/jobs")
def jobs():
    return sorted((public(j) for j in JOBS.values()), key=lambda j: -j["created"])


@app.get("/api/jobs/{jid}")
def job(jid: str):
    if jid not in JOBS:
        raise HTTPException(404)
    return public(JOBS[jid], full=True)


@app.post("/api/jobs/{jid}/cancel")
def cancel(jid: str):
    j = JOBS.get(jid) or {}
    if j.get("status") in ("queued", "running"):
        j["status"], j["stage"] = "cancelled", "Annulé"
        p = PROCS.get(jid)
        if p:
            p.terminate()
        save_jobs()
    return {"ok": True}


@app.delete("/api/jobs/{jid}")
def delete_job(jid: str):
    with _lock:
        j = JOBS.get(jid)
        if j and j["status"] not in ("queued", "running"):
            JOBS.pop(jid)
    save_jobs()
    return {"ok": True}


# ------------------------------------------------------------------ shorts (results) + editing
def edl_path(slug: str, n: int) -> Path:
    p = OUT / slug / f"{slug}_short{n}_edl.json"
    if not inside(p, OUT) or not p.exists():
        raise HTTPException(404, "Short introuvable")
    return p


@app.get("/api/shorts")
def shorts():
    res = []
    for e in OUT.glob("*/*_short*_edl.json"):
        m = re.match(r"(.+)_short(\d+)_edl\.json", e.name)
        if not m:
            continue
        slug, n = m.group(1), int(m.group(2))
        mp4 = e.parent / f"{slug}_short{n}.mp4"
        qc = e.parent / f"{slug}_short{n}_qc.json"
        try:
            d = json.loads(e.read_text(encoding="utf-8"))
            qcd = json.loads(qc.read_text(encoding="utf-8")) if qc.exists() else None
        except Exception:
            continue
        res.append({"slug": slug, "n": n, "title": d.get("title") or slug, "duration": d.get("duration"),
                    "stats": d.get("stats", {}), "rendered": mp4.exists(), "qc_pass": qcd and qcd.get("pass"),
                    "virality": (d.get("virality") or {}).get("total"), "hook": d.get("hook", ""),
                    "mtime": (mp4 if mp4.exists() else e).stat().st_mtime,
                    "cover": f"/media/outbox/{slug}/{slug}_short{n}_cover.jpg?v={int(e.stat().st_mtime)}"})
    return sorted(res, key=lambda r: -r["mtime"])


def chunks_of(words: list[dict]) -> list[dict]:
    from autoedit.render import _captions_module
    mc = _captions_module()
    ids = {id(w): i for i, w in enumerate(words)}
    out = []
    for s, e, c in mc.chunk_words(words):
        idx = [ids[id(w)] for w in c]
        out.append({"start": round(s, 2), "end": round(e, 2), "i0": idx[0], "i1": idx[-1],
                    "text": " ".join(mc.clean(w["word"], True) for w in c)})
    return out


def viral_labels() -> dict:
    from autoedit.viral import LABELS
    return LABELS


@app.get("/api/shorts/{slug}/{n}")
def short(slug: str, n: int):
    e = edl_path(slug, n)
    d = json.loads(e.read_text(encoding="utf-8"))
    base = f"/media/outbox/{slug}/{slug}_short{n}"
    mp4 = e.parent / f"{slug}_short{n}.mp4"
    v = int(mp4.stat().st_mtime) if mp4.exists() else 0
    qc = e.parent / f"{slug}_short{n}_qc.json"
    cr = e.parent / f"{slug}_short{n}_credits.txt"
    shots = []
    for i, s in enumerate(d["shots"]):
        a = s.get("asset") or {}
        shots.append({"i": i, "t0": s["t0"], "t1": s["t1"], "kind": s["kind"], "zoom": s.get("zoom"),
                      "word": s.get("word"), "query": s.get("query"), "asset_kind": a.get("kind"),
                      "asset_path": a.get("path"), "source": a.get("source"), "credit": a.get("credit"),
                      "in": s.get("in")})
    return {"slug": slug, "n": n, "title": d.get("title"), "duration": d["duration"], "stats": d.get("stats"),
            "mode": d.get("mode", "podcast"), "shots": shots, "chunks": chunks_of(d["words"]),
            "qc": json.loads(qc.read_text()) if qc.exists() else None,
            "credits": cr.read_text(encoding="utf-8") if cr.exists() else "",
            "video": f"{base}.mp4?v={v}" if mp4.exists() else None, "srt": f"{base}.srt", "cover": f"{base}_cover.jpg?v={v}",
            "final_path": str(mp4), "dirty": d.get("dirty", False),
            "hook": d.get("hook", ""), "virality": d.get("virality"), "teaser": (d.get("stats") or {}).get("teaser", 0),
            "labels": viral_labels()}


@app.post("/api/shorts/{slug}/{n}/shot/{i}")
async def edit_shot(slug: str, n: int, i: int, req: Request):
    b = await req.json()
    e = edl_path(slug, n)
    d = json.loads(e.read_text(encoding="utf-8"))
    if not 0 <= i < len(d["shots"]):
        raise HTTPException(404)
    s = d["shots"][i]
    act = b.get("action")
    if act == "remove":                                  # back to the speaker
        s.pop("asset", None)
        s.update(kind="A", zoom=s.get("zoom") or 1.12)
    elif act == "asset":                                 # from search results / library / an uploaded file
        a = b["asset"]
        path = Path(a["path"]).resolve()
        if not (inside(path, WS, *LIB.values(), ROOT / "autoedit_out") or known_asset(path)) or not path.is_file():
            raise HTTPException(400, "Fichier non autorisé")
        kind = "image" if path.suffix.lower() in IMAGE_EXT else "video"
        asset = {k: v for k, v in a.items() if k in ("credit", "license", "source", "query", "in", "max_len", "dur",
                                                     "motion", "crop_x", "match")}
        asset.update(path=str(path), kind=kind)
        asset.setdefault("source", "manual")
        asset.setdefault("credit", "")
        s.update(kind="B", asset=asset, **{"in": float(a.get("in") or 0.0)})
        if b.get("query"):
            s["query"] = b["query"]
    else:
        raise HTTPException(400, "action inconnue")
    d["dirty"] = True
    e.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return short(slug, n)


@app.post("/api/shorts/{slug}/{n}/caption")
async def edit_caption(slug: str, n: int, req: Request):
    b = await req.json()
    e = edl_path(slug, n)
    d = json.loads(e.read_text(encoding="utf-8"))
    ch = chunks_of(d["words"])
    k = int(b["chunk"])
    if not 0 <= k < len(ch):
        raise HTTPException(404)
    c = ch[k]
    old = d["words"][c["i0"]:c["i1"] + 1]
    toks = str(b.get("text", "")).split()
    if not toks:
        raise HTTPException(400, "Texte vide")
    t0, t1 = old[0]["start"], old[-1]["end"]
    step = (t1 - t0) / len(toks)
    new = [{"word": w, "start": round(t0 + j * step, 3), "end": round(t0 + (j + 1) * step, 3)} for j, w in enumerate(toks)]
    d["words"][c["i0"]:c["i1"] + 1] = new
    d["dirty"] = True
    e.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return short(slug, n)


@app.post("/api/shorts/{slug}/{n}/hook")
async def edit_hook(slug: str, n: int, req: Request):
    """On-screen hook title of the first seconds (empty = none)."""
    b = await req.json()
    e = edl_path(slug, n)
    d = json.loads(e.read_text(encoding="utf-8"))
    d["hook"] = " ".join(str(b.get("text", "")).split())[:90]
    d["dirty"] = True
    e.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return short(slug, n)


@app.post("/api/shorts/{slug}/{n}/rerender")
def rerender(slug: str, n: int):
    e = edl_path(slug, n)
    d = json.loads(e.read_text(encoding="utf-8"))
    d["dirty"] = False
    e.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    job = new_job("rerender", f"{d.get('title') or slug} — re-rendu",
                  [sys.executable, "-m", "autoedit", "--rerender", str(e)], {"slug": slug, "n": n})
    return public(job)


@app.post("/api/assets")
async def upload_asset(file: UploadFile = File(...)):
    ext = Path(file.filename or "x.mp4").suffix.lower()
    if ext not in VIDEO_EXT | IMAGE_EXT:
        raise HTTPException(400, "Vidéo ou image attendue")
    dest = ASSETS / f"{uuid.uuid4().hex[:8]}_{re.sub(r'[^A-Za-z0-9._-]+', '_', file.filename)[-60:]}"
    with open(dest, "wb") as fh:
        shutil.copyfileobj(file.file, fh, 1 << 20)
    return {"path": str(dest), "kind": "image" if ext in IMAGE_EXT else "video", "source": "upload",
            "credit": "", "name": file.filename}


# ------------------------------------------------------------------ B-roll search (second lane)
SEARCHES: dict[str, dict] = {}
SEARCH_LOCK = threading.Lock()


def _search(sid: str, query: str, photos: bool):
    s = SEARCHES[sid]
    with SEARCH_LOCK:                                   # one CLIP search at a time (memory)
        s["status"] = "running"
        cmd = [sys.executable, "-m", "autoedit.search", query, "--cache", str(OUT / "_broll_cache")]
        if photos:
            cmd.append("--photos")
        try:
            p = subprocess.run(cmd, cwd=ROOT, env=sub_env(), capture_output=True, text=True, timeout=900)
            m = re.search(r"@@RESULT@@(.*)$", p.stdout, re.M)
            s["results"] = json.loads(m.group(1)) if m else []
            s["log"] = [l for l in p.stdout.splitlines() if l.startswith("[autoedit")][-30:]
            s["status"] = "done"
        except Exception as e:
            s.update(status="failed", error=str(e), results=[])


@app.post("/api/search")
async def search(req: Request):
    b = await req.json()
    q = str(b.get("query", "")).strip()
    if not q:
        raise HTTPException(400, "Recherche vide")
    sid = uuid.uuid4().hex[:8]
    SEARCHES[sid] = {"id": sid, "query": q, "status": "queued", "results": []}
    threading.Thread(target=_search, args=(sid, q, bool(b.get("photos"))), daemon=True).start()
    return SEARCHES[sid]


@app.get("/api/search/{sid}")
def search_status(sid: str):
    if sid not in SEARCHES:
        raise HTTPException(404)
    return SEARCHES[sid]


# ------------------------------------------------------------------ library
@app.get("/api/library")
def library():
    out = {}
    for kind, d in LIB.items():
        exts = (VIDEO_EXT | IMAGE_EXT) if kind == "broll" else AUDIO_EXT
        out[kind] = [{"name": p.name, "path": str(p), "size": p.stat().st_size,
                      "kind": "image" if p.suffix.lower() in IMAGE_EXT else ("audio" if kind == "music" else "video"),
                      "url": f"/libmedia/{kind}/{p.name}"}
                     for p in sorted(d.iterdir()) if p.is_file() and p.suffix.lower() in exts]
    return out


@app.post("/api/library/{kind}")
async def library_upload(kind: str, files: list[UploadFile] = File(...)):
    if kind not in LIB:
        raise HTTPException(404)
    exts = (VIDEO_EXT | IMAGE_EXT) if kind == "broll" else AUDIO_EXT
    for f in files:
        name = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(f.filename).name)
        if Path(name).suffix.lower() not in exts:
            raise HTTPException(400, f"Format non supporté : {f.filename}")
        with open(LIB[kind] / name, "wb") as fh:
            shutil.copyfileobj(f.file, fh, 1 << 20)
    return library()


@app.delete("/api/library/{kind}/{name}")
def library_delete(kind: str, name: str):
    if kind not in LIB:
        raise HTTPException(404)
    p = (LIB[kind] / name).resolve()
    if inside(p, LIB[kind]) and p.is_file():
        p.unlink()
    return library()


# ------------------------------------------------------------------ settings
EDITABLE = ["brand", "count", "min_dur", "max_dur", "target_dur", "whisper_model", "language", "llm",
            "cold_open", "loop_ending", "hook_title", "min_virality", "whisper_model_arabic", "intro_punch",
            "broll_sources", "photo_fallback", "music_db_under_voice", "lut_mix", "sharpen", "montage_dur"]


@app.get("/api/settings")
def get_settings():
    from autoedit.config import Config
    cfg = Config.load(CONFIG if CONFIG.exists() else None)
    s = secrets()
    return {"config": {k: getattr(cfg, k) for k in EDITABLE},
            "keys": {k: bool(s.get(k)) for k in ("pexels", "pixabay", "anthropic")},
            "workspace": str(WS)}


@app.put("/api/settings")
async def put_settings(req: Request):
    b = await req.json()
    data = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    for k, v in (b.get("config") or {}).items():
        if k in EDITABLE:
            data[k] = v
    data.setdefault("broll_dirs", ["broll"])
    data.setdefault("music_dirs", ["music"])
    CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    keys = b.get("keys") or {}
    if keys:
        s = secrets()
        for k in ("pexels", "pixabay", "anthropic"):
            if k in keys:
                if keys[k]:
                    s[k] = keys[k]
                else:
                    s.pop(k, None)
        SECRETS.write_text(json.dumps(s), encoding="utf-8")
        try:
            os.chmod(SECRETS, 0o600)
        except OSError:
            pass
    return get_settings()


@app.get("/api/health")
def health():
    from autoedit import vision
    return {"ffmpeg": bool(shutil.which("ffmpeg")), "libass": bool(shutil.which("ffmpeg")) and has_libass(),
            "vision": vision.available(),
            "deno_or_node": bool(shutil.which("deno") or shutil.which("node")),
            "queue": sum(1 for j in JOBS.values() if j["status"] in ("queued", "running"))}


@app.exception_handler(HTTPException)
async def http_err(_, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
