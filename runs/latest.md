# Latest run

- Finished: 2026-11-25T16:01:04Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24, freehire 24
- raw rows 7391 → deduped 4585 → kept 554 (excluded 4031) → **new 106** (already seen 448)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 15.5 | 28.0 | 0 | True | 55 | 30 |
| naukri | 66 | 15 | 0 | 0 | 2 | 0 | 0 | 375 | 0 | 0 | 4.2 | 12.1 | 0 | False | 61 | 3 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3125 | 0 | 0 | 20.2 | 20.3 | 0 | True | 51 | 6 |
| ats | 119 | 104 | 14 | 0 | 0 | 0 | 1 | 2198 | 0 | 0 | 0.8 | 2.8 | 0 | True | 30 | 5 |
| freehire | 20 | 17 | 3 | 0 | 0 | 0 | 0 | 1143 | 0 | 0 | 0.8 | 0.8 | 0 | True | 368 | 68 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 28 | 300 | 0 |
| greenhouse | 64 | 58 | 1158 | 0 |
| lever | 20 | 18 | 740 | 1 |
