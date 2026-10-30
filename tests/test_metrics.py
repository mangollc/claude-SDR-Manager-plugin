from __future__ import annotations

import unittest
from datetime import date

from sdrlib import metrics, targets
from tests.helpers import WINDOW_COUNTS, activity_row, meeting, window_meetings

WINDOW_START = date(2026, 10, 5)
WINDOW_END = date(2026, 11, 1)
WEEKS = ["2026-W41", "2026-W42", "2026-W43", "2026-W44"]
ALL_CHANNELS = ["call", "email", "linkedin"]


def resolved_targets(channels=None):
    return targets.resolve_targets({"channels": channels or ALL_CHANNELS, "targets": {}})


class FixtureTests(unittest.TestCase):
    """Every expected value here was worked out by hand from the fixture."""

    def setUp(self):
        self.rates = metrics.calculate_rates(WINDOW_COUNTS)
        self.summary = metrics.meeting_summary(window_meetings(), WINDOW_START, WINDOW_END)

    def test_touches(self):
        self.assertEqual(metrics.touches(WINDOW_COUNTS), 2080)

    def test_connect_rate(self):
        self.assertAlmostEqual(self.rates["connect_rate"], 0.054545, places=6)

    def test_email_reply_rate(self):
        self.assertAlmostEqual(self.rates["email_reply_rate"], 0.034146, places=6)

    def test_bounce_rate(self):
        self.assertAlmostEqual(self.rates["bounce_rate"], 0.012195, places=6)

    def test_linkedin_acceptance_rate(self):
        self.assertAlmostEqual(self.rates["li_accept_rate"], 0.300000, places=6)

    def test_linkedin_reply_rate(self):
        self.assertAlmostEqual(self.rates["li_reply_rate"], 0.100000, places=6)

    def test_conversations(self):
        self.assertEqual(metrics.conversations(WINDOW_COUNTS), 95)

    def test_meeting_rate(self):
        self.assertAlmostEqual(metrics.meeting_rate(12, 95), 0.126316, places=6)

    def test_meeting_counts(self):
        self.assertEqual(self.summary["booked"], 12)
        self.assertEqual(self.summary["due"], 12)
        self.assertEqual(self.summary["held"], 9)
        self.assertEqual(self.summary["no_show"], 2)
        self.assertEqual(self.summary["cancelled"], 1)
        self.assertEqual(self.summary["accepted_yes"], 6)
        self.assertEqual(self.summary["accepted_no"], 3)

    def test_show_rate(self):
        self.assertAlmostEqual(self.summary["show_rate"], 0.75, places=6)

    def test_acceptance_rate(self):
        self.assertAlmostEqual(self.summary["acceptance_rate"], 0.666667, places=6)

    def test_window_targets(self):
        result = metrics.window_targets(
            {"name": "Ava Reyes", "start_date": "2025-01-06"},
            WEEKS,
            {},
            resolved_targets(),
            ALL_CHANNELS,
            None,
            targets.load_defaults()["ramp"],
        )

        self.assertEqual(result["working_days"], 20)
        self.assertEqual(result["touches"], 2080)
        self.assertAlmostEqual(result["meetings_held"], 9.23, places=2)


class RateEdgeTests(unittest.TestCase):
    def test_zero_dials_gives_no_connect_rate(self):
        self.assertIsNone(metrics.calculate_rates({**WINDOW_COUNTS, "dials": 0})["connect_rate"])

    def test_zero_conversations_gives_no_meeting_rate(self):
        self.assertIsNone(metrics.meeting_rate(3, 0))

    def test_sum_counts_adds_rows_together(self):
        rows = [activity_row("2026-10-26", dials=3), activity_row("2026-10-27", dials=4)]

        self.assertEqual(metrics.sum_counts(rows)["dials"], 7)

    def test_sum_counts_of_nothing_is_all_zero(self):
        self.assertEqual(metrics.sum_counts([])["emails"], 0)


class MeetingSummaryTests(unittest.TestCase):
    def summary(self, meetings):
        return metrics.meeting_summary(meetings, WINDOW_START, WINDOW_END)

    def test_meeting_due_after_the_window_counts_as_booked_only(self):
        result = self.summary([meeting("scheduled", "pending", due="2026-11-05")])

        self.assertEqual(result["booked"], 1)
        self.assertEqual(result["due"], 0)

    def test_meeting_booked_before_the_window_counts_as_due_only(self):
        result = self.summary([meeting("held", "yes", booked="2026-09-28", due="2026-10-06")])

        self.assertEqual(result["booked"], 0)
        self.assertEqual(result["due"], 1)

    def test_rescheduled_and_scheduled_meetings_are_not_due(self):
        result = self.summary([meeting("rescheduled"), meeting("scheduled")])

        self.assertEqual(result["due"], 0)
        self.assertIsNone(result["show_rate"])

    def test_pending_meetings_stay_out_of_the_acceptance_rate(self):
        result = self.summary([meeting("held", "yes"), meeting("held", "pending")])

        self.assertEqual(result["acceptance_rate"], 1.0)
        self.assertEqual(result["pending"], 1)

    def test_blank_acceptance_gives_no_rate_and_no_pending(self):
        result = self.summary([meeting("held", ""), meeting("held", "")])

        self.assertIsNone(result["acceptance_rate"])
        self.assertEqual(result["pending"], 0)

    def test_window_edges_are_included(self):
        first = meeting("held", booked="2026-10-05", due="2026-10-05")
        last = meeting("held", booked="2026-11-01", due="2026-11-01")

        self.assertEqual(self.summary([first, last])["booked"], 2)


class WorkingDayTests(unittest.TestCase):
    no_time_off = {"team_days_off": 0, "rep_days_off": {}}

    def test_a_full_week_has_five_days(self):
        self.assertEqual(metrics.working_days("2026-W44", self.no_time_off, "Ben Carter"), 5)

    def test_team_and_rep_days_off_both_count(self):
        time_off = {"team_days_off": 1, "rep_days_off": {"Ben Carter": 2}}

        self.assertEqual(metrics.working_days("2026-W44", time_off, "Ben Carter"), 2)

    def test_time_off_applies_to_the_named_rep_only(self):
        time_off = {"team_days_off": 0, "rep_days_off": {"Ben Carter": 2}}

        self.assertEqual(metrics.working_days("2026-W44", time_off, "Ava Reyes"), 5)

    def test_a_full_week_off_gives_zero_days(self):
        time_off = {"team_days_off": 0, "rep_days_off": {"Ben Carter": 5}}

        self.assertEqual(metrics.working_days("2026-W44", time_off, "Ben Carter"), 0)

    def test_working_days_never_go_negative(self):
        time_off = {"team_days_off": 3, "rep_days_off": {"Ben Carter": 5}}

        self.assertEqual(metrics.working_days("2026-W44", time_off, "Ben Carter"), 0)

    def test_data_ending_wednesday_gives_three_days(self):
        result = metrics.working_days(
            "2026-W44", self.no_time_off, "Ben Carter", date(2026, 10, 28)
        )

        self.assertEqual(result, 3)

    def test_data_ending_on_the_weekend_is_a_full_week(self):
        result = metrics.working_days("2026-W44", self.no_time_off, "Ben Carter", date(2026, 11, 1))

        self.assertEqual(result, 5)


class DaysActiveTests(unittest.TestCase):
    def test_counts_distinct_weekdays(self):
        rows = [
            activity_row("2026-10-26", dials=1),
            activity_row("2026-10-26", channel="email", emails=1),
            activity_row("2026-10-27", dials=1),
        ]

        self.assertEqual(metrics.days_active(rows), 2)

    def test_weekend_touches_add_no_working_days(self):
        rows = [activity_row("2026-10-26", dials=1), activity_row("2026-10-31", dials=9)]

        self.assertEqual(metrics.days_active(rows), 1)

    def test_weekly_rows_give_no_answer(self):
        self.assertIsNone(
            metrics.days_active([activity_row("2026-10-26", granularity="week", dials=9)])
        )


class TargetTests(unittest.TestCase):
    def test_touch_target_uses_only_the_channels_given(self):
        result = metrics.touch_target_per_day(resolved_targets(), ["call", "email"])

        self.assertEqual(result, 85)

    def test_new_hire_targets_follow_the_ramp(self):
        result = metrics.window_targets(
            {"name": "Nina Patel", "start_date": "2026-09-20"},
            WEEKS,
            {},
            resolved_targets(),
            ALL_CHANNELS,
            None,
            targets.load_defaults()["ramp"],
        )

        self.assertEqual(result["working_days"], 20)
        self.assertEqual(result["touches"], 520)
        self.assertAlmostEqual(result["meetings_held"], 2.31, places=2)

    def test_no_start_date_means_full_targets(self):
        result = metrics.window_targets(
            {"name": "Ava Reyes"},
            WEEKS,
            {},
            resolved_targets(),
            ALL_CHANNELS,
            None,
            targets.load_defaults()["ramp"],
        )

        self.assertEqual(result["touches"], 2080)

    def test_time_off_lowers_targets(self):
        time_off = {"2026-W44": {"team_days_off": 0, "rep_days_off": {"Ava Reyes": 5}}}

        result = metrics.window_targets(
            {"name": "Ava Reyes"},
            WEEKS,
            time_off,
            resolved_targets(),
            ALL_CHANNELS,
            None,
            targets.load_defaults()["ramp"],
        )

        self.assertEqual(result["working_days"], 15)
        self.assertEqual(result["touches"], 1560)

    def test_a_partial_final_week_lowers_targets(self):
        result = metrics.window_targets(
            {"name": "Ava Reyes"},
            WEEKS,
            {},
            resolved_targets(),
            ALL_CHANNELS,
            date(2026, 10, 28),
            targets.load_defaults()["ramp"],
        )

        self.assertEqual(result["working_days"], 18)
        self.assertEqual(result["touches"], 1872)


if __name__ == "__main__":
    unittest.main()
