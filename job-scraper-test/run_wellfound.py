import argparse
from pathlib import Path

import pandas as pd

import config
import wellfound

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".", help="output dir")
    ap.add_argument("--terms", help="override search terms (semicolon-separated)")
    ap.add_argument("--locations", help="override locations (semicolon-separated)")
    ap.add_argument("--max-pages", type=int, default=config.WELLFOUND_MAX_PAGES)
    args = ap.parse_args()

    terms = args.terms.split(";") if args.terms else config.SEARCH_TERMS
    locs = args.locations.split(";") if args.locations else config.LOCATIONS
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    raw, recs = wellfound.scrape(terms, locs, args.max_pages)
    raw.to_csv(out / "raw_wellfound.csv", index=False)
    pd.DataFrame(recs).to_csv(out / "runs_wellfound.csv", index=False)
    print(f"\nwrote {out / 'raw_wellfound.csv'} ({len(raw)} rows) and runs_wellfound.csv")
