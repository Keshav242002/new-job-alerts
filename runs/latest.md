# Latest run

- Finished: 2026-11-03T13:06:24Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 146, wellfound 24, ats 24, freehire 24
- raw rows 7470 → deduped 4527 → kept 428 (excluded 4099) → **new 53** (already seen 375)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 6.9 | 18.9 | 0 | True | 57 | 22 |
| naukri | 66 | 16 | 0 | 0 | 2 | 0 | 0 | 400 | 0 | 0 | 4.3 | 12.9 | 0 | False | 38 | 1 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3380 | 0 | 0 | 20.3 | 20.4 | 0 | True | 67 | 6 |
| ats | 123 | 111 | 11 | 0 | 0 | 0 | 1 | 2364 | 0 | 0 | 0.6 | 2.8 | 0 | True | 24 | 4 |
| freehire | 20 | 12 | 8 | 0 | 0 | 0 | 0 | 776 | 0 | 0 | 0.8 | 0.8 | 0 | True | 263 | 23 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 29 | 304 | 0 |
| greenhouse | 66 | 63 | 1220 | 0 |
| lever | 22 | 19 | 840 | 1 |
