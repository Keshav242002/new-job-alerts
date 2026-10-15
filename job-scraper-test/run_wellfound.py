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
                    help="incremental: up to 5 pages; full: up to 10 pages (both stop early only when a page "
                         "returns no jobs); auto: full on Sundays (IST), else incremental")
    ap.add_argument("--max-pages", type=int, help="override the mode's page cap")
    args = ap.parse_args()

    mode = resolve_mode(args.mode)
    max_pages = args.max_pages or (config.WELLFOUND_FULL_MAX_PAGES if mode == "full"
                                   else config.WELLFOUND_INCREMENTAL_MAX_PAGES)
    print(f"wellfound mode={mode} max_pages={max_pages}")

    terms = args.terms.split(";") if args.terms else config.SEARCH_TERMS
    locs = args.locations.split(";") if args.locations else config.LOCATIONS
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    raw, recs = wellfound.scrape(terms, locs, max_pages)
    raw.to_csv(out / "raw_wellfound.csv", index=False)
    pd.DataFrame(recs).to_csv(out / "runs_wellfound.csv", index=False)
    print(f"\nwrote {out / 'raw_wellfound.csv'} ({len(raw)} rows) and runs_wellfound.csv")
