# Coverage & phone alerts

## Which companies are covered

Three layers, so "every company that posts a tech / AI / quant role" is the goal rather than a
hand-picked list:

1. **Static boards** in `config.py` — the quant firms + 33 tech companies, polled every 15 min
   with full descriptions.
2. **Auto-discovered boards** in `boards_auto.json` — every company whose apply link in the
   Simplify / vanshb03 / Northwestern lists points at an ATS with a public API (Greenhouse,
   Lever, Ashby, Workday, SmartRecruiters, Workable). Currently ~390 boards (Nvidia, AMD,
   Adobe, Tesla, TikTok, Amex, Moderna, P&G, …); discovery re-runs on every 6-hour pass and the
   list only grows. Once a company is in here, its *new* postings are caught directly from its
   board every 15 min — you're no longer waiting on the list maintainers.
3. **Aggregator lists + LinkedIn** — catches the rest (iCIMS, Oracle, Eightfold and custom
   career sites we can't poll directly).

Add a board by hand: append to `GREENHOUSE` / `LEVER` / `ASHBY` in `config.py`, or add an
entry to `boards_auto.json`.

## Schedule

The workflow runs in two modes:

* **every 15 minutes** — quick pass over all ~470 company job boards + GitHub lists, then a
  push notification for anything new (this is the "instant" path; GitHub sometimes delays
  scheduled runs by a few minutes at peak, so expect 5–20 min from posting to phone)
* **every 6 hours** — full pass that also hits LinkedIn and firm careers pages and marks
  vanished postings as Closed

Alerts go through [ntfy](https://ntfy.sh) — free, no account.

## Set up (2 minutes)

1. Install the **ntfy** app (iOS App Store / Google Play).
2. In the app tap **+** / *Subscribe to topic* and enter a private topic name nobody would
   guess, e.g. `career-radar-akshita-7x3k9q`. (Topic names are the only "password", so make
   it random-ish.)
3. On GitHub: repo → **Settings → Secrets and variables → Actions → New repository secret**
   * Name: `NTFY_TOPIC` · Secret: the topic name from step 2 → **Add secret**
4. Done. The next run that finds something new will ping you. To test right now:
   **Actions → Scrape and publish → Run workflow** (mode `quick`).

Optional: to run locally with alerts, `export NTFY_TOPIC=your-topic` then `python3 scraper.py --quick --alert`.
`python3 alerts.py` sends a single test notification.

## What triggers an alert

Configured in `config.py`:

```python
ALERT_INDUSTRIES = {"Quant / trading"}                        # any new role at a quant firm
ALERT_CATEGORIES = {"Quant Trading", "Quant Research", "Quant Dev"}   # these roles at any company
ALERT_COMPANY_SITE_ONLY_FOR_TECH = True   # tech roles alert only when seen on the firm's own board
```

So by default: every quant-firm posting, every quant-titled posting anywhere, and tech roles
that appear on one of the 33 tech boards we poll directly (Anthropic, Databricks, Roblox, …).
SWE roles that only arrive via the Simplify / vanshb03 lists still show on the site but
don't ping you — set `ALERT_COMPANY_SITE_ONLY_FOR_TECH = False` if you want everything.

Each notification: **Company — Title**, then location · level · role, tap to open the posting,
with an *Apply* and *Open Radar* action button. If a run finds more than 12 new postings at
once (first run, or after an outage) you get one summary instead of a burst.

## Turning it off

Delete the `NTFY_TOPIC` secret, or unsubscribe from the topic in the app.
