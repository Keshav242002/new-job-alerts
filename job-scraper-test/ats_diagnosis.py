"""Diagnose the ATS source: per-rule removals and engineering share per company.

Usage: python ats_diagnosis.py <raw_ats.csv> [window_hours]
"""
import re
import sys

import pandas as pd

import process as P

ENG_RE = re.compile(r"\b(?:engineer\w*|developer|sde|sdet|software|devops|sre|programmer|architect|full[\s-]?stack|"
                    r"back[\s-]?end|front[\s-]?end|mobile|android|ios|qa|data scientist|machine learning|ml)\b", re.I)


def main(path: str, window_h: float) -> None:
    raw = P.add_dates(P.add_experience(pd.read_csv(path)))
    ref = pd.Timestamp.now(tz="UTC").tz_localize(None)
    m = P.apply_rules(P.dedupe(raw), ref, window_h)
    reasons = m["exclusion_reason"].str.split("; ").map(lambda rs: [r.split(" (")[0] for r in rs if r])
    print(f"India ATS jobs {len(raw)} → deduped {len(m)} → kept {int((m['exclusion_reason'] == '').sum())} "
          f"(window {window_h:g}h)\n")
    rows = [{"rule": r, "jobs matching": int(reasons.map(lambda rs: r in rs).sum()),
             "removed by this rule alone": int(reasons.map(lambda rs: rs == [r]).sum())} for r in P.RULES]
    print(P.md_table(pd.DataFrame(rows)), "\n")
    raw["eng"] = raw["title"].fillna("").str.contains(ENG_RE)
    kept_by_co = m[m["exclusion_reason"] == ""]["company"].value_counts()
    top = raw.groupby("company").agg(india_jobs=("title", "size"), engineering=("eng", "sum")).sort_values(
        "india_jobs", ascending=False).head(15)
    top["non_engineering"] = top["india_jobs"] - top["engineering"]
    top["kept"] = [int(kept_by_co.get(c, 0)) for c in top.index]
    print(P.md_table(top.reset_index()), "\n")
    kept = m[m["exclusion_reason"] == ""]
    kc = kept.groupby("company").agg(kept=("title", "size")).sort_values("kept", ascending=False).head(15)
    kc["india_jobs"] = [int((raw["company"] == c).sum()) for c in kc.index]
    print("Top companies by kept jobs:\n")
    print(P.md_table(kc.reset_index()))
    print("\nflags on kept:", kept["flags"].str.split(";").explode().replace("", pd.NA).dropna().value_counts().to_dict())


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 72)
