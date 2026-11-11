# Latest run

- Finished: 2026-11-11T13:04:28Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24, freehire 24
- raw rows 7452 → deduped 4522 → kept 398 (excluded 4124) → **new 50** (already seen 348)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 10.9 | 22.8 | 0 | True | 45 | 25 |
| naukri | 66 | 21 | 0 | 0 | 2 | 0 | 0 | 525 | 0 | 0 | 5.0 | 16.3 | 0 | False | 42 | 7 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3314 | 0 | 0 | 20.4 | 20.4 | 0 | True | 49 | 2 |
| ats | 122 | 111 | 11 | 0 | 0 | 0 | 0 | 2356 | 0 | 0 | 0.8 | 2.8 | 0 | True | 22 | 4 |
| freehire | 20 | 13 | 7 | 0 | 0 | 0 | 0 | 707 | 0 | 0 | 0.6 | 0.7 | 0 | True | 252 | 12 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 28 | 306 | 0 |
| greenhouse | 66 | 63 | 1220 | 0 |
| lever | 21 | 20 | 830 | 0 |
