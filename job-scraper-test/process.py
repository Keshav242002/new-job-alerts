"""Post-process raw_jobspy.csv + raw_jobdrop.csv -> merged.csv, excluded.csv, report.md.

Usage: python process.py [dir]      (dir defaults to "."; use "smoke" for the smoke run)
pandas only, so it runs in either venv.
"""
from __future__ import annotations

import re
import string
from urllib.parse import parse_qsl, urlencode, urlsplit
import sys
from pathlib import Path

import pandas as pd

import config

LIBS = ["jobspy", "jobdrop"]
HERE = Path(__file__).resolve().parent

# ------------------------------------------------------------------ experience

_Y = r"(?:years?|yrs?)"
_N = r"(\d{1,2}(?:\.\d)?)"
EXP_PATTERNS = [
    # "3-5 years", "2 to 4 yrs", "3+ - 6 years"
    (re.compile(rf"{_N}\s*\+?\s*(?:-|–|—|to)\s*{_N}\s*\+?\s*{_Y}", re.I), "range"),
    # "minimum 4 years", "at least 3 yrs", "min. of 2 years"
    (re.compile(rf"(?:minimum|min\.?|at\s*least|atleast)\s*(?:of\s*)?{_N}\s*\+?\s*{_Y}", re.I), "min"),
    # "5+ yrs", "5 + years"
    (re.compile(rf"{_N}\s*\+\s*{_Y}", re.I), "min"),
    # "4 years of experience", "2 yrs exp", "3 years' experience"
    (re.compile(rf"{_N}\s*{_Y}'?\s*(?:of\s*)?(?:relevant\s*|professional\s*|hands[- ]on\s*|industry\s*|work\s*)?(?:experience|exp\b)", re.I), "min"),
    # "experience: 2-4 years" handled by range; "experience of 3 years"
    (re.compile(rf"experience\s*(?:of|:)?\s*{_N}\s*\+?\s*{_Y}", re.I), "min"),
]


def parse_experience(text: str) -> tuple[float | None, float | None]:
    """Return (min, max) years. With several mentions, the smallest minimum wins
    (conservative: we'd rather keep a job than wrongly exclude it)."""
    if not isinstance(text, str) or not text:
        return None, None
    cands: list[tuple[float, float | None]] = []
    for rx, kind in EXP_PATTERNS:
        for m in rx.finditer(text):
            lo = float(m.group(1))
            hi = float(m.group(2)) if kind == "range" else None
            if lo > 30 or (hi is not None and (hi > 40 or hi < lo)):
                continue
            cands.append((lo, hi))
    if not cands:
        return None, None
    return min(cands, key=lambda c: (c[0], c[1] is None))


def add_experience(df: pd.DataFrame) -> pd.DataFrame:
    """Prefer structured min/max from the board; else regex over title + description."""
    df = df.copy()
    has = df["min_exp"].notna()
    df["exp_source"] = has.map({True: "structured", False: None})
    parsed = (df.loc[~has, "title"].fillna("") + " \n " + df.loc[~has, "description"].fillna("")).map(parse_experience)
    df.loc[~has, "min_exp"] = parsed.map(lambda t: t[0])
    df.loc[~has, "max_exp"] = parsed.map(lambda t: t[1])
    df.loc[~has & df["min_exp"].notna(), "exp_source"] = "regex"
    return df


# ------------------------------------------------------------------------ dates

# Naukri job URLs end in a 12-digit id whose first 6 digits are DDMMYY of creation.
# Checked in the smoke run: matched date_posted within 1 day for 28/32 rows; the rest
# were reposts (date_posted later), so the id date is a lower bound.
NAUKRI_ID_RE = re.compile(r"-(\d{6})\d{6}(?:[?#/]|$)")


def add_dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date_posted"] = pd.to_datetime(df["date_posted"], errors="coerce")
    df["date_source"] = df["date_posted"].notna().map({True: "board", False: None})
    miss = df["date_posted"].isna() & df["site"].eq("naukri")
    ids = df.loc[miss, "job_url"].astype(str).str.extract(NAUKRI_ID_RE)[0]
    derived = pd.to_datetime(ids, format="%d%m%y", errors="coerce")
    df.loc[miss, "date_posted"] = derived
    df.loc[miss & df["date_posted"].notna(), "date_source"] = "naukri_id"
    return df


# --------------------------------------------------------------- normalization

_PUNCT = str.maketrans({c: " " for c in string.punctuation})
COMPANY_SUFFIXES = {
    "private", "limited", "pvt", "ltd", "inc", "llc", "llp", "corp", "corporation",
    "co", "technologies", "technology", "india",
}
CITY_ALIASES = {
    "gurgaon": "gurugram", "bengaluru": "bangalore", "new delhi": "delhi ncr",
    "delhi": "delhi ncr", "bombay": "mumbai", "madras": "chennai",
}


def _norm(s) -> str:
    if not isinstance(s, str):
        return ""
    return " ".join(s.lower().translate(_PUNCT).split())


def norm_company(s) -> str:
    toks = _norm(s).split()
    while toks and toks[-1] in COMPANY_SUFFIXES:
        toks.pop()
    return " ".join(toks)


def norm_city(loc) -> str:
    if not isinstance(loc, str) or not loc.strip():
        return ""
    city = _norm(loc.split(",")[0])
    return CITY_ALIASES.get(city, city)


_TRACKING_PARAMS = {"src", "sid", "xid", "from", "refid", "trackingid", "ref", "position", "pagenum", "trk"}


def norm_url(u) -> str:
    """Keep identifying query params (Indeed ?jk=, Glassdoor ?jl=, Google ?q=), drop tracking ones."""
    if not isinstance(u, str) or not u.strip():
        return ""
    sp = urlsplit(u.strip())
    q = sorted((k.lower(), v) for k, v in parse_qsl(sp.query)
               if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS)
    return f"{sp.netloc.lower()}{sp.path.rstrip('/').lower()}" + (f"?{urlencode(q)}" if q else "")


# ---------------------------------------------------------------------- dedupe

def dedupe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.reset_index(drop=True)
    df["_key"] = df["company"].map(norm_company) + "|" + df["title"].map(_norm) + "|" + df["location"].map(norm_city)
    df["_url"] = df["job_url"].map(norm_url)
    df["_src"] = df["source_lib"] + ":" + df["site"]

    parent = list(range(len(df)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for col in ("_key", "_url"):
        for _, idx in df.groupby(col).groups.items():
            idx = list(idx)
            if col == "_key" and df.at[idx[0], "_key"].startswith("|"):
                continue  # no company -> don't merge on key alone
            for j in idx[1:]:
                parent[find(j)] = find(idx[0])
    # Jobgether re-posts other companies' jobs: merge a Jobgether row into a non-Jobgether row with
    # the same normalized title (3+ words, so generic titles like "Software Engineer" don't merge).
    is_jg = df["company"].fillna("").str.contains("jobgether", case=False)
    titles = df["title"].map(_norm)
    if is_jg.any():
        other_by_title = {}
        for i in df.index[~is_jg]:
            other_by_title.setdefault(titles[i], i)
        for i in df.index[is_jg]:
            j = other_by_title.get(titles[i])
            if j is not None and len(titles[i].split()) >= 3:
                parent[find(i)] = find(j)
    df["_grp"] = [find(i) for i in range(len(df))]

    df["_score"] = (df[["date_posted", "description", "min_exp", "company", "location"]].notna().sum(axis=1)
                    + (df["exp_source"] == "structured") * 2
                    - is_jg.astype(int) * 10)  # never keep the Jobgether copy when the original is present
    rows = []
    for _, g in df.groupby("_grp", sort=False):
        best = g.sort_values("_score", ascending=False).iloc[0].copy()
        best["sources"] = ";".join(sorted(g["_src"].unique()))
        best["libs"] = ";".join(sorted(g["source_lib"].unique()))
        best["search_terms"] = ";".join(sorted(g["search_term"].dropna().unique()))
        best["dup_count"] = len(g)
        best["urls"] = ";".join(sorted({u for u in g["_url"] if u}))
        # experience: structured beats regex; otherwise smallest parsed min
        s = g[g["exp_source"] == "structured"]
        pool = s if len(s) else g[g["min_exp"].notna()]
        if len(pool):
            r = pool.sort_values("min_exp").iloc[0]
            best["min_exp"], best["max_exp"], best["exp_source"] = r["min_exp"], r["max_exp"], r["exp_source"]
        # date: newest across copies (a repost elsewhere means the job is live)
        dated = g[g["date_posted"].notna()]
        if len(dated):
            r = dated.sort_values("date_posted").iloc[-1]
            best["date_posted"], best["date_source"] = r["date_posted"], r["date_source"]
        longest = g["description"].dropna()
        if len(longest):
            best["description"] = max(longest, key=len)
        rows.append(best)
    out = pd.DataFrame(rows).drop(columns=["_key", "_url", "_src", "_grp", "_score"])
    return out.reset_index(drop=True)


# ----------------------------------------------------------- exclusion / flags

FULLSTACK_RE = re.compile(r"full[\s\-]?stack", re.I)
REACT_RE = re.compile(r"\breact(?:\.?js)?\b(?!\s*native)", re.I)
FLUTTER_RE = re.compile(r"\bflutter\b", re.I)
ANGULAR_VUE_RE = re.compile(r"\b(?:angular(?:\.?js)?|vue(?:\.?js)?)\b", re.I)
SENIOR_RE = re.compile(r"\b(?:senior|sr\.?|lead|staff|principal)\b", re.I)
MOBILE_OTHER_RE = re.compile(r"\b(?:react\s*native|kotlin|swift)\b", re.I)


# On-topic if the title (or, failing that, the description) matches the keyword family
# of any search term that found the job. Flag name kept as approved: off_topic_title.
_DEV = r"developer|engineer|sde|programmer"
TERM_FAMILIES = {
    "Full Stack Developer": r"full[\s\-]?stack|mern|mean",
    "Flutter Developer": r"flutter",
    "Mobile Application Developer": r"mobile|android|ios|flutter|\bapp(?:lication)? developer",
    "SDE 1": rf"\bsde\b|software|{_DEV}",
    "SDE 2": rf"\bsde\b|software|{_DEV}",
    "Software Developer": rf"software|{_DEV}",
    "Software Engineer": rf"software|{_DEV}",
    "Backend Developer": r"back[\s\-]?end|server[\s\-]?side|api",
    "Django Developer": r"django|python",
    "Python Developer": r"python|django|fastapi|flask",
    "FastAPI Developer": r"fastapi|python",
}
TERM_FAMILY_RE = {k: re.compile(v, re.I) for k, v in TERM_FAMILIES.items()}


def on_topic(title: str, desc: str, search_terms: str) -> bool:
    terms = [t for t in str(search_terms).split(";") if t in TERM_FAMILY_RE]
    return not terms or any(TERM_FAMILY_RE[t].search(title) or TERM_FAMILY_RE[t].search(desc) for t in terms)


SKILL_RE = re.compile(r"\b(?:flutter|dart|python|django|fast\s?api|react(?:\.?js)?)\b", re.I)
# Job type from the board's field when present, else from the title ("smart contract" is a skill, not a type).
JOBTYPE_TITLE_RE = re.compile(
    r"\b(?:intern(?:ship)?s?|apprentice(?:ship)?s?|part[\s\-]?time|freelanc\w*|(?<!smart )contract(?:ual|or)?|c2h|"
    r"contract[\s\-]to[\s\-]hire)\b", re.I)
JOBTYPE_FIELD_RE = re.compile(r"part[\s\-]?time|intern|contract|freelanc|temporary", re.I)
FRESHER_TITLE_RE = re.compile(r"\b(?:intern(?:ship)?s?|trainee|freshers?)\b", re.I)
SENIORITY_RE = re.compile(r"\b(?:senior|sr\.?|lead|staff|principal|architect|manager)\b", re.I)

# Staffing / recruitment agencies: flag only (they often re-post client jobs).
STAFFING_COMPANY_RE = re.compile(
    r"staffing|recruit|consult|manpower|placement|talent\s*(?:solutions|acquisition|hub)|hr\s*(?:solutions|services)|"
    r"outsourc|workforce|headhunt|search\s*partners|human\s*resource|hunting\s*cube|\bhire\b|hiring\s*(?:solutions|services)|"
    r"jobgether",
    re.I)
STAFFING_DESC_RE = re.compile(
    r"(?:hiring|recruiting)\s+(?:for|on behalf of)\s+(?:one of\s+)?(?:our|a)\s+(?:leading\s+)?client|"
    r"on behalf of (?:our|a|one of our) (?:client|partner)|our client,? (?:a|an|is)|for (?:a|our) (?:leading|reputed) client",
    re.I)

# My skills in a title: rescues a title from off_role_title.
MY_SKILL_TITLE_RE = re.compile(r"\b(?:flutter|dart|python|django|fast\s?api|react(?:\.?js)?|full[\s\-]?stack)\b", re.I)
# other_stack_title exemption: a named skill — "Full Stack" alone does NOT exempt (e.g. "Java Full Stack Developer").
STACK_EXEMPT_TITLE_RE = re.compile(r"\b(?:flutter|dart|python|django|fast\s?api|react(?:\.?js)?)\b", re.I)
# Title names a different primary stack.
OTHER_STACK_TITLE_RE = re.compile(
    r"\bjava\b(?!\s*script)|\.net\b|\bdot\s?net\b|\bc#|\bc\+\+|\bgolang\b|\bgo\s+(?:developer|engineer|lang)\b|\bphp\b|"
    r"\bruby\b|\brails\b|\bsalesforce\b|\bsap\b|\bangular(?:\.?js)?\b|\bvue(?:\.?js)?\b|\bkotlin\b|\bswift\b|\bios\b|"
    r"\bandroid\b", re.I)
# Non-dev role families.
OFF_ROLE_TITLE_RE = re.compile(
    r"\bsupport\b|\bnetwork(?:ing)?\b|\bsecurity\b|\bqa\b|\bquality\s+assurance\b|\btest(?:ing|er)?\b|\bsdet\b|"
    r"\bautomation\s+test|\bdevops\b|\bsre\b|site\s+reliability|\bplatform\b|\bdata\s+analyst\b|\bsales\b|"
    r"\bconsultant\b|\badministrator\b|\badmin\b", re.I)
AI_ML_TITLE_RE = re.compile(
    r"\b(?:ai|ml|gen\s?ai|llm|machine\s+learning|deep\s+learning|data\s+scien\w*|applied\s+scien\w*|nlp|computer\s+vision)\b",
    re.I)
PYTHON_RE = re.compile(r"\bpython\b", re.I)
# Allowed locations (any listed city matches). Remote = is_remote or "remote"/"work from home" in location.
ALLOWED_CITY_RE = re.compile(
    r"bangalore|bengaluru|gurugram|gurgaon|\bnoida\b|greater\s+noida|\bdelhi\b|new\s+delhi|\bncr\b|ghaziabad|faridabad|"
    r"\bpune\b|mumbai|navi\s+mumbai|\bthane\b|hyderabad|chennai", re.I)
REMOTE_LOC_RE = re.compile(r"remote|work\s*from\s*home|\bwfh\b", re.I)


def location_check(location, is_remote) -> str:
    """-> 'ok', 'unclear' (exactly India / blank: keep + flag) or 'excluded'."""
    loc = location.strip() if isinstance(location, str) else ""
    remote = is_remote is True or str(is_remote).strip().lower() == "true"
    if ALLOWED_CITY_RE.search(loc) or remote or REMOTE_LOC_RE.search(loc):
        return "ok"
    if loc == "" or loc.lower() in ("india", "in", "ind"):
        return "unclear"
    return "excluded"


# Stable rule names (exclusion_reason may append details in parentheses).
RULES = ["older_than_window", "location", "no_skill_match", "job_type", "fresher_only", "seniority_title",
         "other_stack_title", "off_role_title", "min_exp>4", "fullstack_angular_vue_only"]


def excluded_job_type(title: str, job_type) -> str | None:
    if isinstance(job_type, str) and job_type.strip():
        jt = job_type.lower()
        if JOBTYPE_FIELD_RE.search(jt) and not re.search(r"full[\s\-]?time", jt):
            return job_type.strip()
    m = JOBTYPE_TITLE_RE.search(title)
    return f"title: {m.group(0)}" if m else None


def apply_rules(df: pd.DataFrame, ref_date: pd.Timestamp, window_hours=None) -> pd.DataFrame:
    """window_hours: a number, or a per-row Series (e.g. the widest window among a job's sources)."""
    df = df.copy()
    window_hours = config.HOURS_OLD if window_hours is None else window_hours
    text = df["title"].fillna("") + " \n " + df["description"].fillna("")
    hours = (window_hours.reindex(df.index) if isinstance(window_hours, pd.Series)
             else pd.Series(float(window_hours), index=df.index))
    cutoffs = (ref_date - pd.to_timedelta(hours, unit="h")).dt.normalize()  # date_posted is day-granular
    job_types = df["job_type"] if "job_type" in df.columns else pd.Series([None] * len(df), index=df.index)
    reasons, flags = [], []
    approxs = df["date_approx"] if "date_approx" in df.columns else pd.Series([None] * len(df), index=df.index)
    remotes = df["is_remote"] if "is_remote" in df.columns else pd.Series([None] * len(df), index=df.index)
    for t, title, mn, mx, dp, st, desc, jt, cutoff, approx, company, loc, rem in zip(
            text, df["title"].fillna(""), df["min_exp"], df["max_exp"], df["date_posted"],
            df["search_terms"], df["description"].fillna(""), job_types, cutoffs, approxs, df["company"].fillna(""),
            df["location"], remotes):
        r = []
        if pd.notna(dp) and dp < cutoff:
            r.append(f"older_than_window ({dp.date()})")
        loc_status = location_check(loc, rem)
        if loc_status == "excluded":
            r.append(f"location ({str(loc)[:40]})")
        has_desc = bool(desc.strip())
        if not SKILL_RE.search(t) and has_desc:
            r.append("no_skill_match")
        if (why := excluded_job_type(title, jt)):
            r.append(f"job_type ({why})")
        if (pd.notna(mx) and mx == 0) or FRESHER_TITLE_RE.search(title):
            r.append("fresher_only")
        if SENIORITY_RE.search(title) and not (pd.notna(mx) and mx <= 4):
            r.append(f"seniority_title ({SENIORITY_RE.search(title).group(0)})")
        if pd.notna(mn) and mn > 4:
            r.append(f"min_exp>4 ({mn:g})")
        if FULLSTACK_RE.search(t) and ANGULAR_VUE_RE.search(t) and not REACT_RE.search(t) and not FLUTTER_RE.search(t):
            r.append("fullstack_angular_vue_only")
        my_skill_in_title = bool(MY_SKILL_TITLE_RE.search(title))
        if (m := OTHER_STACK_TITLE_RE.search(title)) and not STACK_EXEMPT_TITLE_RE.search(title):
            r.append(f"other_stack_title ({m.group(0).strip()})")
        if (m := OFF_ROLE_TITLE_RE.search(title)) and not my_skill_in_title:
            r.append(f"off_role_title ({m.group(0).strip()})")
        reasons.append("; ".join(r))
        f = []
        if not has_desc and not SKILL_RE.search(title):
            f.append("no_description")
        if pd.isna(mn):
            f.append("exp_unknown")
            if SENIOR_RE.search(title):
                f.append("senior_title_no_exp")
        if MOBILE_OTHER_RE.search(t) and not FLUTTER_RE.search(t):
            f.append("mobile_non_flutter")
        if pd.isna(dp):
            f.append("date_unknown")
        elif approx is True or str(approx).lower() == "true":
            f.append("date_approx")
        if not on_topic(title, desc, st):
            f.append("off_topic_title")
        if STAFFING_COMPANY_RE.search(company) or STAFFING_DESC_RE.search(desc):
            f.append("staffing_agency")
        if loc_status == "unclear":
            f.append("location_unclear")
        if AI_ML_TITLE_RE.search(title) and PYTHON_RE.search(t):
            f.append("ai_ml_role")
        flags.append(";".join(f))
    df["exclusion_reason"] = reasons
    df["flags"] = flags
    return df


# ---------------------------------------------------------------------- report

def gha_verdict(site: str, lib: str, bad_share: float) -> str:
    if lib == "jobdrop" and site in config.GOOGLE_SERP_SITES:
        return "at-risk (Google SERP in headless browser)"
    if lib == "jobdrop" and site in config.BROWSER_SITES:
        return "uncertain (headless browser, datacenter IP)"
    if bad_share >= 0.5:
        return "at-risk (blocked locally)"
    if site == "linkedin":
        return "uncertain (LinkedIn throttles datacenter IPs)"
    return "likely"


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.values) + " |")
    return "\n".join(lines)


def pct(n, d) -> str:
    return f"{100 * n / d:.0f}%" if d else "–"


def main(d: Path) -> None:
    raws, runs = [], []
    for lib in LIBS:
        if (d / f"raw_{lib}.csv").exists():
            raws.append(pd.read_csv(d / f"raw_{lib}.csv"))
            runs.append(pd.read_csv(d / f"runs_{lib}.csv"))
    raw = add_dates(add_experience(pd.concat(raws, ignore_index=True)))
    runs = pd.concat(runs, ignore_index=True)
    runs["reason"] = runs["reason"].fillna("")
    for c in ("n429", "attempts"):
        if c not in runs.columns:
            runs[c] = 0
    runs[["n429", "attempts"]] = runs[["n429", "attempts"]].fillna(0).astype(int)
    # reference "now" = when the scrape finished (raw file mtime), not when we post-process
    ref_date = pd.Timestamp.fromtimestamp(max((d / f"raw_{l}.csv").stat().st_mtime
                                              for l in LIBS if (d / f"raw_{l}.csv").exists()))

    merged_all = apply_rules(dedupe(raw), ref_date)
    for df_ in (merged_all,):
        df_["date_posted"] = df_["date_posted"].dt.date
    excluded = merged_all[merged_all["exclusion_reason"] != ""]
    kept = merged_all[merged_all["exclusion_reason"] == ""].drop(columns=["exclusion_reason"])
    kept.to_csv(d / "merged.csv", index=False)
    excluded.to_csv(d / "excluded.csv", index=False)
    stale_mask = excluded["exclusion_reason"].str.contains("older_than_window")
    smoke = d.name == "smoke"

    R: list[str] = [f"# Job scraper comparison — {'smoke test' if smoke else 'full run'}\n",
                    f"Run finished {ref_date:%Y-%m-%d %H:%M}. "
                    f"{len(config.SMOKE_TERMS if smoke else config.SEARCH_TERMS)} terms × "
                    f"{len(config.SMOKE_LOCATIONS if smoke else config.LOCATIONS)} locations "
                    f"(LinkedIn: {', '.join(config.LINKEDIN_LOCATIONS) if not smoke else 'same'} only), "
                    f"hours_old={config.HOURS_OLD}, results_wanted={config.RESULTS_WANTED}/query. "
                    f"The 72h cut is applied here on date_posted (day granularity) to every site.\n",
                    f"Totals: {len(raw)} raw rows → {len(merged_all)} after dedupe → "
                    f"**{len(kept)} kept**, {len(excluded)} excluded "
                    f"({int(stale_mask.sum())} of them only/also for being older than {config.HOURS_OLD}h).\n"]

    # per lib per site
    rows = []
    kept_src = kept["sources"].str.split(";")
    stale_src = excluded.loc[stale_mask, "sources"].str.split(";")
    for (lib, site), g in runs.groupby(["lib", "site"], sort=False):
        st = g["status"].value_counts()
        bad = sum(st.get(k, 0) for k in ("blocked", "captcha", "timeout", "error", "skipped"))
        fails = ", ".join(f"{k}:{v}" for k, v in st.items() if k != "ok")
        tag = f"{lib}:{site}"
        rows.append({
            "lib": lib, "site": site,
            "queries": len(g),
            "raw": int((raw["source_lib"].eq(lib) & raw["site"].eq(site)).sum()),
            "stale >72h": int(stale_src.map(lambda s: tag in s).sum()),
            "kept": int(kept_src.map(lambda s: tag in s).sum()),
            "ok": int(st.get("ok", 0)),
            "non-ok (empty/blocked/captcha/timeout/error/skipped)": fails or "–",
            "failure type": "ok" if st.get("ok", 0) >= len(g) / 2 else st.drop("ok", errors="ignore").idxmax(),
            "429s": int(g["n429"].sum()),
            "runtime_total_min": round(g["runtime_s"].sum() / 60, 1),
            "runtime_median_s": round(g["runtime_s"].median(), 1),
            "likely OK on GitHub Actions?": gha_verdict(site, lib, bad / len(g)),
        })
    site_df = pd.DataFrame(rows)
    R += ["## Per library × site\n",
          "Query statuses: ok / empty (no rows, no error) / blocked (429/403) / captcha / timeout / error / "
          "skipped (after 3 consecutive blocks). \"failure type\" is ok when ≥50% of queries returned rows, "
          "otherwise the most common non-ok status. Kept = age-filtered, non-excluded, deduped jobs this source contributed to.\n",
          md_table(site_df), ""]

    errs = runs[runs["status"].isin(["blocked", "captcha", "timeout", "error", "skipped"])]
    if len(errs):
        R += ["### Failure samples\n",
              md_table(errs.groupby(["lib", "site", "status"]).agg(n=("reason", "size"), sample=("reason", "first"))
                       .reset_index().assign(sample=lambda x: x["sample"].str.replace("|", "/").str.split().str.join(" ").str[:160])), ""]

    # 429s
    l429 = runs.groupby("lib").agg(**{"429 responses": ("n429", "sum"),
                                      "queries with ≥1 429": ("n429", lambda x: int((x > 0).sum())),
                                      "backoff retries": ("attempts", lambda x: int((x - 1).clip(lower=0).sum()))})
    R += ["## HTTP 429 (rate limit) per library\n",
          f"LinkedIn backoff: {config.LINKEDIN_DELAY_RANGE[0]}–{config.LINKEDIN_DELAY_RANGE[1]}s between queries; "
          f"on 429 with no rows, retry after {', '.join(map(str, config.BACKOFF_429))}s.\n",
          md_table(l429.reset_index()), ""]

    # dates
    dq = []
    for lib in LIBS:
        g = raw[raw["source_lib"] == lib]
        dq.append({"lib": lib, "raw rows": len(g),
                   "board date": int((g["date_source"] == "board").sum()),
                   "Naukri-ID-derived date": int((g["date_source"] == "naukri_id").sum()),
                   "no date": int(g["date_posted"].isna().sum())})
    R += ["## Posting dates\n",
          "Naukri job ids encode creation date (DDMMYY); used only when the board gave no date. "
          "Smoke check: id date matched date_posted within 1 day for 28/32 rows (others were reposts), "
          "so id dates can make a reposted job look older than it is.\n",
          md_table(pd.DataFrame(dq)),
          f"\nKept jobs with ID-derived date: {int((kept['date_source'] == 'naukri_id').sum())}; "
          f"kept with no date (flag date_unknown): {int(kept['date_posted'].isna().sum())}.", ""]

    # naukri head-to-head
    def site_stats(lib, site):
        tag = f"{lib}:{site}"
        other = f"{'jobdrop' if lib == 'jobspy' else 'jobspy'}:{site}"
        r = runs[(runs["lib"] == lib) & (runs["site"] == site)]
        g = raw[raw["source_lib"].eq(lib) & raw["site"].eq(site)]
        k = kept_src.map(lambda s: tag in s)
        return {
            "lib": f"{lib} ({'browser' if lib == 'jobdrop' else 'HTTP'})",
            "raw": len(g),
            "stale >72h": int(stale_src.map(lambda s: tag in s).sum()),
            "kept": int(k.sum()),
            "kept off-topic": int((k & kept["flags"].str.contains("off_topic_title")).sum()),
            f"unique vs other lib's {site}": int(kept_src.map(lambda s: tag in s and other not in s).sum()),
            "id-derived dates (raw)": int((g["date_source"] == "naukri_id").sum()),
            "ok queries": f"{(r['status'] == 'ok').sum()}/{len(r)}",
            "runtime_total_min": round(r["runtime_s"].sum() / 60, 1),
        }
    R += ["## Naukri head-to-head\n",
          md_table(pd.DataFrame([site_stats("jobspy", "naukri"), site_stats("jobdrop", "naukri")])), ""]
    if (d / "naukri_param_test.md").exists() or (HERE / "naukri_param_test.md").exists():
        R += [((d / "naukri_param_test.md") if (d / "naukri_param_test.md").exists()
               else HERE / "naukri_param_test.md").read_text(), ""]

    # overlap (kept = deduped, age-filtered, not excluded)
    both = int(kept["libs"].eq("jobdrop;jobspy").sum())
    only = {lib: int(kept["libs"].eq(lib).sum()) for lib in LIBS}
    n = len(kept)
    R += ["## Overlap (kept, age-filtered jobs after dedupe)\n",
          md_table(pd.DataFrame([
              {"bucket": "found by both", "jobs": both, "share": pct(both, n)},
              {"bucket": "unique to jobspy", "jobs": only["jobspy"], "share": pct(only["jobspy"], n)},
              {"bucket": "unique to jobdrop", "jobs": only["jobdrop"], "share": pct(only["jobdrop"], n)},
          ])), ""]

    # data quality
    q = []
    for lib in LIBS:
        g = raw[raw["source_lib"] == lib]
        q.append({"lib": lib, "raw rows": len(g),
                  "% date_posted (board)": pct((g["date_source"] == "board").sum(), len(g)),
                  "% date incl. Naukri id": pct(g["date_posted"].notna().sum(), len(g)),
                  "% description": pct(g["description"].notna().sum(), len(g)),
                  "% parsed experience": pct(g["min_exp"].notna().sum(), len(g)),
                  "of which structured": pct((g["exp_source"] == "structured").sum(), len(g))})
    R += ["## Data quality (raw rows)\n", md_table(pd.DataFrame(q)), ""]

    # exclusions & flags
    ex = excluded["exclusion_reason"].str.split("; ").explode().str.replace(r" \(.*\)", "", regex=True).value_counts()
    fl = kept["flags"].fillna("").str.split(";").explode().replace("", pd.NA).dropna().value_counts()
    R += ["## Exclusions and flags\n",
          "Excluded (a job can have several reasons): " + (", ".join(f"{k} {v}" for k, v in ex.items()) or "none") + "  ",
          "Flags on kept jobs: " + (", ".join(f"{k} {v}" for k, v in fl.items()) or "none"), ""]

    # top companies
    top = kept.assign(c=kept["company"].map(norm_company)).query("c != ''").groupby("c").agg(
        company=("company", "first"), jobs=("c", "size")).sort_values("jobs", ascending=False).head(10)
    R += ["## Top 10 companies (kept)\n", md_table(top.reset_index(drop=True)), ""]

    # recommendation
    share = {lib: only[lib] / n if n else 0 for lib in LIBS}
    kept_by = {lib: int(kept["libs"].str.contains(lib).sum()) for lib in LIBS}
    drop = site_df[~site_df["failure type"].isin(["ok", "empty"])]
    R += ["## Recommendation\n",
          "Rule: keep both if each library contributes ≥15% of kept (age-filtered) jobs uniquely; "
          "otherwise keep the better one; drop any site a library is blocked on.\n",
          f"- Unique share of kept jobs: jobspy {share['jobspy']:.0%} ({only['jobspy']}), "
          f"jobdrop {share['jobdrop']:.0%} ({only['jobdrop']}); total kept {n}."]
    if all(v >= 0.15 for v in share.values()):
        R.append("- **Keep both** — each clears the 15% unique bar.")
    else:
        best = max(LIBS, key=lambda l: kept_by[l])
        R.append(f"- **Keep {best}** only (kept jobs: jobspy {kept_by['jobspy']}, jobdrop {kept_by['jobdrop']}); "
                 f"the other doesn't clear the 15% unique bar.")
    risky = set(site_df.loc[site_df["likely OK on GitHub Actions?"].str.startswith("at-risk"), "lib"]
                + ":" + site_df.loc[site_df["likely OK on GitHub Actions?"].str.startswith("at-risk"), "site"])
    if risky:
        srcs = kept["sources"].str.split(";").map(lambda xs: [x for x in xs if x not in risky])
        alive = srcs.map(len) > 0
        libs_left = srcs[alive].map(lambda xs: sorted({x.split(":")[0] for x in xs}))
        n2 = int(alive.sum())
        only2 = {lib: int(libs_left.map(lambda l: l == [lib]).sum()) for lib in LIBS}
        verdict = "keep both still holds" if all(only2[l] / n2 >= 0.15 for l in LIBS) else "keep-both would NOT hold"
        R.append(f"- Sensitivity — without at-risk sources ({', '.join(sorted(risky))}): {n2} kept jobs; unique share "
                 f"jobspy {only2['jobspy'] / n2:.0%} ({only2['jobspy']}), jobdrop {only2['jobdrop'] / n2:.0%} "
                 f"({only2['jobdrop']}) → {verdict}.")
    for lib in LIBS:
        u = kept.loc[kept["libs"] == lib, "sources"].value_counts().head(4)
        R.append(f"- Unique-to-{lib} jobs by source: " + ", ".join(f"{k} {v}" for k, v in u.items()))
    if len(drop):
        R.append("- Drop (mostly failing in this run): " + ", ".join(f"{r['lib']}:{r['site']} ({r['failure type']})" for _, r in drop.iterrows()))
    at_risk = site_df[site_df["likely OK on GitHub Actions?"].str.startswith("at-risk")]
    if len(at_risk):
        R.append("- At risk on GitHub Actions: " + ", ".join(f"{r.lib}:{r.site}" for r in at_risk.itertuples()))

    R += ["", "## Failed in smoke test (not run in full matrix)\n",
          md_table(pd.DataFrame([{"lib": lib, "site": s, "reason": why}
                                 for lib, m in config.FAILED_IN_SMOKE.items() for s, why in m.items()])),
          "", "## Not run (by policy)\n",
          "- Bundled third-party API keys: " + ", ".join(config.DISABLED["bundled_keys"]),
          "- Not India-relevant: " + ", ".join(config.DISABLED["non_india"]), ""]

    (d / "report.md").write_text("\n".join(R))
    print("\n".join(R))


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
