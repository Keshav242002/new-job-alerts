"""Fetch window per source: time since that source's last successful run.

Rules: first run of a source -> FIRST_RUN_WINDOW_HOURS (72); otherwise
max(MIN_WINDOW_HOURS (24), hours since last success). Tracked per source because
Google and Wellfound run once a day while LinkedIn/Indeed/Naukri run twice.

State file (committed by the pipeline): state/last_success.json
    {"linkedin": "2026-10-15T03:15:00+00:00", ...}

CLI:  python window.py                     # print current windows
      python window.py --mark linkedin naukri   # record success now
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import config

STATE_PATH = Path(__file__).resolve().parent / "state" / "last_success.json"


def _load(path: Path = STATE_PATH) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def window_hours(source: str, now: datetime | None = None, path: Path = STATE_PATH) -> int:
    now = now or datetime.now(timezone.utc)
    last = _load(path).get(source)
    if not last:
        return config.FIRST_RUN_WINDOW_HOURS
    elapsed = (now - datetime.fromisoformat(last)).total_seconds() / 3600
    return max(config.MIN_WINDOW_HOURS, math.ceil(elapsed))


def mark_success(sources: list[str], when: datetime | None = None, path: Path = STATE_PATH) -> None:
    when = when or datetime.now(timezone.utc)
    state = _load(path)
    for s in sources:
        state[s] = when.isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark", nargs="+", help="record a successful run (now) for these sources")
    args = ap.parse_args()
    if args.mark:
        mark_success(args.mark)
    for s in config.PROD_SOURCES:
        print(f"{s:<10} window={window_hours(s)}h  last={_load().get(s, 'never')}")
