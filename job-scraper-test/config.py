"""Shared search config for run_jobspy.py, run_jobdrop.py and process.py."""

SEARCH_TERMS = [
    "Full Stack Developer",
    "Flutter Developer",
    "Mobile Application Developer",
    "SDE 1",
    "SDE 2",
    "Software Developer",
    "Software Engineer",
    "Backend Developer",
    "Django Developer",
    "Python Developer",
    "FastAPI Developer",
]

# "Remote" -> location="India", is_remote=True; "India" -> pan-India search.
LOCATIONS = [
    "Bangalore",
    "Gurugram",
    "Noida",
    "Delhi NCR",
    "Pune",
    "Mumbai",
    "Hyderabad",
    "Chennai",
    "Remote",
    "India",
]

SMOKE_TERMS = ["Flutter Developer"]
SMOKE_LOCATIONS = ["Bangalore"]

COUNTRY = "India"
HOURS_OLD = 72
RESULTS_WANTED = 25
FETCH_DESCRIPTION = True  # needed for experience parsing (LinkedIn has none otherwise)
DESCRIPTION_MAX_CHARS = 10000  # full enough for skill matching; new_jobs.csv shows NEW_JOBS_DESCRIPTION_CHARS

# Polite delay (seconds, random uniform) between consecutive queries to the same site.
DELAY_RANGE = (4, 9)

# Per-query hard timeouts (seconds). The worker process group is killed on expiry.
TIMEOUT_HTTP = 180
TIMEOUT_BROWSER = 300
TIMEOUT_BY_SITE = {"linkedin": 300}  # LinkedIn fetches 25 descriptions per query (~2.5 min typical)
# After this many seconds a LinkedIn query stops fetching descriptions and returns the jobs it has
# (remaining rows have no description) so it finishes before TIMEOUT_BY_SITE instead of losing all rows.
LINKEDIN_DESCRIPTION_BUDGET_S = 270

# LinkedIn only: country-level searches instead of per-city, slower pace, backoff on 429.
LINKEDIN_LOCATIONS = ["India", "Remote"]
LINKEDIN_DELAY_RANGE = (25, 45)
# Naukri (best-effort, morning only): fewer locations and slower pace to avoid 406 rate limits.
NAUKRI_LOCATIONS = ["India", "Bangalore", "Gurugram", "Noida", "Pune", "Hyderabad"]
NAUKRI_DELAY_RANGE = (20, 40)
BACKOFF_429 = [60, 120, 240]  # seconds before retry 1/2/3 when a query got 429s and no rows
BACKOFF_SITES = {"linkedin"}

# jobspy naukri: drop jobAge/sort=f (relevance order) and age-filter in process.py.
# See naukri_param_test.md for the before/after comparison.
JOBSPY_NAUKRI_RELEVANCE = True

SITES = {
    "jobspy": ["linkedin", "indeed", "naukri", "google", "glassdoor"],
    "jobdrop": [
        # plain HTTP
        "linkedin", "indeed", "trueup", "remoteok", "weworkremotely",
        # headless browser
        "naukri", "google",
    ],
}

# Not in the full run — failed in the smoke test (2026-10-14).
FAILED_IN_SMOKE = {
    "jobdrop": {
        "greenhouse": "Google /sorry/ CAPTCHA during SERP discovery",
        "lever": "Google /sorry/ CAPTCHA during SERP discovery",
        "ashby": "0 Google SERP hits (likely silent Google block)",
        "workday": "0 Google SERP hits (likely silent Google block)",
        "icims": "0 Google SERP hits (likely silent Google block)",
        "glassdoor": "403 on location lookup (blocked)",
        "wellfound": "needs Camoufox; 1.29 GB download at ~2 MB/min, stopped (not retried)",
        "hiring_cafe": "stale buildId -> Camoufox fallback -> timeout at 180s; Camoufox unavailable",
    },
}

# Sites that drive a headless browser (jobdrop only).
BROWSER_SITES = {
    "naukri", "google", "glassdoor", "wellfound",
    "greenhouse", "lever", "ashby", "workday", "icims",
}
# Browser sites that discover jobs via Google SERPs -> at risk on CI / datacenter IPs.
GOOGLE_SERP_SITES = {"google", "greenhouse", "lever", "ashby", "workday", "icims"}

# Off by policy: bundled third-party API keys / not India-relevant.
DISABLED = {
    "bundled_keys": ["adzuna", "jooble", "usajobs", "findwork", "the_muse"],
    "non_india": [
        "zip_recruiter", "bayt", "bdjobs", "hellowork", "builtin", "dice",
        "insight_global", "clearance_jobs", "kforce", "collab_work", "snagajob",
        "idealist", "careerbuilder", "handshake", "governmentjobs",
    ],
}


def google_query(term: str, location: str, hours: int = 72) -> str:
    where = "India" if location in ("India", "Remote") else f"{location}, India"
    remote = " remote" if location == "Remote" else ""
    days = max(1, -(-hours // 24))
    since = "since yesterday" if days == 1 else f"in the last {days} days"
    return f"{term}{remote} jobs in {where} {since}"

# Stop querying a site after this many consecutive blocked/captcha results (rest marked "skipped").
BLOCK_STREAK_LIMIT = 3
BLOCK_STREAK_BY_SITE = {"naukri": 2}  # Naukri: stop for the day after 2 consecutive 406 (recaptcha) responses

# Wellfound (plain HTTP role pages; see wellfound.py for role/location slug maps)
WELLFOUND_DELAY_RANGE = (3, 6)
WELLFOUND_MAX_PAGES = 10  # pages aren't date-sorted; walk until no new ids (cap)


# ---------------------------------------------------------------- production
# Source -> (library, site). Decided after the comparison + Actions feasibility tests.
PROD_SOURCES = {
    "linkedin": ("jobdrop", "linkedin"),
    # "indeed": ("jobspy", "indeed"),  # removed from the pipeline 2026-10-14 (code kept; re-enable here)
    "naukri": ("jobspy", "naukri"),   # no hours_old (JOBSPY_NAUKRI_RELEVANCE); date-filtered in process.py
    # "google": ("jobdrop", "google"),  # dropped 2026-10-14: Google CAPTCHAs the Actions runner (code kept)
    "wellfound": ("wellfound", "wellfound"),
    "ats": ("ats", "ats"),             # Greenhouse / Lever / Ashby boards from companies.json
}
# Which sources each scheduled run fetches (see SCHEDULE.md).
PROD_RUNS = {
    "morning": ["linkedin", "naukri", "wellfound", "ats"],
    "evening": ["linkedin", "wellfound", "ats"],  # repeats of the morning are removed by seen_jobs
}
# Only these sources fail the workflow when they fail; the rest are best-effort (logged in
# runs/latest.md, run still passes). A failed data push always fails the run.
CRITICAL_SOURCES = {"linkedin", "wellfound"}
# Fetch window = time since the source's last successful run, at least 24h; 72h on its first run.
MIN_WINDOW_HOURS = 24
FIRST_RUN_WINDOW_HOURS = 72
# ATS postings stay live for weeks: backfill 30 days on the source's first run.
FIRST_RUN_WINDOW_HOURS_BY_SOURCE = {"ats": 30 * 24}

# Wellfound modes: "incremental" = up to 5 pages per role/location, stop at the first page whose ids
# are all already in seen_jobs; "full" = 10-page cap (Sundays only when mode is "auto").
WELLFOUND_INCREMENTAL_MAX_PAGES = 5
WELLFOUND_FULL_MAX_PAGES = 10
WELLFOUND_FULL_WEEKDAY = 6  # Sunday, in IST
# process.py date filter: max posting age for every source (the fetch window is separate, window.py)
MAX_POSTING_AGE_DAYS = 14
EXCLUDED_LOG_DAYS = 7  # excluded_log.csv keeps this many days of excluded jobs
SEEN_RETENTION_DAYS = 90  # drop seen_jobs entries not seen for this long
NEW_JOBS_DESCRIPTION_CHARS = 600
BROWSER_CONNECT_RETRIES = 2  # retries for headless Chrome 'Failed to connect to browser'

# ATS (Greenhouse/Lever/Ashby public APIs)
ATS_DELAY_RANGE = (0.5, 1.5)  # between companies
