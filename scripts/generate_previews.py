import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

MATCHES_JSON = os.path.join(os.path.dirname(__file__), '..', 'matches.json')
WINDOW_PREVIEW  = timedelta(days=7)
WINDOW_FINISHED = timedelta(minutes=105)
API_URL         = 'https://api.anthropic.com/v1/messages'
DEFAULT_MODEL   = 'claude-sonnet-4-6'
BATCH_SIZE      = 8

SYSTEM_PROMPT = (
    'You are a world-renowned football commentator. '
    'You must write 3 to 5 sentences per match. '
    'Use all resources you have including online websites. '
    'Always respond with valid JSON only — no prose before or after.'
)

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


def build_batch_prompt(to_generate):
    """Build one prompt for all matches. to_generate: list of (match_dict, field)."""
    items = []
    for match, field in to_generate:
        no   = match['no']
        home = match.get('home', '?')
        away = match.get('away', '?')
        if field == 'summary':
            hs  = match.get('homeScore', '?')
            aws = match.get('awayScore', '?')
            items.append(
                f'{{"id": {no}, "type": "summary", '
                f'"match": "{home} {hs}:{aws} {away} (beendet)"}}'
            )
        else:
            stage = match.get('stage') or match.get('group', '')
            try:
                ko      = datetime.fromisoformat(match['utc'].replace('Z', '+00:00'))
                date_de = f"{ko.day}. {MONTH_DE[ko.month]} {ko.year}"
            except (KeyError, ValueError):
                date_de = ''
            items.append(
                f'{{"id": {no}, "type": "preview", '
                f'"match": "{home} vs {away}, {stage}, {date_de}"}}'
            )

    matches_block = '[\n  ' + ',\n  '.join(items) + '\n]'
    return (
        f"Erstelle deutschsprachige Kommentare für folgende WM-2026-Spiele.\n\n"
        f"Eingabe:\n{matches_block}\n\n"
        f"Gib ausschließlich ein JSON-Array zurück. Kein Text davor oder danach.\n"
        f"Format: [{{\"id\": <Spielnummer>, \"text\": \"<Kommentar>\"}}, ...]\n\n"
        f"- type=preview: spannende Vorschau auf das bevorstehende Spiel.\n"
        f"- type=summary: Zusammenfassung des beendeten Spiels basierend auf dem angegebenen Ergebnis. "
        f"Keine Fragen, keine Vorbehalte.\n"
        f"Kommentar auf Deutsch, kein Titel."
    )


def parse_batch_response(text):
    """Extract and return a list of {{id, text}} dicts from Claude's response."""
    stripped = text.strip()
    # Direct parse
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # Markdown code fence: ```json [...] ```
    m = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', stripped, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Bare array anywhere in the response
    m = re.search(r'\[.*\]', stripped, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


def merge_ai_text(match, field, text):
    if not text or not text.strip():
        return dict(match), False
    stripped = text.strip()
    # Reject refusals: Claude asking a question back instead of generating text
    if stripped.endswith('?'):
        return dict(match), False
    updated = dict(match)
    updated[field] = stripped
    return updated, True


def call_claude(prompt, api_key, model=DEFAULT_MODEL, base_url=API_URL):
    payload = json.dumps({
        'model': model,
        'max_tokens': 8000,
        'system': SYSTEM_PROMPT,
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
    with urllib.request.urlopen(req, timeout=120) as resp:
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

    to_generate = []
    for m in matches:
        if needs_summary(m, now):
            to_generate.append((m, 'summary'))
        elif needs_preview(m, now):
            to_generate.append((m, 'preview'))

    skipped = len(matches) - len(to_generate)

    if not to_generate:
        print(f'Generated: 0 previews, 0 summaries. Skipped: {skipped}.')
        return

    # Process in batches to avoid API timeouts
    result_map = {}
    batches = [to_generate[i:i + BATCH_SIZE] for i in range(0, len(to_generate), BATCH_SIZE)]
    for i, batch in enumerate(batches, 1):
        print(f'Batch {i}/{len(batches)}: {len(batch)} matches…')
        try:
            response_text = call_claude(build_batch_prompt(batch), api_key, model)
        except Exception as e:
            print(f'API error on batch {i}: {e}', file=sys.stderr)
            continue
        results = parse_batch_response(response_text)
        if results is None:
            print(f'Failed to parse batch {i} response:\n{response_text[:300]}',
                  file=sys.stderr)
            continue
        for item in results:
            if isinstance(item, dict) and 'id' in item and 'text' in item:
                result_map[item['id']] = item['text']

    field_map = {m['no']: field for m, field in to_generate}
    previews_gen = summaries_gen = 0
    updated_matches = []
    any_changed = False

    for m in matches:
        no = m['no']
        if no in field_map and no in result_map:
            field = field_map[no]
            m, changed = merge_ai_text(m, field, result_map[no])
            if changed:
                any_changed = True
                if field == 'preview':
                    previews_gen += 1
                else:
                    summaries_gen += 1
        updated_matches.append(m)

    if any_changed:
        with open(MATCHES_JSON, 'w', encoding='utf-8') as f:
            json.dump(updated_matches, f, ensure_ascii=False, indent=2)
            f.write('\n')

    print(f'Generated: {previews_gen} previews, {summaries_gen} summaries. Skipped: {skipped}.')


if __name__ == '__main__':
    main()
