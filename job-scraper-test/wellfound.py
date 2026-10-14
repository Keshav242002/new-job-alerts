"""Wellfound scraper — plain HTTP GET of public role pages, parsed from __NEXT_DATA__.

Role pages (/role/l/<role>/<location>, /role/r/<role> for remote) embed an Apollo
cache with JobListingSearchResult objects (title, locations, experience, salary,
posted time) and StartupResult objects (company name) that reference them.
An unknown role/location slug redirects to a generic page, so any redirect is
treated as "no such page" rather than parsed.

Usage:
    python run_wellfound.py [--out DIR] [--terms "A;B"] [--locations "X;Y"] [--max-pages N]
"""
from __future__ import annotations

import json
import random
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import pandas as pd
import requests

import config
from harness import SCHEMA

BASE = "https://wellfound.com"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Search term -> Wellfound role slugs (verified 2026-10-14; unknown slugs redirect).
ROLE_SLUGS = {
    "Full Stack Developer": ["full-stack-engineer", "full-stack-developer"],
    "Flutter Developer": ["flutter-developer"],
    "Mobile Application Developer": ["mobile-engineer"],
    "SDE 1": ["software-engineer"],
    "SDE 2": ["software-engineer"],
    "Software Developer": ["software-developer"],
    "Software Engineer": ["software-engineer"],
    "Backend Developer": ["backend-engineer", "backend-developer"],
    "Django Developer": ["django-developer"],
    "Python Developer": ["python-developer"],
    "FastAPI Developer": ["python-developer"],  # no fastapi page
}
# Location -> slug. "r" = remote role page. None = Wellfound has no page (covered by "india").
LOCATION_SLUGS = {
    "Bangalore": "bangalore",
    "Gurugram": "gurgaon",  # /gurugram exists but is empty
    "Noida": "noida",
    "Delhi NCR": "new-delhi",
    "Pune": "pune",
    "Mumbai": "mumbai",
    "Hyderabad": "hyderabad",
    "Chennai": None,
    "Remote": "r",
    "India": "india",
}

INDIA_RE = re.compile(
    r"\bindia\b|bengaluru|bangalore|gurugram|gurgaon|noida|delhi|pune|mumbai|hyderabad|chennai|kolkata|"
    r"ahmedabad|kochi|jaipur|chandigarh|indore|coimbatore|thiruvananthapuram|trivandrum|mysore|mysuru", re.I)

NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
BOT_RE = re.compile(r"datadome|captcha-delivery\.com|<title>just a moment|cf_chl_opt|cf-chl-widget|captcha", re.I)


def page_url(role: str, loc_slug: str, page: int) -> str:
    path = f"/role/r/{role}" if loc_slug == "r" else f"/role/l/{role}/{loc_slug}"
    return BASE + path + (f"?page={page}" if page > 1 else "")


def parse_page(html: str) -> list[dict]:
    """Return raw job dicts (listing fields + company) from a role page."""
    m = NEXT_DATA_RE.search(html)
    if not m:
        return []
    pp = json.loads(m.group(1)).get("props", {}).get("pageProps", {})
    state = pp.get("apolloState", {})
    state = state.get("data", state)
    company_of: dict[str, dict] = {}
    for v in state.values():
        if isinstance(v, dict) and v.get("__typename") == "StartupResult":
            for ref in v.get("highlightedJobListings") or []:
                company_of[ref.get("__ref", "")] = v
    jobs = []
    for key, v in state.items():
        if not (isinstance(v, dict) and v.get("__typename") == "JobListingSearchResult"):
            continue
        startup = company_of.get(key) or company_of.get(f"JobListingSearchResult:{v.get('id')}") or {}
        jobs.append({**v, "_company": startup.get("name"), "_company_slug": startup.get("slug")})
    return jobs


def _remote(job: dict) -> bool:
    kind = ((job.get("remoteConfig") or {}).get("kind") or "").upper()
    return bool(job.get("remote")) or kind in ("REMOTE", "REMOTE_ONLY", "FULLY_REMOTE")


def open_to_india(job: dict) -> bool:
    """Remote role pages are global: keep jobs located in India, accepting India-based
    remote candidates, or with no remote-location restriction at all."""
    places = " ".join((job.get("locationNames") or []) + (job.get("acceptedRemoteLocationNames") or []))
    return bool(INDIA_RE.search(places)) or not (job.get("acceptedRemoteLocationNames") or [])


def to_schema(jobs: list[dict], term: str, loc: str) -> pd.DataFrame:
    rows = []
    for j in jobs:
        posted = j.get("liveStartAt")
        locs = j.get("locationNames") or []
        desc = j.get("description")
        rows.append({
            "source_lib": "wellfound",
            "site": "wellfound",
            "title": j.get("title"),
            "company": j.get("_company"),
            "location": ", ".join(locs) if locs else ("Remote" if _remote(j) else None),
            "is_remote": _remote(j),
            "date_posted": datetime.fromtimestamp(posted, tz=timezone.utc).date() if posted else None,
            "job_url": f"{BASE}/jobs/{j.get('id')}-{j.get('slug')}" if j.get("id") else None,
            "min_exp": j.get("yearsExperienceMin"),
            "max_exp": j.get("yearsExperienceMax"),
            "salary": (j.get("compensation") or "").strip() or None,
            "description": desc[: config.DESCRIPTION_MAX_CHARS] if isinstance(desc, str) else None,
            "search_term": term,
            "search_location": loc,
        })
    return pd.DataFrame(rows, columns=SCHEMA)


def fetch(sess: requests.Session, url: str) -> tuple[str, str, list[dict], int]:
    """-> (status, reason, jobs, n429). Retries 429 with backoff."""
    n429 = 0
    for attempt, wait in enumerate([0] + config.BACKOFF_429):
        if wait:
            time.sleep(wait)
        try:
            r = sess.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            return "error", f"{type(e).__name__}: {e}"[:200], [], n429
        if r.status_code == 429:
            n429 += 1
            continue
        final = urlsplit(r.url)
        want = urlsplit(url)
        if final.path.rstrip("/") != want.path.rstrip("/"):
            return "error", f"redirected to {final.path} (slug no longer valid?)", [], n429
        if r.status_code in (403, 401):
            return ("captcha" if BOT_RE.search(r.text) else "blocked"), f"HTTP {r.status_code}", [], n429
        if r.status_code != 200:
            return "error", f"HTTP {r.status_code}", [], n429
        jobs = parse_page(r.text)
        if not jobs and BOT_RE.search(r.text):
            return "captcha", "bot-check page", [], n429
        if not jobs and not NEXT_DATA_RE.search(r.text):
            return "error", "no __NEXT_DATA__ (page layout changed?)", [], n429
        return ("ok" if jobs else "empty"), "", jobs, n429
    return "blocked", f"429 after {len(config.BACKOFF_429)} retries", [], n429


def scrape(terms: list[str], locations: list[str], max_pages: int = 2) -> tuple[pd.DataFrame, list[dict]]:
    """Fetch every (role slug × location) page once; attribute rows to all terms sharing the slug."""
    slug_terms: dict[str, list[str]] = {}
    for t in terms:
        for s in ROLE_SLUGS.get(t, []):
            slug_terms.setdefault(s, []).append(t)

    sess = requests.Session()
    frames, recs = [], []
    first = True
    for slug, slug_term_list in slug_terms.items():
        term_label = ";".join(slug_term_list)
        for loc in locations:
            loc_slug = LOCATION_SLUGS.get(loc)
            if loc_slug is None:
                recs.append({"lib": "wellfound", "site": "wellfound", "search_term": term_label,
                             "search_location": loc, "status": "skipped", "rows": 0, "runtime_s": 0.0,
                             "reason": "no Wellfound page for this location", "n429": 0, "attempts": 0})
                continue
            seen_ids: set[str] = set()
            t0 = time.perf_counter()
            status, reason, n429, pages, rows, dropped = "empty", "", 0, 0, [], 0
            for page in range(1, max_pages + 1):
                if not first:
                    time.sleep(random.uniform(*config.WELLFOUND_DELAY_RANGE))
                first = False
                st, why, jobs, k = fetch(sess, page_url(slug, loc_slug, page))
                n429 += k
                pages += 1
                new = [j for j in jobs if str(j.get("id")) not in seen_ids]
                seen_ids.update(str(j.get("id")) for j in new)
                if loc_slug == "r":
                    dropped += sum(not open_to_india(j) for j in new)
                    rows += [j for j in new if open_to_india(j)]
                else:
                    rows += new
                if page == 1:
                    status, reason = st, why
                elif st not in ("ok", "empty"):
                    reason = f"page {page}: {st} {why}".strip()
                if st != "ok" or not new:
                    break
            else:
                reason = (reason + f" hit page cap ({max_pages}); more pages may exist").strip()
            if dropped:
                reason = (reason + f" dropped {dropped} remote jobs not open to India").strip()
            df = to_schema(rows, term_label, loc)
            frames.append(df)
            recs.append({"lib": "wellfound", "site": "wellfound", "search_term": term_label,
                         "search_location": loc, "status": "ok" if len(df) else status, "rows": len(df),
                         "runtime_s": round(time.perf_counter() - t0, 1), "reason": reason,
                         "n429": n429, "attempts": pages})
            r = recs[-1]
            print(f"[wellfound {len(recs)}] {slug:<22} {loc:<10} {r['status']:<8} rows={r['rows']:<3} "
                  f"pages={pages} {r['runtime_s']:>5.1f}s 429s={n429} {reason[:70]}", flush=True)
    raw = pd.concat([f for f in frames if len(f)], ignore_index=True) if any(len(f) for f in frames) \
        else pd.DataFrame(columns=SCHEMA)
    return raw, recs
