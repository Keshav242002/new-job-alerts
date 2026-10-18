"""freehire collector — freehire.me public search API (keyless, plain HTTP).

    GET https://freehire.me/api/v1/agent/jobs/search?q=...&countries=IN&posted_within_days=14&...

freehire aggregates postings from company ATS boards (Greenhouse, Lever, Ashby, Workday, Keka,
Zoho Recruit, ...). The agent endpoint takes the same filters as /jobs/search but returns full
descriptions (/jobs/search truncates them to a ~1000-char preview). Pagination is limit/offset;
responses are {"data": [...], "meta": {"total", "limit", "offset", "ignored_params"?}}.

Each query runs once per pass in config.FREEHIRE_PASSES (India, worldwide remote). A filter the
API doesn't recognise is listed in meta.ignored_params and silently broadens the search, so such
a response counts as an error.

Usage: python run_freehire.py [--out DIR] [--terms "A;B"] [--max-pages N]
"""
from __future__ import annotations

import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd
import requests

import config
from ats import HEADERS, _date, _text, is_india
from harness import SCHEMA

URL = "https://freehire.me/api/v1/agent/jobs/search"
JOB_PAGE = "https://freehire.me/jobs/{slug}"
# freehire's AI estimate of minimum experience; process.add_experience uses it only when the
# description states no figure. Not part of the shared SCHEMA (raw_freehire.csv only).
COLUMNS = SCHEMA + ["exp_estimate"]


def _clean_url(u: str | None) -> str | None:
    """Drop freehire's utm_source from the original ATS/company URL."""
    if not u:
        return None
    sp = urlsplit(u)
    q = parse_qsl(sp.query, keep_blank_values=True)
    if not any(k.lower().startswith("utm_") for k, _ in q):
        return u
    return urlunsplit(sp._replace(query=urlencode([(k, v) for k, v in q if not k.lower().startswith("utm_")])))


def _salary(e: dict) -> str | None:
    lo, hi = e.get("salary_min"), e.get("salary_max")
    if lo is None and hi is None:
        return None
    rng = str(lo if hi is None or lo == hi else hi if lo is None else f"{lo}-{hi}")
    return " ".join(x for x in (e.get("salary_currency"), rng, e.get("salary_period")) if x)


def open_to_india(job: dict) -> bool:
    """Remote pass: keep jobs with no country restriction, or located in / open to India."""
    countries = [c.lower() for c in job.get("countries") or []]
    return not countries or "in" in countries or is_india(job.get("location"))


def to_schema(jobs: list[dict], term: str, loc: str) -> pd.DataFrame:
    rows = []
    for j in jobs:
        e = j.get("enrichment") or {}
        jt = e.get("employment_type")
        rows.append({
            "source_lib": "freehire",
            "site": "freehire",
            "title": j.get("title"),
            "company": j.get("company") or None,
            "location": j.get("location") or ", ".join(j.get("cities") or []) or None,
            "is_remote": j.get("work_mode") == "remote",
            "date_posted": _date(j.get("posted_at")),
            "job_url": _clean_url(j.get("url")) or (JOB_PAGE.format(slug=j["public_slug"])
                                                    if j.get("public_slug") else None),
            "job_type": jt.replace("_", "-") if isinstance(jt, str) else None,  # part-time / full-time for process.py
            "min_exp": None,  # regex over title + description in process.add_experience, as for ATS rows
            "max_exp": None,
            "salary": _salary(e),
            "description": _text(j.get("description")),
            "search_term": term,
            "search_location": loc,
            "date_approx": False,
            "exp_estimate": e.get("experience_years_min"),
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def fetch(sess: requests.Session, params: dict) -> tuple[str, str, dict | None, int]:
    """-> (status, reason, json or None, n429). Retries 429/5xx/timeouts once with backoff; never raises."""
    n429 = 0
    last = ("error", "")
    wait = config.FREEHIRE_RETRY_BACKOFF_S
    for attempt in range(2):
        if attempt:
            time.sleep(wait)
            wait = config.FREEHIRE_RETRY_BACKOFF_S
        try:
            r = sess.get(URL, params=params, headers=HEADERS, timeout=config.FREEHIRE_TIMEOUT_S)
        except requests.Timeout:
            last = ("timeout", f"no response in {config.FREEHIRE_TIMEOUT_S}s")
            continue
        except requests.RequestException as e:
            last = ("error", f"{type(e).__name__}: {e}"[:200])
            continue
        if r.status_code == 429:
            n429 += 1
            last = ("blocked", "HTTP 429")
            ra = r.headers.get("Retry-After", "")
            if ra.isdigit():
                wait = min(wait, int(ra))
            continue
        if r.status_code >= 500:
            last = ("error", f"HTTP {r.status_code}")
            continue
        try:
            data = r.json()
        except ValueError:
            return "error", f"HTTP {r.status_code}, not JSON", None, n429
        if r.status_code != 200:
            return "error", f"HTTP {r.status_code}: {str(data.get('error', ''))[:120]}", None, n429
        ignored = (data.get("meta") or {}).get("ignored_params")
        if ignored:
            names = ", ".join(str(p.get("param", p)) if isinstance(p, dict) else str(p) for p in ignored)
            return "error", f"API ignored params: {names}", None, n429
        if not isinstance(data.get("data"), list):
            return "error", "response has no data list", None, n429
        return ("ok" if data["data"] else "empty"), "", data, n429
    return last[0], (last[1] + " (after 1 retry)").strip(), None, n429


def query_params(q: str, geo: dict, page_size: int, backfill: bool = False) -> dict:
    """Base params + pass geography + per-query overrides (None removes a param); backfill swaps the
    generic queries' 2-day first-recorded window for the 14-day posted window."""
    params = {**config.FREEHIRE_PARAMS, **geo, **config.FREEHIRE_QUERY_PARAMS.get(q, {})}
    if backfill and q in config.FREEHIRE_GENERIC_QUERIES:
        params |= config.FREEHIRE_BACKFILL_PARAMS
    return {k: v for k, v in params.items() if v is not None} | {"q": q, "limit": page_size}


def scrape(queries: list[str], passes: dict[str, dict], max_pages: int = config.FREEHIRE_MAX_PAGES,
           page_size: int = config.FREEHIRE_PAGE_SIZE, sess: requests.Session | None = None,
           backfill: bool = False) -> tuple[pd.DataFrame, list[dict]]:
    """Run every query × pass, paging by offset until a short page, meta.total, the page cap (max_pages, or
    config.FREEHIRE_QUERY_MAX_PAGES for that query), a page with no new jobs, or a failed page (rows from
    earlier pages are kept)."""
    sess = sess or requests.Session()
    frames, recs = [], []
    first = True
    for q in queries:
        cap = config.FREEHIRE_QUERY_MAX_PAGES.get(q, max_pages)
        for loc, geo in passes.items():
            params = query_params(q, geo, page_size, backfill)
            t0 = time.perf_counter()
            status, reason, n429, pages, rows, dropped = "error", "", 0, 0, [], 0
            try:
                slugs: set[str] = set()
                for page in range(cap):
                    if not first:
                        time.sleep(config.FREEHIRE_DELAY_S)
                    first = False
                    st, why, data, k = fetch(sess, {**params, "offset": page * page_size})
                    n429 += k
                    pages += 1
                    jobs = (data or {}).get("data") or []
                    new = [j for j in jobs if j.get("public_slug") not in slugs]
                    slugs.update(j.get("public_slug") for j in new)
                    if loc == "Remote":
                        dropped += sum(not open_to_india(j) for j in new)
                        rows += [j for j in new if open_to_india(j)]
                    else:
                        rows += new
                    if page == 0:
                        status, reason = st, why
                    elif st not in ("ok", "empty"):
                        reason = f"page {page + 1}: {st} {why}".strip()
                    total = ((data or {}).get("meta") or {}).get("total") or 0
                    if st != "ok" or not new or len(jobs) < page_size or (page + 1) * page_size >= total:
                        break
                else:
                    reason = (reason + f" hit page cap ({cap}); more pages may exist").strip()
                if dropped:
                    reason = (reason + f" dropped {dropped} remote jobs not open to India").strip()
                df = to_schema(rows, q, loc)
            except Exception as e:  # noqa: BLE001 — record a code error for this query, keep going
                status, reason = "error", f"{type(e).__name__}: {e}"[:200]
                df = pd.DataFrame(columns=COLUMNS)
            frames.append(df)
            if len(df):
                status = "ok"
            elif status == "ok":
                status = "empty"
            recs.append({"lib": "freehire", "site": "freehire", "search_term": q, "search_location": loc,
                         "status": status, "rows": len(df), "runtime_s": round(time.perf_counter() - t0, 1),
                         "reason": reason, "n429": n429, "attempts": pages})
            print(f"[freehire {len(recs)}] {q!r:<22} {loc:<7} {status:<8} rows={len(df):<3} pages={pages} "
                  f"{recs[-1]['runtime_s']:>5.1f}s 429s={n429} {reason[:70]}", flush=True)
    raw = pd.concat([f for f in frames if len(f)], ignore_index=True) if any(len(f) for f in frames) \
        else pd.DataFrame(columns=COLUMNS)
    return raw, recs
