# Latest run

- Finished: 2026-10-24T03:46:41Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24, freehire 24
- raw rows 7361 → deduped 4486 → kept 321 (excluded 4165) → **new 39** (already seen 282)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 17.4 | 29.6 | 0 | True | 51 | 16 |
| naukri | 66 | 23 | 0 | 0 | 2 | 0 | 0 | 575 | 0 | 0 | 6.5 | 19.3 | 0 | False | 42 | 6 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3375 | 0 | 0 | 20.4 | 20.5 | 0 | True | 61 | 1 |
| ats | 123 | 114 | 9 | 0 | 0 | 0 | 0 | 2330 | 0 | 0 | 0.4 | 2.5 | 0 | True | 17 | 0 |
| freehire | 20 | 11 | 9 | 0 | 0 | 0 | 0 | 531 | 0 | 0 | 0.6 | 0.7 | 0 | True | 163 | 17 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 31 | 299 | 0 |
| greenhouse | 66 | 62 | 1219 | 0 |
| lever | 22 | 21 | 812 | 0 |
