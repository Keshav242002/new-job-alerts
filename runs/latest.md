# Latest run

- Finished: 2026-10-14T14:38:14Z (UTC)
- Run: morning
- Windows (h): linkedin 24, naukri 24, wellfound 24, ats 24
- raw rows 3686 → deduped 2642 → kept 11 (excluded 2631) → **new 0** (already seen 11)
- Failed sources: linkedin, naukri

| source | queries | ok | empty | blocked | captcha | timeout | error | rows | 429s | browser_retries | runtime_min | process_exit | success | kept | new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| linkedin | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 1 | False | 0 | 0 |
| naukri | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 1 | False | 0 | 0 |
| wellfound | 100 | 90 | 0 | 0 | 0 | 0 | 0 | 1663 | 0 | 0 | 6.9 | 0 | True | 7 | 0 |
| ats | 123 | 113 | 8 | 0 | 0 | 0 | 2 | 2023 | 0 | 0 | 1.7 | 0 | True | 4 | 0 |

ATS boards scanned:

| ats | companies | with_india_jobs | india_jobs | errors |
|---|---|---|---|---|
| ashby | 35 | 30 | 305 | 1 |
| greenhouse | 66 | 63 | 1255 | 0 |
| lever | 22 | 20 | 463 | 1 |
