from __future__ import annotations

import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from tests.helpers import make_workspace, run_cli, window_meetings
from tests.test_scorecard import seed_activity

from sdrlib import history, reports
from sdrlib.reports import (
    format_value,
    load_brand,
    render_one_on_one,
    render_team,
    sparkline,
)
from sdrlib.scorecard import build_scorecard

NOW = datetime(2026, 10, 30, 12, 0, 0)
BRAND = "Andy Gheewalla"
TEAM_NARRATIVE = {
    "headline": "A steady week with one clear gap",
    "observations": ["First note", "Second note"],
    "rep_notes": {"Ava Reyes": "Ask about the LinkedIn follow-ups"},
}
ONE_ON_ONE_NARRATIVE = {
    "wins": ["Held meetings stayed close to goal"],
    "focus_summary": "Replies on LinkedIn are the first soft spot",
    "evidence": ["Message replies are under target"],
    "commitment_progress": ["Started calling earlier"],
    "questions": ["What gets in the way of follow-ups?"],
    "agenda": ["Check-in", "Wins", "Focus", "Next steps"],
}
THREE_REPS = [
    {"name": "Ava Reyes", "start_date": "2025-01-06"},
    {"name": "Ben Carter", "start_date": "2025-01-06"},
    {"name": "Cy Young", "start_date": "2025-01-06"},
]


class ReportTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.workspace = make_workspace(self.folder, reps=THREE_REPS)
        seed_activity(self.workspace)
        history.write_meetings(self.workspace, "2026-W44", window_meetings())
        history.write_sources(
            self.workspace,
            "2026-W44",
            [
                {
                    "file": "calls.csv",
                    "kind": "activities",
                    "rows_read": 900,
                    "rows_rejected": 3,
                    "first_date": "2026-10-05",
                    "last_date": "2026-10-30",
                }
            ],
        )
        self.metrics = build_scorecard(self.workspace, now=NOW)

    def changed(self, **top_level):
        return {**self.metrics, **top_level}


class FormatValueTests(unittest.TestCase):
    def test_rates_are_percentages(self):
        self.assertEqual(format_value("connect_rate", 0.054545), "5.5%")

    def test_counts_have_thousands_separators(self):
        self.assertEqual(format_value("touches", 2080), "2,080")

    def test_whole_float_counts_drop_the_decimal(self):
        self.assertEqual(format_value("touches", 2080.0), "2,080")

    def test_fractional_counts_keep_one_decimal(self):
        self.assertEqual(format_value("meetings_held", 9.23), "9.2")

    def test_missing_values_are_never_zero(self):
        self.assertEqual(format_value("connect_rate", None), "Not available")


class FormatTargetTests(unittest.TestCase):
    def test_shows_a_target_exactly(self):
        self.assertEqual(reports.format_target("email_reply_rate", 0.0343), "3.43%")

    def test_drops_trailing_zeros(self):
        self.assertEqual(reports.format_target("connect_rate", 0.054), "5.4%")
        self.assertEqual(reports.format_target("show_rate", 0.8), "80%")

    def test_leaves_counts_to_the_normal_format(self):
        self.assertEqual(reports.format_target("touches", 2080.0), "2,080")

    def test_missing_targets_are_never_zero(self):
        self.assertEqual(reports.format_target("show_rate", None), "Not available")

    def test_a_close_call_stays_visible_in_the_report(self):
        rendered = reports._team_row("Email reply rate", "email_reply_rate", 0.0341, 0.0343)

        self.assertIn("3.4%", rendered)
        self.assertIn("3.43%", rendered)
        self.assertIn("Near", rendered)


class SparklineTests(unittest.TestCase):
    def test_draws_a_line(self):
        self.assertIn("<polyline", sparkline([1, 2, 3, 4]))

    def test_leaves_a_gap_for_missing_values(self):
        svg = sparkline([1, 2, None, 3, 4])

        self.assertEqual(svg.count("<polyline"), 2)

    def test_flat_values_stay_valid(self):
        self.assertIn("<polyline", sparkline([5, 5, 5, 5]))

    def test_no_values_gives_an_empty_chart(self):
        self.assertNotIn("<polyline", sparkline([None, None]))

    def test_a_single_value_draws_a_dot(self):
        self.assertIn("<circle", sparkline([None, 3, None]))


class BrandTests(ReportTest):
    def test_brand_file_names_the_brand(self):
        self.assertEqual(load_brand(), BRAND)

    def test_team_report_shows_the_brand_on_the_first_page(self):
        output = render_team(self.metrics, TEAM_NARRATIVE)

        first_page = output[output.index("<section") : output.index("</section>")]
        self.assertIn(f'class="wordmark">{BRAND}<', first_page)

    def test_team_report_footer_on_every_page(self):
        output = render_team(self.metrics, TEAM_NARRATIVE)

        footers = re.findall(r'<footer class="page-footer">(.*?)</footer>', output)
        self.assertEqual(len(footers), 5)
        for footer in footers:
            self.assertIn(BRAND, footer)
            self.assertIn("2026-W44", footer)

    def test_one_on_one_shows_the_brand_in_header_and_footer(self):
        output = render_one_on_one(self.metrics, "Ava Reyes", ONE_ON_ONE_NARRATIVE, "")

        self.assertIn(f'class="wordmark">{BRAND}<', output)
        footer = re.search(r'<footer class="page-footer">(.*?)</footer>', output).group(1)
        self.assertIn(BRAND, footer)
        self.assertIn("Ava Reyes", footer)

    def test_titles_start_with_the_brand(self):
        team = render_team(self.metrics, TEAM_NARRATIVE)
        one_on_one = render_one_on_one(self.metrics, "Ava Reyes", ONE_ON_ONE_NARRATIVE, "")

        self.assertIn(f"<title>{BRAND}", team)
        self.assertIn(f"<title>{BRAND}", one_on_one)

    def test_brand_text_is_escaped(self):
        with mock.patch.object(reports, "load_brand", return_value="Andy & Co"):
            output = render_team(self.metrics, TEAM_NARRATIVE)

        self.assertIn("Andy &amp; Co", output)
        self.assertNotIn("Andy & Co", output)


class TeamReportTests(ReportTest):
    def render(self, metrics=None, narrative=None):
        return render_team(metrics or self.metrics, narrative or TEAM_NARRATIVE)

    def test_reps_appear_alphabetically(self):
        output = self.render()

        self.assertLess(output.index("<h1>Ava Reyes"), output.index("<h1>Ben Carter"))

    def test_contains_no_ranking_language(self):
        output = self.render().lower()

        self.assertNotIn("rank", output)
        self.assertNotIn("leaderboard", output)

    def test_shows_every_step_status_in_words(self):
        output = self.render()

        for word in ("On target", "Near", "Below"):
            self.assertIn(word, output)

    def test_escapes_data_values(self):
        hostile = "<script>alert(1)</script>"
        reps = [{**self.metrics["reps"][0], "name": hostile}] + self.metrics["reps"][1:]

        output = self.render(self.changed(reps=reps))

        self.assertNotIn(hostile, output)
        self.assertIn("&lt;script&gt;", output)

    def test_escapes_narrative_text(self):
        output = self.render(narrative={**TEAM_NARRATIVE, "headline": "<b>loud</b>"})

        self.assertNotIn("<b>loud</b>", output)

    def test_shows_at_most_three_observations(self):
        notes = [f"Observation {number}" for number in "ABCDE"]

        output = self.render(narrative={**TEAM_NARRATIVE, "observations": notes})

        self.assertIn("Observation C", output)
        self.assertNotIn("Observation D", output)

    def test_shows_a_partial_week_banner(self):
        self.assertNotIn("Partial week", self.render())
        self.assertIn("Partial week", self.render(self.changed(partial_week=True)))

    def test_lists_files_rows_and_date_range(self):
        output = self.render()

        self.assertIn("calls.csv", output)
        self.assertIn("900", output)
        self.assertIn("2026-10-05", output)

    def test_shows_a_team_pattern_when_there_is_one(self):
        pattern = {"step": 2, "name": "Response", "reps": 3, "judged": 5}
        team = {**self.metrics["team"], "pattern": pattern}

        output = self.render(self.changed(team=team))

        self.assertIn("Team pattern", output)
        self.assertIn("3 of 5", output)

    def test_leaves_out_the_pattern_section_without_one(self):
        self.assertNotIn("Team pattern", self.render())

    def test_final_page_lists_every_target_with_its_source(self):
        output = self.render()

        for entry in self.metrics["targets"].values():
            self.assertIn(entry["label"], output)
            self.assertIn(reports.escape(entry["source"]), output)

    def test_shows_a_deliverability_warning_on_the_rep_page(self):
        rep = {**self.metrics["reps"][0], "flags": ["bounce_warning"]}

        output = self.render(self.changed(reps=[rep] + self.metrics["reps"][1:]))

        self.assertIn("Deliverability warning", output)

    def test_shows_rep_notes_from_the_narrative(self):
        self.assertIn("Ask about the LinkedIn follow-ups", self.render())

    def test_handles_a_report_with_no_meetings_file(self):
        history_free = self.metrics["reps"][0]
        rep = {
            **history_free,
            "window": {**history_free["window"], "meetings": None},
            "this_week": {**history_free["this_week"], "meetings": None},
        }

        output = self.render(self.changed(reps=[rep]))

        self.assertIn("Not available", output)

    def test_describes_every_rep_status_without_a_focus(self):
        for status in ("Onboarding", "Review", "Limited data", "On track"):
            rep = {**self.metrics["reps"][0], "status": status, "focus": None}

            self.assertIn(status, self.render(self.changed(reps=[rep])))

    def test_describes_a_stretch_focus(self):
        stretch = {
            "step": 2,
            "metric": "connect_rate",
            "actual": 0.07,
            "target": 0.133,
            "kind": "stretch",
        }
        rep = {**self.metrics["reps"][0], "status": "On track", "focus": stretch}

        output = self.render(self.changed(reps=[rep]))

        self.assertIn("13.3%", output)


class OneOnOneTests(ReportTest):
    def render(self, narrative=None, coaching_text=""):
        return render_one_on_one(
            self.metrics, "Ava Reyes", narrative or ONE_ON_ONE_NARRATIVE, coaching_text
        )

    def test_has_every_section(self):
        output = self.render()

        headings = (
            "Wins",
            "Coaching focus",
            "Commitments",
            "Questions",
            "Agenda",
            "The five steps",
            "Meeting notes",
        )
        for heading in headings:
            self.assertIn(heading, output)

    def test_shows_the_narrative(self):
        output = self.render()

        for text in ("Held meetings stayed close", "first soft spot", "What gets in the way"):
            self.assertIn(text, output)

    def test_shows_the_latest_commitments_from_the_history(self):
        history_text = (
            "## 2026-10-16\n- Focus: Activity\n- Agreed: Old promise\n- Check by: 2026-10-23\n"
            "\n## 2026-10-30\n- Focus: Response\n- Agreed: Newest promise\n"
            "- Check by: 2026-11-13\n"
        )

        output = self.render(coaching_text=history_text)

        self.assertIn("Newest promise", output)
        self.assertNotIn("Old promise", output)

    def test_says_when_there_are_no_commitments_yet(self):
        self.assertIn("No earlier commitments", self.render())

    def test_gives_agenda_topics_fixed_timings(self):
        output = self.render()

        self.assertIn("5 min", output)
        self.assertIn("Next steps", output)

    def test_escapes_narrative_text(self):
        output = self.render({**ONE_ON_ONE_NARRATIVE, "wins": ["<i>bold claim</i>"]})

        self.assertNotIn("<i>bold claim</i>", output)

    def test_escapes_commitments(self):
        output = self.render(coaching_text="## 2026-10-30\n- Agreed: <b>promise</b>\n")

        self.assertNotIn("<b>promise</b>", output)

    def test_unknown_rep_is_named(self):
        with self.assertRaisesRegex(ValueError, "Nobody Here"):
            render_one_on_one(self.metrics, "Nobody Here", ONE_ON_ONE_NARRATIVE, "")


class ReportCommandTests(ReportTest):
    def run_report(self, kind, narrative, *extra):
        path = self.folder / "narrative.json"
        path.write_text(json.dumps(narrative))
        arguments = ("report", kind, "--workspace", str(self.workspace))
        arguments += ("--week", "2026-W44", "--narrative", str(path)) + extra
        with mock.patch("sdrlib.pdf.print_to_pdf", return_value=False):
            return run_cli(*arguments)

    def test_team_report_saves_html_and_reports_the_fallback(self):
        code, output = self.run_report("team", TEAM_NARRATIVE)

        self.assertEqual(code, 0)
        self.assertTrue(Path(output["html"]).exists())
        self.assertTrue(output["fallback"])
        self.assertIsNone(output["pdf"])

    def test_one_on_one_needs_a_rep(self):
        code, output = self.run_report("one-on-one", ONE_ON_ONE_NARRATIVE)

        self.assertEqual(code, 2)
        self.assertIn("rep", output["error"])

    def test_one_on_one_saves_a_file_named_for_the_rep(self):
        code, output = self.run_report(
            "one-on-one", ONE_ON_ONE_NARRATIVE, "--rep", "Ava Reyes"
        )

        self.assertEqual(code, 0)
        self.assertIn("one-on-one-ava-reyes", output["html"])

    def test_a_failed_number_check_writes_no_files(self):
        code, output = self.run_report("team", {**TEAM_NARRATIVE, "headline": "Hit 4,444 dials"})

        self.assertEqual(code, 2)
        self.assertEqual(output["problems"][0]["number"], "4,444")
        self.assertFalse((self.workspace / "reports").exists())


if __name__ == "__main__":
    unittest.main()
