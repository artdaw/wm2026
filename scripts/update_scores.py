#!/usr/bin/env python3
"""Fetch WC 2026 live scores from football-data.org and update matches.json."""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

MATCHES_JSON = Path(__file__).parent.parent / "matches.json"
API_URL = "https://api.football-data.org/v4/competitions/WC/matches"
WINDOW_BEFORE = timedelta(minutes=15)
WINDOW_AFTER = timedelta(minutes=105)


def is_in_match_window(matches, now):
    """Return True if any match has utc within [-15 min, +105 min] of now."""
    for m in matches:
        kick_off = datetime.fromisoformat(m["utc"].replace("Z", "+00:00"))
        delta = kick_off - now
        if -WINDOW_AFTER <= delta <= WINDOW_BEFORE:
            return True
    return False


def map_api_status(api_status):
    """Map football-data.org status string to our numeric status (0 or 3)."""
    return 3 if api_status in ("IN_PLAY", "PAUSED", "LIVE") else 0


def extract_scores(api_match):
    """Return (home_score, away_score) integers or (None, None) for unplayed matches."""
    score = api_match.get("score", {})
    status = api_match.get("status", "")
    if status in ("IN_PLAY", "PAUSED", "LIVE"):
        rt = score.get("regularTime") or {}
        if rt.get("home") is not None:
            return rt["home"], rt["away"]
        ft = score.get("fullTime") or {}
        return ft.get("home"), ft.get("away")
    if status == "FINISHED":
        ft = score.get("fullTime") or {}
        return ft.get("home"), ft.get("away")
    return None, None


def format_minute(api_match):
    """Return minute as string like \"45'\" or None if not available."""
    minute = api_match.get("minute")
    if minute is None:
        return None
    return f"{minute}'"


def merge_match(existing, api_match):
    """
    Update dynamic fields in existing match from api_match.
    Returns (updated_match, changed_bool). Static fields are never touched.
    """
    home_score, away_score = extract_scores(api_match)
    new_status = map_api_status(api_match.get("status", "SCHEDULED"))
    new_minute = format_minute(api_match)

    updated = dict(existing)
    changed = False
    for field, new_val in [
        ("homeScore", home_score),
        ("awayScore", away_score),
        ("status", new_status),
        ("minute", new_minute),
    ]:
        if updated.get(field) != new_val:
            updated[field] = new_val
            changed = True
    return updated, changed


def build_lookup(api_matches):
    """Build {(homeTla, awayTla): api_match} dict from API response list."""
    result = {}
    for m in api_matches:
        home = m.get("homeTeam", {}).get("tla")
        away = m.get("awayTeam", {}).get("tla")
        if home and away:
            result[(home, away)] = m
    return result


def fetch_api_matches(api_key):
    req = urllib.request.Request(API_URL, headers={"X-Auth-Token": api_key})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data.get("matches", [])


def main():
    check_window = "--check-window" in sys.argv
    existing = json.loads(MATCHES_JSON.read_text())

    if check_window:
        now = datetime.now(timezone.utc)
        if not is_in_match_window(existing, now):
            print("No match in window, skipping.")
            return

    api_key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
    if not api_key:
        print("ERROR: FOOTBALL_DATA_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    try:
        api_matches = fetch_api_matches(api_key)
    except Exception as e:
        print(f"ERROR fetching API: {e}", file=sys.stderr)
        return  # exit 0 — transient errors should not fail the workflow

    lookup = build_lookup(api_matches)
    updated_matches = []
    changed_count = 0

    for m in existing:
        key = (m.get("homeCode"), m.get("awayCode"))
        if key in lookup:
            new_m, changed = merge_match(m, lookup[key])
            updated_matches.append(new_m)
            if changed:
                changed_count += 1
        else:
            updated_matches.append(m)

    if changed_count == 0:
        print("No changes detected.")
        return

    MATCHES_JSON.write_text(
        json.dumps(updated_matches, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"Updated {changed_count} match(es).")


if __name__ == "__main__":
    main()
