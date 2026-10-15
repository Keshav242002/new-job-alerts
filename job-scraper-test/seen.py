"""seen_jobs.csv: every job the pipeline has ever seen (kept or excluded).

A job from this run is "seen" if its dedupe key (normalized company|title|city) or any
of its normalized URLs matches an earlier entry. Excluded jobs are recorded too, so they
aren't re-reported every run.
Entries not seen for SEEN_RETENTION_DAYS are pruned (a re-posted old job would then be
age-filtered anyway).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import config
import process as P

SEEN_COLS = ["key", "urls", "first_seen_utc", "last_seen_utc", "status"]


def job_key(df: pd.DataFrame) -> pd.Series:
    company = df["company"].map(P.norm_company)
    key = company + "|" + df["title"].map(P._norm) + "|" + df["location"].map(P.norm_city)
    return key.where(company != "", "")  # no company -> match on URL only


def load(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path, dtype=str, keep_default_na=False)[SEEN_COLS]
    return pd.DataFrame(columns=SEEN_COLS)


def match_new(merged: pd.DataFrame, seen: pd.DataFrame) -> pd.Series:
    """True for jobs never seen before."""
    seen_keys = set(seen["key"]) - {""}
    seen_urls = {u for us in seen["urls"] for u in us.split(";") if u}
    keys = job_key(merged)
    urls = merged["urls"].fillna("").str.split(";")
    old = keys.isin(seen_keys) | urls.map(lambda us: any(u in seen_urls for u in us if u))
    return ~old


def update(merged: pd.DataFrame, seen: pd.DataFrame, is_new: pd.Series, now: pd.Timestamp) -> pd.DataFrame:
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    keys = job_key(merged)
    urls = merged["urls"].fillna("")
    status = merged["exclusion_reason"].map(lambda r: "kept" if not r else "excluded: " + r.split(" (")[0].split(";")[0])

    # refresh last_seen for re-seen entries
    hit_keys = set(keys[~is_new]) - {""}
    hit_urls = {u for us in urls[~is_new] for u in us.split(";") if u}
    seen = seen.copy()
    rehit = seen["key"].isin(hit_keys) | seen["urls"].map(lambda us: any(u in hit_urls for u in us.split(";") if u))
    seen.loc[rehit, "last_seen_utc"] = stamp

    new_rows = pd.DataFrame({"key": keys[is_new], "urls": urls[is_new], "first_seen_utc": stamp,
                             "last_seen_utc": stamp, "status": status[is_new]})
    out = pd.concat([seen, new_rows], ignore_index=True)
    cutoff = (now - pd.Timedelta(days=config.SEEN_RETENTION_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return out[out["last_seen_utc"] >= cutoff]
