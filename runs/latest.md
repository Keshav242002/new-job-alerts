# Latest run

- Finished: 2026-10-29T11:50:58Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 25, wellfound 24, ats 24, freehire 24
- raw rows 7627 → deduped 4625 → kept 383 (excluded 4242) → **new 40** (already seen 343)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 8.5 | 21.0 | 0 | True | 50 | 14 |
| naukri | 66 | 23 | 0 | 0 | 2 | 0 | 0 | 575 | 0 | 0 | 8.0 | 19.8 | 0 | False | 47 | 5 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3368 | 0 | 0 | 21.2 | 21.3 | 0 | True | 70 | 5 |
| ats | 123 | 113 | 10 | 0 | 0 | 0 | 0 | 2325 | 0 | 0 | 1.0 | 3.1 | 0 | True | 18 | 0 |
| freehire | 20 | 11 | 9 | 0 | 0 | 0 | 0 | 809 | 0 | 0 | 0.7 | 0.8 | 0 | True | 213 | 16 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 29 | 301 | 0 |
| greenhouse | 66 | 63 | 1216 | 0 |
| lever | 22 | 21 | 808 | 0 |
