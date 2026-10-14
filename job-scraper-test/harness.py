"""Shared runner harness for run_jobspy.py / run_jobdrop.py.

Each (site, term, location) query runs in its own subprocess + process group so a
hung headless browser can be killed on timeout. Queries to the same site run
sequentially with a polite delay; different sites run in parallel "lanes", except
that all Google-SERP-driven sites share one lane so we never hit Google concurrently.
Each finished query is saved under <out>/parts/ so an interrupted run can resume.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import random
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pandas as pd

import config

SCHEMA = [
    "source_lib", "site", "title", "company", "location", "is_remote", "date_posted",
    "job_url", "min_exp", "max_exp", "description", "search_term", "search_location",
]

HERE = Path(__file__).resolve().parent


# --------------------------------------------------------------------------- worker

def _worker(lib: str, site: str, term: str, loc: str, out: str) -> None:
    """Runs inside the child process: one scrape_jobs call, pickled to `out`."""
    import importlib
    import logging

    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    mod = importlib.import_module(lib)

    remote = loc == "Remote"
    kwargs = dict(
        site_name=[site],
        search_term=term,
        google_search_term=config.google_query(term, loc),
        location="India" if remote else loc,
        is_remote=remote,
        results_wanted=config.RESULTS_WANTED,
        hours_old=config.HOURS_OLD,
        country_indeed=config.COUNTRY.lower(),
        verbose=2,
    )
    if lib == "jobspy":
        kwargs["fetch_description"] = config.FETCH_DESCRIPTION
        if site == "naukri" and config.JOBSPY_NAUKRI_RELEVANCE:
            # hours_old makes jobspy send jobAge+sort=f, which pads results with
            # off-topic fresh jobs; search by relevance and age-filter in process.py.
            kwargs["hours_old"] = None
    else:
        kwargs["linkedin_fetch_description"] = config.FETCH_DESCRIPTION

    meta: dict = {"error": None, "per_source": None}
    df = pd.DataFrame()
    try:
        df = mod.scrape_jobs(**kwargs)
        meta["per_source"] = df.attrs.get("per_source")
        src = (meta["per_source"] or {}).get(site) or {}
        meta["error"] = src.get("error")
    except Exception as e:  # noqa: BLE001
        meta["error"] = f"{type(e).__name__}: {e}"
    with open(out, "wb") as f:
        pickle.dump({"df": pd.DataFrame(df), "meta": meta}, f)


# ------------------------------------------------------------------- classification

CAPTCHA_RE = re.compile(r"captcha|challenge|cloudflare|datadome|unusual traffic|/sorry/|verify you are human|px-captcha", re.I)
BLOCKED_RE = re.compile(r"\b(429|403|999)\b|rate.?limit|too many requests|blocked|forbidden|access denied", re.I)
ERRLINE_RE = re.compile(r"(ERROR|Traceback|Exception|Error:)", re.I)


def classify(rows: int, timed_out: bool, error: str | None, log_text: str) -> tuple[str, str]:
    """-> (status, short reason). status in ok/empty/blocked/captcha/timeout/error."""
    # strip "YYYY-MM-DD HH:MM:SS,mmm" so millisecond values like ",429" don't look like HTTP codes
    err_lines = [re.sub(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}", "", l)
                 for l in log_text.splitlines() if ERRLINE_RE.search(l)]
    signal_text = " ".join([error or ""] + err_lines)
    reason = (error or (err_lines[-1] if err_lines else ""))[-220:]
    if timed_out:
        return "timeout", reason or "killed after timeout"
    if rows > 0:
        # partial data with an error (e.g. 429 on page 2) is still a usable result
        return "ok", reason
    if CAPTCHA_RE.search(signal_text):
        return "captcha", reason
    if BLOCKED_RE.search(signal_text):
        return "blocked", reason
    if error or err_lines:
        return "error", reason
    if re.search(r"extracted 0 raw cards", log_text):
        return "empty", "page loaded but 0 job cards (likely soft block of headless browser)"
    if re.search(r"discovered 0 ", log_text):
        return "empty", "0 Google SERP hits (likely silent Google block)"
    return "empty", ""


# -------------------------------------------------------------------- normalization

_EXP_RE = re.compile(r"(\d+)\s*(?:-|to)\s*(\d+)")


def _structured_exp(val) -> tuple[float | None, float | None]:
    """Parse a board-provided experience range like '2-5 Yrs' / '3 to 6 years'."""
    if not isinstance(val, str) or not val.strip():
        return None, None
    m = _EXP_RE.search(val)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+)", val)
    return (float(m.group(1)), None) if m else (None, None)


def normalize(df: pd.DataFrame, lib: str, site: str, term: str, loc: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=SCHEMA)
    g = lambda c: df[c] if c in df.columns else pd.Series([None] * len(df), index=df.index)  # noqa: E731
    exp = g("experience_range").map(_structured_exp)
    out = pd.DataFrame({
        "source_lib": lib,
        "site": g("site").fillna(site),
        "title": g("title"),
        "company": g("company") if "company" in df.columns else g("company_name"),
        "location": g("location"),
        "is_remote": g("is_remote"),
        "date_posted": pd.to_datetime(g("date_posted"), errors="coerce").dt.date,
        "job_url": g("job_url"),
        "min_exp": exp.map(lambda t: t[0]),
        "max_exp": exp.map(lambda t: t[1]),
        "description": g("description").map(
            lambda s: s[: config.DESCRIPTION_MAX_CHARS] if isinstance(s, str) else None),
        "search_term": term,
        "search_location": loc,
    })
    return out[SCHEMA]


# ------------------------------------------------------------------------- runner

def _slug(*parts: str) -> str:
    s = "__".join(parts)
    return re.sub(r"[^A-Za-z0-9]+", "_", s)[:80] + "_" + hashlib.md5(s.encode()).hexdigest()[:6]


RE_429 = re.compile(r"(?:status(?: code)?|response|HTTP)\D{0,12}429\b|\b429 Too Many|Too Many Requests", re.I)


def _attempt(lib: str, site: str, term: str, loc: str, raw_out: Path, log_path: Path):
    timeout = config.TIMEOUT_BROWSER if site in config.BROWSER_SITES and lib == "jobdrop" else config.TIMEOUT_HTTP
    cmd = [sys.executable, str(HERE / "harness.py"), "--worker", lib, site, term, loc, str(raw_out)]
    timed_out = False
    with open(log_path, "w") as logf:
        p = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, cwd=HERE, start_new_session=True)
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            p.wait()
    df, error = pd.DataFrame(), None
    if raw_out.exists():
        payload = pickle.loads(raw_out.read_bytes())
        df, error = payload["df"], payload["meta"]["error"]
        raw_out.unlink()
    elif not timed_out:
        error = f"worker exited {p.returncode} without output"
    log_text = log_path.read_text(errors="replace")
    n429 = len(RE_429.findall(log_text)) + len(RE_429.findall(error or ""))
    return df, error, timed_out, log_text, n429


def run_one(lib: str, site: str, term: str, loc: str, out_dir: Path) -> dict:
    parts = out_dir / "parts"
    logs = out_dir / "logs"
    parts.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    slug = _slug(lib, site, term, loc)
    rec_path = parts / f"{slug}.json"
    if rec_path.exists():  # resume
        return json.loads(rec_path.read_text())

    backoff = config.BACKOFF_429 if site in config.BACKOFF_SITES else []
    t0 = time.perf_counter()
    n429_total = 0
    for attempt in range(len(backoff) + 1):
        log_path = logs / (f"{slug}.log" if attempt == 0 else f"{slug}.retry{attempt}.log")
        df, error, timed_out, log_text, n429 = _attempt(lib, site, term, loc, parts / f"{slug}.raw.pkl", log_path)
        n429_total += n429
        if n429 and len(df) == 0 and attempt < len(backoff):
            print(f"  [{lib} {site}] 429 on {term!r}/{loc}; backing off {backoff[attempt]}s "
                  f"(retry {attempt + 1}/{len(backoff)})", flush=True)
            time.sleep(backoff[attempt])
            continue
        break
    runtime = time.perf_counter() - t0  # includes backoff sleeps

    norm = normalize(df, lib, site, term, loc)
    norm.to_pickle(parts / f"{slug}.pkl")
    status, reason = classify(len(norm), timed_out, error, log_text)
    rec = {
        "lib": lib, "site": site, "search_term": term, "search_location": loc,
        "status": status, "rows": len(norm), "runtime_s": round(runtime, 1), "reason": reason,
        "n429": n429_total, "attempts": attempt + 1,
    }
    rec_path.write_text(json.dumps(rec))
    return rec


def skip_one(lib: str, site: str, term: str, loc: str, out_dir: Path, reason: str) -> dict:
    parts = out_dir / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    slug = _slug(lib, site, term, loc)
    rec_path = parts / f"{slug}.json"
    if rec_path.exists():
        return json.loads(rec_path.read_text())
    pd.DataFrame(columns=SCHEMA).to_pickle(parts / f"{slug}.pkl")
    rec = {"lib": lib, "site": site, "search_term": term, "search_location": loc,
           "status": "skipped", "rows": 0, "runtime_s": 0.0, "reason": reason, "n429": 0, "attempts": 0}
    rec_path.write_text(json.dumps(rec))
    return rec


def site_queries(site: str, smoke: bool, terms=None, locations=None, linkedin_locations=None) -> list[tuple[str, str]]:
    terms = terms or (config.SMOKE_TERMS if smoke else config.SEARCH_TERMS)
    if smoke:
        locs = config.SMOKE_LOCATIONS
    elif site == "linkedin":
        locs = linkedin_locations or config.LINKEDIN_LOCATIONS
    else:
        locs = locations or config.LOCATIONS
    return [(t, l) for t in terms for l in locs]


def run(lib: str) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="1 term x 1 location, sites run one at a time")
    ap.add_argument("--sites", help="comma-separated subset of sites")
    ap.add_argument("--out", help="output dir (default: smoke/ or .)")
    ap.add_argument("--terms", help="override search terms (semicolon-separated)")
    ap.add_argument("--locations", help="override locations for non-LinkedIn sites (semicolon-separated)")
    ap.add_argument("--linkedin-locations", help="override LinkedIn locations (semicolon-separated)")
    args = ap.parse_args()

    sites = args.sites.split(",") if args.sites else config.SITES[lib]
    out_dir = Path(args.out or ("smoke" if args.smoke else ".")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # lanes: one per site; all Google-SERP sites share a lane; smoke = one lane total
    lanes: dict[str, list[str]] = {}
    for s in sites:
        key = "all" if args.smoke else ("google_serp" if s in config.GOOGLE_SERP_SITES else s)
        lanes.setdefault(key, []).append(s)

    lock = threading.Lock()
    records: list[dict] = []
    split = lambda v: v.split(";") if v else None  # noqa: E731
    jobs = {s: site_queries(s, args.smoke, split(args.terms), split(args.locations), split(args.linkedin_locations))
            for s in sites}
    total = sum(map(len, jobs.values()))

    def lane_worker(lane_sites: list[str]) -> None:
        first = True
        streak = {s: 0 for s in lane_sites}  # consecutive blocked/captcha per site
        # interleave the lane's sites query by query
        tasks = [(s, q) for i in range(max(len(jobs[s]) for s in lane_sites))
                 for s in lane_sites if i < len(jobs[s]) for q in [jobs[s][i]]]
        for site, (term, loc) in tasks:
            if streak[site] >= config.BLOCK_STREAK_LIMIT:
                rec = skip_one(lib, site, term, loc, out_dir,
                               f"skipped after {config.BLOCK_STREAK_LIMIT} consecutive blocks")
            else:
                if not first and not (out_dir / "parts" / f"{_slug(lib, site, term, loc)}.json").exists():
                    delay = config.LINKEDIN_DELAY_RANGE if site == "linkedin" else config.DELAY_RANGE
                    time.sleep(random.uniform(*delay))
                first = False
                rec = run_one(lib, site, term, loc, out_dir)
                streak[site] = streak[site] + 1 if rec["status"] in ("blocked", "captcha") else 0
            with lock:
                records.append(rec)
                print(f"[{lib} {len(records)}/{total}] {site:<15} {term!r:<32} {loc:<10} "
                      f"{rec['status']:<8} rows={rec['rows']:<3} {rec['runtime_s']:>6.1f}s "
                      f"429s={rec.get('n429', 0)} {rec['reason'][:80]}", flush=True)

    threads = [threading.Thread(target=lane_worker, args=(ls,)) for ls in lanes.values()]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # assemble outputs from all parts (covers resumed runs too)
    frames, recs = [], []
    for site in sites:
        for term, loc in jobs[site]:
            slug = _slug(lib, site, term, loc)
            recs.append(json.loads((out_dir / "parts" / f"{slug}.json").read_text()))
            part = pd.read_pickle(out_dir / "parts" / f"{slug}.pkl")
            if len(part):
                frames.append(part)
    raw = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=SCHEMA)
    raw.to_csv(out_dir / f"raw_{lib}.csv", index=False)
    pd.DataFrame(recs).to_csv(out_dir / f"runs_{lib}.csv", index=False)
    print(f"\nwrote {out_dir / f'raw_{lib}.csv'} ({len(raw)} rows) and runs_{lib}.csv")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker(*sys.argv[2:7])
