from __future__ import annotations

import json
import re
import unittest

from tests.helpers import REPO_ROOT

import sdr

SKILLS = ("setup", "scorecard", "one-on-one")
REFERENCES = ("file-mapping-guide.md", "metric-definitions.md", "coaching-playbook.md")
MAX_SKILL_WORDS = 3000


def skill_text(name):
    return (REPO_ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def frontmatter(text):
    """Read simple `key: value` lines between the opening and closing markers."""
    block = text.split("---")[1]
    return dict(line.split(": ", 1) for line in block.strip().splitlines())


def all_skill_text():
    return "\n".join(skill_text(name) for name in SKILLS)


def command_names():
    parser = sdr.build_parser()
    subparsers = next(
        action for action in parser._actions if hasattr(action, "choices") and action.choices
    )
    return list(subparsers.choices)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())

    def test_identifies_the_plugin(self):
        self.assertEqual(self.manifest["name"], "sdr-manager")
        self.assertEqual(self.manifest["version"], "0.1.0")

    def test_names_the_author(self):
        self.assertEqual(self.manifest["author"]["name"], "Manish Singh")


class SkillTests(unittest.TestCase):
    def test_name_matches_the_folder(self):
        for name in SKILLS:
            self.assertEqual(frontmatter(skill_text(name))["name"], name)

    def test_has_a_description_with_trigger_phrases(self):
        for name in SKILLS:
            description = frontmatter(skill_text(name))["description"]
            self.assertIn("This skill should be used when", description, name)
            self.assertIn('"', description, name)

    def test_has_an_argument_hint(self):
        for name in SKILLS:
            self.assertIn("argument-hint", frontmatter(skill_text(name)), name)

    def test_stays_under_the_word_limit(self):
        for name in SKILLS:
            self.assertLess(len(skill_text(name).split()), MAX_SKILL_WORDS, name)

    def test_uses_the_plugin_root_variable(self):
        for name in SKILLS:
            self.assertIn("${CLAUDE_PLUGIN_ROOT}", skill_text(name), name)


class CoverageTests(unittest.TestCase):
    def test_every_reference_file_exists_and_is_used(self):
        text = all_skill_text()
        for name in REFERENCES:
            self.assertTrue((REPO_ROOT / "references" / name).exists(), name)
            self.assertIn(name, text, name)

    def test_every_command_is_used_by_a_skill(self):
        text = all_skill_text()
        for command in command_names():
            self.assertIn(command, text, command)

    def test_no_file_names_a_fixed_home_folder(self):
        folders = ("skills", "references", "assets", ".claude-plugin")
        paths = [path for folder in folders for path in (REPO_ROOT / folder).rglob("*")]
        paths.append(REPO_ROOT / "README.md")
        for path in paths:
            if path.is_file():
                self.assertIsNone(
                    re.search(r"/Users/|C:\\\\Users", path.read_text(encoding="utf-8")), path
                )


class SafetyRuleTests(unittest.TestCase):
    def test_scorecard_keeps_full_exports_away_from_claude(self):
        self.assertIn("Never open an export", skill_text("scorecard"))

    def test_one_on_one_refuses_employment_recommendations(self):
        self.assertIn("HR", skill_text("one-on-one"))

    def test_setup_warns_about_sensitive_notes(self):
        self.assertIn("sensitive", skill_text("setup"))

    def test_scorecard_forbids_ranking_reps(self):
        self.assertIn("Never rank", skill_text("scorecard"))


class ReadmeTests(unittest.TestCase):
    def setUp(self):
        self.text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    def test_covers_what_a_new_user_needs(self):
        for topic in (
            "Requirements",
            "Install",
            "Privacy",
            "Tested",
            "sample",
            "Andy Gheewalla",
        ):
            self.assertIn(topic, self.text, topic)

    def test_is_honest_about_what_claude_reads(self):
        self.assertIn("Claude plan", self.text)


if __name__ == "__main__":
    unittest.main()
