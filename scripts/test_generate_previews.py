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
