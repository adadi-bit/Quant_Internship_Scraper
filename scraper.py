"""
Runs every source, normalises postings, classifies them and merges into the DB.

    python scraper.py            # full refresh, prints a summary
    python scraper.py --quick    # skip LinkedIn + careers pages (fast)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import config
import db
import discover
import sources

log = logging.getLogger("scraper")

_RX = lambda pats: re.compile("|".join(pats), re.I)
INTERN_RE = _RX(config.INTERN_PATTERNS)
QUANT_RE = _RX(config.QUANT_PATTERNS)
EXCL_RE = _RX(config.EXCLUDE_PATTERNS)
CATS = [(name, _RX(p)) for name, p in config.CATEGORY_RULES]
HUBS = [(name, _RX(p)) for name, p in config.HUBS]
SEASON_RE = re.compile(r"\b(summer|spring|fall|autumn|winter)\s*'?((?:20)?\d\d)\b", re.I)
YEAR_RE = re.compile(r"\b(202[5-9])\b")
NEWGRAD_RE = re.compile(r"\b(new grad|graduate program|full[- ]time|experienced|senior|lead|director|vp\b|head of)\b", re.I)


# ------------------------------------------------------------------ helpers
_TRACKING = {"utm_source", "utm_medium", "utm_campaign", "ref", "gh_src", "source", "lever-source", "src"}


def canonical_url(url: str) -> str:
    p = urlparse(url.strip())
    q = [(k, v) for k, v in parse_qsl(p.query) if k not in _TRACKING]
    path = p.path.rstrip("/")
    return urlunparse((p.scheme.lower() or "https", p.netloc.lower(), path, "", urlencode(q), ""))


_GH_ID = re.compile(r"(?:gh_jid=|greenhouse\.io/[^/]+/jobs/)(\d+)")
_LEVER_ID = re.compile(r"lever\.co/[^/]+/([0-9a-f-]{36})")
_ASHBY_ID = re.compile(r"ashbyhq\.com/[^/]+/([0-9a-f-]{36})")
_WD_ID = re.compile(r"myworkday(?:jobs|site)\.com/.*?_(R-?\d+|JR\d+|\d{5,})\b")
_LI_ID = re.compile(r"linkedin\.com/jobs/view/(?:[^/]*-)?(\d+)")


def job_id(url: str) -> str:
    """Stable id. The same posting reached via different URLs (company site,
    Greenhouse board, Simplify link with tracking) collapses to one id."""
    for tag, rx in (("gh", _GH_ID), ("lever", _LEVER_ID), ("ashby", _ASHBY_ID), ("wd", _WD_ID), ("li", _LI_ID)):
        m = rx.search(url)
        if m:
            return hashlib.sha1(f"{tag}:{m.group(1)}".encode()).hexdigest()[:16]
    return hashlib.sha1(canonical_url(url).encode()).hexdigest()[:16]


def canonical_company(name: str) -> str:
    n = re.sub(r"[^\w&.,'()+/ -]", "", name or "")          # drop 🔥 and other decorations
    n = re.sub(r"\s+", " ", n.strip())
    low = n.lower()
    for alias, canon in config.COMPANY_ALIASES.items():
        if low == alias or low.startswith(alias + " ") or low.startswith(alias + ","):
            return canon
    return n or "Unknown"


NEWGRAD_PAT = _RX(config.NEWGRAD_PATTERNS)
SENIOR_RE = re.compile(r"\b(senior|sr\.?|lead|principal|staff|director|head of|vp|vice president|manager|experienced|mid[- ]level|\d\+? ?years?)\b", re.I)


def level_of(title: str, department: str = "", hint: str | None = None) -> str | None:
    """'Internship' | 'New Grad' | None (not early-career, or excluded)."""
    hay = f"{title} {department}"
    if EXCL_RE.search(title):
        return None
    if re.search(r"\bintern", title, re.I) or (INTERN_RE.search(hay) and not NEWGRAD_PAT.search(title)):
        return "Internship"
    if SENIOR_RE.search(title):
        return None
    if NEWGRAD_PAT.search(hay):
        return "New Grad"
    if hint == "New Grad":            # curated new-grad list: trust it
        return "New Grad"
    if hint == "Internship":
        return "Internship"
    return None


TECH_ROLE_CATS = {"Quant Trading", "Quant Research", "Quant Dev", "Software Eng", "Data & ML", "Hardware/FPGA"}


def is_relevant(company: str, title: str, department: str, source_type: str, category: str) -> bool:
    """SWE / AI / quant / hardware roles anywhere; any role at a quant firm or bank quant desk."""
    if source_type == "Company site":
        return True
    if category in TECH_ROLE_CATS:
        return True
    c = (company or "").lower()
    if any(n in c for n in config.QUANT_FIRM_NAMES if len(n) > 3):
        return True
    return bool(QUANT_RE.search(f"{title} {department}"))


def categorize(title: str, department: str) -> str:
    hay = f"{title} {department}"
    for name, rx in CATS:
        if rx.search(hay):
            return name
    return "Other"


def hubs_for(location: str) -> list[str]:
    loc = location or ""
    found = []
    for name, rx in HUBS:
        if rx.search(loc):
            found.append(name)
    us_specific = [h for h in found if h not in ("Other US", "Remote") and h in
                   {"New York", "Chicago", "Bay Area", "Boston", "Connecticut", "Philadelphia",
                    "Austin", "Miami", "Houston", "Los Angeles", "Seattle"}]
    if us_specific and "Other US" in found:
        found.remove("Other US")
    return found or (["Not specified"] if not loc.strip() else ["Other"])


def eligibility(title: str, desc: str) -> str:
    t = title.lower()
    d = (desc or "").lower()
    if re.search(r"\bph\.?d\b|doctoral", t):
        return "PhD"
    if re.search(r"\b(master'?s?|msc|ms\b|mfe|graduate students?)\b", t):
        return "Master's"
    if re.search(r"\b(undergrad|bachelor|sophomore|junior|freshman|first[- ]year|second[- ]year|penultimate)\b", t):
        return "Undergrad"
    if re.search(r"\bph\.?d\b", d) and not re.search(r"\b(undergrad|bachelor|sophomore|junior)\b", d):
        return "PhD"
    if re.search(r"\b(sophomore|freshman|first[- ]year|second[- ]year)\b", d):
        return "Undergrad (early)"
    if re.search(r"\b(undergrad|bachelor|junior|penultimate)\b", d):
        return "Undergrad"
    if re.search(r"\b(master'?s?|msc|mfe)\b", d):
        return "Master's"
    return "Not specified"


def work_mode(title: str, desc: str, location: str) -> str:
    hay = f"{title} {location} {desc[:1500] if desc else ''}".lower()
    if "hybrid" in hay:
        return "Hybrid"
    if re.search(r"\bremote\b", hay):
        return "Remote"
    if re.search(r"\b(in[- ]person|on[- ]site|onsite|in[- ]office)\b", hay):
        return "In person"
    return "Not specified"


def season(title: str, desc: str) -> str:
    for hay in (title, desc or ""):
        m = SEASON_RE.search(hay)
        if m:
            yr = m.group(2)
            yr = yr if len(yr) == 4 else "20" + yr
            return f"{m.group(1).title()} {yr}"
    m = YEAR_RE.search(title)
    if m:
        return m.group(1)
    return "Not specified"


def normalise(raw: dict) -> dict | None:
    title = (raw.get("title") or "").strip()
    url = raw.get("url")
    if not title or not url or not url.startswith("http"):
        return None
    dept = raw.get("department") or ""
    level = level_of(title, dept, raw.get("level_hint"))
    if not level:
        return None
    category = categorize(title, dept)
    if not is_relevant(raw.get("company", ""), title, dept, raw.get("source_type", ""), category):
        return None
    desc = raw.get("description") or ""
    loc = raw.get("location") or ""
    company = canonical_company(raw.get("company"))
    return {
        "id": job_id(url),
        "company": company,
        "industry": config.industry_of(company),
        "title": title,
        "url": url,
        "location": loc,
        "hubs": hubs_for(loc),
        "category": category,
        "level": level,
        "eligibility": eligibility(title, desc),
        "work_mode": work_mode(title, desc, loc),
        "season": season(title, desc),
        "posted_at": raw.get("posted_at"),
        "description": desc[:2500],
        "source": raw.get("source", ""),
        "source_type": raw.get("source_type", ""),
        "closed": bool(raw.get("closed")),
    }


# --------------------------------------------------------------------- run
def collect(quick: bool = False, progress=None) -> tuple[list[dict], dict]:
    tasks = []
    for name, slug in config.GREENHOUSE:
        tasks.append((f"Greenhouse · {name}", sources.fetch_greenhouse, (name, slug)))
    for name, slug in config.LEVER:
        tasks.append((f"Lever · {name}", sources.fetch_lever, (name, slug)))
    for name, slug in config.ASHBY:
        tasks.append((f"Ashby · {name}", sources.fetch_ashby, (name, slug)))
    for name, url, kind, level in config.GITHUB_LISTS:
        tasks.append((f"GitHub · {name}", sources.fetch_github_list, (name, url, kind, level)))
    # auto-discovered boards (boards_auto.json) — every company the aggregator lists have ever linked
    auto = discover.load()
    for slug, name in auto.get("greenhouse", {}).items():
        tasks.append((f"Greenhouse · {name}", sources.fetch_greenhouse, (name, slug, False)))
    for slug, name in auto.get("lever", {}).items():
        tasks.append((f"Lever · {name}", sources.fetch_lever, (name, slug)))
    for slug, name in auto.get("ashby", {}).items():
        tasks.append((f"Ashby · {name}", sources.fetch_ashby, (name, slug)))
    for key, name in auto.get("workday", {}).items():
        host, site = key.split("/", 1)
        tasks.append((f"Workday · {name}", sources.fetch_workday, (name, host, site)))
    for slug, name in auto.get("smartrecruiters", {}).items():
        tasks.append((f"SmartRecruiters · {name}", sources.fetch_smartrecruiters, (name, slug)))
    for slug, name in auto.get("workable", {}).items():
        tasks.append((f"Workable · {name}", sources.fetch_workable, (name, slug)))
    if not quick:
        for name, url in config.HTML_PAGES:
            tasks.append((f"Careers page · {name}", sources.fetch_html_page, (name, url)))
        for kw, loc in config.LINKEDIN_QUERIES:
            tasks.append((f"LinkedIn · {kw} ({loc})", sources.fetch_linkedin, (kw, loc)))

    stats, jobs, done = {}, {}, 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(fn, *args): label for label, fn, args in tasks}
        for fut in as_completed(futs):
            label = futs[fut]
            done += 1
            try:
                raws = fut.result()
            except Exception as e:           # belt and braces
                log.warning("%s crashed: %s", label, e)
                raws = []
            kept = 0
            for raw in raws:
                j = normalise(raw)
                if not j:
                    continue
                prev = jobs.get(j["id"])
                if prev is None or _better(j, prev):
                    if prev is not None:
                        # better source wins; only fill gaps from the other record
                        j["posted_at"] = j["posted_at"] or prev["posted_at"]
                        j["description"] = j["description"] or prev["description"]
                    jobs[j["id"]] = j
                kept += 1
            stats[label] = {"fetched": len(raws), "kept": kept}
            if progress:
                progress(done, len(tasks), label, len(raws), kept)
    return _dedupe_similar(list(jobs.values())), stats


def _dedupe_similar(jobs: list[dict]) -> list[dict]:
    """Same company + same title + same hubs reached via two different URLs
    (e.g. a GitHub list linking the Greenhouse board while the company site
    links its own wrapper page). Keep the best-sourced one, note the other URL."""
    by_key: dict[tuple, dict] = {}
    for j in sorted(jobs, key=lambda x: {"Company site": 0, "GitHub list": 1, "Job board": 2}.get(x["source_type"], 9)):
        key = (j["company"].lower(), re.sub(r"[^a-z0-9]+", " ", j["title"].lower()).strip(), tuple(sorted(j["hubs"])))
        if key in by_key:
            keep = by_key[key]
            keep["posted_at"] = keep["posted_at"] or j["posted_at"]
            keep["description"] = keep["description"] or j["description"]
            if j["source"] not in keep["source"]:
                keep["source"] += f" · also {j['source']}"
            continue
        by_key[key] = j
    return list(by_key.values())


def _better(new: dict, old: dict) -> bool:
    """Prefer company-site records over aggregator records for the same URL."""
    rank = {"Company site": 0, "GitHub list": 1, "Job board": 2}
    return rank.get(new["source_type"], 9) < rank.get(old["source_type"], 9)


DOCS = Path(__file__).parent / "docs"


def export_json(summary: dict | None = None) -> Path:
    """Write docs/jobs.json — the static site's only data file."""
    DOCS.mkdir(exist_ok=True)
    jobs = db.all_jobs(include_inactive=True)
    for j in jobs:                                   # keep the site's data file small
        j["description"] = (j.get("description") or "")[:500]
    last = dict(summary or db.last_run() or {})
    last.pop("new_ids", None)
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "last_run": last, "jobs": jobs}
    out = DOCS / "jobs.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return out


def should_alert(j: dict) -> bool:
    if j.get("industry") in config.ALERT_INDUSTRIES:
        return True
    if j.get("category") in config.ALERT_CATEGORIES:
        return True
    if config.ALERT_COMPANY_SITE_ONLY_FOR_TECH:
        return j.get("source_type") == "Company site"
    return True


def refresh(quick: bool = False, progress=None, alert: bool = False) -> dict:
    if not quick:
        try:                                   # grow the board list from the aggregator lists
            _, added = discover.discover(discover.rows_from_lists())
            if added:
                log.warning("discovered %d new boards: %s", len(added), ", ".join(added[:10]))
        except Exception as e:
            log.warning("discovery failed: %s", e)
    jobs, stats = collect(quick=quick, progress=progress)
    had_data = db.count_jobs() > 0
    summary = db.upsert_jobs(jobs, full_run=not quick)
    summary["sources"] = stats
    summary["ran_at"] = datetime.now(timezone.utc).isoformat()
    db.record_run(summary)
    export_json({k: v for k, v in summary.items() if k != "sources"})
    if alert and had_data and summary.get("new_ids"):
        import alerts
        new_jobs = [j for j in jobs if j["id"] in set(summary["new_ids"]) and should_alert(j) and not j.get("closed")]
        summary["alerts_sent"] = alerts.send_new_jobs(new_jobs)
    summary.pop("new_ids", None)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip LinkedIn + careers pages")
    ap.add_argument("--alert", action="store_true", help="push new postings to ntfy (needs NTFY_TOPIC)")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO if a.v else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    def prog(done, total, label, fetched, kept):
        print(f"[{done:>2}/{total}] {label:<55} {fetched:>4} fetched  {kept:>3} internships", file=sys.stderr)

    s = refresh(quick=a.quick, progress=prog, alert=a.alert)
    print(f"\n{s['total_active']} active roles ({s['new']} new, {s['reactivated']} back, {s['closed']} closed this run)"
          + (f" · {s['alerts_sent']} alert(s) sent" if "alerts_sent" in s else ""))
