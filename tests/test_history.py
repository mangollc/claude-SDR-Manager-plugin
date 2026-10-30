from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from sdrlib import history
from tests.helpers import activity_row


class WeekTests(unittest.TestCase):
    def test_names_a_week(self):
        self.assertEqual(history.iso_week(date(2026, 10, 26)), "2026-W44")

    def test_finds_week_bounds(self):
        self.assertEqual(history.week_bounds("2026-W44"), (date(2026, 10, 26), date(2026, 11, 1)))

    def test_rejects_a_badly_formed_week(self):
        with self.assertRaisesRegex(ValueError, "2026-W44"):
            history.week_bounds("week 44")

    def test_metrics_path_refuses_path_characters(self):
        with self.assertRaisesRegex(ValueError, "2026-W44"):
            history.metrics_path(Path("workspace"), "../metrics/2026-W44")

    def test_rejects_a_week_that_does_not_exist(self):
        with self.assertRaises(ValueError):
            history.week_bounds("2026-W99")

    def test_previous_weeks_cross_the_year_boundary(self):
        self.assertEqual(
            history.previous_weeks("2026-W02", 4),
            ["2025-W51", "2025-W52", "2026-W01", "2026-W02"],
        )


class MergeActivityTests(unittest.TestCase):
    def test_keeps_dates_outside_the_import(self):
        existing = [activity_row(f"2026-10-0{day}", dials=1) for day in (5, 6, 7, 8, 9)]
        new = [activity_row("2026-10-07", dials=9), activity_row("2026-10-08", dials=9)]

        merged = history.merge_activity(existing, new)

        self.assertEqual(
            [(row["date"], row["dials"]) for row in merged],
            [
                ("2026-10-05", 1),
                ("2026-10-06", 1),
                ("2026-10-07", 9),
                ("2026-10-08", 9),
                ("2026-10-09", 1),
            ],
        )

    def test_leaves_other_channels_alone(self):
        existing = [activity_row("2026-10-07", channel="email", emails=4)]
        new = [activity_row("2026-10-07", dials=9)]

        merged = history.merge_activity(existing, new)

        self.assertEqual(len(merged), 2)

    def test_a_rep_missing_from_an_imported_date_loses_the_old_row(self):
        existing = [activity_row("2026-10-08", rep="Ben Carter", dials=4)]
        new = [activity_row("2026-10-08", dials=1)]

        merged = history.merge_activity(existing, new)

        self.assertNotIn("Ben Carter", [row["rep"] for row in merged])

    def test_a_stray_old_date_does_not_erase_the_days_between(self):
        existing = [activity_row(day, dials=1) for day in ("2026-10-05", "2026-10-12")]
        new = [activity_row("2026-09-01", dials=2), activity_row("2026-10-26", dials=2)]

        merged = history.merge_activity(existing, new)

        self.assertEqual(
            [row["date"] for row in merged],
            ["2026-09-01", "2026-10-05", "2026-10-12", "2026-10-26"],
        )

    def test_daily_rows_replace_a_stored_weekly_row_for_that_week(self):
        existing = [activity_row("2026-10-19", granularity="week", dials=176)]
        new = [activity_row("2026-10-20", dials=44)]

        merged = history.merge_activity(existing, new)

        self.assertEqual([(row["date"], row["dials"]) for row in merged], [("2026-10-20", 44)])

    def test_a_stored_weekly_row_for_another_week_stays(self):
        existing = [activity_row("2026-10-12", granularity="week", dials=176)]
        new = [activity_row("2026-10-20", dials=44)]

        self.assertEqual(len(history.merge_activity(existing, new)), 2)

    def test_weekly_rows_replace_the_whole_week_for_that_channel(self):
        existing = [activity_row("2026-10-08", dials=4), activity_row("2026-10-12", dials=4)]
        new = [activity_row("2026-10-05", granularity="week", dials=20)]

        merged = history.merge_activity(existing, new)

        self.assertEqual(
            [(row["date"], row["dials"]) for row in merged],
            [("2026-10-05", 20), ("2026-10-12", 4)],
        )

    def test_does_not_change_its_inputs(self):
        existing = [activity_row("2026-10-07", dials=1)]
        new = [activity_row("2026-10-07", dials=9)]

        history.merge_activity(existing, new)

        self.assertEqual(existing[0]["dials"], 1)
        self.assertEqual(new[0]["dials"], 9)


class StorageTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.workspace = Path(folder.name)


class ActivityStorageTests(StorageTest):
    def test_round_trips_counts_as_numbers(self):
        history.write_activity(self.workspace, [activity_row("2026-10-26", dials=7, connected=2)])

        rows = history.read_activity(self.workspace, ["2026-W44"])

        self.assertEqual(rows[0]["dials"], 7)
        self.assertEqual(rows[0]["connected"], 2)
        self.assertEqual(rows[0]["rep"], "Ava Reyes")

    def test_splits_rows_into_week_files(self):
        history.write_activity(
            self.workspace,
            [activity_row("2026-10-23", dials=1), activity_row("2026-10-26", dials=1)],
        )

        names = sorted(p.name for p in (self.workspace / "history" / "activity").iterdir())

        self.assertEqual(names, ["2026-W43.csv", "2026-W44.csv"])

    def test_a_stray_date_leaves_the_weeks_between_on_disk(self):
        history.write_activity(
            self.workspace, [activity_row(day, dials=1) for day in ("2026-10-05", "2026-10-12")]
        )
        history.write_activity(
            self.workspace,
            [activity_row("2026-09-01", dials=2), activity_row("2026-10-26", dials=2)],
        )

        rows = history.read_activity(self.workspace, ["2026-W41", "2026-W42"])

        self.assertEqual(len(rows), 2)

    def test_writing_the_same_import_twice_gives_identical_files(self):
        rows = [activity_row("2026-10-26", dials=7), activity_row("2026-10-27", dials=3)]
        path = self.workspace / "history" / "activity" / "2026-W44.csv"

        history.write_activity(self.workspace, rows)
        first = path.read_bytes()
        history.write_activity(self.workspace, rows)

        self.assertEqual(path.read_bytes(), first)

    def test_later_import_keeps_earlier_dates(self):
        history.write_activity(self.workspace, [activity_row("2026-10-26", dials=7)])
        history.write_activity(self.workspace, [activity_row("2026-10-27", dials=3)])

        rows = history.read_activity(self.workspace, ["2026-W44"])

        self.assertEqual([row["dials"] for row in rows], [7, 3])

    def test_missing_week_gives_no_rows(self):
        self.assertEqual(history.read_activity(self.workspace, ["2026-W01"]), [])

    def test_latest_week_uses_the_newest_file(self):
        history.write_activity(
            self.workspace,
            [activity_row("2026-10-19", dials=1), activity_row("2026-10-26", dials=1)],
        )

        self.assertEqual(history.latest_week(self.workspace), "2026-W44")

    def test_latest_week_is_none_without_history(self):
        self.assertIsNone(history.latest_week(self.workspace))


class MeetingStorageTests(StorageTest):
    meeting = {
        "rep": "Ava Reyes",
        "booked_date": "2026-10-20",
        "due_date": "2026-10-22",
        "status": "held",
        "accepted": "yes",
    }

    def test_returns_the_newest_snapshot(self):
        history.write_meetings(self.workspace, "2026-W43", [self.meeting])
        history.write_meetings(self.workspace, "2026-W44", [{**self.meeting, "status": "no_show"}])

        rows = history.read_latest_meetings(self.workspace)

        self.assertEqual(rows[0]["status"], "no_show")

    def test_no_snapshot_gives_none(self):
        self.assertIsNone(history.read_latest_meetings(self.workspace))


class SourceStorageTests(StorageTest):
    def test_new_import_of_a_file_replaces_its_entry(self):
        first = {"file": "calls.csv", "rows_read": 5}
        other = {"file": "emails.csv", "rows_read": 2}
        history.write_sources(self.workspace, "2026-W44", [first, other])
        history.write_sources(self.workspace, "2026-W44", [{"file": "calls.csv", "rows_read": 9}])

        sources = {item["file"]: item for item in history.read_sources(self.workspace, "2026-W44")}

        self.assertEqual(sources["calls.csv"]["rows_read"], 9)
        self.assertEqual(sources["emails.csv"]["rows_read"], 2)

    def test_missing_week_gives_no_sources(self):
        self.assertEqual(history.read_sources(self.workspace, "2026-W44"), [])


class TimeOffTests(StorageTest):
    def test_missing_file_means_no_time_off(self):
        self.assertEqual(
            history.read_time_off(self.workspace, "2026-W44"),
            {"team_days_off": 0, "rep_days_off": {}},
        )

    def test_reads_a_saved_file(self):
        folder = self.workspace / "history" / "time-off"
        folder.mkdir(parents=True)
        (folder / "2026-W44.json").write_text(
            json.dumps({"team_days_off": 1, "rep_days_off": {"Ben Carter": 2}})
        )

        result = history.read_time_off(self.workspace, "2026-W44")

        self.assertEqual(result["rep_days_off"]["Ben Carter"], 2)

    def test_knows_when_the_question_is_unanswered(self):
        self.assertFalse(history.has_time_off(self.workspace, "2026-W44"))

    def test_counts_an_answer_of_none_as_answered(self):
        folder = self.workspace / "history" / "time-off"
        folder.mkdir(parents=True)
        (folder / "2026-W44.json").write_text(json.dumps({"team_days_off": 0}))

        self.assertTrue(history.has_time_off(self.workspace, "2026-W44"))

    def test_refuses_anything_but_a_week_name(self):
        with self.assertRaises(ValueError):
            history.has_time_off(self.workspace, "../../secrets")


if __name__ == "__main__":
    unittest.main()
