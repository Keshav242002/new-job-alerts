import argparse
from pathlib import Path

import pandas as pd

import ats

HERE = Path(__file__).resolve().parent

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".", help="output dir")
    ap.add_argument("--companies", default=str(HERE / "companies.json"))
    ap.add_argument("--limit", type=int, help="only the first N active companies (testing)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    raw, recs, stats = ats.collect(Path(args.companies), args.limit)
    raw.to_csv(out / "raw_ats.csv", index=False)
    pd.DataFrame(recs).to_csv(out / "runs_ats.csv", index=False)
    runs = pd.DataFrame(recs)
    print(f"scanned per ATS: {stats['scanned']}; boards with India jobs: {int((runs['rows'] > 0).sum())}; "
          f"India jobs: {len(raw)}; errors: {int((runs['status'] == 'error').sum())}; "
          f"newly inactive (404): {len(stats['dead'])}")
