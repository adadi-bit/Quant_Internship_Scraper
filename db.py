"""SQLite storage: jobs, per-job user status (saved/applied/hidden), run log."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "jobs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    company TEXT, title TEXT, url TEXT, location TEXT,
    hubs TEXT, category TEXT, level TEXT, eligibility TEXT, work_mode TEXT, season TEXT,
    posted_at TEXT, description TEXT, source TEXT, source_type TEXT,
    first_seen TEXT, last_seen TEXT, active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS runs (
    ran_at TEXT, summary TEXT
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}
    if "hubs" not in cols or "level" not in cols:   # old schema -> rebuild
        conn.executescript("DROP TABLE jobs;" + SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def upsert_jobs(jobs: list[dict], full_run: bool = True) -> dict:
    conn = connect()
    now = _now()
    existing = {r["id"]: r for r in conn.execute("SELECT id, active, posted_at, description FROM jobs")}
    new = reactivated = 0
    seen_ids = set()
    for j in jobs:
        seen_ids.add(j["id"])
        prev = existing.get(j["id"])
        active = 0 if j.get("closed") else 1
        if prev is None:
            new += 1 if active else 0
            conn.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (j["id"], j["company"], j["title"], j["url"], j["location"], json.dumps(j["hubs"]),
                 j["category"], j["level"], j["eligibility"], j["work_mode"], j["season"], j["posted_at"],
                 j["description"], j["source"], j["source_type"], now, now, active))
        else:
            if active and not prev["active"]:
                reactivated += 1
            conn.execute(
                """UPDATE jobs SET company=?, title=?, url=?, location=?, hubs=?, category=?, level=?, eligibility=?,
                   work_mode=?, season=?, posted_at=COALESCE(?, posted_at), description=CASE WHEN ?='' THEN description ELSE ? END,
                   source=?, source_type=?, last_seen=?, active=? WHERE id=?""",
                (j["company"], j["title"], j["url"], j["location"], json.dumps(j["hubs"]), j["category"], j["level"],
                 j["eligibility"], j["work_mode"], j["season"], j["posted_at"], j["description"], j["description"],
                 j["source"], j["source_type"], now, active, j["id"]))
    closed = 0
    if full_run:
        # anything from a *live* source that vanished this run is closed.
        # (GitHub-list entries have no reliable "gone" signal; leave them.)
        rows = conn.execute("SELECT id FROM jobs WHERE active=1 AND source_type='Company site'").fetchall()
        for r in rows:
            if r["id"] not in seen_ids:
                conn.execute("UPDATE jobs SET active=0 WHERE id=?", (r["id"],))
                closed += 1
    conn.commit()
    total_active = conn.execute("SELECT COUNT(*) FROM jobs WHERE active=1").fetchone()[0]
    conn.close()
    return {"new": new, "reactivated": reactivated, "closed": closed, "total_active": total_active, "scraped": len(jobs)}


def record_run(summary: dict):
    conn = connect()
    conn.execute("INSERT INTO runs VALUES (?,?)", (summary["ran_at"], json.dumps(summary)))
    conn.commit()
    conn.close()


def last_run() -> dict | None:
    conn = connect()
    r = conn.execute("SELECT summary FROM runs ORDER BY ran_at DESC LIMIT 1").fetchone()
    conn.close()
    return json.loads(r[0]) if r else None


def all_jobs(include_inactive: bool = False) -> list[dict]:
    conn = connect()
    q = "SELECT * FROM jobs"
    if not include_inactive:
        q += " WHERE active=1"
    rows = conn.execute(q).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["hubs"] = json.loads(d["hubs"] or "[]")
        d["active"] = bool(d["active"])
        out.append(d)
    return out

