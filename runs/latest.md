# Latest run

- Finished: 2026-10-15T08:46:09Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24
- raw rows 5068 → deduped 3534 → kept 68 (excluded 3466) → **new 16** (already seen 52)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 13.2 | 25.1 | 0 | True | 48 | 10 |
| naukri | 66 | 20 | 0 | 0 | 2 | 0 | 0 | 500 | 0 | 0 | 5.2 | 16.1 | 0 | False | 9 | 4 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 1656 | 0 | 0 | 6.6 | 6.7 | 0 | True | 1 | 0 |
| ats | 123 | 115 | 8 | 0 | 0 | 0 | 0 | 2362 | 0 | 0 | 0.4 | 2.6 | 0 | True | 11 | 2 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 31 | 313 | 0 |
| greenhouse | 66 | 63 | 1251 | 0 |
| lever | 22 | 21 | 798 | 0 |
