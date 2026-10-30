from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from sdrlib import coaching, history
from sdrlib.workspace import SAMPLE_WEEK, describe_workspace, find_workspaces, init_workspace
from tests.helpers import make_workspace, run_cli

NOW = datetime(2026, 11, 9, 9, 0, 0)


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "sdr-workspace"


class InitWorkspaceTests(WorkspaceTest):
    def test_creates_folders_profile_and_gitignore(self):
        result = init_workspace(self.path)

        for name in ("imports", "mappings", "history", "reports", "coaching"):
            self.assertTrue((self.path / name).is_dir(), name)
        self.assertEqual((self.path / ".gitignore").read_text().strip(), "*")
        profile = json.loads((self.path / "team-profile.json").read_text())
        self.assertEqual(profile["reps"], [])
        self.assertFalse(result["already_exists"])

    def test_leaves_an_existing_workspace_untouched(self):
        init_workspace(self.path)
        profile_path = self.path / "team-profile.json"
        profile_path.write_text('{"company": "Keep me"}')

        result = init_workspace(self.path, sample=True)

        self.assertTrue(result["already_exists"])
        self.assertIn("Keep me", profile_path.read_text())
        self.assertFalse((self.path / "imports" / SAMPLE_WEEK).exists())


class SampleWorkspaceTests(WorkspaceTest):
    def test_copies_the_profile_and_exports_but_no_mappings(self):
        result = init_workspace(self.path, sample=True)

        profile = json.loads((self.path / "team-profile.json").read_text())
        self.assertEqual(len(profile["reps"]), 7)
        exports = sorted(p.name for p in (self.path / "imports" / SAMPLE_WEEK).iterdir())
        self.assertEqual(
            exports,
            [
                "crm-calls.csv",
                "crm-meetings.csv",
                "linkedin-activity.csv",
                "sequencer-emails.csv",
            ],
        )
        self.assertEqual(list((self.path / "mappings").iterdir()), [])
        self.assertEqual(result["imports"], str(self.path / "imports" / SAMPLE_WEEK))


class FindWorkspaceTests(WorkspaceTest):
    def test_finds_a_real_team_before_the_sample(self):
        init_workspace(self.path.parent / "sdr-demo", sample=True)
        init_workspace(self.path)

        names = [item.name for item in find_workspaces(self.path.parent)]

        self.assertEqual(names, ["sdr-workspace", "sdr-demo"])

    def test_finds_a_workspace_in_the_current_folder(self):
        init_workspace(self.path)

        self.assertEqual(find_workspaces(self.path), [self.path.resolve()])

    def test_finds_nothing_in_an_empty_folder(self):
        self.path.mkdir()

        self.assertEqual(find_workspaces(self.path), [])


class DescribeWorkspaceTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.workspace = make_workspace(self.path)

    def save_scorecard(self):
        reps = [{"name": "Ava Reyes", "status": "Watch"}]
        scorecard = {"generated_at": "2026-10-30T12:00:00", "reps": reps}
        history.write_metrics(self.workspace, "2026-W44", scorecard)

    def test_reports_no_scorecard_yet(self):
        result = describe_workspace(self.workspace, NOW)

        self.assertIsNone(result["latest_week"])
        self.assertIsNone(result["metrics_path"])
        self.assertIsNone(result["metrics_age_days"])

    def test_reports_the_latest_scorecard_and_its_age(self):
        self.save_scorecard()

        result = describe_workspace(self.workspace, NOW)

        self.assertEqual(result["latest_week"], "2026-W44")
        self.assertEqual(result["metrics_age_days"], 9)
        self.assertTrue(Path(result["metrics_path"]).exists())

    def test_lists_active_reps_with_their_status_and_history(self):
        self.save_scorecard()
        entry = {"focus": "Activity", "agreed": ["Protect calling time"], "check_by": "2026-11-13"}
        coaching.append_entry(self.workspace, "Ben Carter", entry, NOW.date())

        reps = {rep["name"]: rep for rep in describe_workspace(self.workspace, NOW)["reps"]}

        self.assertEqual(reps["Ava Reyes"]["status"], "Watch")
        self.assertFalse(reps["Ava Reyes"]["has_coaching_history"])
        self.assertTrue(reps["Ben Carter"]["has_coaching_history"])
        self.assertIsNone(reps["Ben Carter"]["status"])
        self.assertEqual(reps["Ben Carter"]["slug"], "ben-carter")

    def test_lists_exports_waiting_in_the_imports_folder(self):
        folder = self.workspace / "imports" / "2026-W44"
        folder.mkdir(parents=True)
        (folder / "calls.csv").write_text("x")

        result = describe_workspace(self.workspace, NOW)

        self.assertEqual(result["imports"], {"2026-W44": ["calls.csv"]})


class StatusCommandTests(WorkspaceTest):
    def test_uses_the_folder_it_is_given(self):
        init_workspace(self.path)

        code, output = run_cli("status", "--workspace", str(self.path))

        self.assertEqual(code, 0)
        self.assertEqual(output["workspace"], str(self.path))

    def test_looks_in_the_current_folder_by_default(self):
        init_workspace(self.path)

        with mock.patch("sdr.Path.cwd", return_value=self.path.parent):
            code, output = run_cli("status")

        self.assertEqual(code, 0)
        self.assertEqual(Path(output["workspace"]).name, "sdr-workspace")

    def test_mentions_other_workspaces(self):
        init_workspace(self.path)
        init_workspace(self.path.parent / "sdr-demo")

        with mock.patch("sdr.Path.cwd", return_value=self.path.parent):
            _, output = run_cli("status")

        self.assertEqual(len(output["other_workspaces"]), 1)

    def test_points_to_setup_when_there_is_no_workspace(self):
        self.path.mkdir()

        with mock.patch("sdr.Path.cwd", return_value=self.path):
            code, output = run_cli("status")

        self.assertEqual(code, 2)
        self.assertIn("setup", output["error"])


class InitWorkspaceCommandTests(WorkspaceTest):
    def test_creates_a_workspace(self):
        code, output = run_cli("init-workspace", "--path", str(self.path))

        self.assertEqual(code, 0)
        self.assertEqual(output["path"], str(self.path))
        self.assertTrue((self.path / "team-profile.json").exists())

    def test_sample_flag_loads_the_sample_team(self):
        code, _ = run_cli("init-workspace", "--path", str(self.path), "--sample")

        self.assertEqual(code, 0)
        self.assertTrue((self.path / "imports" / SAMPLE_WEEK / "crm-calls.csv").exists())


if __name__ == "__main__":
    unittest.main()
