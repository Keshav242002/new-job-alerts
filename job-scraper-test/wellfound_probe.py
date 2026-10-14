"""Plain HTTP GET of a Wellfound role page: is it real job listings or a bot-check page?

Usage: python wellfound_probe.py <out_dir>
Writes <out_dir>/wellfound.html and <out_dir>/summary_wellfound.json.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

URL = "https://wellfound.com/role/l/flutter-developer/india"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
BOT_MARKERS = {
    "datadome": r"datadome|captcha-delivery\.com|geo\.captcha-delivery",
    # challenge-platform scripts appear on normal Cloudflare pages too; match interstitials only
    "cloudflare_challenge": r"<title>just a moment|cf_chl_opt|cf-chl-widget",
    "captcha": r"captcha",
    "enable_js": r"please enable js|enable javascript",
    "access_denied": r"access denied|forbidden",
}

out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
out_dir.mkdir(parents=True, exist_ok=True)

t0 = time.perf_counter()
result = {"url": URL}
try:
    r = requests.get(URL, headers=HEADERS, timeout=30)
    html = r.text
    (out_dir / "wellfound.html").write_text(html)
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    job_links = set(re.findall(r'href="(/jobs/\d+[^"]*)"', html))
    bot = [name for name, rx in BOT_MARKERS.items() if re.search(rx, html, re.I)]
    has_next_data = "__NEXT_DATA__" in html
    listings_in_state = len(re.findall(r'"__typename"\s*:\s*"JobListing', html))
    if job_links or listings_in_state:
        verdict = "job listings"
    elif bot:
        verdict = "bot-check page"
    else:
        verdict = "unclear (no listings, no known bot markers)"
    result |= {
        "status": r.status_code, "final_url": r.url, "bytes": len(html),
        "title": title.group(1).strip()[:120] if title else None,
        "job_links": len(job_links), "joblisting_objects": listings_in_state,
        "has___NEXT_DATA__": has_next_data, "bot_markers": bot, "verdict": verdict,
        "server": r.headers.get("server"), "x-datadome": r.headers.get("x-datadome"),
    }
except requests.RequestException as e:
    result |= {"status": None, "error": f"{type(e).__name__}: {e}", "verdict": "request failed"}
result["runtime_s"] = round(time.perf_counter() - t0, 1)

text = "### wellfound (plain HTTP GET)\n\n```json\n" + json.dumps(result, indent=2) + "\n```\n"
print(text)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
        f.write(text)
(out_dir / "summary_wellfound.json").write_text(json.dumps(result, indent=2))
