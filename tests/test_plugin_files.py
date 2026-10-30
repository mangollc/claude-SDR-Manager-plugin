from __future__ import annotations

import json
import unittest

from tests.helpers import REPO_ROOT


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())

    def test_identifies_the_plugin(self):
        self.assertEqual(self.manifest["name"], "sdr-manager")
        self.assertEqual(self.manifest["version"], "0.1.0")

    def test_names_the_author(self):
        self.assertEqual(self.manifest["author"]["name"], "Manish Singh")


if __name__ == "__main__":
    unittest.main()
