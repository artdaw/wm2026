# Match Preview / AI Commentary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AI-generated German match previews and post-match summaries to each Spielplan card, pre-generated daily via GitHub Actions and stored in `matches.json`.

**Architecture:** A Python script calls the LiquidAI API (OpenAI-compatible), writes `preview` and `summary` fields into `matches.json`, and redeploys Pages. The frontend reads those fields and renders an inline expand panel per card. No runtime API calls from the browser.

**Tech Stack:** Python 3.9 stdlib only, LiquidAI API, GitHub Actions, vanilla JS.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `scripts/generate_previews.py` | Create | Pure functions + `main()` — LiquidAI API call, merge into matches.json |
| `scripts/test_generate_previews.py` | Create | pytest unit tests for all pure functions (no API calls) |
| `.github/workflows/generate-previews.yml` | Create | Daily cron + manual trigger, Pages deploy |
| `index.html` | Modify | CSS, card template (button + panel), delegated click handler |

---

## Task 1: Pure functions + tests (TDD)

**Files:**
- Create: `scripts/test_generate_previews.py`
- Create: `scripts/generate_previews.py`

- [ ] **Step 1: Create the test file**

Create `/Users/gleb/Developer/wm2026/scripts/test_generate_previews.py`:

```python
import sys, unittest
from datetime import datetime, timezone, timedelta
sys.path.insert(0, __file__.replace('/test_generate_previews.py', ''))
from generate_previews import (
    needs_preview, needs_summary,
    build_preview_prompt, build_summary_prompt,
    merge_ai_text,
)

NOW = datetime(2026, 6, 14, 6, 0, 0, tzinfo=timezone.utc)


class TestNeedsPreview(unittest.TestCase):
    def _m(self, days_from_now, preview=None):
        utc = (NOW + timedelta(days=days_from_now)).strftime('%Y-%m-%dT%H:%M:%SZ')
        return {'utc': utc, 'preview': preview, 'summary': None, 'status': 0}

    def test_upcoming_within_7_days_no_preview_true(self):
        self.assertTrue(needs_preview(self._m(3), NOW))

    def test_already_has_preview_false(self):
        self.assertFalse(needs_preview(self._m(3, preview='Some text'), NOW))

    def test_more_than_7_days_away_false(self):
        self.assertFalse(needs_preview(self._m(8), NOW))

    def test_in_the_past_false(self):
        self.assertFalse(needs_preview(self._m(-1), NOW))

    def test_exactly_7_days_away_true(self):
        self.assertTrue(needs_preview(self._m(7), NOW))


class TestNeedsSummary(unittest.TestCase):
    def _m(self, hours_ago, home_score=None, away_score=None, summary=None):
        utc = (NOW - timedelta(hours=hours_ago)).strftime('%Y-%m-%dT%H:%M:%SZ')
        return {'utc': utc, 'homeScore': home_score, 'awayScore': away_score,
                'summary': summary, 'status': 0}

    def test_finished_with_scores_no_summary_true(self):
        self.assertTrue(needs_summary(self._m(2, home_score=2, away_score=1), NOW))

    def test_already_has_summary_false(self):
        self.assertFalse(needs_summary(self._m(2, 2, 1, summary='Text'), NOW))

    def test_no_scores_false(self):
        self.assertFalse(needs_summary(self._m(2, None, None), NOW))

    def test_too_recent_under_105_min_false(self):
        self.assertFalse(needs_summary(self._m(1, home_score=1, away_score=0), NOW))

    def test_score_of_zero_still_valid(self):
        self.assertTrue(needs_summary(self._m(3, home_score=0, away_score=0), NOW))


class TestBuildPreviewPrompt(unittest.TestCase):
    def _m(self):
        return {
            'home': 'Deutschland', 'away': 'Brasilien',
            'stage': 'Gruppe A', 'group': None,
            'utc': '2026-06-17T18:00:00Z',
        }

    def test_contains_home_team(self):
        self.assertIn('Deutschland', build_preview_prompt(self._m()))

    def test_contains_away_team(self):
        self.assertIn('Brasilien', build_preview_prompt(self._m()))

    def test_contains_stage(self):
        self.assertIn('Gruppe A', build_preview_prompt(self._m()))

    def test_asks_for_german(self):
        self.assertIn('Deutsch', build_preview_prompt(self._m()))


class TestBuildSummaryPrompt(unittest.TestCase):
    def _m(self):
        return {'home': 'Deutschland', 'away': 'Brasilien',
                'homeScore': 2, 'awayScore': 1}

    def test_contains_home_team(self):
        self.assertIn('Deutschland', build_summary_prompt(self._m()))

    def test_contains_away_team(self):
        self.assertIn('Brasilien', build_summary_prompt(self._m()))

    def test_contains_score(self):
        prompt = build_summary_prompt(self._m())
        self.assertIn('2', prompt)
        self.assertIn('1', prompt)


class TestMergeAiText(unittest.TestCase):
    def test_sets_field_and_changed_true(self):
        m = {'home': 'Deutschland', 'preview': None}
        updated, changed = merge_ai_text(m, 'preview', 'Spannende Vorschau.')
        self.assertEqual(updated['preview'], 'Spannende Vorschau.')
        self.assertTrue(changed)

    def test_does_not_mutate_original(self):
        m = {'home': 'Deutschland', 'preview': None}
        merge_ai_text(m, 'preview', 'Text')
        self.assertIsNone(m['preview'])

    def test_empty_string_no_change(self):
        m = {'home': 'Deutschland', 'preview': None}
        updated, changed = merge_ai_text(m, 'preview', '')
        self.assertIsNone(updated['preview'])
        self.assertFalse(changed)

    def test_whitespace_only_no_change(self):
        m = {'home': 'Deutschland', 'preview': None}
        updated, changed = merge_ai_text(m, 'preview', '   ')
        self.assertFalse(changed)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
cd /Users/gleb/Developer/wm2026
python3 -m pytest scripts/test_generate_previews.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'generate_previews'`

- [ ] **Step 3: Create `scripts/generate_previews.py` with all pure functions**

Create `/Users/gleb/Developer/wm2026/scripts/generate_previews.py`:

```python
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

MATCHES_JSON = os.path.join(os.path.dirname(__file__), '..', 'matches.json')
WINDOW_PREVIEW  = timedelta(days=7)
WINDOW_FINISHED = timedelta(minutes=105)
API_URL         = 'https://api.liquid.ai/v1/chat/completions'
DEFAULT_MODEL   = 'lfm-7b'

MONTH_DE = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
            'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']


def needs_preview(match, now):
    if match.get('preview'):
        return False
    try:
        kick_off = datetime.fromisoformat(match['utc'].replace('Z', '+00:00'))
    except (KeyError, ValueError):
        return False
    delta = kick_off - now
    return timedelta(0) < delta <= WINDOW_PREVIEW


def needs_summary(match, now):
    if match.get('summary'):
        return False
    if match.get('homeScore') is None or match.get('awayScore') is None:
        return False
    try:
        kick_off = datetime.fromisoformat(match['utc'].replace('Z', '+00:00'))
    except (KeyError, ValueError):
        return False
    return (now - kick_off) >= WINDOW_FINISHED


def build_preview_prompt(match):
    home  = match.get('home', '?')
    away  = match.get('away', '?')
    stage = match.get('stage') or match.get('group', '')
    try:
        kick_off = datetime.fromisoformat(match['utc'].replace('Z', '+00:00'))
        date_de  = f"{kick_off.day}. {MONTH_DE[kick_off.month]} {kick_off.year}"
    except (KeyError, ValueError):
        date_de = ''
    return (
        f"Schreib eine spannende Vorschau in 2 Sätzen auf Deutsch für das "
        f"WM-2026-Spiel: {home} vs {away}, {stage}, {date_de}. "
        f"Nur die 2 Sätze, kein Titel."
    )


def build_summary_prompt(match):
    home       = match.get('home', '?')
    away       = match.get('away', '?')
    home_score = match.get('homeScore', '?')
    away_score = match.get('awayScore', '?')
    return (
        f"Schreib eine knappe Zusammenfassung in 1-2 Sätzen auf Deutsch für das "
        f"WM-2026-Spiel: {home} {home_score}:{away_score} {away}. "
        f"Nur die Sätze, kein Titel."
    )


def merge_ai_text(match, field, text):
    if not text or not text.strip():
        return dict(match), False
    updated = dict(match)
    updated[field] = text.strip()
    return updated, True


def call_liquid_ai(prompt, api_key, model=DEFAULT_MODEL, base_url=API_URL):
    payload = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 80,
        'temperature': 0.7,
    }).encode()
    req = urllib.request.Request(
        base_url,
        data=payload,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data['choices'][0]['message']['content']


def main():
    api_key = os.environ.get('LIQUID_AI_API_KEY', '')
    model   = os.environ.get('LIQUID_AI_MODEL', DEFAULT_MODEL)

    if not api_key:
        print('LIQUID_AI_API_KEY not set — skipping', file=sys.stderr)
        return

    with open(MATCHES_JSON, encoding='utf-8') as f:
        matches = json.load(f)

    now = datetime.now(timezone.utc)
    previews_gen = 0
    summaries_gen = 0
    skipped = 0
    updated_matches = []
    any_changed = False

    for m in matches:
        if needs_summary(m, now):
            try:
                text = call_liquid_ai(build_summary_prompt(m), api_key, model)
                m, changed = merge_ai_text(m, 'summary', text)
                if changed:
                    summaries_gen += 1
                    any_changed = True
            except Exception as e:
                print(f"Summary error for {m.get('home')} vs {m.get('away')}: {e}",
                      file=sys.stderr)
        elif needs_preview(m, now):
            try:
                text = call_liquid_ai(build_preview_prompt(m), api_key, model)
                m, changed = merge_ai_text(m, 'preview', text)
                if changed:
                    previews_gen += 1
                    any_changed = True
            except Exception as e:
                print(f"Preview error for {m.get('home')} vs {m.get('away')}: {e}",
                      file=sys.stderr)
        else:
            skipped += 1
        updated_matches.append(m)

    if any_changed:
        with open(MATCHES_JSON, 'w', encoding='utf-8') as f:
            json.dump(updated_matches, f, ensure_ascii=False, indent=2)
            f.write('\n')

    print(f"Generated: {previews_gen} previews, {summaries_gen} summaries. "
          f"Skipped: {skipped}.")


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests — all must pass**

```bash
cd /Users/gleb/Developer/wm2026
python3 -m pytest scripts/test_generate_previews.py -v
```

Expected output (21 tests):
```
PASSED scripts/test_generate_previews.py::TestNeedsPreview::test_upcoming_within_7_days_no_preview_true
PASSED scripts/test_generate_previews.py::TestNeedsPreview::test_already_has_preview_false
PASSED scripts/test_generate_previews.py::TestNeedsPreview::test_more_than_7_days_away_false
PASSED scripts/test_generate_previews.py::TestNeedsPreview::test_in_the_past_false
PASSED scripts/test_generate_previews.py::TestNeedsPreview::test_exactly_7_days_away_true
PASSED scripts/test_generate_previews.py::TestNeedsSummary::test_finished_with_scores_no_summary_true
PASSED scripts/test_generate_previews.py::TestNeedsSummary::test_already_has_summary_false
PASSED scripts/test_generate_previews.py::TestNeedsSummary::test_no_scores_false
PASSED scripts/test_generate_previews.py::TestNeedsSummary::test_too_recent_under_105_min_false
PASSED scripts/test_generate_previews.py::TestNeedsSummary::test_score_of_zero_still_valid
PASSED scripts/test_generate_previews.py::TestBuildPreviewPrompt::test_contains_home_team
PASSED scripts/test_generate_previews.py::TestBuildPreviewPrompt::test_contains_away_team
PASSED scripts/test_generate_previews.py::TestBuildPreviewPrompt::test_contains_stage
PASSED scripts/test_generate_previews.py::TestBuildPreviewPrompt::test_asks_for_german
PASSED scripts/test_generate_previews.py::TestBuildSummaryPrompt::test_contains_home_team
PASSED scripts/test_generate_previews.py::TestBuildSummaryPrompt::test_contains_away_team
PASSED scripts/test_generate_previews.py::TestBuildSummaryPrompt::test_contains_score
PASSED scripts/test_generate_previews.py::TestMergeAiText::test_sets_field_and_changed_true
PASSED scripts/test_generate_previews.py::TestMergeAiText::test_does_not_mutate_original
PASSED scripts/test_generate_previews.py::TestMergeAiText::test_empty_string_no_change
PASSED scripts/test_generate_previews.py::TestMergeAiText::test_whitespace_only_no_change

21 passed in ...s
```

If any test fails, fix `generate_previews.py` (not the test file) to make it pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_previews.py scripts/test_generate_previews.py
git commit -m "feat: add preview generation script with tests"
```

---

## Task 2: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/generate-previews.yml`

- [ ] **Step 1: Create the workflow file**

Create `/Users/gleb/Developer/wm2026/.github/workflows/generate-previews.yml`:

```yaml
name: Generate match previews

on:
  schedule:
    - cron: '0 6 * * *'   # daily at 06:00 UTC
  workflow_dispatch:        # manual trigger for testing

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: preview-generation  # no cancel-in-progress — LLM runs are slow

jobs:
  generate:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Generate previews
        env:
          LIQUID_AI_API_KEY: ${{ secrets.LIQUID_AI_API_KEY }}
          LIQUID_AI_MODEL: ${{ vars.LIQUID_AI_MODEL || 'lfm-7b' }}
        run: python3 scripts/generate_previews.py

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

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/generate-previews.yml
git commit -m "feat: add daily preview generation workflow"
```

- [ ] **Step 3: Add LIQUID_AI_API_KEY secret to GitHub**

Go to: `https://github.com/artdaw/wm2026/settings/secrets/actions`

Add secret: `LIQUID_AI_API_KEY` → your LiquidAI API key from `https://platform.liquid.ai`

Then trigger a manual run to verify:
- Go to Actions → "Generate match previews" → Run workflow
- Check the log output: should print `Generated: N previews, M summaries. Skipped: X.`
- If `LIQUID_AI_API_KEY` is not set yet, it will print the skip message and exit 0 (no error)

---

## Task 3: Frontend — button, panel, click handler

**Files:**
- Modify: `index.html`

The schedule list element is `scheduleList` (`document.getElementById('schedule-list')` at line 308). The card template is in `renderSchedule()` starting at line 398. The existing click handlers are at lines 431–438.

- [ ] **Step 1: Add CSS for the preview panel**

In `index.html`, find the closing `</style>` tag (it's the first one, inside `<head>`). Add these rules immediately before it:

```css
  .preview-btn{margin-top:6px;border:1px solid var(--accent);background:transparent;color:var(--accent);border-radius:6px;padding:3px 8px;font-size:11px;font-weight:700;cursor:pointer;align-self:flex-start}
  .preview-panel{display:none;grid-column:1/-1;padding:10px 12px;background:#13161e;border-top:1px solid var(--line)}
  .match-card.preview-open .preview-panel{display:block}
  .preview-label{font-size:10px;color:var(--accent);font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
  .preview-text{font-size:12px;line-height:1.6;color:var(--txt);margin:0}
  .preview-attr{font-size:10px;color:var(--muted);margin-top:6px;text-align:right}
```

- [ ] **Step 2: Modify the card template in `renderSchedule()`**

Find this exact block inside `renderSchedule()` (around line 398):

```javascript
    const cards = dayMatches.map(m=>{
      const status = matchStatus(m);
      const hasScore = Number.isFinite(m.homeScore) && Number.isFinite(m.awayScore);
      const score = hasScore ? `${m.homeScore}:${m.awayScore}` : 'vs';
      const meta = [`Spiel ${m.no}`, m.group || m.stage, m.city].filter(Boolean).join(' · ');
      const codes = [m.homeCode, m.awayCode].filter(Boolean).join(' / ');
      return `
        <article class="match-card ${status.cls}" data-match-no="${escapeHtml(m.no)}">
          <div class="match-time">
            <strong>${escapeHtml(timeLabelFmt.format(new Date(m.utc)))}</strong>
            <span>Berlin</span>
          </div>
          <div class="match-main">
            <div class="match-meta">${escapeHtml(meta)}</div>
            <div class="match-teams">
              <span class="team">${escapeHtml(m.home)}</span>
              <span class="score">${escapeHtml(score)}</span>
              <span class="team">${escapeHtml(m.away)}</span>
              ${codes ? `<span class="team-code">${escapeHtml(codes)}</span>` : ''}
            </div>
            <div class="match-place">${escapeHtml(m.stadium)}</div>
          </div>
          <div class="match-status ${status.cls}">${escapeHtml(status.text)}</div>
        </article>
      `;
    }).join('');
```

Replace it with:

```javascript
    const cards = dayMatches.map(m=>{
      const status = matchStatus(m);
      const hasScore = Number.isFinite(m.homeScore) && Number.isFinite(m.awayScore);
      const score = hasScore ? `${m.homeScore}:${m.awayScore}` : 'vs';
      const meta = [`Spiel ${m.no}`, m.group || m.stage, m.city].filter(Boolean).join(' · ');
      const codes = [m.homeCode, m.awayCode].filter(Boolean).join(' / ');
      const aiText = m.summary || m.preview || '';
      const aiLabel = m.summary ? '⚡ Zusammenfassung' : '⚡ Vorschau';
      const aiPanelLabel = m.summary ? '⚡ KI-Zusammenfassung' : '⚡ KI-Vorschau';
      return `
        <article class="match-card ${status.cls}" data-match-no="${escapeHtml(m.no)}">
          <div class="match-time">
            <strong>${escapeHtml(timeLabelFmt.format(new Date(m.utc)))}</strong>
            <span>Berlin</span>
          </div>
          <div class="match-main">
            <div class="match-meta">${escapeHtml(meta)}</div>
            <div class="match-teams">
              <span class="team">${escapeHtml(m.home)}</span>
              <span class="score">${escapeHtml(score)}</span>
              <span class="team">${escapeHtml(m.away)}</span>
              ${codes ? `<span class="team-code">${escapeHtml(codes)}</span>` : ''}
            </div>
            <div class="match-place">${escapeHtml(m.stadium)}</div>
            ${aiText ? `<button class="preview-btn" type="button">${escapeHtml(aiLabel)}</button>` : ''}
          </div>
          <div class="match-status ${status.cls}">${escapeHtml(status.text)}</div>
          ${aiText ? `
          <div class="preview-panel">
            <div class="preview-label">${escapeHtml(aiPanelLabel)}</div>
            <p class="preview-text">${escapeHtml(aiText)}</p>
            <div class="preview-attr">LiquidAI</div>
          </div>` : ''}
        </article>
      `;
    }).join('');
```

- [ ] **Step 3: Add the delegated click handler**

Find this line (around line 438):
```javascript
scheduleSearch.addEventListener('input', renderSchedule);
```

Add immediately after it:
```javascript
scheduleList.addEventListener('click', e=>{
  if(e.target.classList.contains('preview-btn'))
    e.target.closest('.match-card').classList.toggle('preview-open');
});
```

- [ ] **Step 4: Test with a seeded match in the browser**

To verify the UI without waiting for the workflow, temporarily add preview/summary data to one match in `matches.json`. Find any match and add:

```json
"preview": "Deutschland und Brasilien treffen in einem packenden Gruppenduell aufeinander. Beide Teams zeigen bislang starke Leistungen — ein enges Spiel ist garantiert.",
"summary": null
```

Then open `index.html` in a browser:
```bash
open /Users/gleb/Developer/wm2026/index.html
```

Verify:
- The "⚡ Vorschau" button appears on the seeded match card only
- Clicking it expands the yellow-bordered panel with the preview text
- Clicking again collapses it
- Other cards show no button
- Switch tabs and back — panel state resets (expected, renderSchedule re-renders)

Then revert the test seed before committing:
```bash
git checkout matches.json
```

- [ ] **Step 5: Commit and push**

```bash
git add index.html
git commit -m "feat: add AI preview panel to match cards"
git push
```
