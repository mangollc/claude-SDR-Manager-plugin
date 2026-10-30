from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sdrlib import history
from sdrlib.file_reader import header_signature
from sdrlib.history import ACTIVITY_COUNTS, ACTIVITY_FIELDS, MEETING_FIELDS
from sdrlib.normalize import channel_conflicts, find_mapping, normalize_file, normalize_files
from tests.helpers import make_workspace, run_cli

REPS = {"ava reyes": "Ava Reyes", "a. reyes": "Ava Reyes", "morgan lee": None}

CALL_MAPPING = {
    "kind": "activities",
    "header_row": 1,
    "date_format": "%Y-%m-%d",
    "columns": {"date": "Date", "rep": "Rep"},
    "fixed": {"action": "dial"},
    "flags": {
        "connected": {"column": "Result", "true": ["Connected"], "false": ["No Answer"]},
    },
}

MEETING_MAPPING = {
    "kind": "meetings",
    "header_row": 1,
    "date_format": "%Y-%m-%d",
    "columns": {
        "rep": "Owner",
        "booked_date": "Booked",
        "due_date": "Due",
        "status": "State",
        "accepted": "AE",
    },
    "values": {
        "status": {
            "Done": "held",
            "Missed": "no_show",
            "Off": "cancelled",
            "Moved": "rescheduled",
            "Booked": "scheduled",
        },
        "accepted": {"Accepted": "yes", "Rejected": "no"},
    },
}


class NormalizeTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def write(self, name, text):
        path = self.folder / name
        path.write_text(text, encoding="utf-8")
        return path


class RowCountTests(NormalizeTest):
    cases = [
        ("dial", None, "call", {"dials": 1}),
        ("dial", "connected", "call", {"dials": 1, "connected": 1}),
        ("email", None, "email", {"emails": 1}),
        ("email", "replied", "email", {"emails": 1, "replies": 1}),
        ("email", "bounced", "email", {"emails": 1, "bounces": 1}),
        ("email_reply", None, "email", {"replies": 1}),
        ("email_bounce", None, "email", {"bounces": 1}),
        ("li_request", None, "linkedin", {"li_requests": 1}),
        ("li_request", "accepted", "linkedin", {"li_requests": 1, "li_accepted": 1}),
        ("li_accept", None, "linkedin", {"li_accepted": 1}),
        ("li_message", None, "linkedin", {"li_messages": 1}),
        ("li_message", "replied", "linkedin", {"li_messages": 1, "li_replies": 1}),
        ("li_reply", None, "linkedin", {"li_replies": 1}),
        ("li_other", None, "linkedin", {"li_other": 1}),
    ]

    def test_each_action_adds_the_right_counts(self):
        path = self.write("a.csv", "Date,Rep,Hit\n2026-10-26,Ava Reyes,yes\n")
        for action, flag, channel, expected in self.cases:
            with self.subTest(action=action, flag=flag):
                mapping = {
                    "kind": "activities",
                    "date_format": "%Y-%m-%d",
                    "columns": {"date": "Date", "rep": "Rep"},
                    "fixed": {"action": action},
                    "flags": (
                        {flag: {"column": "Hit", "true": ["yes"], "false": []}} if flag else {}
                    ),
                }

                row = normalize_file(path, mapping, REPS).activity[0]

                self.assertEqual(row["channel"], channel)
                self.assertEqual({k: row[k] for k in ACTIVITY_COUNTS if row[k]}, expected)


class ActivityTests(NormalizeTest):
    def test_rolls_rows_up_to_one_row_per_rep_and_day(self):
        path = self.write(
            "a.csv",
            "Date,Rep,Result\n"
            "2026-10-26,Ava Reyes,Connected\n"
            "2026-10-26,Ava Reyes,Connected\n"
            "2026-10-26,Ava Reyes,No Answer\n",
        )

        result = normalize_file(path, CALL_MAPPING, REPS)

        self.assertEqual(len(result.activity), 1)
        self.assertEqual(result.activity[0]["dials"], 3)
        self.assertEqual(result.activity[0]["connected"], 2)
        self.assertEqual(result.activity[0]["granularity"], "day")

    def test_stores_the_canonical_name_for_an_alias(self):
        path = self.write("a.csv", "Date,Rep,Result\n2026-10-26,A. Reyes,Connected\n")

        self.assertEqual(normalize_file(path, CALL_MAPPING, REPS).activity[0]["rep"], "Ava Reyes")

    def test_leaves_out_ignored_names_without_an_error(self):
        path = self.write("a.csv", "Date,Rep,Result\n2026-10-26,Morgan Lee,Connected\n")

        result = normalize_file(path, CALL_MAPPING, REPS)

        self.assertEqual(result.activity, ())
        self.assertEqual(result.unknown_reps, {})
        self.assertEqual(result.rows_rejected, 0)

    def test_reports_unknown_reps_with_row_counts(self):
        path = self.write(
            "a.csv",
            "Date,Rep,Result\n2026-10-26,New Person,Connected\n2026-10-27,New Person,Connected\n",
        )

        self.assertEqual(normalize_file(path, CALL_MAPPING, REPS).unknown_reps, {"New Person": 2})

    def test_reports_a_new_value_in_a_flag_column(self):
        path = self.write("a.csv", "Date,Rep,Result\n2026-10-26,Ava Reyes,Gatekeeper\n")

        self.assertEqual(
            normalize_file(path, CALL_MAPPING, REPS).unmapped, {"Result": ("Gatekeeper",)}
        )

    def test_blank_flag_counts_as_false(self):
        path = self.write("a.csv", "Date,Rep,Result\n2026-10-26,Ava Reyes,\n")

        result = normalize_file(path, CALL_MAPPING, REPS)

        self.assertEqual(result.activity[0]["connected"], 0)
        self.assertEqual(result.unmapped, {})

    def test_any_value_flag_counts_every_filled_cell(self):
        mapping = {
            **CALL_MAPPING,
            "fixed": {"action": "email"},
            "flags": {"replied": {"column": "Replied At", "any": True}},
        }
        path = self.write(
            "a.csv",
            "Date,Rep,Replied At\n2026-10-26,Ava Reyes,2026-10-27 09:15\n2026-10-26,Ava Reyes,\n",
        )

        row = normalize_file(path, mapping, REPS).activity[0]

        self.assertEqual((row["emails"], row["replies"]), (2, 1))

    def test_action_column_translates_and_skips_unrelated_rows(self):
        mapping = {
            "kind": "activities",
            "date_format": "%Y-%m-%d",
            "columns": {"date": "Date", "rep": "Rep", "action": "Type"},
            "values": {"action": {"Call": "dial", "Note": "skip"}},
        }
        path = self.write(
            "a.csv", "Date,Rep,Type\n2026-10-26,Ava Reyes,Call\n2026-10-26,Ava Reyes,Note\n"
        )

        result = normalize_file(path, mapping, REPS)

        self.assertEqual(result.activity[0]["dials"], 1)
        self.assertEqual(result.rows_rejected, 0)

    def test_reports_a_new_value_in_the_action_column(self):
        mapping = {
            "kind": "activities",
            "date_format": "%Y-%m-%d",
            "columns": {"date": "Date", "rep": "Rep", "action": "Type"},
            "values": {"action": {"Call": "dial"}},
        }
        path = self.write("a.csv", "Date,Rep,Type\n2026-10-26,Ava Reyes,Fax\n")

        self.assertEqual(normalize_file(path, mapping, REPS).unmapped, {"Type": ("Fax",)})

    def test_rejects_rows_with_bad_dates_or_no_rep(self):
        path = self.write(
            "a.csv",
            "Date,Rep,Result\n"
            "not a date,Ava Reyes,Connected\n"
            "2026-10-26,,Connected\n"
            "2026-10-26,Ava Reyes,Connected\n",
        )

        result = normalize_file(path, CALL_MAPPING, REPS)

        self.assertEqual(result.rows_read, 3)
        self.assertEqual(result.rows_rejected, 2)
        self.assertEqual(result.activity[0]["dials"], 1)

    def test_rejects_a_footer_row(self):
        path = self.write(
            "a.csv", "Date,Rep,Result\n2026-10-26,Ava Reyes,Connected\nTotal rows: 1,,\n"
        )

        self.assertEqual(normalize_file(path, CALL_MAPPING, REPS).rows_rejected, 1)

    def test_rejected_examples_hide_prospect_details(self):
        path = self.write(
            "a.csv",
            "Date,Rep,Result,Contact Name,Notes\nbad,Ava Reyes,Connected,Jane Doe,jane@acme.io\n",
        )

        examples = " ".join(normalize_file(path, CALL_MAPPING, REPS).rejected_examples)

        self.assertNotIn("Jane Doe", examples)
        self.assertNotIn("jane@acme.io", examples)
        self.assertIn("bad", examples)

    def test_mapping_naming_a_missing_column_is_explained(self):
        path = self.write("a.csv", "Date,Rep\n2026-10-26,Ava Reyes\n")

        with self.assertRaisesRegex(ValueError, "Result"):
            normalize_file(path, CALL_MAPPING, REPS)

    def test_unknown_mapping_kind_is_explained(self):
        path = self.write("a.csv", "Date,Rep\n2026-10-26,Ava Reyes\n")

        with self.assertRaisesRegex(ValueError, "kind"):
            normalize_file(path, {"kind": "mystery"}, REPS)

    def test_keeps_only_standard_fields(self):
        path = self.write(
            "a.csv",
            "Date,Rep,Result,Contact Name\n2026-10-26,Ava Reyes,Connected,Jane Doe\n",
        )

        row = normalize_file(path, CALL_MAPPING, REPS).activity[0]

        self.assertEqual(tuple(row), ACTIVITY_FIELDS)


class SummaryTests(NormalizeTest):
    mapping = {
        "kind": "rep_summary",
        "date_format": "%Y-%m-%d",
        "columns": {
            "week_start": "Week",
            "rep": "Rep",
            "dials": "Calls",
            "connected": "Connects",
            "emails": "Sent",
            "replies": "Replies",
        },
    }

    def test_splits_a_row_by_channel_and_marks_it_weekly(self):
        path = self.write(
            "a.csv",
            'Week,Rep,Calls,Connects,Sent,Replies\n2026-10-26,Ava Reyes,"1,200",60,300,10\n',
        )

        rows = normalize_file(path, self.mapping, REPS).activity

        by_channel = {row["channel"]: row for row in rows}
        self.assertEqual(set(by_channel), {"call", "email"})
        self.assertEqual(by_channel["call"]["dials"], 1200)
        self.assertEqual(by_channel["email"]["replies"], 10)
        self.assertEqual(by_channel["call"]["granularity"], "week")

    def test_dates_a_midweek_row_to_its_monday(self):
        path = self.write(
            "a.csv", "Week,Rep,Calls,Connects,Sent,Replies\n2026-10-28,Ava Reyes,1,0,1,0\n"
        )

        self.assertEqual(normalize_file(path, self.mapping, REPS).activity[0]["date"], "2026-10-26")

    def test_a_sunday_week_start_moves_to_the_following_monday(self):
        path = self.write(
            "a.csv", "Week,Rep,Calls,Connects,Sent,Replies\n2026-10-25,Ava Reyes,1,0,1,0\n"
        )

        self.assertEqual(normalize_file(path, self.mapping, REPS).activity[0]["date"], "2026-10-26")

    def test_blank_counts_are_zero(self):
        path = self.write(
            "a.csv", "Week,Rep,Calls,Connects,Sent,Replies\n2026-10-26,Ava Reyes,5,,5,\n"
        )

        self.assertEqual(normalize_file(path, self.mapping, REPS).activity[0]["connected"], 0)

    def test_rejects_a_row_with_text_in_a_count(self):
        path = self.write(
            "a.csv", "Week,Rep,Calls,Connects,Sent,Replies\n2026-10-26,Ava Reyes,many,0,1,0\n"
        )

        self.assertEqual(normalize_file(path, self.mapping, REPS).rows_rejected, 1)


class MeetingTests(NormalizeTest):
    def test_translates_status_and_acceptance(self):
        path = self.write(
            "m.csv",
            "Owner,Booked,Due,State,AE\nAva Reyes,2026-10-20,2026-10-22,Done,Accepted\n",
        )

        meeting = normalize_file(path, MEETING_MAPPING, REPS).meetings[0]

        self.assertEqual(
            meeting,
            {
                "rep": "Ava Reyes",
                "booked_date": "2026-10-20",
                "due_date": "2026-10-22",
                "status": "held",
                "accepted": "yes",
            },
        )
        self.assertEqual(tuple(meeting), MEETING_FIELDS)

    def test_missing_due_date_uses_the_booked_date_with_a_note(self):
        path = self.write(
            "m.csv", "Owner,Booked,Due,State,AE\nAva Reyes,2026-10-20,,Done,Accepted\n"
        )

        result = normalize_file(path, MEETING_MAPPING, REPS)

        self.assertEqual(result.meetings[0]["due_date"], "2026-10-20")
        self.assertTrue(result.notes)

    def test_blank_acceptance_is_pending(self):
        path = self.write(
            "m.csv", "Owner,Booked,Due,State,AE\nAva Reyes,2026-10-20,2026-10-22,Done,\n"
        )

        self.assertEqual(
            normalize_file(path, MEETING_MAPPING, REPS).meetings[0]["accepted"], "pending"
        )

    def test_no_acceptance_column_stores_blank(self):
        columns = {k: v for k, v in MEETING_MAPPING["columns"].items() if k != "accepted"}
        mapping = {**MEETING_MAPPING, "columns": columns}
        path = self.write("m.csv", "Owner,Booked,Due,State\nAva Reyes,2026-10-20,2026-10-22,Done\n")

        self.assertEqual(normalize_file(path, mapping, REPS).meetings[0]["accepted"], "")

    def test_reports_a_new_status(self):
        path = self.write(
            "m.csv", "Owner,Booked,Due,State,AE\nAva Reyes,2026-10-20,2026-10-22,Lost,\n"
        )

        self.assertEqual(normalize_file(path, MEETING_MAPPING, REPS).unmapped, {"State": ("Lost",)})

    def test_rejects_a_blank_status(self):
        path = self.write("m.csv", "Owner,Booked,Due,State,AE\nAva Reyes,2026-10-20,2026-10-22,,\n")

        self.assertEqual(normalize_file(path, MEETING_MAPPING, REPS).rows_rejected, 1)

    def test_rejects_a_bad_booked_date(self):
        path = self.write("m.csv", "Owner,Booked,Due,State,AE\nAva Reyes,soon,2026-10-22,Done,\n")

        self.assertEqual(normalize_file(path, MEETING_MAPPING, REPS).rows_rejected, 1)


class ChannelConflictTests(NormalizeTest):
    def test_names_both_files_for_one_channel(self):
        text = "Date,Rep,Result\n2026-10-26,Ava Reyes,Connected\n"
        first = normalize_file(self.write("crm.csv", text), CALL_MAPPING, REPS)
        second = normalize_file(self.write("dialer.csv", text), CALL_MAPPING, REPS)

        self.assertEqual(channel_conflicts([first, second]), {"call": ["crm.csv", "dialer.csv"]})

    def test_names_both_files_when_two_cover_meetings(self):
        text = "Owner,Booked,Due,State,AE\nAva Reyes,2026-10-20,2026-10-22,Done,Accepted\n"
        first = normalize_file(self.write("crm.csv", text), MEETING_MAPPING, REPS)
        second = normalize_file(self.write("tool.csv", text), MEETING_MAPPING, REPS)

        self.assertEqual(channel_conflicts([first, second]), {"meetings": ["crm.csv", "tool.csv"]})

    def test_one_file_per_channel_has_no_conflict(self):
        text = "Date,Rep,Result\n2026-10-26,Ava Reyes,Connected\n"
        result = normalize_file(self.write("crm.csv", text), CALL_MAPPING, REPS)

        self.assertEqual(channel_conflicts([result]), {})


class FindMappingTests(NormalizeTest):
    def test_returns_the_saved_mapping(self):
        path = self.write("a.csv", "Date,Rep,Result\n2026-10-26,Ava Reyes,Connected\n")
        mappings = self.folder / "mappings"
        mappings.mkdir()
        saved = {**CALL_MAPPING, "signature": header_signature(["Date", "Rep", "Result"])}
        (mappings / "calls.json").write_text(json.dumps(saved))

        self.assertEqual(find_mapping(path, mappings)["kind"], "activities")

    def test_returns_none_without_a_match(self):
        path = self.write("a.csv", "Date,Rep,Result\n2026-10-26,Ava Reyes,Connected\n")
        mappings = self.folder / "mappings"
        mappings.mkdir()

        self.assertIsNone(find_mapping(path, mappings))


class NormalizeFilesTests(NormalizeTest):
    def setUp(self):
        super().setUp()
        self.workspace = make_workspace(self.folder)
        saved = {**CALL_MAPPING, "signature": header_signature(["Date", "Rep", "Result"])}
        (self.workspace / "mappings" / "calls.json").write_text(json.dumps(saved))

    def rows(self, total, rejected=0):
        good = "2026-10-26,Ava Reyes,Connected\n" * (total - rejected)
        return "Date,Rep,Result\n" + good + "bad,Ava Reyes,Connected\n" * rejected

    def test_stores_counts_and_sources(self):
        path = self.write("calls.csv", self.rows(4))

        report = normalize_files(self.workspace, [path])

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["week"], "2026-W44")
        self.assertEqual(history.read_activity(self.workspace, ["2026-W44"])[0]["dials"], 4)
        source = history.read_sources(self.workspace, "2026-W44")[0]
        self.assertEqual(source["file"], "calls.csv")
        self.assertEqual(source["rows_read"], 4)
        self.assertEqual((source["first_date"], source["last_date"]), ("2026-10-26", "2026-10-26"))

    def test_five_percent_rejected_is_accepted(self):
        report = normalize_files(self.workspace, [self.write("calls.csv", self.rows(100, 5))])

        self.assertEqual(report["status"], "ok")

    def test_six_percent_rejected_needs_the_manager_and_stores_nothing(self):
        report = normalize_files(self.workspace, [self.write("calls.csv", self.rows(100, 6))])

        self.assertEqual(report["status"], "needs_input")
        self.assertTrue(report["rejected_examples"])
        self.assertEqual(history.read_activity(self.workspace, ["2026-W44"]), [])

    def test_unknown_rep_needs_the_manager_and_stores_nothing(self):
        path = self.write(
            "calls.csv",
            "Date,Rep,Result\n2026-10-26,Ava Reyes,Connected\n2026-10-26,New Person,Connected\n",
        )

        report = normalize_files(self.workspace, [path])

        self.assertEqual(report["status"], "needs_input")
        self.assertEqual(report["unknown_reps"], {"New Person": 1})
        self.assertEqual(history.read_activity(self.workspace, ["2026-W44"]), [])

    def test_unmapped_value_needs_the_manager(self):
        path = self.write("calls.csv", "Date,Rep,Result\n2026-10-26,Ava Reyes,Gatekeeper\n")

        report = normalize_files(self.workspace, [path])

        self.assertEqual(report["status"], "needs_input")
        self.assertEqual(report["unmapped_values"], {"Result": ["Gatekeeper"]})

    def test_file_without_a_mapping_needs_the_manager(self):
        report = normalize_files(self.workspace, [self.write("new.csv", "A,B\n1,2\n")])

        self.assertEqual(report["status"], "needs_input")
        self.assertEqual(report["files_without_mapping"], ["new.csv"])

    def test_two_files_for_one_channel_need_the_manager(self):
        first = self.write("crm.csv", self.rows(1))
        second = self.write("dialer.csv", self.rows(1))

        report = normalize_files(self.workspace, [first, second])

        self.assertEqual(report["status"], "needs_input")
        self.assertEqual(report["channel_conflicts"], {"call": ["crm.csv", "dialer.csv"]})

    def test_meetings_snapshot_uses_the_given_week(self):
        saved = {
            **MEETING_MAPPING,
            "signature": header_signature(["Owner", "Booked", "Due", "State", "AE"]),
        }
        (self.workspace / "mappings" / "meetings.json").write_text(json.dumps(saved))
        path = self.write(
            "m.csv", "Owner,Booked,Due,State,AE\nAva Reyes,2026-10-20,2026-10-22,Done,Accepted\n"
        )

        report = normalize_files(self.workspace, [path], week="2026-W44")

        self.assertEqual(report["week"], "2026-W44")
        self.assertTrue((self.workspace / "history" / "meetings" / "2026-W44.csv").exists())

    def test_meetings_snapshot_defaults_to_the_latest_booked_week(self):
        saved = {
            **MEETING_MAPPING,
            "signature": header_signature(["Owner", "Booked", "Due", "State", "AE"]),
        }
        (self.workspace / "mappings" / "meetings.json").write_text(json.dumps(saved))
        path = self.write(
            "m.csv", "Owner,Booked,Due,State,AE\nAva Reyes,2026-10-20,2026-10-22,Done,Accepted\n"
        )

        self.assertEqual(normalize_files(self.workspace, [path])["week"], "2026-W43")

    def test_stored_files_hold_no_prospect_details(self):
        (self.workspace / "mappings" / "calls.json").unlink()
        headers = ["Date", "Rep", "Result", "Contact Name", "Contact Email"]
        saved = {**CALL_MAPPING, "signature": header_signature(headers)}
        (self.workspace / "mappings" / "calls.json").write_text(json.dumps(saved))
        path = self.write(
            "calls.csv",
            ",".join(headers) + "\n2026-10-26,Ava Reyes,Connected,Jane Doe,jane@acme.io\n",
        )

        normalize_files(self.workspace, [path])

        stored = "".join(
            item.read_text() for item in (self.workspace / "history").rglob("*") if item.is_file()
        )
        self.assertNotIn("Jane Doe", stored)
        self.assertNotIn("jane@acme.io", stored)


class NormalizeCommandTests(NormalizeTest):
    def test_exit_code_shows_when_the_manager_is_needed(self):
        workspace = make_workspace(self.folder)
        path = self.write("new.csv", "A,B\n1,2\n")

        code, output = run_cli("normalize", "--workspace", str(workspace), "--files", str(path))

        self.assertEqual(code, 2)
        self.assertEqual(output["status"], "needs_input")

    def test_exit_code_zero_on_success(self):
        workspace = make_workspace(self.folder)
        saved = {**CALL_MAPPING, "signature": header_signature(["Date", "Rep", "Result"])}
        (workspace / "mappings" / "calls.json").write_text(json.dumps(saved))
        path = self.write("calls.csv", "Date,Rep,Result\n2026-10-26,Ava Reyes,Connected\n")

        code, output = run_cli("normalize", "--workspace", str(workspace), "--files", str(path))

        self.assertEqual(code, 0)
        self.assertEqual(output["status"], "ok")


if __name__ == "__main__":
    unittest.main()
