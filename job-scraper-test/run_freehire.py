import argparse
import sys
from pathlib import Path

import pandas as pd

import config
import freehire


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".", help="output dir")
    ap.add_argument("--terms", help="override config.FREEHIRE_QUERIES (semicolon-separated)")
    ap.add_argument("--max-pages", type=int, default=config.FREEHIRE_MAX_PAGES, help="page cap per query/pass")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    queries = args.terms.split(";") if args.terms else config.FREEHIRE_QUERIES
    try:
        raw, recs = freehire.scrape(queries, config.FREEHIRE_PASSES, args.max_pages, config.FREEHIRE_PAGE_SIZE)
    except Exception as e:  # noqa: BLE001 — fail soft: no rows + an error rec, the pipeline marks freehire failed
        print(f"freehire failed: {type(e).__name__}: {e}", flush=True)
        raw = pd.DataFrame(columns=freehire.COLUMNS)
        recs = [{"lib": "freehire", "site": "freehire", "search_term": "*", "search_location": "*",
                 "status": "error", "rows": 0, "runtime_s": 0.0, "reason": f"{type(e).__name__}: {e}"[:200],
                 "n429": 0, "attempts": 0}]
    raw.to_csv(out / "raw_freehire.csv", index=False)
    pd.DataFrame(recs).to_csv(out / "runs_freehire.csv", index=False)
    runs = pd.DataFrame(recs)
    print(f"\nwrote {out / 'raw_freehire.csv'} ({len(raw)} rows) and runs_freehire.csv; "
          f"statuses: {runs['status'].value_counts().to_dict()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
