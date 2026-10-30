from __future__ import annotations

import unittest
from datetime import date

from sdrlib import focus, metrics, targets
from sdrlib.focus import (
    BELOW,
    NEAR,
    NOT_AVAILABLE,
    NOT_ENOUGH_DATA,
    ON_TARGET,
    bounce_flag,
    choose_status,
    compare,
    evaluate_outcome,
    evaluate_steps,
    stretch_focus,
    team_pattern,
)
from tests.helpers import WINDOW_COUNTS, window_meetings

TARGETS = targets.resolve_targets({"channels": ["call", "email", "linkedin"], "targets": {}})
MINIMUMS = targets.load_defaults()["minimums"]
NEAR_BAND = targets.load_defaults()["near_band"]
START, END = date(2026, 10, 5), date(2026, 11, 1)


def build_window(meetings=None, **count_changes):
    """Build a four-week window from the fixture, with optional count changes."""
    counts = {**WINDOW_COUNTS, **count_changes}
    summary = metrics.meeting_summary(
        window_meetings() if meetings is None else meetings, START, END
    )
    rate = metrics.meeting_rate(summary["booked"], metrics.conversations(counts))
    return {
        "counts": counts,
        "touches": metrics.touches(counts),
        "conversations": metrics.conversations(counts),
        "rates": {**metrics.calculate_rates(counts), "meeting_rate": rate},
        "meetings": summary,
        "targets": {"touches": 2080, "meetings_held": 9.23},
    }


def steps(*statuses):
    return [
        {
            "number": number,
            "name": f"Step {number}",
            "status": status,
            "metric": f"metric_{number}",
            "actual": 1,
            "target": 2,
        }
        for number, status in enumerate(statuses, start=1)
    ]


def outcome(status):
    return {"actual": 1, "target": 2, "status": status}


ALL_ON_TARGET = (ON_TARGET,) * 5
STRETCH = {"step": 2, "metric": "connect_rate", "actual": 0.07, "target": 0.133, "kind": "stretch"}


class CompareTests(unittest.TestCase):
    def test_exactly_at_target_is_on_target(self):
        self.assertEqual(compare(100, 100), ON_TARGET)

    def test_exactly_at_85_percent_is_near(self):
        self.assertEqual(compare(85, 100), NEAR)

    def test_just_under_85_percent_is_below(self):
        self.assertEqual(compare(84.9, 100), BELOW)

    def test_zero_actual_is_below(self):
        self.assertEqual(compare(0, 100), BELOW)

    def test_missing_actual_is_not_available(self):
        self.assertEqual(compare(None, 100), NOT_AVAILABLE)

    def test_missing_target_is_not_available(self):
        self.assertEqual(compare(10, None), NOT_AVAILABLE)

    def test_zero_target_is_not_available(self):
        self.assertEqual(compare(10, 0), NOT_AVAILABLE)

    def test_not_available_comes_before_not_enough_data(self):
        self.assertEqual(compare(None, 100, enough_data=False), NOT_AVAILABLE)

    def test_small_sample_is_not_enough_data(self):
        self.assertEqual(compare(50, 100, enough_data=False), NOT_ENOUGH_DATA)


class FixtureTests(unittest.TestCase):
    """The hand-worked fixture, step by step."""

    def setUp(self):
        self.window = build_window()
        self.steps = evaluate_steps(self.window, TARGETS, MINIMUMS, NEAR_BAND)
        self.outcome = evaluate_outcome(self.window, NEAR_BAND)

    def test_step_statuses(self):
        self.assertEqual(
            [step["status"] for step in self.steps],
            [ON_TARGET, NEAR, ON_TARGET, NEAR, ON_TARGET],
        )

    def test_step_numbers_and_names(self):
        self.assertEqual(
            [(step["number"], step["name"]) for step in self.steps],
            [
                (1, "Activity"),
                (2, "Response"),
                (3, "Meetings booked"),
                (4, "Meetings held"),
                (5, "Meetings accepted"),
            ],
        )

    def test_response_step_names_its_weakest_metric(self):
        self.assertEqual(self.steps[1]["metric"], "li_reply_rate")

    def test_outcome_is_near(self):
        self.assertEqual(self.outcome["status"], NEAR)
        self.assertEqual(self.outcome["actual"], 9)

    def test_result_is_watch_on_the_response_step(self):
        decision = choose_status(self.steps, self.outcome, False, None)

        self.assertEqual(decision["status"], "Watch")
        self.assertEqual(decision["focus"]["step"], 2)
        self.assertEqual(decision["focus"]["metric"], "li_reply_rate")
        self.assertEqual(decision["focus"]["kind"], "gap")


class StepTests(unittest.TestCase):
    def test_response_skips_metrics_with_small_samples(self):
        window = build_window(li_messages=10, li_replies=0)

        step = evaluate_steps(window, TARGETS, MINIMUMS, NEAR_BAND)[1]

        self.assertNotEqual(step["metric"], "li_reply_rate")

    def test_response_with_only_small_samples_is_not_enough_data(self):
        window = build_window(dials=10, emails=10, li_requests=10, li_messages=10)

        step = evaluate_steps(window, TARGETS, MINIMUMS, NEAR_BAND)[1]

        self.assertEqual(step["status"], NOT_ENOUGH_DATA)

    def test_response_with_no_data_is_not_available(self):
        window = build_window(dials=0, emails=0, li_requests=0, li_messages=0)

        step = evaluate_steps(window, TARGETS, MINIMUMS, NEAR_BAND)[1]

        self.assertEqual(step["status"], NOT_AVAILABLE)

    def test_acceptance_with_a_small_sample_is_not_enough_data(self):
        meetings = window_meetings()[:4]

        step = evaluate_steps(build_window(meetings), TARGETS, MINIMUMS, NEAR_BAND)[4]

        self.assertEqual(step["status"], NOT_ENOUGH_DATA)

    def test_show_rate_with_a_small_sample_is_not_enough_data(self):
        meetings = window_meetings()[:4]

        step = evaluate_steps(build_window(meetings), TARGETS, MINIMUMS, NEAR_BAND)[3]

        self.assertEqual(step["status"], NOT_ENOUGH_DATA)

    def test_meeting_rate_with_few_conversations_is_not_enough_data(self):
        window = build_window(connected=2, replies=2, li_replies=2)

        step = evaluate_steps(window, TARGETS, MINIMUMS, NEAR_BAND)[2]

        self.assertEqual(step["status"], NOT_ENOUGH_DATA)

    def test_no_meetings_file_leaves_later_steps_unavailable(self):
        window = {**build_window(), "meetings": None}
        window["rates"] = {**window["rates"], "meeting_rate": None}

        result = evaluate_steps(window, TARGETS, MINIMUMS, NEAR_BAND)

        self.assertEqual([step["status"] for step in result[2:]], [NOT_AVAILABLE] * 3)
        self.assertEqual(evaluate_outcome(window, NEAR_BAND)["status"], NOT_AVAILABLE)

    def test_zero_count_target_is_not_available(self):
        window = {**build_window(), "targets": {"touches": 0, "meetings_held": 0}}

        self.assertEqual(
            evaluate_steps(window, TARGETS, MINIMUMS, NEAR_BAND)[0]["status"], NOT_AVAILABLE
        )
        self.assertEqual(evaluate_outcome(window, NEAR_BAND)["status"], NOT_AVAILABLE)


class ChooseStatusTests(unittest.TestCase):
    def test_month_one_rep_is_onboarding_however_strong(self):
        decision = choose_status(steps(*ALL_ON_TARGET), outcome(ON_TARGET), True, STRETCH)

        self.assertEqual(decision, {"status": "Onboarding", "focus": None})

    def test_met_goal_with_clean_steps_is_on_track_with_stretch(self):
        decision = choose_status(steps(*ALL_ON_TARGET), outcome(ON_TARGET), False, STRETCH)

        self.assertEqual(decision, {"status": "On track", "focus": STRETCH})

    def test_met_goal_outranks_a_weak_early_step(self):
        given = steps(BELOW, ON_TARGET, ON_TARGET, ON_TARGET, ON_TARGET)

        decision = choose_status(given, outcome(ON_TARGET), False, None)

        self.assertEqual(decision["status"], "On track")

    def test_met_goal_with_poor_acceptance_needs_attention(self):
        given = steps(ON_TARGET, ON_TARGET, ON_TARGET, ON_TARGET, BELOW)

        decision = choose_status(given, outcome(ON_TARGET), False, STRETCH)

        self.assertEqual(decision["status"], "Needs attention")
        self.assertEqual(decision["focus"]["step"], 5)

    def test_first_below_step_wins(self):
        given = steps(ON_TARGET, BELOW, ON_TARGET, BELOW, ON_TARGET)

        decision = choose_status(given, outcome(BELOW), False, None)

        self.assertEqual(decision["status"], "Needs attention")
        self.assertEqual(decision["focus"]["step"], 2)

    def test_below_outranks_an_earlier_near_step(self):
        given = steps(NEAR, ON_TARGET, BELOW, ON_TARGET, ON_TARGET)

        self.assertEqual(choose_status(given, outcome(BELOW), False, None)["focus"]["step"], 3)

    def test_near_with_nothing_below_is_watch(self):
        given = steps(ON_TARGET, ON_TARGET, NEAR, ON_TARGET, ON_TARGET)

        decision = choose_status(given, outcome(NEAR), False, None)

        self.assertEqual(decision["status"], "Watch")
        self.assertEqual(decision["focus"]["step"], 3)

    def test_short_of_goal_with_clean_steps_is_review(self):
        decision = choose_status(steps(*ALL_ON_TARGET), outcome(BELOW), False, None)

        self.assertEqual(decision, {"status": "Review", "focus": None})

    def test_short_of_goal_with_no_usable_steps_is_review(self):
        decision = choose_status(steps(*(NOT_ENOUGH_DATA,) * 5), outcome(NEAR), False, None)

        self.assertEqual(decision["status"], "Review")

    def test_no_meetings_file_with_clean_steps_is_limited_data(self):
        given = steps(ON_TARGET, ON_TARGET, NOT_AVAILABLE, NOT_AVAILABLE, NOT_AVAILABLE)

        decision = choose_status(given, outcome(NOT_AVAILABLE), False, None)

        self.assertEqual(decision, {"status": "Limited data", "focus": None})

    def test_no_meetings_file_with_a_weak_step_needs_attention(self):
        given = steps(BELOW, ON_TARGET, NOT_AVAILABLE, NOT_AVAILABLE, NOT_AVAILABLE)

        decision = choose_status(given, outcome(NOT_AVAILABLE), False, None)

        self.assertEqual(decision["status"], "Needs attention")
        self.assertEqual(decision["focus"]["step"], 1)

    def test_no_working_days_is_limited_data(self):
        given = steps(*(NOT_AVAILABLE,) * 5)

        decision = choose_status(given, outcome(NOT_AVAILABLE), False, None)

        self.assertEqual(decision["status"], "Limited data")


class StretchTests(unittest.TestCase):
    def test_chooses_the_metric_furthest_from_its_stretch(self):
        window = build_window(connected=64, dials=920, replies=44, emails=840)

        result = stretch_focus(window, TARGETS, MINIMUMS)

        self.assertEqual(result["metric"], "connect_rate")
        self.assertEqual(result["kind"], "stretch")
        self.assertEqual(result["target"], 0.133)

    def test_no_focus_when_every_stretch_is_met(self):
        window = build_window(connected=200, dials=900, replies=80, emails=800)

        self.assertIsNone(stretch_focus(window, TARGETS, MINIMUMS))

    def test_skips_metrics_with_small_samples(self):
        window = build_window(dials=50, connected=2)

        self.assertEqual(stretch_focus(window, TARGETS, MINIMUMS)["metric"], "email_reply_rate")


class BounceTests(unittest.TestCase):
    def window(self, emails, rate):
        return {"counts": {"emails": emails}, "rates": {"bounce_rate": rate}}

    def test_two_percent_on_100_emails_raises_the_flag(self):
        self.assertTrue(bounce_flag(self.window(100, 0.02), TARGETS))

    def test_under_two_percent_raises_no_flag(self):
        self.assertFalse(bounce_flag(self.window(100, 0.019), TARGETS))

    def test_a_small_sample_raises_no_flag(self):
        self.assertFalse(bounce_flag(self.window(50, 0.05), TARGETS))

    def test_no_emails_raises_no_flag(self):
        self.assertFalse(bounce_flag(self.window(0, None), TARGETS))


def rep(status="Needs attention", step=None):
    return {
        "status": status,
        "focus": {"step": step, "kind": "gap"} if step else None,
    }


class TeamPatternTests(unittest.TestCase):
    def test_half_of_six_reps_sharing_a_step_is_a_pattern(self):
        reps = [rep(step=2)] * 3 + [rep("On track")] * 3

        self.assertEqual(team_pattern(reps)["step"], 2)

    def test_fewer_than_three_reps_is_no_pattern(self):
        self.assertIsNone(team_pattern([rep(step=2)] * 2 + [rep("On track")] * 2))

    def test_under_half_is_no_pattern(self):
        self.assertIsNone(team_pattern([rep(step=2)] * 3 + [rep("On track")] * 4))

    def test_unjudged_reps_are_left_out_of_the_count(self):
        reps = [rep(step=2)] * 3 + [rep("On track")] * 3 + [rep("Onboarding"), rep("Limited data")]

        self.assertEqual(team_pattern(reps)["step"], 2)

    def test_stretch_focus_never_counts_as_sharing_a_step(self):
        reps = [{"status": "On track", "focus": {"step": 2, "kind": "stretch"}} for _ in range(4)]

        self.assertIsNone(team_pattern(reps))

    def test_pattern_names_the_step_and_the_counts(self):
        result = team_pattern([rep(step=4)] * 3)

        self.assertEqual(result, {"step": 4, "name": "Meetings held", "reps": 3, "judged": 3})

    def test_no_reps_is_no_pattern(self):
        self.assertIsNone(team_pattern([]))


class ModuleTests(unittest.TestCase):
    def test_lists_five_steps(self):
        self.assertEqual(len(focus.STEP_NAMES), 5)


if __name__ == "__main__":
    unittest.main()
