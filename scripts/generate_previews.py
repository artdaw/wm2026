import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

MATCHES_JSON = os.path.join(os.path.dirname(__file__), '..', 'matches.json')
WINDOW_PREVIEW  = timedelta(days=7)
WINDOW_FINISHED = timedelta(minutes=105)
API_URL         = 'https://api.anthropic.com/v1/messages'
DEFAULT_MODEL   = 'claude-opus-4-7'

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


def call_claude(prompt, api_key, model=DEFAULT_MODEL, base_url=API_URL):
    payload = json.dumps({
        'model': model,
        'max_tokens': 150,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode()
    req = urllib.request.Request(
        base_url,
        data=payload,
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data['content'][0]['text']


def main():
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    model   = os.environ.get('CLAUDE_MODEL', DEFAULT_MODEL)

    if not api_key:
        print('ANTHROPIC_API_KEY not set — skipping', file=sys.stderr)
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
                text = call_claude(build_summary_prompt(m), api_key, model)
                m, changed = merge_ai_text(m, 'summary', text)
                if changed:
                    summaries_gen += 1
                    any_changed = True
            except Exception as e:
                print(f"Summary error for {m.get('home')} vs {m.get('away')}: {e}",
                      file=sys.stderr)
        elif needs_preview(m, now):
            try:
                text = call_claude(build_preview_prompt(m), api_key, model)
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
