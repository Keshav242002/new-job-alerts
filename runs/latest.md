# Latest run

- Finished: 2026-11-19T15:07:49Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 49, wellfound 24, ats 24, freehire 24
- raw rows 7814 → deduped 4741 → kept 505 (excluded 4236) → **new 92** (already seen 413)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 1 | 0 | 32.4 | 44.4 | 0 | True | 52 | 23 |
| naukri | 66 | 29 | 0 | 0 | 2 | 0 | 0 | 725 | 0 | 0 | 8.0 | 22.9 | 0 | False | 72 | 10 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3233 | 0 | 0 | 20.1 | 20.2 | 0 | True | 42 | 1 |
| ats | 122 | 109 | 12 | 0 | 0 | 0 | 1 | 2191 | 0 | 0 | 1.4 | 3.5 | 0 | True | 26 | 2 |
| freehire | 20 | 15 | 5 | 0 | 0 | 0 | 0 | 1115 | 0 | 0 | 0.9 | 0.9 | 0 | True | 330 | 60 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 28 | 307 | 0 |
| greenhouse | 66 | 62 | 1203 | 0 |
| lever | 21 | 19 | 681 | 1 |
