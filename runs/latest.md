# Latest run

- Finished: 2026-11-22T13:58:51Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24, freehire 24
- raw rows 8986 → deduped 4987 → kept 481 (excluded 4506) → **new 43** (already seen 438)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 1 | 0 | 29.0 | 41.1 | 0 | True | 40 | 12 |
| naukri | 66 | 27 | 0 | 0 | 5 | 0 | 0 | 665 | 0 | 0 | 7.1 | 22.8 | 0 | False | 73 | 1 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 4454 | 0 | 0 | 26.8 | 26.9 | 0 | True | 45 | 3 |
| ats | 121 | 108 | 13 | 0 | 0 | 0 | 0 | 2292 | 0 | 0 | 0.4 | 2.5 | 0 | True | 26 | 0 |
| freehire | 20 | 15 | 5 | 0 | 0 | 0 | 0 | 1025 | 0 | 0 | 0.8 | 0.9 | 0 | True | 307 | 28 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 28 | 313 | 0 |
| greenhouse | 65 | 60 | 1199 | 0 |
| lever | 21 | 20 | 780 | 0 |
