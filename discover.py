"""
Auto-discover company job boards.

Every apply link in the aggregator lists (Simplify, vanshb03, Northwestern) points at some
ATS. When that ATS has a public API we can poll the *whole board* directly — so a company
only needs to appear in a list once, and from then on every new posting it makes is picked
up within 15 minutes, straight from the source.

Recognised: Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Workable.
State lives in boards_auto.json (committed by the workflow) and only ever grows.

    python discover.py          # refresh boards_auto.json, print what was added
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import config
import sources

BOARDS_FILE = Path(__file__).parent / "boards_auto.json"

PATTERNS = {
    "greenhouse": re.compile(r"greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)"),
    "lever": re.compile(r"jobs\.lever\.co/([A-Za-z0-9_-]+)"),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9_.-]+)"),
    "workday": re.compile(r"https?://([a-z0-9-]+\.wd\d+\.myworkday(?:jobs|site)\.com)/(?:[a-z]{2}-[A-Z]{2}/)?(?:recruiting/[^/]+/)?([A-Za-z0-9_-]+)"),
    "smartrecruiters": re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)"),
    "workable": re.compile(r"apply\.workable\.com/([A-Za-z0-9_-]+)"),
}
_SKIP_SLUGS = {"embed", "job", "jobs", "boards", "api", "en-US", "en"}


def load() -> dict:
    if BOARDS_FILE.exists():
        return json.loads(BOARDS_FILE.read_text())
    return {k: {} for k in PATTERNS}


def _static_keys() -> set[tuple[str, str]]:
    keys = {("greenhouse", s) for _, s in config.GREENHOUSE}
    keys |= {("lever", s) for _, s in config.LEVER}
    keys |= {("ashby", s) for _, s in config.ASHBY}
    return keys


def board_key(ats: str, m: re.Match) -> str:
    if ats == "workday":
        return f"{m.group(1)}/{m.group(2)}"          # host/site
    return m.group(1)


def discover(rows: list[dict]) -> tuple[dict, list[str]]:
    boards = load()
    static = _static_keys()
    added = []
    for r in rows:
        url, company = r.get("url") or "", re.sub(r"[^\w&.,'()+ -]", "", r.get("company") or "").strip()
        if not url or not company or company in ("↳", "Unknown"):
            continue
        for ats, rx in PATTERNS.items():
            m = rx.search(url)
            if not m:
                continue
            key = board_key(ats, m)
            if key in _SKIP_SLUGS or (ats, key) in static:
                break
            if key not in boards.setdefault(ats, {}):
                boards[ats][key] = company
                added.append(f"{ats}:{key} ({company})")
            break
    BOARDS_FILE.write_text(json.dumps(boards, indent=1, sort_keys=True))
    return boards, added


def rows_from_lists() -> list[dict]:
    rows = []
    for name, url, kind, level in config.GITHUB_LISTS:
        rows.extend(sources.fetch_github_list(name, url, kind, level))
    return rows


if __name__ == "__main__":
    boards, added = discover(rows_from_lists())
    total = sum(len(v) for v in boards.values())
    print(f"{total} auto-discovered boards: " + ", ".join(f"{k} {len(v)}" for k, v in boards.items()))
    print(f"{len(added)} new this run" + (":\n  " + "\n  ".join(added[:40]) if added else ""))
