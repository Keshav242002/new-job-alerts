# Latest run

- Finished: 2026-10-19T03:37:44Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24, freehire 24
- raw rows 7135 → deduped 4201 → kept 276 (excluded 3925) → **new 18** (already seen 258)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 7.8 | 20.3 | 0 | True | 43 | 10 |
| naukri | 66 | 22 | 0 | 0 | 2 | 0 | 0 | 550 | 0 | 0 | 5.6 | 17.3 | 0 | False | 61 | 0 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3509 | 0 | 0 | 20.6 | 20.7 | 0 | True | 67 | 1 |
| ats | 123 | 115 | 8 | 0 | 0 | 0 | 0 | 2309 | 0 | 0 | 0.4 | 2.4 | 0 | True | 25 | 1 |
| freehire | 20 | 15 | 5 | 0 | 0 | 0 | 0 | 217 | 0 | 0 | 0.4 | 0.5 | 0 | True | 87 | 7 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 31 | 316 | 0 |
| greenhouse | 66 | 63 | 1236 | 0 |
| lever | 22 | 21 | 757 | 0 |
