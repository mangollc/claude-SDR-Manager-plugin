from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from sdrlib.coaching import append_entry, coaching_path, read_history
from tests.helpers import make_workspace, run_cli

ENTRY = {
    "focus": "Response (connect rate)",
    "agreed": ["Call before 10am", "Clean the list"],
    "check_by": "2026-11-13",
    "notes": "Good energy",
}


class CoachingTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)


class AppendEntryTests(CoachingTest):
    def test_writes_the_expected_format(self):
        append_entry(self.folder, "Ben Carter", ENTRY, date(2026, 10, 30))

        self.assertEqual(
            read_history(self.folder, "Ben Carter"),
            "## 2026-10-30\n"
            "- Focus: Response (connect rate)\n"
            "- Agreed: Call before 10am\n"
            "- Agreed: Clean the list\n"
            "- Check by: 2026-11-13\n"
            "- Notes: Good energy\n",
        )

    def test_keeps_both_entries_oldest_first(self):
        append_entry(self.folder, "Ben Carter", ENTRY, date(2026, 10, 16))
        append_entry(self.folder, "Ben Carter", ENTRY, date(2026, 10, 30))

        text = read_history(self.folder, "Ben Carter")

        self.assertLess(text.index("2026-10-16"), text.index("2026-10-30"))

    def test_uses_a_safe_file_name(self):
        path = append_entry(self.folder, "Ana O'Neil", ENTRY, date(2026, 10, 30))

        self.assertEqual(path.name, "ana-oneil.md")
        self.assertEqual(path, coaching_path(self.folder, "Ana O'Neil"))

    def test_a_missing_field_is_named(self):
        entry = {key: value for key, value in ENTRY.items() if key != "agreed"}

        with self.assertRaisesRegex(ValueError, "agreed"):
            append_entry(self.folder, "Ben Carter", entry, date(2026, 10, 30))

    def test_notes_are_optional(self):
        entry = {key: value for key, value in ENTRY.items() if key != "notes"}

        append_entry(self.folder, "Ben Carter", entry, date(2026, 10, 30))

        self.assertNotIn("Notes", read_history(self.folder, "Ben Carter"))


class ReadHistoryTests(CoachingTest):
    def test_rep_with_no_file_has_an_empty_history(self):
        self.assertEqual(read_history(self.folder, "Ben Carter"), "")


class LogCoachingCommandTests(CoachingTest):
    def test_saves_an_entry_from_a_file(self):
        workspace = make_workspace(self.folder)
        entry_file = self.folder / "entry.json"
        entry_file.write_text(json.dumps(ENTRY))

        code, output = run_cli(
            "log-coaching",
            "--workspace",
            str(workspace),
            "--rep",
            "Ben Carter",
            "--entry-file",
            str(entry_file),
        )

        self.assertEqual(code, 0)
        self.assertTrue(Path(output["path"]).exists())

    def test_unknown_rep_needs_the_manager(self):
        workspace = make_workspace(self.folder)
        entry_file = self.folder / "entry.json"
        entry_file.write_text(json.dumps(ENTRY))

        code, output = run_cli(
            "log-coaching",
            "--workspace",
            str(workspace),
            "--rep",
            "Nobody Here",
            "--entry-file",
            str(entry_file),
        )

        self.assertEqual(code, 2)
        self.assertIn("Nobody Here", output["error"])


if __name__ == "__main__":
    unittest.main()
