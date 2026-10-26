# Latest run

- Finished: 2026-10-26T03:40:34Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24, freehire 24
- raw rows 7573 → deduped 4473 → kept 290 (excluded 4183) → **new 48** (already seen 242)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 6.7 | 20.2 | 0 | True | 38 | 18 |
| naukri | 66 | 29 | 0 | 0 | 4 | 0 | 0 | 708 | 0 | 0 | 7.4 | 23.4 | 0 | False | 47 | 1 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3436 | 0 | 0 | 20.6 | 20.7 | 0 | True | 70 | 2 |
| ats | 123 | 114 | 9 | 0 | 0 | 0 | 0 | 2346 | 0 | 0 | 0.8 | 2.8 | 0 | True | 18 | 0 |
| freehire | 20 | 12 | 8 | 0 | 0 | 0 | 0 | 533 | 0 | 0 | 0.5 | 0.6 | 0 | True | 134 | 28 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 31 | 299 | 0 |
| greenhouse | 66 | 62 | 1215 | 0 |
| lever | 22 | 21 | 832 | 0 |
