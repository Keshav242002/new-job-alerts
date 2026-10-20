# Latest run

- Finished: 2026-10-20T04:18:56Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24, freehire 24
- raw rows 6731 → deduped 3993 → kept 256 (excluded 3737) → **new 18** (already seen 238)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 519 | 9 | 0 | 50.3 | 61.8 | 0 | True | 44 | 6 |
| naukri | 66 | 10 | 0 | 0 | 2 | 0 | 0 | 250 | 0 | 0 | 2.4 | 7.9 | 0 | False | 46 | 4 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3437 | 0 | 0 | 20.6 | 20.7 | 0 | True | 67 | 4 |
| ats | 123 | 115 | 8 | 0 | 0 | 0 | 0 | 2279 | 0 | 0 | 0.5 | 2.7 | 0 | True | 23 | 0 |
| freehire | 20 | 15 | 5 | 0 | 0 | 0 | 0 | 246 | 0 | 0 | 0.4 | 0.5 | 0 | True | 83 | 4 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 31 | 298 | 0 |
| greenhouse | 66 | 63 | 1218 | 0 |
| lever | 22 | 21 | 763 | 0 |
