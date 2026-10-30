from __future__ import annotations

import unittest
from unittest import mock

from sdrlib import environment
from tests.helpers import run_cli


class CheckEnvTests(unittest.TestCase):
    def test_reports_python_openpyxl_and_browser(self):
        code, output = run_cli("check-env")

        self.assertEqual(code, 0)
        self.assertTrue({"python", "openpyxl", "browser"} <= set(output))


class ErrorHandlingTests(unittest.TestCase):
    def test_unknown_command_returns_json_error(self):
        code, output = run_cli("nonsense")

        self.assertEqual(code, 2)
        self.assertIn("error", output)

    def test_no_command_returns_json_error(self):
        code, output = run_cli()

        self.assertEqual(code, 2)
        self.assertIn("error", output)


class EnvironmentTests(unittest.TestCase):
    def test_python_38_is_too_old(self):
        self.assertFalse(environment.python_ok((3, 8)))

    def test_python_39_is_supported(self):
        self.assertTrue(environment.python_ok((3, 9)))

    def test_find_browser_returns_none_when_nothing_is_installed(self):
        with (
            mock.patch.object(environment.Path, "exists", return_value=False),
            mock.patch.object(environment.shutil, "which", return_value=None),
        ):
            self.assertIsNone(environment.find_browser())

    def test_find_browser_falls_back_to_commands_on_the_path(self):
        with (
            mock.patch.object(environment.Path, "exists", return_value=False),
            mock.patch.object(
                environment.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"
            ),
        ):
            self.assertEqual(environment.find_browser(), "/usr/bin/google-chrome")


if __name__ == "__main__":
    unittest.main()
