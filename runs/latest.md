# Latest run

- Finished: 2026-10-27T04:04:18Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24, freehire 24
- raw rows 7747 → deduped 4682 → kept 351 (excluded 4331) → **new 46** (already seen 305)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 531 | 3 | 0 | 34.2 | 47.7 | 0 | True | 53 | 4 |
| naukri | 66 | 27 | 0 | 0 | 3 | 0 | 0 | 670 | 0 | 0 | 9.5 | 23.9 | 0 | False | 49 | 11 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3374 | 0 | 0 | 20.6 | 20.7 | 0 | True | 67 | 0 |
| ats | 123 | 113 | 10 | 0 | 0 | 0 | 0 | 2346 | 0 | 0 | 0.3 | 2.3 | 0 | True | 22 | 0 |
| freehire | 20 | 12 | 8 | 0 | 0 | 0 | 0 | 826 | 0 | 0 | 0.7 | 0.8 | 0 | True | 181 | 33 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 30 | 297 | 0 |
| greenhouse | 66 | 62 | 1219 | 0 |
| lever | 22 | 21 | 830 | 0 |
