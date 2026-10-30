# Latest run

- Finished: 2026-10-30T11:43:15Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 49, wellfound 24, ats 24, freehire 24
- raw rows 7599 → deduped 4606 → kept 403 (excluded 4203) → **new 72** (already seen 331)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 7.3 | 19.1 | 0 | True | 56 | 34 |
| naukri | 66 | 19 | 0 | 0 | 2 | 0 | 0 | 465 | 0 | 0 | 6.5 | 16.9 | 0 | False | 44 | 5 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3396 | 0 | 0 | 20.5 | 20.6 | 0 | True | 63 | 2 |
| ats | 123 | 112 | 11 | 0 | 0 | 0 | 0 | 2325 | 0 | 0 | 1.0 | 3.1 | 0 | True | 21 | 1 |
| freehire | 20 | 12 | 8 | 0 | 0 | 0 | 0 | 863 | 0 | 0 | 0.7 | 0.8 | 0 | True | 235 | 31 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 29 | 304 | 0 |
| greenhouse | 66 | 62 | 1220 | 0 |
| lever | 22 | 21 | 801 | 0 |
