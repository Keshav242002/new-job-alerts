"""Volume + cost estimate for the production setup, from the saved comparison runs.

Re-applies process.py's rules to full/raw_jobspy.csv, full/raw_jobdrop.csv and
wf-local/raw_wellfound.csv restricted to the production sources, then writes
production_report.md: kept jobs/day, per-rule removals, per-term coverage and an
Actions-minutes estimate for the schedule in SCHEDULE.md.

Usage: python volume_report.py
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

import config
import process as P

HERE = Path(__file__).resolve().parent
RAW = [HERE / "full/raw_jobspy.csv", HERE / "full/raw_jobdrop.csv", HERE / "wf-local/raw_wellfound.csv"]
RUNS = [HERE / "full/runs_jobspy.csv", HERE / "full/runs_jobdrop.csv", HERE / "wf-local/runs_wellfound.csv"]
PROD = {v for v in config.PROD_SOURCES.values()}  # {(lib, site)}
WINDOW_H = 72  # the saved runs fetched 72h

# Per-job overhead measured on Actions (checkout, setup-python, pip, artifact upload) + ~10s job setup.
OVERHEAD_S = {"linkedin": 36 + 10, "jobspy": 22 + 10, "google": 37 + 10, "wellfound": 5 + 15 + 10, "process": 60}
# Steady-state incremental Wellfound: most role/location pages stop after page 1 (all ids seen).
WELLFOUND_INCREMENTAL_PAGES_PER_COMBO = 1.3
SUNDAYS_PER_MONTH = 30 / 7


def lane_wall_s(runs: pd.DataFrame, lib: str, site: str, delay: tuple[float, float]) -> float:
    """Query runtimes (include any 429 backoff sleeps) + polite delays between queries."""
    r = runs[(runs["lib"] == lib) & (runs["site"] == site)]
    return float(r["runtime_s"].sum()) + max(len(r) - 1, 0) * sum(delay) / 2


def billed_min(seconds: float) -> int:
    return math.ceil(seconds / 60)


def main() -> None:
    raw = pd.concat([pd.read_csv(p) for p in RAW], ignore_index=True)
    raw = raw[[(l, s) in PROD for l, s in zip(raw["source_lib"], raw["site"])]].reset_index(drop=True)
    runs = pd.concat([pd.read_csv(p) for p in RUNS], ignore_index=True)
    ref = pd.Timestamp.fromtimestamp(max(p.stat().st_mtime for p in RAW[:2]))  # end of the jobspy/jobdrop run

    raw = P.add_dates(P.add_experience(raw))
    merged = P.apply_rules(P.dedupe(raw), ref, WINDOW_H)
    merged["date_posted"] = pd.to_datetime(merged["date_posted"])
    kept = merged[merged["exclusion_reason"] == ""]
    excl = merged[merged["exclusion_reason"] != ""]
    out = HERE / "production_report.md"
    kept.to_csv(HERE / "full/merged_production.csv", index=False)
    excl.to_csv(HERE / "full/excluded_production.csv", index=False)

    R = ["# Production volume & cost estimate\n",
         f"Source data: the 2026-10-14 comparison runs (72h window), restricted to production sources "
         f"({', '.join(f'{l}:{s}' for l, s in sorted(PROD))}). Rules from process.py as of this report.\n",
         f"{len(raw)} raw rows → {len(merged)} after dedupe → **{len(kept)} kept**, {len(excl)} excluded.\n"]

    # 1. kept per day
    # only days entirely inside the fetch window (its first and last days are partial)
    first_full = (ref - pd.Timedelta(hours=WINDOW_H)).normalize() + pd.Timedelta(days=1)
    full_days = pd.date_range(first_full, ref.normalize() - pd.Timedelta(days=1), freq="D")
    by_day = kept.groupby(kept["date_posted"].dt.normalize()).size()
    per_day = [int(by_day.get(d, 0)) for d in full_days]
    est = sum(per_day) / len(per_day)
    src_rows = []
    for name, (lib, site) in config.PROD_SOURCES.items():
        tag = f"{lib}:{site}"
        k = kept[kept["sources"].str.split(";").map(lambda xs: tag in xs)]
        kd = k.groupby(k["date_posted"].dt.normalize()).size()
        r = runs[(runs["lib"] == lib) & (runs["site"] == site)]
        capped = int((r["rows"] >= config.RESULTS_WANTED).sum()) if lib != "wellfound" else None
        src_rows.append({"source": name, "kept (72h)": len(k),
                         "kept/day (avg full days)": round(sum(int(kd.get(d, 0)) for d in full_days) / len(full_days), 1),
                         "queries hitting 25-result cap": f"{capped}/{len(r)}" if capped is not None else "n/a (paged)"})
    R += ["## 1. Estimated kept jobs per day\n",
          f"Kept jobs by posting date over the full days in the window: "
          + ", ".join(f"{d:%b %d} {n}" for d, n in zip(full_days, per_day))
          + f" → **≈{est:.0f} kept jobs/day** (deduped across sources and terms; "
            f"partial days excluded: {(first_full - pd.Timedelta(days=1)):%b %d} {int(by_day.get(first_full - pd.Timedelta(days=1), 0))}, "
            f"{ref:%b %d} {int(by_day.get(ref.normalize(), 0))}). Based on {len(full_days)} weekday(s) only — weekend volume is likely lower.\n",
          P.md_table(pd.DataFrame(src_rows)),
          "\nSources overlap, so per-source figures sum to more than the total. Where queries hit the 25-result "
          "cap over a 72h window, a 24h window will lose less to the cap, so the real daily figure is likely somewhat "
          "higher for those sources. New jobs/day after `seen_jobs.csv` will be at or below this.\n"]

    # 2. per-rule removals
    reasons = excl["exclusion_reason"].str.split("; ").map(lambda rs: [x.split(" (")[0] for x in rs])
    rule_rows = []
    for rule in P.RULES:
        hit = reasons.map(lambda rs: rule in rs)
        sole = reasons.map(lambda rs: rs == [rule])
        rule_rows.append({"rule": rule, "jobs matching": int(hit.sum()), "removed by this rule alone": int(sole.sum())})
    nodesc_kept = int(kept["flags"].str.contains("no_description").sum())
    nodesc_all = int(merged["flags"].str.contains("no_description").sum())
    R += ["## 2. Jobs removed per rule\n",
          "A job can match several rules; \"alone\" = no other rule would have excluded it.\n",
          P.md_table(pd.DataFrame(rule_rows)),
          f"\n`no_description` flag (no description and no skill in title → kept instead of `no_skill_match`): "
          f"**{nodesc_kept} kept jobs** ({nodesc_all} across kept + excluded).",
          "Job type comes from the title only in this re-run (the saved CSVs predate the `job_type` column); "
          "future runs also use the board's job-type field.\n"]

    # 3. per-term
    terms = kept["search_terms"].fillna("").str.split(";")
    term_rows = [{"search term": t, "kept jobs": int(terms.map(lambda xs: t in xs).sum()),
                  "unique (no other term found it)": int(terms.map(lambda xs: xs == [t]).sum())}
                 for t in config.SEARCH_TERMS]
    R += ["## 3. Per search term (kept, deduped)\n", P.md_table(pd.DataFrame(term_rows)),
          "\nWellfound has no per-term pages for SDE 1 / SDE 2 / Software Engineer (all `software-engineer`) or "
          "Python / FastAPI (both `python-developer`), so its jobs are credited to every term sharing the page; "
          "those terms can't be \"unique\" for Wellfound jobs.\n"]

    # 4. Actions minutes
    li = lane_wall_s(runs, "jobdrop", "linkedin", config.LINKEDIN_DELAY_RANGE)
    ind = lane_wall_s(runs, "jobspy", "indeed", config.DELAY_RANGE)
    nk = lane_wall_s(runs, "jobspy", "naukri", config.DELAY_RANGE)
    gg = lane_wall_s(runs, "jobdrop", "google", config.DELAY_RANGE)
    wf_runs = runs[runs["lib"] == "wellfound"]
    sec_per_req = wf_runs["runtime_s"].sum() / max(wf_runs["attempts"].sum(), 1)
    combos = int((wf_runs["status"] != "skipped").sum())
    wf_full = float(wf_runs["runtime_s"].sum())
    wf_inc = combos * WELLFOUND_INCREMENTAL_PAGES_PER_COMBO * sec_per_req
    jobs = {
        "linkedin": li + OVERHEAD_S["linkedin"],
        "jobspy (indeed ∥ naukri)": max(ind, nk) + OVERHEAD_S["jobspy"],
        "google": gg + OVERHEAD_S["google"],
        "wellfound incremental": wf_inc + OVERHEAD_S["wellfound"],
        "wellfound full (Sun)": wf_full + OVERHEAD_S["wellfound"],
        "process + commit": OVERHEAD_S["process"],
    }
    billed = {k: billed_min(v) for k, v in jobs.items()}
    morning = sum(billed[k] for k in ["linkedin", "jobspy (indeed ∥ naukri)", "google", "wellfound incremental", "process + commit"])
    morning_sun = morning - billed["wellfound incremental"] + billed["wellfound full (Sun)"]
    evening = sum(billed[k] for k in ["linkedin", "jobspy (indeed ∥ naukri)", "process + commit"])
    monthly = 30 * (morning + evening) + SUNDAYS_PER_MONTH * (morning_sun - morning)
    job_rows = [{"job": k, "wall time (min)": round(v / 60, 1), "billed (min, rounded up)": billed[k]} for k, v in jobs.items()]
    R += ["## 4. GitHub Actions minutes (schedule in SCHEDULE.md)\n",
          "Wall time = query runtimes (incl. any 429 backoff) + polite delays between queries (sleep is billed) "
          "+ measured per-job overhead (checkout, setup-python, pip install, upload). Each job is billed separately "
          "and rounded up to the next minute; parallel jobs all count.\n",
          P.md_table(pd.DataFrame(job_rows)),
          f"\n- Morning run: **{morning} min** ({morning_sun} on Sundays, Wellfound full)",
          f"- Evening run: **{evening} min**",
          f"- **≈{monthly:,.0f} min/month** (30 days, {SUNDAYS_PER_MONTH:.1f} Sundays). GitHub Free includes 2,000 "
          f"min/month for private repos; public repos are not billed.",
          f"- Assumptions: LinkedIn delays {config.LINKEDIN_DELAY_RANGE[0]}–{config.LINKEDIN_DELAY_RANGE[1]}s, others "
          f"{config.DELAY_RANGE[0]}–{config.DELAY_RANGE[1]}s; jobdrop LinkedIn had 0 429s in the full run — each LinkedIn "
          f"query blocked through all retries would add {sum(config.BACKOFF_429) / 60:.0f} min. Incremental Wellfound "
          f"assumes {WELLFOUND_INCREMENTAL_PAGES_PER_COMBO} pages per role/location at {sec_per_req:.1f}s/page "
          f"({combos} role/location pages); the first incremental run (empty seen_jobs) walks up to 5 pages each.\n"]

    out.write_text("\n".join(R))
    print("\n".join(R))


if __name__ == "__main__":
    main()
