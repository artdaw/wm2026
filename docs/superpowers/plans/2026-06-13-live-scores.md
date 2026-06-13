# Live Scores Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch WC 2026 live scores from football-data.org every 5 min during match windows (hourly otherwise) and redeploy GitHub Pages automatically.

**Architecture:** A Python script updates only `homeScore`, `awayScore`, `status`, and `minute` in `matches.json` by merging football-data.org API data keyed on `(homeCode, awayCode)`. A GitHub Actions workflow with two cron schedules runs the script and redeploys Pages directly (no git commit needed — each run fetches fresh data).

**Tech Stack:** Python 3.9 stdlib only, GitHub Actions, football-data.org v4 REST API, GitHub Pages.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `scripts/update_scores.py` | Create | Pure functions + `main()` — fetch, merge, write |
| `scripts/test_update_scores.py` | Create | Unit tests for all pure functions |
| `.github/workflows/update-scores.yml` | Create | Two-cron workflow: window check, fetch, Pages deploy |

---

## Task 1: Pure functions + unit tests

**Files:**
- Create: `scripts/test_update_scores.py`
- Create: `scripts/update_scores.py`

- [ ] **Step 1: Write failing tests**

Create `scripts/test_update_scores.py`:

```python
import sys, unittest
from datetime import datetime, timezone, timedelta
sys.path.insert(0, __file__.replace('/test_update_scores.py', ''))
from update_scores import (
    is_in_match_window, map_api_status, extract_scores,
    format_minute, merge_match, build_lookup,
)

NOW = datetime(2026, 6, 13, 19, 30, 0, tzinfo=timezone.utc)

class TestMatchWindow(unittest.TestCase):
    def _m(self, utc): return {"utc": utc}

    def test_match_starting_in_10min_is_in_window(self):
        matches = [self._m("2026-06-13T19:40:00Z")]
        self.assertTrue(is_in_match_window(matches, NOW))

    def test_match_that_started_60min_ago_is_in_window(self):
        matches = [self._m("2026-06-13T18:30:00Z")]
        self.assertTrue(is_in_match_window(matches, NOW))

    def test_match_that_ended_over_105min_ago_is_not_in_window(self):
        matches = [self._m("2026-06-13T17:00:00Z")]
        self.assertFalse(is_in_match_window(matches, NOW))

    def test_match_over_15min_in_future_is_not_in_window(self):
        matches = [self._m("2026-06-13T21:00:00Z")]
        self.assertFalse(is_in_match_window(matches, NOW))

    def test_empty_matches_returns_false(self):
        self.assertFalse(is_in_match_window([], NOW))


class TestMapApiStatus(unittest.TestCase):
    def test_in_play_returns_3(self):
        self.assertEqual(map_api_status("IN_PLAY"), 3)

    def test_paused_returns_3(self):
        self.assertEqual(map_api_status("PAUSED"), 3)

    def test_live_returns_3(self):
        self.assertEqual(map_api_status("LIVE"), 3)

    def test_finished_returns_0(self):
        self.assertEqual(map_api_status("FINISHED"), 0)

    def test_scheduled_returns_0(self):
        self.assertEqual(map_api_status("SCHEDULED"), 0)

    def test_timed_returns_0(self):
        self.assertEqual(map_api_status("TIMED"), 0)


class TestExtractScores(unittest.TestCase):
    def _api(self, status, ft_home=None, ft_away=None, rt_home=None, rt_away=None):
        return {
            "status": status,
            "score": {
                "fullTime": {"home": ft_home, "away": ft_away},
                "regularTime": {"home": rt_home, "away": rt_away},
            },
        }

    def test_finished_uses_fulltime(self):
        m = self._api("FINISHED", ft_home=2, ft_away=1)
        self.assertEqual(extract_scores(m), (2, 1))

    def test_in_play_uses_regulartime_when_available(self):
        m = self._api("IN_PLAY", rt_home=1, rt_away=0)
        self.assertEqual(extract_scores(m), (1, 0))

    def test_in_play_falls_back_to_fulltime_when_regulartime_null(self):
        m = self._api("IN_PLAY", ft_home=1, ft_away=0)
        self.assertEqual(extract_scores(m), (1, 0))

    def test_scheduled_returns_none_none(self):
        m = self._api("SCHEDULED")
        self.assertEqual(extract_scores(m), (None, None))

    def test_timed_returns_none_none(self):
        m = self._api("TIMED")
        self.assertEqual(extract_scores(m), (None, None))


class TestFormatMinute(unittest.TestCase):
    def test_integer_minute_becomes_string_with_apostrophe(self):
        self.assertEqual(format_minute({"minute": 45}), "45'")

    def test_none_minute_returns_none(self):
        self.assertIsNone(format_minute({}))

    def test_zero_minute_returns_string(self):
        self.assertEqual(format_minute({"minute": 0}), "0'")


class TestMergeMatch(unittest.TestCase):
    def _existing(self):
        return {
            "homeCode": "MEX", "awayCode": "RSA",
            "homeScore": None, "awayScore": None,
            "status": 0, "minute": None,
        }

    def _api(self, status="FINISHED", ft_home=2, ft_away=1, minute=None):
        return {
            "status": status, "minute": minute,
            "homeTeam": {"tla": "MEX"}, "awayTeam": {"tla": "RSA"},
            "score": {
                "fullTime": {"home": ft_home, "away": ft_away},
                "regularTime": {"home": None, "away": None},
            },
        }

    def test_finished_match_updates_scores_and_status(self):
        result, changed = merge_match(self._existing(), self._api())
        self.assertEqual(result["homeScore"], 2)
        self.assertEqual(result["awayScore"], 1)
        self.assertEqual(result["status"], 0)
        self.assertTrue(changed)

    def test_live_match_updates_status_to_3(self):
        api = self._api(status="IN_PLAY", minute=67)
        api["score"]["regularTime"] = {"home": 1, "away": 0}
        api["score"]["fullTime"] = {"home": None, "away": None}
        result, changed = merge_match(self._existing(), api)
        self.assertEqual(result["status"], 3)
        self.assertEqual(result["minute"], "67'")
        self.assertTrue(changed)

    def test_no_change_when_data_identical(self):
        existing = {
            "homeCode": "MEX", "awayCode": "RSA",
            "homeScore": 2, "awayScore": 1,
            "status": 0, "minute": None,
        }
        _, changed = merge_match(existing, self._api())
        self.assertFalse(changed)

    def test_static_fields_are_preserved(self):
        existing = dict(self._existing(), home="Mexiko", city="Mexiko-Stadt")
        result, _ = merge_match(existing, self._api())
        self.assertEqual(result["home"], "Mexiko")
        self.assertEqual(result["city"], "Mexiko-Stadt")


class TestBuildLookup(unittest.TestCase):
    def test_builds_dict_keyed_on_tla_pair(self):
        api_matches = [
            {"homeTeam": {"tla": "MEX"}, "awayTeam": {"tla": "RSA"}, "status": "FINISHED"},
            {"homeTeam": {"tla": "KOR"}, "awayTeam": {"tla": "CZE"}, "status": "SCHEDULED"},
        ]
        lookup = build_lookup(api_matches)
        self.assertIn(("MEX", "RSA"), lookup)
        self.assertIn(("KOR", "CZE"), lookup)
        self.assertEqual(lookup[("MEX", "RSA")]["status"], "FINISHED")

    def test_skips_entries_with_missing_tla(self):
        api_matches = [{"homeTeam": {}, "awayTeam": {"tla": "RSA"}}]
        lookup = build_lookup(api_matches)
        self.assertEqual(len(lookup), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd /Users/gleb/Developer/wm2026
python3 -m pytest scripts/test_update_scores.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'update_scores'`

- [ ] **Step 3: Create `scripts/update_scores.py` with all pure functions**

```python
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
        if -WINDOW_BEFORE <= delta <= WINDOW_AFTER:
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
    """Return minute as string like '45'' or None if not available."""
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
python3 -m pytest scripts/test_update_scores.py -v
```

Expected output (all green):
```
PASSED test_match_starting_in_10min_is_in_window
PASSED test_match_that_started_60min_ago_is_in_window
PASSED test_match_that_ended_over_105min_ago_is_not_in_window
PASSED test_match_over_15min_in_future_is_not_in_window
PASSED test_empty_matches_returns_false
PASSED test_in_play_returns_3
PASSED test_paused_returns_3
... (all 22 tests pass)
```

- [ ] **Step 5: Smoke-test window check without API key**

```bash
python3 scripts/update_scores.py --check-window
```

Expected: either `No match in window, skipping.` (if no match is live now) or it exits with `ERROR: FOOTBALL_DATA_API_KEY not set` (if a match IS in window). Both are correct.

- [ ] **Step 6: Commit**

```bash
git add scripts/update_scores.py scripts/test_update_scores.py
git commit -m "feat: add live score update script with tests"
```

---

## Task 2: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/update-scores.yml`

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/update-scores.yml`:

```yaml
name: Update live scores

on:
  schedule:
    - cron: '*/5 * * * *'   # every 5 min — window-gated
    - cron: '0 * * * *'     # every hour — always fetches
  workflow_dispatch:         # manual trigger for testing

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: score-updates
  cancel-in-progress: true  # drop stale runs, only latest matters

jobs:
  update:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Fetch scores
        env:
          FOOTBALL_DATA_API_KEY: ${{ secrets.FOOTBALL_DATA_API_KEY }}
        run: |
          if [[ "${{ github.event.schedule }}" == "*/5 * * * *" ]]; then
            python3 scripts/update_scores.py --check-window
          else
            python3 scripts/update_scores.py
          fi

      - name: Detect changes
        id: diff
        run: |
          if git diff --quiet matches.json; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi

      - name: Setup Pages
        if: steps.diff.outputs.changed == 'true'
        uses: actions/configure-pages@v5

      - name: Upload artifact
        if: steps.diff.outputs.changed == 'true'
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'

      - name: Deploy to GitHub Pages
        if: steps.diff.outputs.changed == 'true'
        id: deployment
        uses: actions/deploy-pages@v5
```

- [ ] **Step 2: Verify YAML is valid**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/update-scores.yml'))" 2>/dev/null && echo OK || echo INVALID
```

Expected: `OK`

(If `yaml` module is not installed: `pip3 install pyyaml` or skip — GitHub will validate on push.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/update-scores.yml
git commit -m "feat: add live score update GitHub Actions workflow"
```

---

## Task 3: Add the secret and test end-to-end

**No files to create — manual steps in GitHub UI.**

- [ ] **Step 1: Sign up and get API key**

Go to `https://www.football-data.org/client/register` — free, no credit card. Check email for API key.

- [ ] **Step 2: Add secret to GitHub repo**

In the repo on GitHub: **Settings → Secrets and variables → Actions → New repository secret**

- Name: `FOOTBALL_DATA_API_KEY`
- Value: paste your key

Click **Add secret**.

- [ ] **Step 3: Push the branch and trigger manually**

```bash
git push
```

Then go to **Actions → Update live scores → Run workflow** and click **Run workflow**.

- [ ] **Step 4: Verify the run**

In the Actions tab, open the triggered run. Check:
- "Fetch scores" step prints either `No match in window, skipping.` or `Updated N match(es).`
- "Detect changes" step sets `changed=true` or `changed=false`
- If changed: "Deploy to GitHub Pages" step completes successfully

- [ ] **Step 5: Confirm the API competition code**

football-data.org uses `WC` for the FIFA World Cup. If the "Fetch scores" step returns `Updated 0 match(es)` unexpectedly after matches have been played, check the competition ID:

```bash
FOOTBALL_DATA_API_KEY=<your-key> python3 -c "
import urllib.request, json
req = urllib.request.Request(
    'https://api.football-data.org/v4/competitions/',
    headers={'X-Auth-Token': '$FOOTBALL_DATA_API_KEY'}
)
data = json.loads(urllib.request.urlopen(req).read())
print([c['code'] for c in data['competitions']])
"
```

If the WC 2026 code is different (e.g. `WC26`), update `API_URL` in `scripts/update_scores.py` and recommit.
