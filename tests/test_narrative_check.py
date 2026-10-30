from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import make_workspace, run_cli

from sdrlib import history
from sdrlib.narrative_check import allowed_numbers, check_narrative, extract_numbers

METRICS = {
    "generated_at": "2026-10-30T12:00:00",
    "connect_rate": 0.054545,
    "touches": 2080,
    "held_target": 9.23,
    "booked": 12,
    "nested": [{"dials": 880}],
    "missing": None,
    "flag": True,
    "label": "Near",
}


class ExtractNumberTests(unittest.TestCase):
    def test_finds_percentages_and_counts(self):
        self.assertEqual(
            extract_numbers("Connect rate hit 5.5% on 880 dials"), ["5.5%", "880"]
        )

    def test_ignores_dates_week_names_steps_and_one_on_ones(self):
        text = "On 2026-10-30, in 2026-W44, on Oct 30 and October 30, 2026, Step 3 came up in a 1:1"

        self.assertEqual(extract_numbers(text), [])

    def test_ignores_numeric_dates(self):
        self.assertEqual(extract_numbers("Check on 10/30 or 10/30/2026"), [])

    def test_finds_numbers_with_commas(self):
        self.assertEqual(extract_numbers("2,080 touches"), ["2,080"])

    def test_spelled_out_numbers_are_ignored(self):
        self.assertEqual(extract_numbers("Over the four-week window"), [])

    def test_ignores_ordinary_words_with_digits_next_to_letters(self):
        self.assertEqual(extract_numbers("Sent by SDR2 on Q4"), [])


class AllowedNumberTests(unittest.TestCase):
    def test_skips_the_generated_timestamp(self):
        self.assertNotIn("2026", allowed_numbers({"generated_at": "2026-10-30T12:00:00"}))

    def test_booleans_do_not_count_as_numbers(self):
        self.assertEqual(allowed_numbers({"flag": True}), set())


class CheckNarrativeTests(unittest.TestCase):
    def problems(self, text, coaching_text=""):
        return check_narrative({"headline": text}, METRICS, coaching_text)

    def test_a_correct_rounded_rate_passes(self):
        self.assertEqual(self.problems("Connect rate is 5.5%"), [])

    def test_a_rate_without_a_percent_sign_passes(self):
        self.assertEqual(self.problems("Connect rate moved to 5.5"), [])

    def test_a_wrong_rate_is_reported(self):
        problems = self.problems("Connect rate is 5.6%")

        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["number"], "5.6%")
        self.assertEqual(problems[0]["field"], "headline")

    def test_a_rounded_target_passes(self):
        self.assertEqual(self.problems("Target is 9.2 held meetings"), [])

    def test_a_count_in_the_metrics_passes(self):
        self.assertEqual(self.problems("Booked 12 meetings"), [])

    def test_a_small_number_not_in_the_metrics_is_reported(self):
        self.assertEqual(len(self.problems("Booked 3 meetings")), 1)

    def test_a_count_with_a_comma_matches_the_plain_value(self):
        self.assertEqual(self.problems("Made 2,080 touches"), [])

    def test_the_same_count_without_a_comma_passes(self):
        self.assertEqual(self.problems("Made 2080 touches"), [])

    def test_a_number_from_coaching_history_passes_when_supplied(self):
        history_text = "- Agreed: 50 dials before lunch\n"

        self.assertEqual(self.problems("Agreed to 50 dials", history_text), [])
        self.assertEqual(len(self.problems("Agreed to 50 dials")), 1)

    def test_nested_text_is_checked_and_located(self):
        narrative = {"observations": ["Fine", "Booked 77 meetings"], "rep_notes": {"Ava": "Made 66"}}

        problems = check_narrative(narrative, METRICS)

        fields = {problem["field"]: problem["number"] for problem in problems}
        self.assertEqual(fields, {"observations[1]": "77", "rep_notes.Ava": "66"})

    def test_a_clean_narrative_has_no_problems(self):
        narrative = {"observations": ["Connect rate is 5.5%"], "rep_notes": {"Ava": "Solid week"}}

        self.assertEqual(check_narrative(narrative, METRICS), [])


class CheckNarrativeCommandTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.workspace = make_workspace(self.folder)
        history.write_metrics(self.workspace, "2026-W44", METRICS)

    def run_check(self, narrative, *extra):
        path = self.folder / "narrative.json"
        path.write_text(json.dumps(narrative))
        return run_cli(
            "check-narrative",
            "--workspace",
            str(self.workspace),
            "--week",
            "2026-W44",
            "--narrative",
            str(path),
            *extra,
        )

    def test_clean_text_passes(self):
        code, output = self.run_check({"headline": "Connect rate is 5.5%"})

        self.assertEqual(code, 0)
        self.assertEqual(output["status"], "ok")

    def test_wrong_number_needs_correcting(self):
        code, output = self.run_check({"headline": "Connect rate is 9.9%"})

        self.assertEqual(code, 2)
        self.assertEqual(output["problems"][0]["number"], "9.9%")

    def test_coaching_history_is_used_for_the_named_rep(self):
        coaching = self.workspace / "coaching"
        coaching.mkdir()
        (coaching / "ben-carter.md").write_text("- Agreed: 50 dials\n")

        code, _ = self.run_check({"headline": "Agreed to 50 dials"}, "--rep", "Ben Carter")

        self.assertEqual(code, 0)

    def test_an_alias_finds_the_rep_s_coaching_history(self):
        coaching = self.workspace / "coaching"
        coaching.mkdir()
        (coaching / "ava-reyes.md").write_text("- Agreed: 50 dials\n")

        code, _ = self.run_check({"headline": "Agreed to 50 dials"}, "--rep", "A. Reyes")

        self.assertEqual(code, 0)

    def test_missing_scorecard_needs_the_manager(self):
        code, output = run_cli(
            "check-narrative",
            "--workspace",
            str(self.workspace),
            "--week",
            "2026-W01",
            "--narrative",
            str(self.folder / "nope.json"),
        )

        self.assertEqual(code, 2)
        self.assertIn("2026-W01", output["error"])


if __name__ == "__main__":
    unittest.main()
