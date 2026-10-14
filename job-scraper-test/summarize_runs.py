"""Print a per-site summary of runs_<lib>.csv (and append it to the GitHub step summary).

Usage: python summarize_runs.py <out_dir> <lib>
Writes <out_dir>/summary_<lib>.json for later comparison.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd

out_dir, lib = Path(sys.argv[1]), sys.argv[2]
runs = pd.read_csv(out_dir / f"runs_{lib}.csv")
runs["reason"] = runs["reason"].fillna("")

rows = []
for site, g in runs.groupby("site", sort=False):
    st = g["status"].value_counts()
    rows.append({
        "lib": lib, "site": site, "queries": len(g),
        "ok": int(st.get("ok", 0)), "rows": int(g["rows"].sum()),
        "statuses": ", ".join(f"{k}:{v}" for k, v in st.items()),
        "429s": int(g["n429"].sum()),
        "captcha": int((g["status"] == "captcha").sum()),
        "runtime_s": round(float(g["runtime_s"].sum()), 1),
        "sample_error": next((r for r in g["reason"] if r), "")[:150],
    })
df = pd.DataFrame(rows)

md = [f"### {lib}", "", "| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
md += ["| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in r) + " |" for r in df.itertuples(index=False)]
text = "\n".join(md) + "\n"
print(text)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
        f.write(text)
(out_dir / f"summary_{lib}.json").write_text(json.dumps(rows, indent=2))
