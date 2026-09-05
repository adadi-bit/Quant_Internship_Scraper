"""
Push alerts for newly seen postings via ntfy (https://ntfy.sh).

Config (env vars — set as GitHub repo secrets, or export locally):
    NTFY_TOPIC    required. Your private topic name, e.g. quant-radar-x7k2p9
    NTFY_SERVER   optional, default https://ntfy.sh
    NTFY_TOKEN    optional, only if you use a protected topic / self-hosted server
    SITE_URL      optional, link used in the summary notification

Behaviour
  * one notification per new posting (company — title, location, level), tapping
    it opens the posting; a second action button opens the site
  * if a run finds more than MAX_INDIVIDUAL new postings (e.g. the very first
    run, or after a long outage) it sends a single summary instead of spamming
"""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger("alerts")
MAX_INDIVIDUAL = 12


def _cfg():
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    token = os.environ.get("NTFY_TOKEN", "").strip()
    site = os.environ.get("SITE_URL", "").strip()
    return topic, server, token, site


def _post(server, topic, token, *, title, body, click=None, actions=None, tags=None, priority=None):
    headers = {"Title": title.encode("utf-8", "ignore").decode("latin-1", "ignore")}
    if click:
        headers["Click"] = click
    if actions:
        headers["Actions"] = "; ".join(actions)
    if tags:
        headers["Tags"] = ",".join(tags)
    if priority:
        headers["Priority"] = str(priority)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(f"{server}/{topic}", data=body.encode("utf-8"), headers=headers, timeout=15)
    r.raise_for_status()


def send_new_jobs(new_jobs: list[dict]) -> int:
    """Send alerts for `new_jobs` (dicts as stored in the DB). Returns number sent."""
    topic, server, token, site = _cfg()
    if not topic:
        log.info("NTFY_TOPIC not set — skipping alerts (%d new)", len(new_jobs))
        return 0
    if not new_jobs:
        return 0
    jobs = sorted(new_jobs, key=lambda j: (j.get("company", ""), j.get("title", "")))
    try:
        if len(jobs) > MAX_INDIVIDUAL:
            lines = [f"• {j['company']} — {j['title']}" for j in jobs[:25]]
            if len(jobs) > 25:
                lines.append(f"…and {len(jobs) - 25} more")
            _post(server, topic, token,
                  title=f"{len(jobs)} new quant postings",
                  body="\n".join(lines), click=site or None, tags=["chart_with_upwards_trend"])
            return 1
        sent = 0
        for j in jobs:
            level = j.get("level") or ""
            elig = j.get("eligibility") or ""
            bits = [j.get("location") or ", ".join(j.get("hubs") or []) or "Location n/a",
                    level + (f" · {elig}" if elig and elig != "Not specified" else ""),
                    j.get("category") or ""]
            actions = [f"view, Apply, {j['url']}"]
            if site:
                actions.append(f"view, Open Radar, {site}")
            _post(server, topic, token,
                  title=f"{j['company']} — {j['title']}",
                  body=" · ".join(b for b in bits if b),
                  click=j["url"], actions=actions,
                  tags=["new"] if level == "Internship" else ["mortar_board"])
            sent += 1
        return sent
    except Exception as e:
        log.warning("ntfy alert failed: %s", e)
        return 0


if __name__ == "__main__":       # quick test:  NTFY_TOPIC=... python alerts.py
    n = send_new_jobs([{"company": "Test Firm", "title": "Quant Trading Intern", "url": "https://example.com",
                        "location": "New York, NY", "level": "Internship", "eligibility": "Undergrad", "category": "Quant Trading"}])
    print("sent", n)
