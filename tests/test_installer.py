from __future__ import annotations

import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import install
from tests.helpers import REPO_ROOT

SKILL_NAMES = ("sdr-setup", "sdr-scorecard", "sdr-one-on-one", "sdr-rewrite")


def frontmatter(text):
    block = text.split("---")[1]
    return dict(line.split(": ", 1) for line in block.strip().splitlines())


class InstallerTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.home = Path(folder.name)
        self.skills = self.home / ".agents" / "skills"
        self.runtime = self.home / ".sdr-manager"


class AdaptSkillTests(unittest.TestCase):
    def adapted(self, name="scorecard"):
        text = (REPO_ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        return install.adapt_skill(text, name, Path("/home/rep/.sdr-manager"))

    def test_gives_the_skill_a_clear_global_name(self):
        self.assertEqual(frontmatter(self.adapted())["name"], "sdr-scorecard")

    def test_points_to_the_installed_program(self):
        text = self.adapted()

        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", text)
        self.assertIn('python3 "/home/rep/.sdr-manager/scripts/sdr.py"', text)
        self.assertIn("/home/rep/.sdr-manager/references/coaching-playbook.md", text)

    def test_removes_the_field_that_only_some_tools_accept(self):
        self.assertNotIn("argument-hint", self.adapted())

    def test_uses_forward_slashes_so_commands_work_on_windows(self):
        windows_style = install.adapt_skill(
            "${CLAUDE_PLUGIN_ROOT}/scripts/sdr.py", "setup", Path("C:/Users/rep/.sdr-manager")
        )

        self.assertEqual(windows_style, "C:/Users/rep/.sdr-manager/scripts/sdr.py")


class InstallTests(InstallerTest):
    def install(self, **options):
        return install.install_skills(self.skills, self.runtime, **options)

    def test_writes_every_skill(self):
        self.install()

        for name in SKILL_NAMES:
            self.assertTrue((self.skills / name / "SKILL.md").exists(), name)

    def test_generated_skills_follow_the_agent_skills_format(self):
        self.install()

        for name in SKILL_NAMES:
            fields = frontmatter((self.skills / name / "SKILL.md").read_text(encoding="utf-8"))
            self.assertEqual(fields["name"], name)
            self.assertRegex(fields["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
            self.assertLessEqual(len(fields["description"]), 1024)
            self.assertEqual(set(fields), {"name", "description"})

    def test_copies_everything_the_skills_need(self):
        self.install()

        for name in (
            "scripts/sdr.py",
            "assets/brand.json",
            "assets/outreach-limits.json",
            "references/coaching-playbook.md",
            "references/outreach-playbook.md",
            "sample-data/outreach/weak-email.txt",
        ):
            self.assertTrue((self.runtime / name).exists(), name)
        self.assertTrue((self.runtime / "sample-data" / "exports" / "crm-calls.csv").exists())

    def test_leaves_compiled_python_behind(self):
        self.install()

        self.assertEqual(list(self.runtime.rglob("__pycache__")), [])

    def test_installed_program_runs_on_its_own(self):
        self.install()

        result = subprocess.run(
            [sys.executable, str(self.runtime / "scripts" / "sdr.py"), "check-env"],
            capture_output=True,
            text=True,
            check=True,
            cwd=self.home,
        )

        self.assertIn("python", json.loads(result.stdout))

    def test_installed_program_can_load_the_sample_team(self):
        self.install()
        demo = self.home / "sdr-demo"

        subprocess.run(
            [
                sys.executable,
                str(self.runtime / "scripts" / "sdr.py"),
                "init-workspace",
                "--path",
                str(demo),
                "--sample",
            ],
            capture_output=True,
            check=True,
            cwd=self.home,
        )

        self.assertTrue((demo / "imports" / "2026-W44" / "crm-calls.csv").exists())

    def test_installing_again_replaces_the_old_copy(self):
        self.install()
        stale = self.runtime / "scripts" / "old_file.py"
        stale.write_text("old")

        self.install()

        self.assertFalse(stale.exists())

    def test_refuses_to_install_over_its_own_source(self):
        with self.assertRaisesRegex(ValueError, "source"):
            install.install_skills(self.skills, REPO_ROOT)


class UninstallTests(InstallerTest):
    def test_removes_the_skills_and_the_program(self):
        install.install_skills(self.skills, self.runtime)

        install.uninstall_skills(self.skills, self.runtime)

        for name in SKILL_NAMES:
            self.assertFalse((self.skills / name).exists(), name)
        self.assertFalse(self.runtime.exists())

    def test_leaves_other_skills_alone(self):
        install.install_skills(self.skills, self.runtime)
        other = self.skills / "someone-elses-skill"
        other.mkdir()
        (other / "SKILL.md").write_text("keep me")

        install.uninstall_skills(self.skills, self.runtime)

        self.assertTrue((other / "SKILL.md").exists())

    def test_leaves_team_data_alone(self):
        install.install_skills(self.skills, self.runtime)
        workspace = self.home / "sdr-workspace"
        workspace.mkdir()
        (workspace / "team-profile.json").write_text("{}")

        install.uninstall_skills(self.skills, self.runtime)

        self.assertTrue((workspace / "team-profile.json").exists())

    def test_keeps_anything_else_placed_in_the_program_folder(self):
        install.install_skills(self.skills, self.runtime)
        (self.runtime / "my-notes.txt").write_text("keep me")

        install.uninstall_skills(self.skills, self.runtime)

        self.assertTrue((self.runtime / "my-notes.txt").exists())

    def test_is_harmless_when_nothing_is_installed(self):
        install.uninstall_skills(self.skills, self.runtime)

        self.assertFalse(self.runtime.exists())


class CommandLineTests(InstallerTest):
    def run_main(self, *arguments):
        with contextlib.redirect_stdout(io.StringIO()):
            return install.main(["--home", str(self.home), *arguments])

    def test_default_uses_the_shared_agents_folder(self):
        self.assertEqual(self.run_main(), 0)

        self.assertTrue((self.home / ".agents" / "skills" / "sdr-setup" / "SKILL.md").exists())

    def test_claude_tool_uses_the_claude_folder(self):
        self.assertEqual(self.run_main("--tool", "claude"), 0)

        self.assertTrue((self.home / ".claude" / "skills" / "sdr-setup" / "SKILL.md").exists())

    def test_any_other_tool_can_name_its_own_folder(self):
        folder = self.home / "my-tool" / "skills"

        self.assertEqual(self.run_main("--skills-dir", str(folder)), 0)

        self.assertTrue((folder / "sdr-setup" / "SKILL.md").exists())

    def test_uninstall_flag_removes_it(self):
        self.run_main()

        self.assertEqual(self.run_main("--uninstall"), 0)

        self.assertFalse(self.runtime.exists())

    def test_python_version_check(self):
        self.assertFalse(install.python_ok((3, 8)))
        self.assertTrue(install.python_ok((3, 9)))


class SourceTests(unittest.TestCase):
    def test_every_runtime_folder_exists(self):
        for name in install.RUNTIME_FOLDERS:
            self.assertTrue((REPO_ROOT / name).is_dir(), name)

    def test_program_messages_name_no_tool_specific_command(self):
        for path in (REPO_ROOT / "scripts").rglob("*.py"):
            self.assertIsNone(re.search(r"/sdr-manager:", path.read_text(encoding="utf-8")), path)


if __name__ == "__main__":
    unittest.main()
