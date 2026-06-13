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
