# Latest run

- Finished: 2026-10-14T15:59:34Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24
- raw rows 5014 → deduped 3602 → kept 104 (excluded 3498) → **new 51** (already seen 53)
- Failed sources: naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 22 | 20 | 0 | 0 | 0 | 2 | 0 | 427 | 9 | 0 | 60.3 | 0 | True | 68 | 46 |
| naukri | 110 | 23 | 0 | 0 | 4 | 0 | 0 | 565 | 0 | 0 | 6.4 | 0 | False | 24 | 3 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 1652 | 0 | 0 | 7.0 | 0 | True | 8 | 2 |
| ats | 123 | 115 | 8 | 0 | 0 | 0 | 0 | 2370 | 0 | 0 | 0.9 | 0 | True | 5 | 0 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 31 | 312 | 0 |
| greenhouse | 66 | 63 | 1256 | 0 |
| lever | 22 | 21 | 802 | 0 |
