# Latest run

- Finished: 2026-10-17T03:50:27Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24
- raw rows 6842 → deduped 4066 → kept 195 (excluded 3871) → **new 27** (already seen 168)
- Failed sources (fail the run): none
- Failed best-effort sources (logged only): naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | total_run_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 550 | 0 | 0 | 22.0 | 33.6 | 0 | True | 42 | 18 |
| naukri | 66 | 21 | 0 | 0 | 3 | 0 | 0 | 515 | 0 | 0 | 5.3 | 16.0 | 0 | False | 66 | 8 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 3468 | 0 | 0 | 21.3 | 21.4 | 0 | True | 67 | 1 |
| ats | 123 | 115 | 8 | 0 | 0 | 0 | 0 | 2309 | 0 | 0 | 0.3 | 2.4 | 0 | True | 22 | 0 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 31 | 316 | 0 |
| greenhouse | 66 | 63 | 1250 | 0 |
| lever | 22 | 21 | 743 | 0 |
