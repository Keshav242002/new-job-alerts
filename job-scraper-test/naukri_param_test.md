### jobspy Naukri relevance test (Flutter Developer × Bangalore, 25 results, run 2026-10-14)

| variant | rows | title mentions Flutter | fresh (≤3d) & on-topic |
|---|---|---|---|
| before: `keyword` + `jobAge=3` + `sort=f` (jobspy default with hours_old) | 25 | 1 | 1 |
| relevance sort, keep `jobAge=3` | 25 | 4 | 4 |
| web-style `k`/`l`/`seoKey` + `sort=f` | 25 | 1 | 1 |
| web-style `k`/`l`/`seoKey`, relevance | 20 | 4 | 4 |
| quoted keyword + `jobAge=3` + `sort=f` | 25 | 1 | 1 |
| **after (used): `keyword`, relevance, no `jobAge`; 72h filter applied in process.py** | 25 | **25** | 4 |
| quoted keyword, relevance, no `jobAge` | 25 | 25 | 4 |

With `jobAge` set, Naukri pads the result set with unrelated fresh postings; without it, results are on-topic and the age cut happens downstream.
