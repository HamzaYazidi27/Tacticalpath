"""python -m webui  →  starts autoedit Studio on http://127.0.0.1:8765 and opens the browser."""
import argparse
import threading
import webbrowser

import uvicorn


def main():
    ap = argparse.ArgumentParser(prog="webui", description="autoedit Studio — local web interface")
    ap.add_argument("--host", default="127.0.0.1", help="127.0.0.1 = this computer only (default)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    url = f"http://{'127.0.0.1' if a.host in ('0.0.0.0', '::') else a.host}:{a.port}"
    if a.host not in ("127.0.0.1", "localhost"):
        print("⚠ Studio reachable from your network — it has no login: use only on a trusted network.")
    if not a.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"autoedit Studio → {url}   (Ctrl+C to stop)")
    uvicorn.run("webui.server:app", host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
