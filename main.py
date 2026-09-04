"""
Run Quant Radar locally.

    python main.py              # scrape everything, write docs/jobs.json, open the site
    python main.py --no-scrape  # just open the site with the current docs/jobs.json
    python main.py --quick      # skip LinkedIn + firm careers pages (fast)

The public version of the site is the same docs/ folder, published by GitHub Pages
and refreshed by the GitHub Actions workflow in .github/workflows/scrape.yml.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import threading
import webbrowser
from pathlib import Path

import scraper

DOCS = Path(__file__).parent / "docs"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-scrape", action="store_true")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()

    if not a.no_scrape:
        print("Refreshing listings (1–2 min the first time)…")
        def prog(done, total, label, fetched, kept):
            print(f"  [{done:>2}/{total}] {label:<50} {kept:>3} roles")
        s = scraper.refresh(quick=a.quick, progress=prog)
        print(f"\n{s['total_active']} active roles · {s['new']} new since last run\n")
    elif not (DOCS / "jobs.json").exists():
        scraper.export_json()

    url = f"http://127.0.0.1:{a.port}"
    print(f"Serving {DOCS} at {url}  (Ctrl+C to stop)")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
    http.server.ThreadingHTTPServer(("127.0.0.1", a.port), handler).serve_forever()
