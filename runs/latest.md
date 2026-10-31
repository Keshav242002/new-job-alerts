# Latest run

- Finished: 2026-10-31T11:15:34Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 72, wellfound 24, ats 24, freehire 24
- raw rows 7521 → deduped 4549 → kept 405 (excluded 4144) → **new 60** (already seen 345)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 546 | 0 | 0 | 7.2 | 19.0 | 0 | True | 56 | 11 |
| naukri | 66 | 17 | 0 | 0 | 2 | 0 | 0 | 425 | 0 | 0 | 5.2 | 14.5 | 0 | False | 39 | 3 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3365 | 0 | 0 | 20.4 | 20.5 | 0 | True | 62 | 2 |
| ats | 123 | 112 | 11 | 0 | 0 | 0 | 0 | 2313 | 0 | 0 | 0.6 | 2.8 | 0 | True | 18 | 0 |
| freehire | 20 | 12 | 8 | 0 | 0 | 0 | 0 | 872 | 0 | 0 | 0.8 | 0.8 | 0 | True | 249 | 44 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 29 | 306 | 0 |
| greenhouse | 66 | 62 | 1223 | 0 |
| lever | 22 | 21 | 784 | 0 |
