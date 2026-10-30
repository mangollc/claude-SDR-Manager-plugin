from __future__ import annotations

import copy
import unittest
from datetime import date

from sdrlib import targets

ALL_CHANNELS = ["call", "email", "linkedin"]


def profile(channels=None, overrides=None):
    return {"channels": channels or ALL_CHANNELS, "targets": overrides or {}}


class DefaultTargetTests(unittest.TestCase):
    def test_contains_every_target_from_the_spec(self):
        expected = {
            "dials_per_day",
            "emails_per_day",
            "linkedin_touches_per_day",
            "connect_rate",
            "email_reply_rate",
            "li_accept_rate",
            "li_reply_rate",
            "meeting_rate",
            "meetings_held_per_month",
            "show_rate",
            "acceptance_rate",
            "bounce_limit",
        }
        self.assertEqual(set(targets.load_defaults()["targets"]), expected)

    def test_every_target_names_its_source(self):
        for key, entry in targets.load_defaults()["targets"].items():
            self.assertTrue(entry["source"], key)
            self.assertTrue(entry["label"], key)
            self.assertTrue(entry["as_of"], key)


class ResolveTargetTests(unittest.TestCase):
    def test_derives_meeting_rate_for_all_channels(self):
        resolved = targets.resolve_targets(profile())

        self.assertAlmostEqual(resolved["meeting_rate"]["value"], 0.1209, places=4)
        self.assertEqual(resolved["meeting_rate"]["source"], "Calculated from the other targets")

    def test_derives_meeting_rate_for_call_and_email(self):
        resolved = targets.resolve_targets(profile(["call", "email"]))

        self.assertAlmostEqual(resolved["meeting_rate"]["value"], 0.1525, places=4)

    def test_derives_meeting_rate_for_call_only(self):
        resolved = targets.resolve_targets(profile(["call"]))

        self.assertAlmostEqual(resolved["meeting_rate"]["value"], 0.2428, places=4)

    def test_derived_rate_follows_a_team_show_rate(self):
        resolved = targets.resolve_targets(profile(overrides={"show_rate": {"value": 0.70}}))

        self.assertAlmostEqual(resolved["meeting_rate"]["value"], 0.1382, places=4)

    def test_team_meeting_rate_is_used_as_given(self):
        resolved = targets.resolve_targets(profile(overrides={"meeting_rate": {"value": 0.10}}))

        self.assertEqual(resolved["meeting_rate"]["value"], 0.10)
        self.assertEqual(resolved["meeting_rate"]["source"], "team")

    def test_team_override_changes_only_that_target(self):
        given = profile(overrides={"connect_rate": {"value": 0.08, "as_of": "2026-10-30"}})
        before = copy.deepcopy(given)

        resolved = targets.resolve_targets(given)

        self.assertEqual(resolved["connect_rate"]["value"], 0.08)
        self.assertEqual(resolved["connect_rate"]["source"], "team")
        self.assertEqual(resolved["connect_rate"]["stretch"], 0.133)
        self.assertEqual(resolved["email_reply_rate"]["value"], 0.0343)
        self.assertEqual(given, before)

    def test_unknown_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not_a_target"):
            targets.resolve_targets(profile(overrides={"not_a_target": {"value": 1}}))

    def test_no_channels_gives_no_derived_rate(self):
        result = targets.derive_meeting_rate(targets.load_defaults()["targets"], [])

        self.assertIsNone(result)


class MeetingsPerDayTests(unittest.TestCase):
    def test_default_gives_nine_point_two_held_meetings_in_twenty_days(self):
        per_day = targets.meetings_per_working_day(targets.resolve_targets(profile()))

        self.assertAlmostEqual(per_day * 20, 9.23, places=2)


class RampTests(unittest.TestCase):
    def test_month_in_role_counts_thirty_day_blocks(self):
        start = date(2026, 10, 1)
        cases = [
            (date(2026, 10, 1), 1),
            (date(2026, 10, 30), 1),
            (date(2026, 10, 31), 2),
            (date(2026, 11, 30), 3),
            (date(2026, 12, 30), 4),
        ]
        for on, expected in cases:
            self.assertEqual(targets.month_in_role(start, on), expected, on)

    def test_date_before_the_start_counts_as_month_one(self):
        self.assertEqual(targets.month_in_role(date(2026, 10, 1), date(2026, 9, 1)), 1)

    def test_ramp_multipliers(self):
        ramp = targets.load_defaults()["ramp"]
        cases = [(1, 0.0), (2, 0.5), (3, 0.75), (4, 1.0), (12, 1.0)]
        for month, expected in cases:
            self.assertEqual(targets.ramp_multiplier(month, ramp), expected, month)


if __name__ == "__main__":
    unittest.main()
