"""ATS collector — Greenhouse, Lever and Ashby public job-board APIs (plain HTTP, no browser).

    Greenhouse: https://boards-api.greenhouse.io/v1/boards/<slug>/jobs?content=true
    Lever:      https://api.lever.co/v0/postings/<slug>?mode=json
    Ashby:      https://api.ashbyhq.com/posting-api/job-board/<slug>?includeCompensation=true

Companies come from companies.json ({name, ats, board_slug, discovered_via, active, ...}).
Only India / remote-India postings are kept and mapped to the common schema. A board that
returns 404 is marked inactive in companies.json (not deleted).

Usage: python run_ats.py [--out DIR] [--companies companies.json] [--limit N]
"""
from __future__ import annotations

import html
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

import config
from harness import SCHEMA

HEADERS = {"User-Agent": "job-alerts/1.0 (+https://github.com/Keshav242002/new-job-alerts)",
           "Accept": "application/json"}
ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true",
}
# Lighter variants for slug verification (no descriptions).
VERIFY_ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json&limit=200",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}

# City/country names only: a bare "IN" would also match US addresses like "Indianapolis, IN".
INDIA_RE_I = re.compile(
    r"\bindia\b|bengaluru|bangalore|gurugram|gurgaon|noida|\bdelhi\b|\bncr\b|\bpune\b|mumbai|hyderabad|chennai|"
    r"kolkata|ahmedabad|\bkochi\b|jaipur|chandigarh|\bindore\b|coimbatore|thiruvananthapuram|trivandrum|mysore|mysuru",
    re.I)
TAG_RE = re.compile(r"<[^>]+>")


def is_india(*locations: str | None) -> bool:
    """True if any location string names India or an Indian city (incl. 'Remote - India')."""
    text = " | ".join(l for l in locations if l)
    return bool(INDIA_RE_I.search(text))


def _text(s: str | None) -> str | None:
    if not s:
        return None
    s = TAG_RE.sub(" ", html.unescape(html.unescape(s)))
    return re.sub(r"\s+", " ", s).strip()[: config.DESCRIPTION_MAX_CHARS] or None


def _date(v) -> object:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, tz=timezone.utc).date()
    return pd.to_datetime(v, errors="coerce", utc=True).date() if pd.notna(pd.to_datetime(v, errors="coerce")) else None


# ------------------------------------------------------------------- per-ATS parsing

def parse_greenhouse(data: dict, company: str) -> list[dict]:
    out = []
    for j in data.get("jobs", []):
        locs = [(j.get("location") or {}).get("name")] + [o.get("name") for o in j.get("offices") or []]
        if not is_india(*locs):
            continue
        loc = (j.get("location") or {}).get("name")
        # first_published = original post date; updated_at changes on any edit (approximate only)
        published = j.get("first_published")
        out.append({"title": j.get("title"), "company": company, "location": loc,
                    "is_remote": bool(re.search(r"remote", loc or "", re.I)),
                    "date_posted": _date(published or j.get("updated_at")),
                    "date_approx": not published,
                    "job_url": j.get("absolute_url"), "job_type": None,
                    "salary": None, "description": _text(j.get("content"))})
    return out


def parse_lever(data: list, company: str) -> list[dict]:
    out = []
    for j in data if isinstance(data, list) else []:
        cat = j.get("categories") or {}
        locs = [cat.get("location")] + list(cat.get("allLocations") or [])
        if not (is_india(*locs) or j.get("country") == "IN"):
            continue
        sal = j.get("salaryRange") or {}
        salary = (f"{sal.get('currency', '')} {sal.get('min', '')}-{sal.get('max', '')} {sal.get('interval', '')}".strip()
                  if sal.get("min") or sal.get("max") else None)
        out.append({"title": j.get("text"), "company": company, "location": cat.get("location"),
                    "is_remote": (j.get("workplaceType") == "remote"),
                    "date_posted": _date(j.get("createdAt")), "job_url": j.get("hostedUrl"),
                    "job_type": cat.get("commitment"), "salary": salary,
                    "description": _text(j.get("descriptionPlain") or j.get("description"))})
    return out


def parse_ashby(data: dict, company: str) -> list[dict]:
    out = []
    for j in data.get("jobs", []) if isinstance(data, dict) else []:
        if j.get("isListed") is False:
            continue
        sec = [s.get("location") for s in j.get("secondaryLocations") or []]
        country = (((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry"))
        if not (is_india(j.get("location"), *sec) or country in ("India", "IN")):
            continue
        comp = (j.get("compensation") or {}).get("compensationTierSummary") or None
        out.append({"title": j.get("title"), "company": company, "location": j.get("location"),
                    "is_remote": bool(j.get("isRemote")) or j.get("workplaceType") == "Remote",
                    "date_posted": _date(j.get("publishedAt")), "job_url": j.get("jobUrl"),
                    "job_type": j.get("employmentType"), "salary": comp,
                    "description": _text(j.get("descriptionPlain") or j.get("descriptionHtml"))})
    return out


PARSERS = {"greenhouse": parse_greenhouse, "lever": parse_lever, "ashby": parse_ashby}


def fetch_board(sess: requests.Session, ats: str, slug: str, verify: bool = False) -> tuple[int | None, object]:
    """-> (http_status, json or None). Retries 429 with backoff."""
    url = (VERIFY_ENDPOINTS if verify else ENDPOINTS)[ats].format(slug=slug)
    for wait in [0] + config.BACKOFF_429:
        if wait:
            time.sleep(wait)
        try:
            r = sess.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException:
            return None, None
        if r.status_code == 429:
            continue
        if r.status_code != 200:
            return r.status_code, None
        try:
            return 200, r.json()
        except ValueError:
            return r.status_code, None
    return 429, None


def board_exists(ats: str, data) -> bool:
    if ats == "lever":
        return isinstance(data, list)
    return isinstance(data, dict) and "jobs" in data


# ---------------------------------------------------------------------- collector

def collect(companies_path: Path, limit: int | None = None) -> tuple[pd.DataFrame, list[dict], dict]:
    companies = json.loads(companies_path.read_text())
    active = [c for c in companies if c.get("active", True)][:limit]
    sess = requests.Session()
    rows, recs = [], []
    stats = {"scanned": {}, "dead": []}
    for i, c in enumerate(active):
        if i:
            time.sleep(random.uniform(*config.ATS_DELAY_RANGE))
        t0 = time.perf_counter()
        status, data = fetch_board(sess, c["ats"], c["board_slug"])
        stats["scanned"][c["ats"]] = stats["scanned"].get(c["ats"], 0) + 1
        jobs, st, reason = [], "error", ""
        if status == 404:
            c["active"] = False
            c["inactive_since"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            stats["dead"].append(f"{c['ats']}:{c['board_slug']}")
            st, reason = "error", "404 board not found (marked inactive)"
        elif status == 429:
            st, reason = "blocked", "429 after retries"
        elif status == 200 and board_exists(c["ats"], data):
            jobs = PARSERS[c["ats"]](data, c["name"])
            st = "ok" if jobs else "empty"
        else:
            reason = f"HTTP {status}"
        for j in jobs:
            j |= {"source_lib": "ats", "site": "ats", "search_term": f"ats:{c['ats']}",
                  "search_location": "India", "min_exp": None, "max_exp": None}
        rows += jobs
        recs.append({"lib": "ats", "site": "ats", "search_term": c["ats"], "search_location": c["board_slug"],
                     "status": st, "rows": len(jobs), "runtime_s": round(time.perf_counter() - t0, 1),
                     "reason": reason, "n429": 1 if status == 429 else 0, "attempts": 1})
    if stats["dead"]:
        companies_path.write_text(json.dumps(companies, indent=2, ensure_ascii=False) + "\n")
    df = pd.DataFrame(rows, columns=SCHEMA) if rows else pd.DataFrame(columns=SCHEMA)
    return df, recs, stats
