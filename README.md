# Quant Radar — quant internship & new-grad tracker

A site that looks and works like earlycareerradar.com, but only for quant roles.
It pulls internship **and** new-grad postings from every source it can reach, dedupes
and classifies them, and lets anyone filter, save, mark applied, or hide roles — with a
direct **Apply →** link on each one.

The scraper runs on GitHub Actions every 6 hours and the site is served by GitHub Pages,
so the link you share stays up to date with nothing running on your laptop.

## Run it locally

```bash
cd ~/Internship_Scraper
python3 -m venv .venv && source .venv/bin/activate     # first time only
pip install -r requirements.txt                       # first time only
python3 main.py                                       # scrape, then open http://127.0.0.1:8000
python3 main.py --no-scrape                           # just open the site
python3 scraper.py -v                                 # scrape only, per-source summary
```

## Tags on every role

* **Level**: `Internship` or `New Grad`. Internships also show eligibility when the
  posting states it — `Internship · Undergrad`, `Internship · Master's`, `Internship · PhD`.
* **Role**: Quant Trading, Quant Research, Quant Dev, Software Eng, Data & ML,
  Hardware/FPGA, Finance/Ops.
* **New**: first seen in the last 48 h. **Closed**: pulled from the firm's board
  (still listed under *All roles*).

## Where the listings come from

| Source type | What | Notes |
|---|---|---|
| Company job boards | 48 quant firms with a public Greenhouse / Lever / Ashby feed (Jane Street, HRT, Optiver, IMC, DRW, Jump, Akuna, Five Rings, Tower, CTC, Point72, Qube, Squarepoint, Virtu, AQR, WorldQuant, Voleon, …) | Best — post date + description |
| Firm careers pages | D. E. Shaw, Two Sigma, Citadel, SIG, XTX, G-Research, Radix, Headlands, Wolverine, Millennium, BAM, Bridgewater, … | Best-effort HTML; JS-rendered pages yield nothing |
| GitHub lists | Simplify (Summer 2027 + New Grad), Northwestern Quant 2027, vanshb03 (Summer 2027 + New Grad 2027) | Covers firms without a feed |
| LinkedIn | Public guest search, several quant queries, last 30 days | Rate-limited; empty = try later |

Everything is in `config.py`. To add a firm, find its board slug in the careers URL
(`boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`, `jobs.ashbyhq.com/<slug>`)
and add `("Firm name", "slug")` to the matching list. Push, and the next run picks it up.

## How classification works

* **Internship** — title/department says intern, internship, summer analyst, co-op,
  placement, winternship, "Summer 2027", campus, student.
* **New Grad** — new grad, graduate program/scheme, entry level, early career,
  campus hire, "class of 2027", analyst program, junior trader/quant/dev, trainee.
  Senior/lead/manager/"N+ years" titles are dropped. Curated new-grad lists are trusted.
* **Quant-relevant** — company-site sources are always kept (only quant firms are
  registered); GitHub/LinkedIn rows are kept if the company is a known quant/finance
  firm or the title mentions quant, trading, market making, systematic, HFT, …
* **Dedupe** — the same posting via different URLs (company site, Greenhouse board,
  Simplify link) collapses to one; same company + title + city across sources merges.

## Files

```
scraper.py    runs all sources, classifies, merges into jobs.db, writes docs/jobs.json
sources.py    one fetcher per source type
config.py     firm registry, keyword rules, location hubs
db.py         SQLite state (first_seen / last_seen / active) — committed so history persists
main.py       local runner: scrape + serve docs/
docs/         the site (index.html, styles.css, main.js, jobs.json) — served by GitHub Pages
.github/workflows/scrape.yml   the 6-hourly refresh
```
