# Latest run

- Finished: 2026-11-07T12:02:49Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24, freehire 24
- raw rows 7292 → deduped 4397 → kept 301 (excluded 4096) → **new 14** (already seen 287)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 7.5 | 19.1 | 0 | True | 42 | 12 |
| naukri | 66 | 24 | 0 | 0 | 2 | 0 | 0 | 580 | 0 | 0 | 6.3 | 18.5 | 0 | False | 46 | 1 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3325 | 0 | 0 | 20.0 | 20.1 | 0 | True | 56 | 2 |
| ats | 122 | 110 | 12 | 0 | 0 | 0 | 0 | 2359 | 0 | 0 | 0.9 | 2.9 | 0 | True | 23 | 0 |
| freehire | 20 | 12 | 8 | 0 | 0 | 0 | 0 | 478 | 0 | 0 | 0.5 | 0.6 | 0 | True | 143 | 0 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 29 | 304 | 0 |
| greenhouse | 66 | 62 | 1236 | 0 |
| lever | 21 | 19 | 819 | 0 |
