from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from tests.helpers import activity_row, make_workspace, run_cli, window_meetings

from sdrlib import history
from sdrlib.scorecard import build_scorecard

NOW = datetime(2026, 10, 30, 12, 0, 0)
FRIDAY = "2026-10-30"


def seed_activity(workspace, reps=("Ava Reyes",), day=FRIDAY):
    """Store the hand-worked fixture's totals for each rep on one date, as a single import."""
    rows = []
    for rep in reps:
        rows += [
            activity_row(day, rep, "call", dials=880, connected=48),
            activity_row(day, rep, "email", emails=820, replies=28, bounces=10),
            activity_row(
                day,
                rep,
                "linkedin",
                li_requests=190,
                li_accepted=57,
                li_messages=190,
                li_replies=19,
            ),
        ]
    history.write_activity(workspace, rows)


class ScorecardTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def workspace(self, **profile_changes):
        return make_workspace(self.folder, **profile_changes)

    def seeded(self, **profile_changes):
        workspace = self.workspace(**profile_changes)
        seed_activity(workspace)
        history.write_meetings(workspace, "2026-W44", window_meetings())
        return workspace

    @staticmethod
    def rep(result, name="Ava Reyes"):
        return next(item for item in result["reps"] if item["name"] == name)


class ContractTests(ScorecardTest):
    def test_has_every_top_level_key(self):
        result = build_scorecard(self.seeded(), now=NOW)

        self.assertEqual(
            set(result),
            {
                "schema_version",
                "week",
                "week_start",
                "week_end",
                "window_start",
                "window_end",
                "generated_at",
                "partial_week",
                "last_activity_date",
                "channels_present",
                "sources",
                "targets",
                "minimums",
                "team",
                "reps",
                "notes",
            },
        )

    def test_has_every_rep_key(self):
        rep = self.rep(build_scorecard(self.seeded(), now=NOW))

        self.assertEqual(
            set(rep),
            {
                "name",
                "slug",
                "status",
                "month_in_role",
                "this_week",
                "window",
                "steps",
                "outcome",
                "focus",
                "trend",
                "flags",
                "notes",
            },
        )

    def test_has_every_team_key(self):
        team = build_scorecard(self.seeded(), now=NOW)["team"]

        self.assertTrue(
            {"totals", "rates", "meetings", "status_counts", "pattern", "targets"} <= set(team)
        )

    def test_saves_the_file_and_it_round_trips_as_json(self):
        workspace = self.seeded()

        result = build_scorecard(workspace, now=NOW)

        path = workspace / "history" / "metrics" / "2026-W44.json"
        self.assertEqual(json.loads(path.read_text()), result)

    def test_uses_the_latest_week_by_default(self):
        result = build_scorecard(self.seeded(), now=NOW)

        self.assertEqual(result["week"], "2026-W44")
        self.assertEqual(result["week_start"], "2026-10-26")
        self.assertEqual(result["window_start"], "2026-10-05")
        self.assertEqual(result["window_end"], "2026-11-01")

    def test_records_when_it_was_generated(self):
        result = build_scorecard(self.seeded(), now=NOW)

        self.assertEqual(result["generated_at"], "2026-10-30T12:00:00")


class FixtureTests(ScorecardTest):
    def test_matches_the_hand_worked_result(self):
        rep = self.rep(build_scorecard(self.seeded(), now=NOW))

        self.assertEqual(rep["status"], "Watch")
        self.assertEqual(rep["focus"]["step"], 2)
        self.assertEqual(rep["focus"]["metric"], "li_reply_rate")
        self.assertEqual(rep["window"]["touches"], 2080)
        self.assertEqual(rep["window"]["conversations"], 95)
        self.assertEqual(rep["outcome"]["actual"], 9)
        self.assertAlmostEqual(rep["outcome"]["target"], 9.23, places=2)
        self.assertAlmostEqual(rep["window"]["rates"]["meeting_rate"], 0.126316, places=6)

    def test_counts_this_week_separately_from_the_window(self):
        workspace = self.seeded()
        history.write_activity(workspace, [activity_row("2026-10-12", dials=100)])

        rep = self.rep(build_scorecard(workspace, now=NOW))

        self.assertEqual(rep["this_week"]["counts"]["dials"], 880)
        self.assertEqual(rep["window"]["counts"]["dials"], 980)

    def test_trend_covers_four_weeks_oldest_first(self):
        trend = self.rep(build_scorecard(self.seeded(), now=NOW))["trend"]

        self.assertEqual(trend["weeks"], ["2026-W41", "2026-W42", "2026-W43", "2026-W44"])
        self.assertEqual(trend["touches"], [0, 0, 0, 2080])
        self.assertIsNone(trend["connect_rate"][0])
        self.assertAlmostEqual(trend["connect_rate"][3], 0.054545, places=6)
        self.assertEqual(trend["meetings_booked"], [0, 12, 0, 0])
        self.assertEqual(trend["meetings_held"], [0, 9, 0, 0])


class SelectionTests(ScorecardTest):
    def test_selected_week_with_no_activity_explains_itself(self):
        with self.assertRaisesRegex(ValueError, "2026-W40"):
            build_scorecard(self.seeded(), week="2026-W40", now=NOW)

    def test_no_history_at_all_explains_itself(self):
        with self.assertRaisesRegex(ValueError, "activity"):
            build_scorecard(self.workspace(), now=NOW)


class RepHandlingTests(ScorecardTest):
    def test_inactive_reps_are_left_out_of_reps_and_totals(self):
        workspace = self.workspace(
            reps=[
                {"name": "Ava Reyes", "start_date": "2025-01-06"},
                {"name": "Gone Rep", "start_date": "2025-01-06", "active": False},
            ]
        )
        seed_activity(workspace, reps=("Ava Reyes", "Gone Rep"))

        result = build_scorecard(workspace, now=NOW)

        self.assertEqual([rep["name"] for rep in result["reps"]], ["Ava Reyes"])
        self.assertEqual(result["team"]["totals"]["dials"], 880)

    def test_reps_are_sorted_alphabetically(self):
        workspace = self.seeded(
            reps=[
                {"name": "Ben Carter", "start_date": "2025-01-06"},
                {"name": "Ava Reyes", "start_date": "2025-01-06"},
            ]
        )

        names = [rep["name"] for rep in build_scorecard(workspace, now=NOW)["reps"]]

        self.assertEqual(names, ["Ava Reyes", "Ben Carter"])

    def test_month_one_rep_is_onboarding(self):
        workspace = self.seeded(reps=[{"name": "Ava Reyes", "start_date": "2026-10-12"}])

        rep = self.rep(build_scorecard(workspace, now=NOW))

        self.assertEqual(rep["status"], "Onboarding")
        self.assertEqual(rep["month_in_role"], 1)
        self.assertIsNone(rep["focus"])

    def test_no_start_date_adds_a_note(self):
        workspace = self.seeded(reps=[{"name": "Ava Reyes"}])

        rep = self.rep(build_scorecard(workspace, now=NOW))

        self.assertIsNone(rep["month_in_role"])
        self.assertTrue(any("start date" in note for note in rep["notes"]))
        self.assertEqual(rep["window"]["targets"]["touches"], 2080)

    def test_rep_with_no_working_days_this_week_is_out(self):
        workspace = self.seeded()
        folder = workspace / "history" / "time-off"
        folder.mkdir(parents=True)
        (folder / "2026-W44.json").write_text(
            json.dumps({"team_days_off": 0, "rep_days_off": {"Ava Reyes": 5}})
        )

        rep = self.rep(build_scorecard(workspace, now=NOW))

        self.assertTrue(rep["this_week"]["out"])
        self.assertEqual(rep["this_week"]["working_days"], 0)
        self.assertEqual(rep["window"]["working_days"], 15)

    def test_a_high_bounce_rate_raises_a_flag(self):
        workspace = self.workspace()
        history.write_activity(
            workspace, [activity_row(FRIDAY, channel="email", emails=200, bounces=10)]
        )

        rep = self.rep(build_scorecard(workspace, now=NOW))

        self.assertIn("bounce_warning", rep["flags"])


class PartialWeekTests(ScorecardTest):
    def test_data_ending_before_friday_is_a_partial_week(self):
        workspace = self.workspace()
        seed_activity(workspace, day="2026-10-28")

        result = build_scorecard(workspace, now=NOW)

        self.assertTrue(result["partial_week"])
        self.assertEqual(result["last_activity_date"], "2026-10-28")
        self.assertEqual(self.rep(result)["this_week"]["working_days"], 3)
        self.assertEqual(self.rep(result)["window"]["working_days"], 18)

    def test_data_through_friday_is_a_full_week(self):
        result = build_scorecard(self.seeded(), now=NOW)

        self.assertFalse(result["partial_week"])

    def test_weekly_data_is_never_a_partial_week(self):
        workspace = self.workspace()
        history.write_activity(
            workspace, [activity_row("2026-10-26", granularity="week", dials=220)]
        )

        self.assertFalse(build_scorecard(workspace, now=NOW)["partial_week"])


class ChannelTests(ScorecardTest):
    def test_channel_without_data_leaves_targets(self):
        workspace = self.workspace()
        history.write_activity(
            workspace,
            [
                activity_row(FRIDAY, channel="call", dials=880),
                activity_row(FRIDAY, channel="email", emails=820),
            ],
        )

        result = build_scorecard(workspace, now=NOW)

        self.assertEqual(result["channels_present"], ["call", "email"])
        self.assertEqual(self.rep(result)["window"]["targets"]["touches"], 1700)
        self.assertAlmostEqual(result["targets"]["meeting_rate"]["value"], 0.1525, places=4)

    def test_a_channel_the_team_does_not_use_is_noted_and_not_counted(self):
        workspace = self.workspace(channels=["call"])
        seed_activity(workspace)

        result = build_scorecard(workspace, now=NOW)

        self.assertEqual(result["channels_present"], ["call"])
        self.assertEqual(self.rep(result)["window"]["counts"]["emails"], 0)
        self.assertTrue(any("email" in note for note in result["notes"]))


class NoMeetingsTests(ScorecardTest):
    def test_later_steps_are_unavailable_and_the_report_says_why(self):
        workspace = self.workspace()
        seed_activity(workspace)

        result = build_scorecard(workspace, now=NOW)

        rep = self.rep(result)
        self.assertIsNone(rep["window"]["meetings"])
        self.assertEqual(
            [step["status"] for step in rep["steps"][2:]], ["Not available"] * 3
        )
        self.assertEqual(rep["status"], "Watch")
        self.assertTrue(any("meetings" in note.lower() for note in result["notes"]))
        self.assertEqual(rep["trend"]["meetings_held"], [None] * 4)


class TeamTests(ScorecardTest):
    def test_counts_reps_in_each_status(self):
        result = build_scorecard(self.seeded(), now=NOW)

        counts = result["team"]["status_counts"]
        self.assertEqual(counts["Watch"], 1)
        self.assertEqual(sum(counts.values()), 2)

    def test_targets_add_up_across_reps(self):
        result = build_scorecard(self.seeded(), now=NOW)

        self.assertEqual(result["team"]["targets"]["touches"], 4160)


class MetricsCommandTests(ScorecardTest):
    def test_prints_a_short_summary_and_saves_the_file(self):
        workspace = self.seeded()

        code, output = run_cli("metrics", "--workspace", str(workspace))

        self.assertEqual(code, 0)
        self.assertEqual(output["week"], "2026-W44")
        self.assertEqual(output["reps"][0]["name"], "Ava Reyes")
        self.assertEqual(output["reps"][0]["status"], "Watch")
        self.assertTrue(Path(output["path"]).exists())

    def test_week_with_no_activity_needs_the_manager(self):
        workspace = self.seeded()

        code, output = run_cli("metrics", "--workspace", str(workspace), "--week", "2026-W40")

        self.assertEqual(code, 2)
        self.assertIn("2026-W40", output["error"])


if __name__ == "__main__":
    unittest.main()
