# Latest run

- Finished: 2026-11-02T13:53:53Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 123, wellfound 24, ats 24, freehire 24
- raw rows 7506 → deduped 4546 → kept 408 (excluded 4138) → **new 73** (already seen 335)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 13.7 | 26.0 | 0 | True | 52 | 35 |
| naukri | 66 | 21 | 0 | 0 | 2 | 0 | 0 | 525 | 0 | 0 | 6.9 | 19.0 | 0 | False | 46 | 1 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3402 | 0 | 0 | 21.1 | 21.1 | 0 | True | 66 | 4 |
| ats | 123 | 112 | 11 | 0 | 0 | 0 | 0 | 2369 | 0 | 0 | 1.2 | 3.3 | 0 | True | 19 | 2 |
| freehire | 20 | 12 | 8 | 0 | 0 | 0 | 0 | 660 | 0 | 0 | 0.6 | 0.7 | 0 | True | 236 | 35 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 29 | 301 | 0 |
| greenhouse | 66 | 63 | 1223 | 0 |
| lever | 22 | 20 | 845 | 0 |
