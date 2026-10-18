"""freehire source: field mapping, pagination, fail-soft paths, experience fallback, pipeline wiring.

Run from job-scraper-test/:  pytest tests
"""
import json
from argparse import Namespace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
import requests

import config
import freehire
import pipeline
import process as P
import run_freehire
from harness import SCHEMA

FIXTURE = Path(__file__).parent / "fixtures" / "freehire_search.json"  # real agent-endpoint response, trimmed
REF = pd.Timestamp("2026-10-18")


class Resp:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code, self.body, self.headers = status, body, headers or {}

    def json(self):
        if self.body is None:
            raise ValueError("not json")
        return self.body


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(dict(params or {}))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def job(i, **kw):
    return {"public_slug": f"job-{i}", "title": "Python Developer", "company": "Acme", "location": "Bengaluru, India",
            "countries": ["in"], "work_mode": "onsite", "posted_at": "2026-10-16T00:00:00Z",
            "url": f"https://jobs.lever.co/acme/{i}?utm_source=freehire.me", "description": "Django APIs",
            "enrichment": {}, **kw}


def page(n, total, start=0):
    return Resp(body={"data": [job(i) for i in range(start, start + n)],
                      "meta": {"total": total, "limit": 50, "offset": start}})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(freehire.time, "sleep", sleeps.append)
    return sleeps


def scrape(responses, queries=("python",), passes=None, max_pages=3):
    sess = FakeSession(responses)
    raw, recs = freehire.scrape(list(queries), passes or {"India": {"countries": "IN"}}, max_pages, 50, sess)
    return raw, recs, sess


# ----------------------------------------------------------------------- mapping

def test_mapping_from_fixture():
    data = json.loads(FIXTURE.read_text())["data"]
    df = freehire.to_schema(data, "flutter", "India")
    assert list(df.columns) == freehire.COLUMNS
    cf, syn, fl = (df.iloc[i] for i in range(3))

    assert cf["job_url"] == "https://startup.jobs/sde-iii-frontend-mobile-captain-fresh-2-6358676"
    assert fl["job_url"].startswith("https://flutterbe.wd3.myworkdayjobs.com/") and "utm_" not in fl["job_url"]
    assert cf["date_posted"] == date(2026, 10, 16)
    assert (cf["is_remote"], syn["is_remote"], fl["is_remote"]) == (True, True, False)  # remote, remote, hybrid
    assert cf["location"] == "Bengaluru, India"
    assert syn["location"] == "Gurugram"  # empty location -> cities
    assert cf["job_type"] == "full-time"
    assert cf["exp_estimate"] == 4 and pd.isna(syn["exp_estimate"])
    assert pd.isna(cf["min_exp"]) and pd.isna(cf["max_exp"])
    assert (cf["source_lib"], cf["site"], cf["search_term"], cf["search_location"]) == \
        ("freehire", "freehire", "flutter", "India")
    for d in df["description"]:
        assert "\n" not in d and "  " not in d and "<" not in d and len(d) <= config.DESCRIPTION_MAX_CHARS


def test_mapping_through_process():
    data = json.loads(FIXTURE.read_text())["data"]
    df = freehire.to_schema(data, "flutter", "India")
    merged = P.apply_rules(P.dedupe(P.add_dates(P.add_experience(df))), REF)
    assert set(merged["sources"]) == {"freehire:freehire"}
    by = merged.set_index("company")
    # "4+ years of experience" in the description: the stated figure wins over the estimate
    assert by.loc["Captain Fresh", "min_exp"] == 4 and by.loc["Captain Fresh", "exp_source"] == "regex"
    assert "exp_estimated" not in by.loc["Captain Fresh", "flags"]
    # no figure in the description and no estimate
    assert "exp_unknown" in by.loc["Synthlane Technologies", "flags"]


def test_salary_and_url_helpers():
    assert freehire._salary({"salary_min": 3000000, "salary_max": 5000000, "salary_currency": "INR",
                             "salary_period": "year"}) == "INR 3000000-5000000 year"
    assert freehire._salary({"salary_min": 90000, "salary_currency": "USD"}) == "USD 90000"
    assert freehire._salary({}) is None
    assert freehire._clean_url("https://x.com/j?gh_jid=1&utm_source=freehire.me") == "https://x.com/j?gh_jid=1"
    assert freehire._clean_url("https://x.com/j/%28a%29") == "https://x.com/j/%28a%29"
    row = freehire.to_schema([job(1, url=None)], "q", "India").iloc[0]
    assert row["job_url"] == "https://freehire.me/jobs/job-1"


def test_open_to_india():
    assert freehire.open_to_india({"countries": []})
    assert freehire.open_to_india({"countries": ["us", "in"]})
    assert freehire.open_to_india({"countries": ["us"], "location": "Remote - India"})
    assert not freehire.open_to_india({"countries": ["us"], "location": "Austin, United States"})


def test_remote_pass_drops_jobs_not_open_to_india():
    body = {"data": [job(1, countries=[], work_mode="remote"), job(2, countries=["us"], location="Austin")],
            "meta": {"total": 2}}
    raw, recs, _ = scrape([Resp(body=body)], passes={"Remote": {"work_mode": "remote", "regions": "global"}})
    assert list(raw["job_url"]) == ["https://jobs.lever.co/acme/1"]
    assert "dropped 1 remote jobs" in recs[0]["reason"]


# -------------------------------------------------------------------- pagination

def test_request_params_and_offsets(no_sleep):
    _, recs, sess = scrape([page(50, 1000), page(50, 1000, 50), page(50, 1000, 100)],
                             queries=['"SDE 1"'])
    assert [c["offset"] for c in sess.calls] == [0, 50, 100]
    c = sess.calls[0]
    assert c["q"] == '"SDE 1"' and c["q_fields"] == "title" and c["countries"] == "IN" and c["limit"] == 50
    assert c["seniority_exclude"] == "senior,lead,staff,principal,c_level" and c["source_exclude"] == "telegram"
    assert c["posted_within_days"] == 14 and c["sort"] == "posted_at" and c["order"] == "desc"
    assert recs[0]["rows"] == 150 and "hit page cap (3)" in recs[0]["reason"]
    assert no_sleep == [config.FREEHIRE_DELAY_S] * 2  # between requests, not before the first


def test_stops_on_short_page():
    _, recs, sess = scrape([page(50, 500), page(10, 500, 50)])
    assert len(sess.calls) == 2 and recs[0]["rows"] == 60 and "page cap" not in recs[0]["reason"]


def test_stops_at_meta_total():
    _, recs, sess = scrape([page(50, 100), page(50, 100, 50)])
    assert len(sess.calls) == 2 and recs[0]["rows"] == 100 and "page cap" not in recs[0]["reason"]


def test_stops_when_page_has_no_new_jobs():
    _, recs, sess = scrape([page(50, 1000), page(50, 1000, 0)])
    assert len(sess.calls) == 2 and recs[0]["rows"] == 50


def test_page_error_keeps_earlier_rows():
    raw, recs, sess = scrape([page(50, 1000), Resp(400, {"error": "pagination too deep"})])
    assert len(sess.calls) == 2 and len(raw) == 50
    assert recs[0]["status"] == "ok" and recs[0]["reason"].startswith("page 2: error HTTP 400")


def test_empty_result():
    raw, recs, _ = scrape([Resp(body={"data": [], "meta": {"total": 0}})])
    assert recs[0]["status"] == "empty" and len(raw) == 0 and list(raw.columns) == freehire.COLUMNS


# --------------------------------------------------------------------- fail-soft

def test_connection_errors_never_raise():
    raw, recs, sess = scrape([requests.ConnectionError("down")] * 4, queries=("a", "b"))
    assert len(sess.calls) == 4  # each query: first try + 1 retry
    assert [r["status"] for r in recs] == ["error", "error"] and len(raw) == 0
    assert "after 1 retry" in recs[0]["reason"]


def test_timeout_status():
    _, recs, _ = scrape([requests.Timeout(), requests.Timeout()])
    assert recs[0]["status"] == "timeout"


def test_5xx_retried_once_then_ok(no_sleep):
    _, recs, sess = scrape([Resp(503), page(3, 3)])
    assert len(sess.calls) == 2 and recs[0]["status"] == "ok" and recs[0]["rows"] == 3
    assert config.FREEHIRE_RETRY_BACKOFF_S in no_sleep


def test_5xx_twice_is_error():
    _, recs, _ = scrape([Resp(503), Resp(502)])
    assert recs[0]["status"] == "error" and recs[0]["reason"] == "HTTP 502 (after 1 retry)"


def test_429_twice_is_blocked_and_honours_retry_after(no_sleep):
    _, recs, _ = scrape([Resp(429, headers={"Retry-After": "3"}), Resp(429)])
    assert recs[0]["status"] == "blocked" and recs[0]["n429"] == 2 and no_sleep == [3]


def test_ignored_params_is_error_without_retry():
    body = {"data": [job(1)], "meta": {"total": 1, "ignored_params": [{"param": "country", "did_you_mean": "countries"}]}}
    raw, recs, sess = scrape([Resp(body=body)])
    assert len(sess.calls) == 1 and recs[0]["status"] == "error" and "country" in recs[0]["reason"] and len(raw) == 0


def test_bad_json_is_error():
    _, recs, _ = scrape([Resp(200, None)])
    assert recs[0]["status"] == "error" and "not JSON" in recs[0]["reason"]


def test_code_error_in_one_query_keeps_others(monkeypatch):
    real = freehire.to_schema
    monkeypatch.setattr(freehire, "to_schema", lambda jobs, t, l: (_ for _ in ()).throw(KeyError("x"))
                        if t == "a" and jobs else real(jobs, t, l))
    raw, recs, _ = scrape([page(2, 2), page(2, 2)], queries=("a", "b"))
    assert recs[0]["status"] == "error" and "KeyError" in recs[0]["reason"]
    assert recs[1]["status"] == "ok" and recs[1]["rows"] == 2 and len(raw) == 2


def test_run_freehire_main_fails_soft(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("unexpected")
    monkeypatch.setattr(freehire, "scrape", boom)
    assert run_freehire.main(["--out", str(tmp_path)]) == 0
    raw = pd.read_csv(tmp_path / "raw_freehire.csv")
    runs = pd.read_csv(tmp_path / "runs_freehire.csv")
    assert len(raw) == 0 and list(raw.columns) == freehire.COLUMNS
    assert list(runs["status"]) == ["error"] and "RuntimeError" in runs["reason"][0]


# ------------------------------------------------------------- experience fallback

def _frame(rows):
    base = {c: None for c in freehire.COLUMNS}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_estimate_used_only_when_nothing_stated():
    df = P.add_experience(_frame([
        {"title": "Python Developer", "description": "3+ years of Django", "exp_estimate": 1},
        {"title": "Python Developer", "description": "Django APIs", "exp_estimate": 2},
        {"title": "Python Developer", "description": "Django APIs", "exp_estimate": None},
    ]))
    assert list(df["exp_source"][:2]) == ["regex", "estimate"] and pd.isna(df["exp_source"][2])
    assert list(df["min_exp"][:2]) == [3, 2] and pd.isna(df["min_exp"][2])


def test_estimate_flag_and_rules():
    df = _frame([{"source_lib": "freehire", "site": "freehire", "title": "Python Developer", "company": "Acme",
                  "location": "Pune", "description": "Django APIs", "search_term": "django", "exp_estimate": 5}])
    out = P.apply_rules(P.dedupe(P.add_dates(P.add_experience(df))), REF)
    assert "exp_estimated" in out["flags"][0] and "exp_unknown" not in out["flags"][0]
    assert "min_exp>4 (5)" in out["exclusion_reason"][0]


def test_frames_without_estimate_column_unchanged():
    df = _frame([{"title": "Python Developer", "description": "Django APIs"}]).drop(columns=["exp_estimate"])
    out = P.add_experience(df)
    assert "estimate" not in set(out["exp_source"].dropna()) and pd.isna(out["min_exp"][0])


def test_dedupe_prefers_stated_experience_over_estimate():
    common = {"title": "Python Developer", "company": "Acme", "location": "Pune", "search_term": "x"}
    df = _frame([{**common, "source_lib": "freehire", "site": "freehire", "description": "Django", "exp_estimate": 1},
                 {**common, "source_lib": "ats", "site": "ats", "description": "Django, 3+ years"}])
    out = P.dedupe(P.add_dates(P.add_experience(df)))
    assert len(out) == 1 and out["min_exp"][0] == 3 and out["exp_source"][0] == "regex"


# -------------------------------------------------------------- pipeline wiring

def test_pipeline_end_to_end_keeps_estimate(tmp_path, monkeypatch):
    """raw_freehire.csv with exp_estimate -> pipeline.collect -> process -> new_jobs.csv: the estimate fills
    min_exp and is flagged, other sources are untouched, and the column never reaches the output CSV."""
    today = datetime.now(timezone.utc).date()

    def fake_run_parallel(cmds, work, timeout_s):
        fh = freehire.to_schema([job(1, title="Django Developer", location="Pune", posted_at=f"{today}T00:00:00Z",
                                     description="Build Django APIs", enrichment={"experience_years_min": 2})],
                                "django", "India")
        (work / "freehire").mkdir()
        fh.to_csv(work / "freehire" / "raw_freehire.csv", index=False)
        pd.DataFrame([{"lib": "freehire", "site": "freehire", "search_term": "django", "search_location": "India",
                       "status": "ok", "rows": 1, "runtime_s": 1.0, "reason": "", "n429": 0, "attempts": 1}]
                     ).to_csv(work / "freehire" / "runs_freehire.csv", index=False)
        wf = pd.DataFrame([{"source_lib": "wellfound", "site": "wellfound", "title": "Python Developer",
                            "company": "Beta", "location": "Mumbai", "is_remote": False,
                            "date_posted": today - timedelta(days=1), "job_url": "https://wellfound.com/jobs/1-x",
                            "description": "Python, 3+ years", "search_term": "Python Developer",
                            "search_location": "Mumbai"}]).reindex(columns=SCHEMA)
        (work / "wellfound").mkdir()
        wf.to_csv(work / "wellfound" / "raw_wellfound.csv", index=False)
        pd.DataFrame([{"lib": "wellfound", "site": "wellfound", "search_term": "Python Developer",
                       "search_location": "Mumbai", "status": "ok", "rows": 1, "runtime_s": 1.0, "reason": "",
                       "n429": 0, "attempts": 1}]).to_csv(work / "wellfound" / "runs_wellfound.csv", index=False)
        return {n: 0 for n in cmds}, {n: 0.1 for n in cmds}

    monkeypatch.setattr(pipeline, "run_parallel", fake_run_parallel)
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr("sys.argv", ["pipeline.py", "--run", "morning", "--sources", "freehire,wellfound",
                                     "--data-dir", str(data), "--work-dir", str(tmp_path / "work")])
    assert pipeline.main() == 0

    new = pd.read_csv(data / "new_jobs.csv")
    assert "exp_estimate" not in new.columns
    assert list(new.columns) == ["found_utc", "run", "title", "company", "location", "is_remote", "date_posted",
                                 "job_url", "job_type", "min_exp", "max_exp", "salary", "flags", "sources",
                                 "search_terms", "description"]
    fh = new[new["sources"] == "freehire:freehire"].iloc[0]
    assert fh["min_exp"] == 2 and "exp_estimated" in fh["flags"] and fh["job_url"] == "https://jobs.lever.co/acme/1"
    wf = new[new["sources"] == "wellfound:wellfound"].iloc[0]
    assert wf["min_exp"] == 3 and "exp_estimated" not in str(wf["flags"])

    hist = pd.read_csv(data / "run_history.csv").set_index("source")
    assert bool(hist.loc["freehire", "success"]) and hist.loc["freehire", "new"] == 1
    q = pd.read_csv(data / "last_run_queries.csv")
    assert (q["lib"] == "freehire").sum() == 1


def test_site_summary_marks_failed_freehire_without_affecting_others():
    runs = pd.DataFrame([
        {"lib": "freehire", "site": "freehire", "status": "error", "rows": 0, "runtime_s": 1.0, "n429": 0},
        {"lib": "freehire", "site": "freehire", "status": "timeout", "rows": 0, "runtime_s": 20.0, "n429": 0},
        {"lib": "ats", "site": "ats", "status": "ok", "rows": 5, "runtime_s": 1.0, "n429": 0},
    ])
    cmds = {"freehire": ([], ["freehire"]), "ats": ([], ["ats"])}
    s = pipeline.site_summary(runs, ["freehire", "ats"], {"freehire": 0, "ats": 0}, cmds).set_index("source")
    assert not s.loc["freehire", "success"] and s.loc["ats", "success"]
    assert "freehire" not in config.CRITICAL_SOURCES  # best-effort: logged, doesn't fail the workflow


def test_build_commands_and_runs():
    args = Namespace(py_jobdrop="jd", py_jobspy="js", terms="A;B", locations=None, wellfound_mode="auto")
    work = Path("/tmp/w")
    assert "freehire" not in pipeline.build_commands(["ats"], {"ats": 24}, args, work)
    argv, covers = pipeline.build_commands(["freehire"], {"freehire": 24}, args, work)["freehire"]
    assert argv == ["js", "run_freehire.py", "--out", "/tmp/w/freehire"] and covers == ["freehire"]
    assert config.PROD_SOURCES["freehire"] == ("freehire", "freehire")
    if config.FREEHIRE_ENABLED:
        assert all("freehire" in config.PROD_RUNS[r] for r in ("morning", "evening"))


def test_add_experience_all_none_max_from_csv():
    """Pre-existing pandas-3 crash: max_exp read from CSV is all-NaN float64 and no row has a range."""
    import io
    df = pd.read_csv(io.StringIO("title,description,min_exp,max_exp\nPython Developer,\"Python, 3+ years\",,\n"
                                 "Django Dev,Django,,\n"))
    out = P.add_experience(df)
    assert list(out["min_exp"][:1]) == [3] and out["max_exp"].isna().all()
