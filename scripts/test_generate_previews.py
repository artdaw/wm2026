import sys, unittest
from datetime import datetime, timezone, timedelta
sys.path.insert(0, __file__.replace('/test_generate_previews.py', ''))
from generate_previews import (
    needs_preview, needs_summary,
    build_batch_prompt, parse_batch_response,
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


class TestBuildBatchPrompt(unittest.TestCase):
    def _preview_match(self):
        return {
            'no': 10, 'home': 'Deutschland', 'away': 'Brasilien',
            'stage': 'Gruppe A', 'group': None,
            'utc': '2026-06-17T18:00:00Z',
        }

    def _summary_match(self):
        return {
            'no': 1, 'home': 'Mexiko', 'away': 'Südafrika',
            'homeScore': 2, 'awayScore': 0,
            'utc': '2026-06-11T19:00:00Z',
        }

    def test_contains_match_id(self):
        prompt = build_batch_prompt([(self._preview_match(), 'preview')])
        self.assertIn('10', prompt)

    def test_contains_team_names(self):
        prompt = build_batch_prompt([(self._preview_match(), 'preview')])
        self.assertIn('Deutschland', prompt)
        self.assertIn('Brasilien', prompt)

    def test_preview_type_label(self):
        prompt = build_batch_prompt([(self._preview_match(), 'preview')])
        self.assertIn('preview', prompt)

    def test_summary_includes_score(self):
        prompt = build_batch_prompt([(self._summary_match(), 'summary')])
        self.assertIn('2:0', prompt)
        self.assertIn('summary', prompt)

    def test_multiple_matches(self):
        prompt = build_batch_prompt([
            (self._preview_match(), 'preview'),
            (self._summary_match(), 'summary'),
        ])
        self.assertIn('"id": 10', prompt)
        self.assertIn('"id": 1', prompt)

    def test_requests_json_output(self):
        prompt = build_batch_prompt([(self._preview_match(), 'preview')])
        self.assertIn('JSON', prompt)


class TestParseBatchResponse(unittest.TestCase):
    def test_direct_json_array(self):
        text = '[{"id": 1, "text": "Tolles Spiel."}, {"id": 2, "text": "Spannendes Match."}]'
        result = parse_batch_response(text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 1)

    def test_json_in_markdown_fence(self):
        text = '```json\n[{"id": 5, "text": "Gutes Spiel."}]\n```'
        result = parse_batch_response(text)
        self.assertIsNotNone(result)
        self.assertEqual(result[0]['id'], 5)

    def test_json_with_surrounding_prose(self):
        text = 'Hier sind die Kommentare:\n[{"id": 3, "text": "Super."}]\nViel Spaß!'
        result = parse_batch_response(text)
        self.assertIsNotNone(result)
        self.assertEqual(result[0]['text'], 'Super.')

    def test_invalid_returns_none(self):
        self.assertIsNone(parse_batch_response('Das kann ich leider nicht beantworten.'))

    def test_empty_array(self):
        result = parse_batch_response('[]')
        self.assertEqual(result, [])


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

    def test_refusal_ending_with_question_mark_no_change(self):
        m = {'home': 'Deutschland', 'summary': None}
        refusal = 'Dieses Spiel hat nicht stattgefunden. Soll ich ein anderes Spiel zusammenfassen?'
        updated, changed = merge_ai_text(m, 'summary', refusal)
        self.assertFalse(changed)
        self.assertIsNone(updated['summary'])
