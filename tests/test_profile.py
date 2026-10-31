from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sdrlib.profile import ProfileError, active_reps, load_profile, rep_lookup, rep_slug
from tests.helpers import DEFAULT_PROFILE, make_workspace, run_cli


class ProfileTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)


class OutreachFieldTests(ProfileTest):
    def test_accepts_proof_points_and_limits(self):
        workspace = make_workspace(
            self.folder,
            proof_points=["Northwind Stores cut stockouts by 18%."],
            outreach_limits={"linkedin_note": {"value": 300, "as_of": "2026-10-31"}},
        )

        self.assertEqual(len(load_profile(workspace)["proof_points"]), 1)

    def test_a_team_that_has_not_been_asked_is_valid(self):
        self.assertNotIn("proof_points", load_profile(make_workspace(self.folder)))

    def test_a_team_with_no_proof_points_is_valid(self):
        workspace = make_workspace(self.folder, proof_points=[])

        self.assertEqual(load_profile(workspace)["proof_points"], [])

    def test_rejects_proof_points_that_are_not_a_list_of_text(self):
        for value in ("One sentence", ["Fine", ""], ["Fine", "  "], [5], None):
            workspace = make_workspace(self.folder, proof_points=value)

            with self.assertRaisesRegex(ProfileError, "proof_points"):
                load_profile(workspace)

    def test_rejects_limits_that_are_not_an_object(self):
        workspace = make_workspace(self.folder, outreach_limits=[300])

        with self.assertRaisesRegex(ProfileError, "outreach_limits"):
            load_profile(workspace)

    def test_rejects_a_limit_that_is_not_a_positive_number(self):
        for value in (0, -5, "80", True, None):
            workspace = make_workspace(
                self.folder, outreach_limits={"first_email": {"value": value}}
            )

            with self.assertRaisesRegex(ProfileError, "first_email"):
                load_profile(workspace)

    def test_rejects_a_limit_without_a_value(self):
        workspace = make_workspace(self.folder, outreach_limits={"first_email": 80})

        with self.assertRaisesRegex(ProfileError, "first_email"):
            load_profile(workspace)


class LoadProfileTests(ProfileTest):
    def test_loads_a_valid_profile(self):
        workspace = make_workspace(self.folder)

        self.assertEqual(load_profile(workspace)["company"], "Example Co")

    def test_missing_profile_points_to_setup(self):
        with self.assertRaisesRegex(ProfileError, "setup"):
            load_profile(self.folder)

    def test_invalid_json_is_explained(self):
        workspace = make_workspace(self.folder)
        (workspace / "team-profile.json").write_text("{not json")

        with self.assertRaisesRegex(ProfileError, "team-profile.json"):
            load_profile(workspace)

    def test_rep_without_a_name_is_rejected(self):
        workspace = make_workspace(self.folder, reps=[{"start_date": "2025-01-06"}])

        with self.assertRaisesRegex(ProfileError, "name"):
            load_profile(workspace)

    def test_invalid_channel_is_rejected(self):
        workspace = make_workspace(self.folder, channels=["carrier pigeon"])

        with self.assertRaisesRegex(ProfileError, "carrier pigeon"):
            load_profile(workspace)

    def test_invalid_start_date_is_rejected(self):
        workspace = make_workspace(
            self.folder, reps=[{"name": "Ava Reyes", "start_date": "March 2025"}]
        )

        with self.assertRaisesRegex(ProfileError, "Ava Reyes"):
            load_profile(workspace)

    def test_two_reps_sharing_a_file_name_are_rejected(self):
        workspace = make_workspace(
            self.folder, reps=[{"name": "Jose Nunez"}, {"name": "José Núñez"}]
        )

        with self.assertRaisesRegex(ProfileError, "Jose Nunez"):
            load_profile(workspace)

    def test_blank_start_date_is_allowed(self):
        workspace = make_workspace(self.folder, reps=[{"name": "Ava Reyes", "start_date": ""}])

        self.assertEqual(len(load_profile(workspace)["reps"]), 1)


class RepLookupTests(unittest.TestCase):
    def test_matches_names_and_aliases_in_any_case(self):
        lookup = rep_lookup(DEFAULT_PROFILE)

        self.assertEqual(lookup["ava reyes"], "Ava Reyes")
        self.assertEqual(lookup["a. reyes"], "Ava Reyes")

    def test_ignored_names_map_to_none(self):
        lookup = rep_lookup(DEFAULT_PROFILE)

        self.assertIsNone(lookup["morgan lee"])

    def test_unknown_names_are_absent(self):
        self.assertNotIn("someone else", rep_lookup(DEFAULT_PROFILE))


class ActiveRepTests(unittest.TestCase):
    def test_leaves_out_inactive_reps_and_sorts_by_name(self):
        profile = {
            "reps": [
                {"name": "Ben Carter"},
                {"name": "Zed Inactive", "active": False},
                {"name": "Ava Reyes"},
            ]
        }

        names = [rep["name"] for rep in active_reps(profile)]

        self.assertEqual(names, ["Ava Reyes", "Ben Carter"])


class SlugTests(unittest.TestCase):
    def test_makes_a_safe_file_name(self):
        self.assertEqual(rep_slug("Ana María O'Neil"), "ana-maria-oneil")

    def test_removes_path_characters(self):
        self.assertEqual(rep_slug("../../etc/passwd"), "etc-passwd")

    def test_names_without_latin_letters_still_get_a_slug(self):
        self.assertTrue(rep_slug("李明"))


class TargetsCommandTests(ProfileTest):
    def test_prints_resolved_targets(self):
        workspace = make_workspace(self.folder)

        code, output = run_cli("targets", "--workspace", str(workspace))

        self.assertEqual(code, 0)
        self.assertAlmostEqual(output["targets"]["meeting_rate"]["value"], 0.1209, places=4)

    def test_missing_profile_needs_the_manager(self):
        code, output = run_cli("targets", "--workspace", str(self.folder))

        self.assertEqual(code, 2)
        self.assertIn("setup", output["error"])

    def test_unknown_target_needs_the_manager(self):
        workspace = make_workspace(self.folder, targets={"made_up": {"value": 1}})

        code, output = run_cli("targets", "--workspace", str(workspace))

        self.assertEqual(code, 2)
        self.assertIn("made_up", json.dumps(output))


if __name__ == "__main__":
    unittest.main()
