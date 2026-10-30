from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from sdrlib.file_reader import header_signature, read_table
from sdrlib.normalize import normalize_files
from sdrlib.scorecard import build_scorecard
from sdrlib.workspace import SAMPLE_WEEK, init_workspace
from tests import make_sample_data
from tests.helpers import REPO_ROOT

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "sample-mappings"
NOW = datetime(2026, 11, 2, 9, 0, 0)
EXPECTED = {
    "Ava Reyes": ("On track", 2, "connect_rate", "stretch"),
    "Ben Carter": ("Needs attention", 1, "touches", "gap"),
    "Chloe Nguyen": ("Needs attention", 2, "email_reply_rate", "gap"),
    "Diego Marin": ("Needs attention", 3, "meeting_rate", "gap"),
    "Priya Shah": ("Needs attention", 4, "show_rate", "gap"),
    "Sam Okafor": ("Needs attention", 5, "acceptance_rate", "gap"),
    "Nina Patel": ("Onboarding", None, None, None),
}


def install_mappings(workspace: Path) -> None:
    """Add the confirmed mappings, as a manager would after the first review."""
    imports = workspace / "imports" / SAMPLE_WEEK
    for fixture in FIXTURES.glob("*.json"):
        mapping = json.loads(fixture.read_text())
        table = read_table(imports / mapping.pop("file"), mapping["header_row"])
        saved = {**mapping, "signature": header_signature(table.headers)}
        (workspace / "mappings" / fixture.name).write_text(json.dumps(saved))


class SampleDataTests(unittest.TestCase):
    def test_generator_is_repeatable(self):
        self.assertEqual(make_sample_data.build_exports(), make_sample_data.build_exports())

    def test_saved_exports_match_the_generator(self):
        folder = REPO_ROOT / "sample-data" / "exports"
        for name, text in make_sample_data.build_exports().items():
            self.assertEqual((folder / name).read_text(encoding="utf-8"), text, name)

    def test_saved_profile_matches_the_generator(self):
        saved = json.loads((REPO_ROOT / "sample-data" / "team-profile.json").read_text())

        self.assertEqual(saved, make_sample_data.SAMPLE_PROFILE)


class SampleTeamPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.workspace = Path(cls.folder.name) / "sdr-demo"
        init_workspace(cls.workspace, sample=True)
        install_mappings(cls.workspace)
        files = sorted((cls.workspace / "imports" / SAMPLE_WEEK).iterdir())
        cls.report = normalize_files(cls.workspace, files, SAMPLE_WEEK)
        cls.scorecard = build_scorecard(cls.workspace, SAMPLE_WEEK, now=NOW)
        cls.reps = {rep["name"]: rep for rep in cls.scorecard["reps"]}

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_every_file_passes(self):
        self.assertEqual(self.report["status"], "ok", self.report)

    def test_footer_row_is_rejected_and_counted(self):
        calls = next(item for item in self.report["files"] if item["file"] == "crm-calls.csv")

        self.assertEqual(calls["rows_rejected"], 1)

    def test_every_rep_gets_the_designed_result(self):
        for name, (status, step, metric, kind) in EXPECTED.items():
            with self.subTest(rep=name):
                rep = self.reps[name]
                self.assertEqual(rep["status"], status)
                if step is None:
                    self.assertIsNone(rep["focus"])
                else:
                    self.assertEqual(rep["focus"]["step"], step)
                    self.assertEqual(rep["focus"]["metric"], metric)
                    self.assertEqual(rep["focus"]["kind"], kind)

    def test_only_chloe_has_a_bounce_flag(self):
        flagged = [name for name, rep in self.reps.items() if rep["flags"]]

        self.assertEqual(flagged, ["Chloe Nguyen"])

    def test_there_is_no_team_pattern(self):
        self.assertIsNone(self.scorecard["team"]["pattern"])

    def test_window_totals_match_the_plan(self):
        ava = self.reps["Ava Reyes"]["window"]

        self.assertEqual(ava["counts"]["dials"], 920)
        self.assertEqual(ava["counts"]["connected"], 64)
        self.assertEqual(ava["counts"]["replies"], 44)
        self.assertEqual(ava["meetings"]["booked"], 17)
        self.assertEqual(ava["meetings"]["held"], 13)
        self.assertEqual(ava["days_active"], 20)

    def test_all_three_channels_are_present(self):
        self.assertEqual(self.scorecard["channels_present"], ["call", "email", "linkedin"])

    def test_stored_history_holds_no_prospect_details(self):
        stored = "".join(
            item.read_text(encoding="utf-8")
            for item in (self.workspace / "history").rglob("*")
            if item.is_file()
        )

        for fragment in ("Contact 0", "@example.com", "555-01", "Example Co ", "Morgan Lee"):
            self.assertNotIn(fragment, stored)


if __name__ == "__main__":
    unittest.main()
