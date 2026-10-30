from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sdrlib import pdf
from sdrlib.pdf import print_to_pdf


def output_path(command):
    flag = next(item for item in command if item.startswith("--print-to-pdf="))
    return Path(flag.split("=", 1)[1])


class PrintToPdfTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.html = self.folder / "report.html"
        self.html.write_text("<p>Report</p>")
        self.pdf = self.folder / "report.pdf"

    def test_returns_true_when_the_browser_writes_a_pdf(self):
        def runner(command, **_):
            output_path(command).write_bytes(b"%PDF-1.7")

        self.assertTrue(print_to_pdf(self.html, self.pdf, "/fake/browser", runner))

    def test_sends_the_expected_options(self):
        seen = {}

        def runner(command, **options):
            seen.update(command=command, options=options)
            output_path(command).write_bytes(b"%PDF-1.7")

        print_to_pdf(self.html, self.pdf, "/fake/browser", runner)

        self.assertEqual(seen["command"][0], "/fake/browser")
        self.assertIn("--headless=new", seen["command"])
        self.assertIn("--no-pdf-header-footer", seen["command"])
        self.assertEqual(seen["options"]["timeout"], 60)
        self.assertTrue(seen["command"][-1].startswith("file://"))

    def test_returns_false_when_the_browser_times_out(self):
        def runner(command, **_):
            raise subprocess.TimeoutExpired(command, 60)

        self.assertFalse(print_to_pdf(self.html, self.pdf, "/fake/browser", runner))
        self.assertTrue(self.html.exists())

    def test_returns_false_when_the_browser_cannot_start(self):
        def runner(command, **_):
            raise OSError("not found")

        self.assertFalse(print_to_pdf(self.html, self.pdf, "/fake/browser", runner))

    def test_returns_false_when_no_file_is_written(self):
        self.assertFalse(print_to_pdf(self.html, self.pdf, "/fake/browser", lambda *a, **k: None))

    def test_returns_false_when_the_file_is_not_a_pdf(self):
        def runner(command, **_):
            output_path(command).write_bytes(b"not a pdf")

        self.assertFalse(print_to_pdf(self.html, self.pdf, "/fake/browser", runner))

    def test_an_old_pdf_does_not_hide_a_failure(self):
        self.pdf.write_bytes(b"%PDF-old")

        self.assertFalse(print_to_pdf(self.html, self.pdf, "/fake/browser", lambda *a, **k: None))
        self.assertFalse(self.pdf.exists())

    def test_returns_false_when_no_browser_is_found(self):
        with mock.patch.object(pdf, "find_browser", return_value=None):
            self.assertFalse(print_to_pdf(self.html, self.pdf))


if __name__ == "__main__":
    unittest.main()
