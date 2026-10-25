# Latest run

- Finished: 2026-10-25T03:44:15Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 42, wellfound 24, ats 24, freehire 24
- raw rows 8762 → deduped 4733 → kept 313 (excluded 4420) → **new 32** (already seen 281)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 548 | 0 | 0 | 7.0 | 18.9 | 0 | True | 39 | 20 |
| naukri | 66 | 31 | 0 | 0 | 4 | 0 | 0 | 763 | 0 | 0 | 8.0 | 24.3 | 0 | False | 61 | 3 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 4657 | 0 | 0 | 27.1 | 27.2 | 0 | True | 74 | 3 |
| ats | 123 | 114 | 9 | 0 | 0 | 0 | 0 | 2325 | 0 | 0 | 0.4 | 2.4 | 0 | True | 17 | 0 |
| freehire | 20 | 12 | 8 | 0 | 0 | 0 | 0 | 469 | 0 | 0 | 0.6 | 0.7 | 0 | True | 136 | 7 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 31 | 299 | 0 |
| greenhouse | 66 | 62 | 1216 | 0 |
| lever | 22 | 21 | 810 | 0 |
