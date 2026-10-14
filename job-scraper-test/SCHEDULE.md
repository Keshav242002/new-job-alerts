# Pipeline schedule

Two runs a day on GitHub Actions (cron is UTC; IST = UTC+5:30).

| Run | IST | cron (UTC) | Sources |
|---|---|---|---|
| Morning | 08:45 | `15 3 * * *` | LinkedIn (jobdrop), Naukri (jobspy), Wellfound, ATS (Greenhouse/Lever/Ashby) |
| Evening | 18:45 | `15 13 * * *` | LinkedIn (jobdrop), Naukri (jobspy) |

Removed (code kept, re-enable in `config.PROD_SOURCES`): **Indeed** (removed 2026-10-14) and
**Google Jobs** (Google CAPTCHAs the Actions runner at volume).

GitHub may start scheduled runs late (minutes, occasionally longer) under load.

## Fetch window

Per source, tracked in `state/last_success.json` (`window.py`):

- first run of a source: 72h (ATS: 30 days — postings stay live for weeks)
- afterwards: time since that source's last successful run, minimum 24h

So LinkedIn/Naukri use 24h at both runs (≈10h/14h gaps are below the minimum, so runs
overlap — `seen_jobs.csv` removes repeats), and Wellfound/ATS use 24h from morning to
morning. A missed run widens the next window automatically.

How the window is applied:

| Source | At fetch | In process.py |
|---|---|---|
| LinkedIn | `hours_old = window` | date filter (day granularity) |
| Naukri | no `hours_old` (relevance order) | date filter, Naukri-ID date when no date |
| Wellfound | not filterable (pages aren't date-sorted) | date filter on `liveStartAt` |
| ATS | APIs return all live postings | date filter on Greenhouse `first_published` (else `updated_at`, flagged `date_approx`), Lever `createdAt`, Ashby `publishedAt` |

## Wellfound mode

`run_wellfound.py --mode auto`: **full** on Sundays (IST) — up to 10 pages per
role/location; otherwise **incremental** — up to 5 pages, stopping at the first page
whose job ids are all already in `seen_jobs.csv`.

## Actions jobs per run

Sources per run (each runs as a parallel process inside the single `pipeline` job):

| Source | Morning | Evening |
|---|---|---|
| `linkedin` (jobdrop venv) | ✓ | ✓ |
| `naukri` (jobspy venv) | ✓ | ✓ |
| `wellfound` (requests only) | ✓ | – |
| `ats` — boards in `companies.json` (requests only) | ✓ | – |

All sources run as parallel processes in **one** Actions job (`pipeline.py`), so no data
leaves the runner except to the private data repo. Failure handling: any failed source
(<50% of its queries ok/empty) fails the workflow (GitHub emails you) after data and
`runs/latest.md` are pushed; `runs/latest.md` lists the failed sources. A bad/expired
token fails with "DATA_REPO_TOKEN expired or invalid".
