from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sdrlib.narrative_check import check_narrative, extract_number_words, extract_numbers
from tests.helpers import make_workspace, run_cli


def numbers_found(narrative, coaching_text=""):
    return [problem["number"] for problem in check_narrative(narrative, coaching_text)]


class ExtractNumberTests(unittest.TestCase):
    def test_finds_percentages_and_counts(self):
        self.assertEqual(extract_numbers("Connect rate hit 5.5% on 880 dials"), ["5.5%", "880"])

    def test_ignores_dates_week_names_steps_and_one_on_ones(self):
        text = "On 2026-10-30, in 2026-W44, on Oct 30 and October 30, 2026, Step 3 came up in a 1:1"

        self.assertEqual(extract_numbers(text), [])

    def test_ignores_numeric_dates(self):
        self.assertEqual(extract_numbers("Check on 10/30 or 10/30/2026"), [])

    def test_finds_numbers_with_commas(self):
        self.assertEqual(extract_numbers("2,080 touches"), ["2,080"])

    def test_ignores_ordinary_words_with_digits_next_to_letters(self):
        self.assertEqual(extract_numbers("Sent by SDR2 on Q4"), [])


class ExtractNumberWordTests(unittest.TestCase):
    def test_finds_spelled_out_counts_in_any_case(self):
        self.assertEqual(
            extract_number_words("Thirteen held but only three accepted"), ["Thirteen", "three"]
        )

    def test_finds_fractions_of_a_target(self):
        self.assertEqual(extract_number_words("Reached half the target"), ["half"])

    def test_allows_the_word_one(self):
        self.assertEqual(extract_number_words("One clear gap, and one thing to try"), [])

    def test_allows_the_fixed_four_week_window(self):
        self.assertEqual(extract_number_words("Over the four-week window, the last four weeks"), [])

    def test_ignores_words_that_only_contain_a_number(self):
        self.assertEqual(extract_number_words("Someone often weighed the tension"), [])


class CheckNarrativeTests(unittest.TestCase):
    def test_text_without_numbers_passes(self):
        self.assertEqual(numbers_found({"headline": "Activity is the place to start"}), [])

    def test_any_digit_is_reported(self):
        self.assertEqual(numbers_found({"headline": "Booked 12 meetings"}), ["12"])

    def test_a_real_looking_percentage_is_still_reported(self):
        self.assertEqual(numbers_found({"headline": "Connect rate is 5.5%"}), ["5.5%"])

    def test_spelled_out_counts_are_reported(self):
        found = numbers_found({"rep_notes": {"Sam": "Thirteen held but only three accepted"}})

        self.assertEqual(found, ["Thirteen", "three"])

    def test_problems_say_where_they_are(self):
        narrative = {
            "observations": ["Fine", "Booked 77 meetings"],
            "rep_notes": {"Ava": "Made 66"},
        }

        fields = {problem["field"]: problem["number"] for problem in check_narrative(narrative)}

        self.assertEqual(fields, {"observations[1]": "77", "rep_notes.Ava": "66"})

    def test_dates_steps_and_one_on_ones_pass(self):
        text = "Since 2026-10-16, Step 3 has come up in every 1:1"

        self.assertEqual(numbers_found({"headline": text}), [])

    def test_a_number_from_the_coaching_history_passes_when_supplied(self):
        narrative = {"commitment_progress": ["Agreed to 50 dials"]}

        self.assertEqual(numbers_found(narrative, "- Agreed: 50 dials before lunch\n"), [])
        self.assertEqual(numbers_found(narrative), ["50"])

    def test_a_number_word_from_the_coaching_history_passes(self):
        narrative = {"commitment_progress": ["Kept to two calling blocks"]}

        self.assertEqual(numbers_found(narrative, "- Agreed: Protect two calling blocks\n"), [])
        self.assertEqual(numbers_found(narrative), ["two"])

    def test_a_coaching_number_written_with_a_comma_matches(self):
        narrative = {"commitment_progress": ["Aimed for 1000 touches"]}

        self.assertEqual(numbers_found(narrative, "- Agreed: 1,000 touches\n"), [])

    def test_suggested_questions_may_use_number_words(self):
        narrative = {"questions": ["What would protect two calling blocks a day?"]}

        self.assertEqual(numbers_found(narrative), [])

    def test_agenda_topics_may_use_number_words(self):
        self.assertEqual(numbers_found({"agenda": ["Pick two things to try"]}), [])

    def test_digits_in_questions_are_still_reported(self):
        self.assertEqual(numbers_found({"questions": ["Why only 3 of 13?"]}), ["3", "13"])


class CheckNarrativeCommandTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.workspace = make_workspace(self.folder)

    def run_check(self, narrative, *extra):
        path = self.folder / "narrative.json"
        path.write_text(json.dumps(narrative))
        return run_cli(
            "check-narrative", "--workspace", str(self.workspace), "--narrative", str(path), *extra
        )

    def test_clean_text_passes(self):
        code, output = self.run_check({"headline": "Activity is the place to start"})

        self.assertEqual(code, 0)
        self.assertEqual(output["status"], "ok")

    def test_a_number_needs_rewriting(self):
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


if __name__ == "__main__":
    unittest.main()
