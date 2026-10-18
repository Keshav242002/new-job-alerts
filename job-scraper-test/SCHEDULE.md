# Pipeline schedule

Two runs a day on GitHub Actions (IST = UTC+5:30). GitHub's own cron is best-effort (runs
start hours late or not at all), so the **primary trigger is cron-job.org** calling
`workflow_dispatch` on `.github/workflows/pipeline.yml` with `run=morning` / `run=evening`;
the `run` input decides the sources.

| Run | Primary (cron-job.org) | Backup GitHub cron (UTC) | Sources |
|---|---|---|---|
| Morning | 08:45 IST, `run=morning` | 10:45 IST, `15 5 * * *` | LinkedIn (jobdrop), Naukri (jobspy, best-effort), Wellfound, ATS (Greenhouse/Lever/Ashby, best-effort), freehire (best-effort) |
| Evening | 18:45 IST, `run=evening` | 20:45 IST, `15 15 * * *` | LinkedIn (jobdrop), Wellfound (incremental), ATS (best-effort), freehire (best-effort) |

The backup crons start with a guard: if a successful run of the same type (run title
`morning`/`evening`, or `backup …`) finished in the last 6 hours, the backup exits as success
without scraping — so Naukri never runs twice. The concurrency group queues overlapping
runs instead of running them together. Test dispatches with `sources` set are titled
`… (test)` and don't count for the guard.

Trigger (token: fine-grained, this repo only, Actions: read and write; 204 = accepted):

```
curl -X POST https://api.github.com/repos/Keshav242002/new-job-alerts/actions/workflows/pipeline.yml/dispatches \
  -H "Accept: application/vnd.github+json" -H "Authorization: Bearer $TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" -d '{"ref":"main","inputs":{"run":"morning"}}'
```

**freehire** (`freehire.py`, on/off: `config.FREEHIRE_ENABLED`) — keyless freehire.me search API over
company ATS boards. 8 queries (`config.FREEHIRE_QUERIES`, some title-only or category-limited) × 2 passes (India; worldwide remote, kept only if
open to India), up to 3 pages of 50, 1 s between requests, 20 s timeout, one retry on 429/5xx. Telegram
posts and senior+ seniority are excluded at the API. When the description states no experience,
freehire's AI estimate fills `min_exp` (flag `exp_estimated`).

Removed (code kept, re-enable in `config.PROD_SOURCES`): **Indeed** (removed 2026-10-14) and
**Google Jobs** (Google CAPTCHAs the Actions runner at volume).

GitHub may start scheduled runs late (minutes, occasionally longer) under load.

## Fetch window

Per source, tracked in `state/last_success.json` (`window.py`):

- first run of a source: 72h (ATS: 30 days — postings stay live for weeks)
- afterwards: time since that source's last successful run, minimum 24h

So LinkedIn, Wellfound and ATS use 24h at both runs (≈10h/14h gaps are below the minimum,
so runs overlap — `seen_jobs.csv` removes repeats), and Naukri uses 24h from morning to morning.
A missed run widens the next window automatically.

Per-source pacing:

- **LinkedIn** — 22 queries (11 terms × India, Remote), sequential, 25–45 s apart; 300 s per
  query. Each query fetches 25 job descriptions (~2.5 min); after 270 s it stops fetching
  descriptions and keeps the jobs it has (those rows have no description) rather than being
  killed. 429s back off 60/120/240 s.
- **Naukri** — morning only, 66 queries (11 terms × India, Bangalore, Gurugram, Noida, Pune,
  Hyderabad), 20–40 s apart; stops for the day after 2 consecutive 406 (recaptcha) responses.

How the window is applied:

| Source | At fetch | In process.py |
|---|---|---|
| LinkedIn | `hours_old = window` | 14-day age filter (day granularity) |
| Naukri | no `hours_old` (relevance order) | 14-day age filter, Naukri-ID date when no date |
| Wellfound | not filterable (pages aren't date-sorted) | 14-day age filter on `liveStartAt` |
| ATS | APIs return all live postings | 14-day age filter on Greenhouse `first_published` (else `updated_at`, flagged `date_approx`), Lever `createdAt`, Ashby `publishedAt` |
| freehire | `posted_within_days=14` (fixed, not the window) | 14-day age filter on `posted_at` |

Posting age: `process.py` excludes jobs posted more than **14 days** ago
(`config.MAX_POSTING_AGE_DAYS`, all sources, reason `older_than_14d`) — the fetch window
only decides what is fetched; `seen_jobs.csv` stops repeats.

## Wellfound mode

`run_wellfound.py --mode auto`: **full** on Sundays (IST) — up to 10 pages per
role/location; otherwise **incremental** — up to 5 pages. Pages aren't date-ordered, so
paging never stops on already-seen ids; it stops early only when a page returns no jobs.
The evening run is always incremental (the Sunday full sweep runs once, in the morning).

## Actions jobs per run

Sources per run (each runs as a parallel process inside the single `pipeline` job):

| Source | Morning | Evening |
|---|---|---|
| `linkedin` (jobdrop venv) | ✓ | ✓ |
| `naukri` (jobspy venv) | ✓ | – |
| `wellfound` (requests only) | ✓ | ✓ (incremental) |
| `ats` — boards in `companies.json` (requests only) | ✓ | ✓ |
| `freehire` — freehire.me search API (requests only) | ✓ | ✓ |

All sources run as parallel processes in **one** Actions job (`pipeline.py`), so no data
leaves the runner except to the private data repo.

Failure handling (a source fails when <50% of its queries are ok/empty):

- **LinkedIn or Wellfound** failing fails the workflow (GitHub emails you) after data and
  `runs/latest.md` are pushed.
- **Naukri, ATS and freehire are best-effort**: their failures are listed in `runs/latest.md`
  ("Failed best-effort sources") but don't fail the run.
- A failed data push, or a bad/expired token, fails with "DATA_REPO_TOKEN expired or invalid".
  Each run logs the token's expiry date and warns when fewer than 14 days remain.

`runs/latest.md` shows per-source query statuses, rows, kept/new, 429s, runtime and
`total_run_min` (wall clock including delays and backoff).
