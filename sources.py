"""
Fetchers. Every fetcher returns a list of raw dicts with (at least):
    company, title, url, location, posted_at (ISO str or None),
    description (plain text or ""), source (str), source_type (str)
Everything else (categories, hubs, eligibility ...) is derived in scraper.py.
Fetchers never raise — a failing source logs and returns [].
"""
from __future__ import annotations

import html as htmlmod
import logging
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

import config

log = logging.getLogger("sources")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
for _p in ("https://", "http://"):
    SESSION.mount(_p, requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20))
TIMEOUT = 20


def _get(url, **kw):
    r = SESSION.get(url, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def _text(html_str: str) -> str:
    if not html_str:
        return ""
    soup = BeautifulSoup(htmlmod.unescape(html_str), "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def _iso(dt) -> str | None:
    if not dt:
        return None
    if isinstance(dt, (int, float)):
        return datetime.fromtimestamp(dt / 1000, tz=timezone.utc).date().isoformat()
    try:
        return datetime.fromisoformat(str(dt).replace("Z", "+00:00")).date().isoformat()
    except Exception:
        return None


# ----------------------------------------------------------------- Greenhouse
def fetch_greenhouse(company: str, slug: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        jobs = _get(url).json().get("jobs", [])
    except Exception as e:
        log.warning("greenhouse %s failed: %s", slug, e)
        return []
    out = []
    for j in jobs:
        depts = " ".join(d.get("name", "") for d in j.get("departments", []) or [])
        offices = " | ".join(o.get("name", "") for o in j.get("offices", []) or [])
        loc = (j.get("location") or {}).get("name") or offices
        out.append({
            "company": company,
            "title": j.get("title", "").strip(),
            "url": j.get("absolute_url"),
            "location": loc,
            "posted_at": _iso(j.get("first_published") or j.get("updated_at")),
            "description": _text(j.get("content", ""))[:4000],
            "department": depts,
            "source": f"Greenhouse · {company}",
            "source_type": "Company site",
        })
    return out


# ---------------------------------------------------------------------- Lever
def fetch_lever(company: str, slug: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        jobs = _get(url).json()
    except Exception as e:
        log.warning("lever %s failed: %s", slug, e)
        return []
    out = []
    for j in jobs:
        cats = j.get("categories", {}) or {}
        out.append({
            "company": company,
            "title": j.get("text", "").strip(),
            "url": j.get("hostedUrl"),
            "location": " | ".join(filter(None, [cats.get("location")] + (j.get("allLocations") or []))),
            "posted_at": _iso(j.get("createdAt")),
            "description": (j.get("descriptionPlain") or _text(j.get("description", "")))[:4000],
            "department": " ".join(filter(None, [cats.get("team"), cats.get("department"), cats.get("commitment")])),
            "source": f"Lever · {company}",
            "source_type": "Company site",
        })
    return out


# ---------------------------------------------------------------------- Ashby
def fetch_ashby(company: str, slug: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        jobs = _get(url).json().get("jobs", [])
    except Exception as e:
        log.warning("ashby %s failed: %s", slug, e)
        return []
    out = []
    for j in jobs:
        locs = [j.get("location")] + [s.get("location") for s in j.get("secondaryLocations", []) or []]
        if j.get("isRemote"):
            locs.append("Remote")
        out.append({
            "company": company,
            "title": j.get("title", "").strip(),
            "url": j.get("jobUrl") or j.get("applyUrl"),
            "location": " | ".join(filter(None, locs)),
            "posted_at": _iso(j.get("publishedAt")),
            "description": _text(j.get("descriptionHtml", ""))[:4000],
            "department": " ".join(filter(None, [j.get("department"), j.get("team"), j.get("employmentType")])),
            "source": f"Ashby · {company}",
            "source_type": "Company site",
        })
    return out


# ------------------------------------------------------------ generic HTML page
_INTERN_RE = re.compile("|".join(config.INTERN_PATTERNS), re.I)


def fetch_html_page(company: str, url: str) -> list[dict]:
    """Pull every anchor whose text looks like an internship posting."""
    try:
        r = _get(url)
    except Exception as e:
        log.warning("html %s failed: %s", company, e)
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        text = re.sub(r"\s+", " ", a.get_text(" ")).strip()
        href = urljoin(url, a["href"])
        if not text or len(text) > 140 or not _INTERN_RE.search(text):
            continue
        if href in seen or href.rstrip("/") == url.rstrip("/"):
            continue
        seen.add(href)
        # try to grab a nearby location string
        parent_txt = _text(str(a.find_parent(["li", "tr", "div", "article"]) or ""))[:300]
        out.append({
            "company": company,
            "title": text,
            "url": href,
            "location": _guess_location(parent_txt.replace(text, "")),
            "posted_at": None,
            "description": parent_txt,
            "department": "",
            "source": f"Careers page · {company}",
            "source_type": "Company site",
        })
    return out


_LOC_WORDS = re.compile(
    r"(New York|NYC|Chicago|London|Amsterdam|Hong Kong|Singapore|Sydney|Austin|Boston|"
    r"San Francisco|Bay Area|Miami|Houston|Greenwich|Stamford|Philadelphia|Bala Cynwyd|"
    r"Dublin|Paris|Zurich|Mumbai|Shanghai|Tokyo|Remote|Los Angeles|Seattle|Denver)", re.I)


def _guess_location(text: str) -> str:
    found = []
    for m in _LOC_WORDS.finditer(text or ""):
        v = m.group(1)
        if v.lower() not in [f.lower() for f in found]:
            found.append(v)
    return " | ".join(found)


# ---------------------------------------------------------------- GitHub lists
def fetch_github_list(name: str, url: str, kind: str, level: str | None = None) -> list[dict]:
    try:
        md = _get(url).text
    except Exception as e:
        log.warning("github list %s failed: %s", name, e)
        return []
    parser = {"simplify": _parse_simplify, "nwquant": _parse_nwquant, "vansh": _parse_vansh}.get(kind)
    rows = parser(md, name) if parser else []
    for r in rows:
        r["level_hint"] = level
    return rows


def _rel_date(s: str) -> str | None:
    """'0d' / '12d' / 'Aug 21' -> ISO date."""
    s = (s or "").strip()
    today = datetime.now(timezone.utc).date()
    m = re.fullmatch(r"(\d+)d", s)
    if m:
        return (today - timedelta(days=int(m.group(1)))).isoformat()
    m = re.fullmatch(r"(\d+)mo", s)
    if m:
        return (today - timedelta(days=30 * int(m.group(1)))).isoformat()
    for fmt in ("%b %d", "%B %d"):
        try:
            d = datetime.strptime(s, fmt).date().replace(year=today.year)
            if d > today:
                d = d.replace(year=today.year - 1)
            return d.isoformat()
        except ValueError:
            pass
    return None


def _parse_simplify(md: str, name: str) -> list[dict]:
    """HTML <table> rows: company | role | location | apply links | age."""
    soup = BeautifulSoup(md, "html.parser")
    out, last_company, section = [], "", ""
    # Track which H2 section each table belongs to (Quant Finance section is gold)
    for el in soup.find_all(["h2", "tr"]):
        if el.name == "h2":
            section = el.get_text(" ").strip()
            continue
        tds = el.find_all("td")
        if len(tds) < 5:
            continue
        comp = tds[0].get_text(" ").strip()
        if comp in ("↳", "") or comp.startswith("↳"):
            comp = last_company
        else:
            last_company = comp
        title = tds[1].get_text(" ").strip()
        title = re.sub(r"[\U0001F1E6-\U0001F1FF\U0001F6C2\U0001F512\U0001F393]|🛂|🇺🇸|🔒|🎓", "", title).strip()
        loc = _clean_loc_cell(str(tds[2]))
        link = None
        for a in tds[3].find_all("a", href=True):
            if "simplify.jobs/p/" in a["href"]:
                continue
            link = a["href"]
            break
        if not link:
            continue
        closed = "🔒" in tds[3].get_text() or "closed" in tds[3].get_text().lower()
        out.append({
            "company": comp,
            "title": title,
            "url": link,
            "location": loc,
            "posted_at": _rel_date(tds[4].get_text().strip()),
            "description": "",
            "department": "Quantitative Finance" if "quant" in section.lower() else section,
            "source": f"GitHub · {name}",
            "source_type": "GitHub list",
            "closed": closed,
        })
    return out


_ROLE_LABELS = {"QT": "Quantitative Trading Intern", "QR": "Quantitative Research Intern",
                "QD": "Quantitative Developer Intern", "SWE": "Software Engineering Intern",
                "HW": "Hardware Engineering Intern", "FPGA": "FPGA Engineering Intern",
                "ML": "Machine Learning Intern", "DevOps/SRE": "DevOps / SRE Intern",
                "QR Fellowship": "Quantitative Research Fellowship"}


def _parse_nwquant(md: str, name: str) -> list[dict]:
    """'## Firm' sections with |Role|Links| tables of [✅ label](url)."""
    out = []
    firm, locs = None, ""
    for line in md.splitlines():
        h = re.match(r"^##\s+(.+?)\s*$", line)
        if h:
            firm, locs = h.group(1).strip(), ""
            continue
        m = re.match(r"^\*\*Locations\*\*:\s*(.*)$", line)
        if m:
            locs = m.group(1).strip()
            continue
        m = re.match(r"^\|([^|]+)\|(.+)\|\s*$", line)
        if m and firm and m.group(1).strip() not in ("Role", "-------"):
            role = m.group(1).strip()
            for lm in re.finditer(r"\[(✅|❌)?\s*([^\]]*)\]\((https?://[^)\s]+)\)", m.group(2)):
                status, label, url = lm.group(1), lm.group(2).strip(), lm.group(3)
                base = _ROLE_LABELS.get(role, f"{role} Intern")
                title = f"{base} ({label})" if label else base
                out.append({
                    "company": firm,
                    "title": title,
                    "url": url,
                    "location": locs.replace(",", " |"),
                    "posted_at": None,
                    "description": "",
                    "department": role,
                    "source": f"GitHub · {name}",
                    "source_type": "GitHub list",
                    "closed": status == "❌",
                })
    return out


def _clean_loc_cell(cell: str) -> str:
    """'<details><summary>**5 locations**</summary>Austin, TX<br>NYC</details>' -> 'Austin, TX | NYC'"""
    s = re.sub(r"<summary>.*?</summary>", "", cell, flags=re.S)
    s = re.sub(r"<br\s*/?>|</?details>|</br>", " | ", s)
    s = re.sub(r"<[^>]+>|\*\*", "", s)
    parts = [p.strip() for p in s.split("|") if p.strip() and "locations" not in p.lower()]
    return " | ".join(dict.fromkeys(parts))


def _parse_vansh(md: str, name: str) -> list[dict]:
    """Markdown pipe table: | Company | Role | Location | <a href=...> | Date |"""
    out, last_company = [], ""
    for line in md.splitlines():
        if not line.startswith("| ") or line.startswith("| Company") or line.startswith("| ---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        comp = re.sub(r"\*\*|\[|\]\(.*?\)", "", cells[0]).strip()
        if comp in ("↳", ""):
            comp = last_company
        else:
            last_company = comp
        title = re.sub(r"🛂|🇺🇸|🔒|🎓", "", cells[1]).strip()
        m = re.search(r'href="([^"]+)"', cells[3])
        if not m:
            continue
        out.append({
            "company": comp,
            "title": title,
            "url": htmlmod.unescape(m.group(1)),
            "location": _clean_loc_cell(cells[2]),
            "posted_at": _rel_date(cells[4]),
            "description": "",
            "department": "",
            "source": f"GitHub · {name}",
            "source_type": "GitHub list",
            "closed": "🔒" in cells[3],
        })
    return out


# ------------------------------------------------------------------- LinkedIn
def fetch_linkedin(keywords: str, location: str, pages: int = 3) -> list[dict]:
    """LinkedIn's public 'guest' job search (no login). f_E=1 = Internship."""
    out = []
    for start in range(0, 25 * pages, 25):
        url = ("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
               f"?keywords={requests.utils.quote(keywords)}&location={requests.utils.quote(location)}"
               f"&f_E=1&f_TPR=r2592000&start={start}")
        try:
            r = _get(url)
        except Exception as e:
            log.warning("linkedin '%s' p%d failed: %s", keywords, start // 25, e)
            break
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("li")
        if not cards:
            break
        for c in cards:
            a = c.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
            t = c.select_one(".base-search-card__title")
            comp = c.select_one(".base-search-card__subtitle")
            loc = c.select_one(".job-search-card__location")
            dt = c.select_one("time")
            if not (a and t):
                continue
            href = a["href"].split("?")[0]
            out.append({
                "company": comp.get_text(" ").strip() if comp else "",
                "title": t.get_text(" ").strip(),
                "url": href,
                "location": loc.get_text(" ").strip() if loc else location,
                "posted_at": (dt.get("datetime") if dt else None),
                "description": "",
                "department": "",
                "source": "LinkedIn",
                "source_type": "Job board",
            })
        if len(cards) < 10:
            break
    return out
