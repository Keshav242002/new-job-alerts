"""Production run: scrape the run's sources in parallel, process, dedupe against seen_jobs.

    python pipeline.py --run morning --data-dir ../data --public-dir ..

Data dir (private repo checkout): seen_jobs.csv, new_jobs.csv, run_history.csv,
last_run_queries.csv, state/last_success.json. Public dir: runs/latest.md (counts only — no titles,
companies or URLs; it doubles as the schedule keep-alive commit).

Each scraper runs as its own process in its library's venv; the fetch window per
source comes from window.py. A source is recorded as successful (advancing its
window) when at least half of its queries returned ok/empty.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import json

import config
import process as P
import seen as S
import window as W

HERE = Path(__file__).resolve().parent
STATUSES = ["ok", "empty", "blocked", "captcha", "timeout", "error", "skipped"]


def build_commands(sources: list[str], windows: dict[str, int], args, work: Path) -> dict[str, tuple[list[str], list[str]]]:
    """-> {process name: (argv, sources it covers)}"""
    jd, js = args.py_jobdrop, args.py_jobspy
    extra = []
    if args.terms:
        extra += ["--terms", args.terms]
    if args.locations:
        extra += ["--locations", args.locations]
    cmds = {}
    if "linkedin" in sources:
        cmds["linkedin"] = ([jd, "run_jobdrop.py", "--sites", "linkedin", "--out", str(work / "linkedin"),
                             "--hours-old", str(windows["linkedin"])] + extra, ["linkedin"])
    jobspy_sites = [s for s in ("indeed", "naukri") if s in sources]
    if jobspy_sites:
        # one process, parallel lanes; naukri ignores hours_old (JOBSPY_NAUKRI_RELEVANCE)
        w = windows["indeed"] if "indeed" in sources else windows["naukri"]
        cmds["jobspy"] = ([js, "run_jobspy.py", "--sites", ",".join(jobspy_sites), "--out", str(work / "jobspy"),
                           "--hours-old", str(w)] + extra, jobspy_sites)
    if "google" in sources:
        cmds["google"] = ([jd, "run_jobdrop.py", "--sites", "google", "--out", str(work / "google"),
                           "--hours-old", str(windows["google"])] + extra, ["google"])
    if "wellfound" in sources:
        cmds["wellfound"] = ([js, "run_wellfound.py", "--mode", args.wellfound_mode, "--out", str(work / "wellfound"),
                              "--seen", str(args.data_dir / "seen_jobs.csv")] + extra, ["wellfound"])
    if "ats" in sources:
        cmds["ats"] = ([js, "run_ats.py", "--out", str(work / "ats")], ["ats"])
    return cmds


def run_parallel(cmds: dict, work: Path, timeout_s: int) -> dict[str, int | None]:
    procs, logs, codes = {}, {}, {}
    for name, (argv, _) in cmds.items():
        logs[name] = open(work / f"{name}.console.log", "w")
        procs[name] = subprocess.Popen(argv, cwd=HERE, stdout=logs[name], stderr=subprocess.STDOUT)
        print(f"started {name}", flush=True)
    t0 = time.time()
    while procs:
        for name, p in list(procs.items()):
            if p.poll() is not None:
                codes[name] = p.returncode
                print(f"finished {name} (exit {p.returncode}) after {(time.time() - t0) / 60:.1f} min", flush=True)
                del procs[name]
        if time.time() - t0 > timeout_s:
            for name, p in procs.items():
                p.kill()
                codes[name] = None
                print(f"killed {name} after {timeout_s / 60:.0f} min", flush=True)
            break
        time.sleep(5)
    for f in logs.values():
        f.close()
    return codes


def collect(work: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raws, runs = [], []
    for d in sorted(p for p in work.iterdir() if p.is_dir()):
        for f in d.glob("raw_*.csv"):
            df = pd.read_csv(f)
            if len(df):
                raws.append(df)
        for f in d.glob("runs_*.csv"):
            runs.append(pd.read_csv(f))
    raw = pd.concat(raws, ignore_index=True) if raws else pd.DataFrame(columns=["source_lib", "site"])
    runs = pd.concat(runs, ignore_index=True) if runs else pd.DataFrame(columns=["lib", "site", "status"])
    return raw, runs


def site_summary(runs: pd.DataFrame, sources: list[str], codes: dict, cmds: dict) -> pd.DataFrame:
    rows = []
    for s in sources:
        lib, site = config.PROD_SOURCES[s]
        r = runs[(runs["lib"] == lib) & (runs["site"] == site)]
        st = r["status"].value_counts()
        proc = next(n for n, (_, covers) in cmds.items() if s in covers)
        counted = len(r) - int(st.get("skipped", 0)) if site == "wellfound" else len(r)
        good = int(st.get("ok", 0) + st.get("empty", 0))
        rows.append({
            "source": s, "queries": len(r), **{k: int(st.get(k, 0)) for k in STATUSES},
            "rows": int(r["rows"].sum()) if len(r) else 0,
            "429s": int(r["n429"].sum()) if "n429" in r and len(r) else 0,
            "browser_retries": int(r["browser_retries"].sum()) if "browser_retries" in r and len(r) else 0,
            "runtime_min": round(float(r["runtime_s"].sum()) / 60, 1) if len(r) else 0.0,
            "process_exit": codes.get(proc),
            "success": bool(counted) and good / counted >= 0.5 and codes.get(proc) == 0,
        })
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", choices=list(config.PROD_RUNS), required=True)
    ap.add_argument("--data-dir", type=Path, required=True, help="private data repo checkout")
    ap.add_argument("--public-dir", type=Path, help="public repo root (writes runs/latest.md)")
    ap.add_argument("--work-dir", type=Path, default=HERE / "work")
    ap.add_argument("--py-jobspy", default=str(HERE / "venv-jobspy/bin/python"))
    ap.add_argument("--py-jobdrop", default=str(HERE / "venv-jobdrop/bin/python"))
    ap.add_argument("--wellfound-mode", default="auto", choices=["auto", "incremental", "full"])
    ap.add_argument("--sources", help="override the run's sources (comma-separated)")
    ap.add_argument("--terms", help="override search terms (semicolon-separated; for testing)")
    ap.add_argument("--locations", help="override non-LinkedIn locations (semicolon-separated; for testing)")
    ap.add_argument("--timeout-min", type=int, default=150)
    args = ap.parse_args()
    args.data_dir = args.data_dir.resolve()

    now = pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None)
    state = args.data_dir / "state" / "last_success.json"
    sources = args.sources.split(",") if args.sources else config.PROD_RUNS[args.run]
    windows = {s: W.window_hours(s, now.to_pydatetime().replace(tzinfo=timezone.utc), state) for s in sources}
    print(f"run={args.run} sources={sources} windows(h)={windows}", flush=True)

    work = args.work_dir.resolve()
    if work.exists():
        for p in sorted(work.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    work.mkdir(parents=True, exist_ok=True)

    cmds = build_commands(sources, windows, args, work)
    codes = run_parallel(cmds, work, args.timeout_min * 60)
    raw, runs = collect(work)
    summary = site_summary(runs, sources, codes, cmds)

    # ---- process: rules with each job's widest source window, then dedupe against seen_jobs
    tag_to_source = {f"{lib}:{site}": s for s, (lib, site) in config.PROD_SOURCES.items()}
    if len(raw):
        raw = P.add_dates(P.add_experience(raw))
        merged = P.dedupe(raw)
        row_window = merged["sources"].str.split(";").map(
            lambda tags: max(windows.get(tag_to_source.get(t), config.MIN_WINDOW_HOURS) for t in tags))
        merged = P.apply_rules(merged, now, row_window)
    else:
        merged = pd.DataFrame(columns=["exclusion_reason", "urls", "company", "title", "location"])
    seen_path = args.data_dir / "seen_jobs.csv"
    seen = S.load(seen_path)
    is_new = S.match_new(merged, seen) if len(merged) else pd.Series(dtype=bool)
    kept_mask = merged["exclusion_reason"] == ""
    new_jobs = merged[kept_mask & is_new].copy()
    src_lists = merged["sources"].fillna("").str.split(";") if len(merged) else pd.Series(dtype=object)
    for col, mask in (("kept", kept_mask), ("new", kept_mask & is_new)):
        summary[col] = [int((mask & src_lists.map(lambda xs, t=f"{config.PROD_SOURCES[s][0]}:{config.PROD_SOURCES[s][1]}": t in xs)).sum())
                        if len(merged) else 0 for s in summary["source"]]

    # ---- write private outputs (state uses the run's start time; "finished" is the real end time)
    stamp = pd.Timestamp(datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cols = ["title", "company", "location", "is_remote", "date_posted", "job_url", "job_type", "min_exp", "max_exp",
            "salary", "flags", "sources", "search_terms", "description"]
    out = new_jobs.reindex(columns=cols)
    if len(out):
        out["date_posted"] = pd.to_datetime(out["date_posted"]).dt.date
        out["description"] = out["description"].fillna("").str.slice(0, config.NEW_JOBS_DESCRIPTION_CHARS)
    out.insert(0, "found_utc", stamp)
    out.insert(1, "run", args.run)
    out.to_csv(args.data_dir / "new_jobs.csv", index=False)
    S.update(merged, seen, is_new, now).to_csv(seen_path, index=False)
    if "ats" in sources and len(new_jobs):
        companies_path = HERE / "companies.json"
        companies = json.loads(companies_path.read_text())
        ats_new = new_jobs[new_jobs["sources"].str.split(";").map(lambda xs: "ats:ats" in xs)]
        counts = ats_new["company"].fillna("").str.lower().value_counts()
        for c in companies:
            c["kept_jobs_total"] = int(c.get("kept_jobs_total", 0)) + int(counts.get(c["name"].lower(), 0))
        companies_path.write_text(json.dumps(companies, indent=2, ensure_ascii=False) + "\n")
    ok_sources = summary.loc[summary["success"], "source"].tolist()
    if ok_sources:
        W.mark_success(ok_sources, now.to_pydatetime().replace(tzinfo=timezone.utc), state)
    hist = summary.assign(run_utc=stamp, run=args.run, window_h=summary["source"].map(windows))
    # per-query statuses of this run (private): for debugging a degrading source
    runs.assign(run_utc=stamp, run=args.run).to_csv(args.data_dir / "last_run_queries.csv", index=False)
    hist_path = args.data_dir / "run_history.csv"
    hist.to_csv(hist_path, mode="a", index=False, header=not hist_path.exists())

    # ---- public, counts-only summary
    totals = (f"raw rows {len(raw)} → deduped {len(merged)} → kept {int(kept_mask.sum())} "
              f"(excluded {int((~kept_mask).sum())}) → **new {len(new_jobs)}** "
              f"(already seen {int((kept_mask & ~is_new).sum())})")
    failed = summary.loc[~summary["success"], "source"].tolist()
    md = [f"# Latest run\n", f"- Finished: {stamp} (UTC)", f"- Run: {args.run}",
          f"- Windows (h): " + ", ".join(f"{s} {w}" for s, w in windows.items()),
          f"- {totals}", f"- Failed sources: {', '.join(failed) if failed else 'none'}", "",
          P.md_table(summary.drop(columns=["skipped"]) if "skipped" in summary else summary), ""]
    ats_runs = runs[runs["lib"] == "ats"] if len(runs) else runs
    if len(ats_runs):
        per = ats_runs.groupby("search_term").agg(companies=("status", "size"),
                                                   with_india_jobs=("rows", lambda r: int((r > 0).sum())),
                                                   india_jobs=("rows", "sum"),
                                                   errors=("status", lambda s: int((s == "error").sum())))
        md += ["ATS boards scanned:", "", P.md_table(per.reset_index().rename(columns={"search_term": "ats"})), ""]
    text = "\n".join(md)
    print(text, flush=True)
    if args.public_dir:
        (args.public_dir / "runs").mkdir(parents=True, exist_ok=True)
        (args.public_dir / "runs" / "latest.md").write_text(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text)
    # exit: 0 all sources ok, 2 some failed, 1 all failed (the workflow fails visibly on non-zero)
    (work / "failed_sources.txt").write_text(",".join(failed))
    return 1 if not ok_sources else (2 if failed else 0)


if __name__ == "__main__":
    sys.exit(main())
