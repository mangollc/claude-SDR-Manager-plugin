from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sdrlib.workspace import SAMPLE_WEEK, init_workspace
from tests.helpers import run_cli


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
