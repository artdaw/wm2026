# Live Scores — GitHub Actions Cron Design

**Date:** 2026-06-13  
**Status:** Approved

## Goal

Automatically update `matches.json` with live scores, match status, and elapsed minute from football-data.org, keeping the German-language static data intact.

## Data Strategy

Only 3 fields are updated per match: `homeScore`, `awayScore`, `status`, `minute`. All static fields (German team names, city, stadium, `utc`, `stage`, `group`, `homeCode`, `awayCode`, `no`) are never touched.

Matches are correlated between API response and `matches.json` using the composite key `(homeCode, awayCode)` — 3-letter TLA codes that football-data.org uses identically (MEX, RSA, KOR, etc.).

### Status mapping

| API status | `status` field | scores |
|---|---|---|
| `SCHEDULED`, `TIMED` | `0` | `null` |
| `IN_PLAY`, `PAUSED`, `LIVE` | `3` | current |
| `FINISHED` | `0` | final |

## Files

- `.github/workflows/update-scores.yml` — cron workflow
- `scripts/update_scores.py` — fetch + merge + commit script

## Workflow

Two cron triggers in one workflow file:

```
*/5 * * * *   →  runs script with --check-window (skips if no match in window)
0   * * * *   →  runs script without flag (always fetches)
```

Permissions: `contents: write` to allow commit + push back to `main`. The existing deploy workflow fires on push, so Pages updates automatically.

Secret: `FOOTBALL_DATA_API_KEY` stored in GitHub repo Settings → Secrets → Actions.

## Script Logic (`scripts/update_scores.py`)

1. Parse `--check-window` flag
2. If `--check-window`: scan `matches.json` for any match with `utc` in `[-15 min, +105 min]` of now → exit 0 silently if none in window
3. Fetch `GET https://api.football-data.org/v4/competitions/WC/matches` with `X-Auth-Token` header (returns all matches in one call)
4. Build lookup `{(homeCode, awayCode): api_match}`
5. For each match in `matches.json`: if found in lookup, update the 3 dynamic fields
6. If any match changed: write `matches.json`, `git commit`, `git push`
7. If nothing changed: exit 0 silently

## Error Handling

- API non-200 → print error, exit 0 (skip run, don't fail workflow)
- Match not found in API response → leave untouched (handles knockout TBD slots)
- Git push fails → workflow fails visibly (intentional — signals a real problem)

## Match Window

`[-15 min, +105 min]` relative to each match's `utc`. Covers: buffer before kickoff, 90 min regular time, 15 min stoppage/extra. If a match is in this window the 5-minute cron fires a full update; otherwise it exits immediately without an API call.

## Commit Identity

Git commits use `github-actions[bot]` user to keep history clean.
