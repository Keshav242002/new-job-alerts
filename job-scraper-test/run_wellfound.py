import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import config
import wellfound

IST = timezone(timedelta(hours=5, minutes=30))


def resolve_mode(mode: str) -> str:
    if mode == "auto":
        return "full" if datetime.now(IST).weekday() == config.WELLFOUND_FULL_WEEKDAY else "incremental"
    return mode


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".", help="output dir")
    ap.add_argument("--terms", help="override search terms (semicolon-separated)")
    ap.add_argument("--locations", help="override locations (semicolon-separated)")
    ap.add_argument("--mode", choices=["incremental", "full", "auto"], default="auto",
                    help="incremental: <=5 pages, stop when a page is all already-seen; full: 10-page cap; "
                         "auto: full on Sundays (IST), else incremental")
    ap.add_argument("--seen", default="seen_jobs.csv", help="seen_jobs.csv (job_url column) for incremental mode")
    ap.add_argument("--max-pages", type=int, help="override the mode's page cap")
    args = ap.parse_args()

    mode = resolve_mode(args.mode)
    seen = None
    if mode == "incremental":
        p = Path(args.seen)
        seen = set()
        if p.exists():
            df = pd.read_csv(p, dtype=str, keep_default_na=False)
            col = "urls" if "urls" in df.columns else "job_url"
            seen = wellfound.seen_ids_from(u for us in df[col] for u in us.split(";"))
    max_pages = args.max_pages or (config.WELLFOUND_FULL_MAX_PAGES if mode == "full"
                                   else config.WELLFOUND_INCREMENTAL_MAX_PAGES)
    print(f"wellfound mode={mode} max_pages={max_pages} seen_ids={len(seen) if seen is not None else 'n/a'}")

    terms = args.terms.split(";") if args.terms else config.SEARCH_TERMS
    locs = args.locations.split(";") if args.locations else config.LOCATIONS
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    raw, recs = wellfound.scrape(terms, locs, max_pages, seen)
    raw.to_csv(out / "raw_wellfound.csv", index=False)
    pd.DataFrame(recs).to_csv(out / "runs_wellfound.csv", index=False)
    print(f"\nwrote {out / 'raw_wellfound.csv'} ({len(raw)} rows) and runs_wellfound.csv")
