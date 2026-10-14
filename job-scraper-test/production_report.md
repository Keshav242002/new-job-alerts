# Production volume & cost estimate

Source data: the 2026-10-14 comparison runs (72h window), restricted to production sources (jobdrop:google, jobdrop:linkedin, jobspy:indeed, jobspy:naukri, wellfound:wellfound). Rules from process.py as of this report.

10048 raw rows → 4175 after dedupe → **360 kept**, 3815 excluded.

## 1. Estimated kept jobs per day

Kept jobs by posting date over the full days in the window: Oct 12 105, Oct 13 154 → **≈130 kept jobs/day** (deduped across sources and terms; partial days excluded: Oct 11 18, Oct 14 47). Based on 2 weekday(s) only — weekend volume is likely lower.

| source | kept (72h) | kept/day (avg full days) | queries hitting 25-result cap |
|---|---|---|---|
| linkedin | 55 | 19.0 | 22/22 |
| indeed | 129 | 51.5 | 45/110 |
| naukri | 59 | 25.5 | 108/110 |
| google | 96 | 25.0 | 0/110 |
| wellfound | 22 | 9.0 | n/a (paged) |

Sources overlap, so per-source figures sum to more than the total. Where queries hit the 25-result cap over a 72h window, a 24h window will lose less to the cap, so the real daily figure is likely somewhat higher for those sources. New jobs/day after `seen_jobs.csv` will be at or below this.

## 2. Jobs removed per rule

A job can match several rules; "alone" = no other rule would have excluded it.

| rule | jobs matching | removed by this rule alone |
|---|---|---|
| older_than_window | 2880 | 1003 |
| no_skill_match | 1762 | 267 |
| job_type | 207 | 8 |
| fresher_only | 202 | 6 |
| seniority_title | 1022 | 94 |
| min_exp>4 | 995 | 160 |
| fullstack_angular_vue_only | 74 | 6 |

`no_description` flag (no description and no skill in title → kept instead of `no_skill_match`): **67 kept jobs** (284 across kept + excluded).
Job type comes from the title only in this re-run (the saved CSVs predate the `job_type` column); future runs also use the board's job-type field.

## 3. Per search term (kept, deduped)

| search term | kept jobs | unique (no other term found it) |
|---|---|---|
| Full Stack Developer | 99 | 43 |
| Flutter Developer | 42 | 26 |
| Mobile Application Developer | 35 | 16 |
| SDE 1 | 38 | 13 |
| SDE 2 | 28 | 8 |
| Software Developer | 101 | 18 |
| Software Engineer | 91 | 12 |
| Backend Developer | 80 | 14 |
| Django Developer | 33 | 13 |
| Python Developer | 80 | 36 |
| FastAPI Developer | 38 | 13 |

Wellfound has no per-term pages for SDE 1 / SDE 2 / Software Engineer (all `software-engineer`) or Python / FastAPI (both `python-developer`), so its jobs are credited to every term sharing the page; those terms can't be "unique" for Wellfound jobs.

## 4. GitHub Actions minutes (schedule in SCHEDULE.md)

Wall time = query runtimes (incl. any 429 backoff) + polite delays between queries (sleep is billed) + measured per-job overhead (checkout, setup-python, pip install, upload). Each job is billed separately and rounded up to the next minute; parallel jobs all count.

| job | wall time (min) | billed (min, rounded up) |
|---|---|---|
| linkedin | 29.8 | 30 |
| jobspy (indeed ∥ naukri) | 31.9 | 32 |
| google | 32.8 | 33 |
| wellfound incremental | 10.3 | 11 |
| wellfound full (Sun) | 29.9 | 30 |
| process + commit | 1.0 | 1 |

- Morning run: **107 min** (126 on Sundays, Wellfound full)
- Evening run: **63 min**
- **≈5,181 min/month** (30 days, 4.3 Sundays). GitHub Free includes 2,000 min/month for private repos; public repos are not billed.
- Assumptions: LinkedIn delays 25–45s, others 4–9s; jobdrop LinkedIn had 0 429s in the full run — each LinkedIn query blocked through all retries would add 7 min. Incremental Wellfound assumes 1.3 pages per role/location at 5.0s/page (90 role/location pages); the first incremental run (empty seen_jobs) walks up to 5 pages each.
