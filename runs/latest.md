# Latest run

- Finished: 2026-11-01T12:19:47Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 97, wellfound 24, ats 24, freehire 24
- raw rows 8805 → deduped 4803 → kept 396 (excluded 4407) → **new 38** (already seen 358)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 18.1 | 30.4 | 0 | True | 44 | 19 |
| naukri | 66 | 22 | 0 | 0 | 2 | 0 | 0 | 545 | 0 | 0 | 6.7 | 18.3 | 0 | False | 46 | 3 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 4634 | 0 | 0 | 27.2 | 27.3 | 0 | True | 69 | 4 |
| ats | 123 | 112 | 11 | 0 | 0 | 0 | 0 | 2305 | 0 | 0 | 0.4 | 2.5 | 0 | True | 19 | 0 |
| freehire | 20 | 13 | 7 | 0 | 0 | 0 | 0 | 771 | 0 | 0 | 0.7 | 0.8 | 0 | True | 235 | 12 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 29 | 305 | 0 |
| greenhouse | 66 | 62 | 1222 | 0 |
| lever | 22 | 21 | 778 | 0 |
