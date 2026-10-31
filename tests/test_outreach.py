from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from sdrlib import outreach
from tests.helpers import REPO_ROOT, make_workspace, run_cli

TEAM = {
    "company": "Example Analytics",
    "product": "Forecasting software for retailers.",
    "ideal_customer": "Operations leaders at retailers with 50 to 500 stores.",
    "proof_points": ["Northwind Stores cut stockouts by 18% in a year."],
}
OPT_OUT = "To stop receiving these emails, just reply and say so."
ADDRESS = "Example Analytics, 100 Market Street, Chicago, IL 60606"
FOOTER = f"{OPT_OUT}\n{ADDRESS}"
ORIGINAL = f"Hi {{{{first_name}}}}, we sell software to retailers.\n{FOOTER}"
DAY = date(2026, 10, 31)


def make_draft(**changes):
    """Build a follow-up email that passes every check, then apply the changes."""
    draft = {
        "kind": "follow_up_email",
        "name": "Follow-up one",
        "original": ORIGINAL,
        "subject": "",
        "body": "{{first_name}}, we sell software to retailers.",
        "footer": FOOTER,
        "changes": ["It gets to the point faster"],
    }
    return {**draft, **changes}


def bare_draft(**changes):
    """Build a draft whose original holds no placeholders or protected text."""
    return make_draft(**{"original": "Rough notes.", "body": "A", "footer": "", **changes})


def checked(team=None, **changes):
    return outreach.check_draft(make_draft(**changes), TEAM if team is None else team)


def checked_bare(team=None, **changes):
    return outreach.check_draft(bare_draft(**changes), TEAM if team is None else team)


def rules_of(result, key="problems"):
    return [item["rule"] for item in result[key]]


def texts_of(result, rule, key="problems"):
    return [item.get("text") for item in result[key] if item["rule"] == rule]


class LimitTests(unittest.TestCase):
    def test_every_kind_has_a_positive_limit_and_a_source(self):
        limits = outreach.resolve_limits({})

        self.assertEqual(sorted(limits), sorted(outreach.KINDS))
        for kind, limit in limits.items():
            self.assertGreater(limit["value"], 0, kind)
            self.assertTrue(limit["source"], kind)

    def test_starting_limits_match_the_design(self):
        limits = outreach.resolve_limits({})

        self.assertEqual(
            (limits["first_email"]["value"], limits["first_email"]["unit"]), (80, "words")
        )
        self.assertEqual(limits["follow_up_email"]["value"], 125)
        self.assertEqual(limits["call_script"]["value"], 150)
        self.assertEqual(
            (limits["linkedin_note"]["value"], limits["linkedin_note"]["unit"]), (200, "characters")
        )
        self.assertEqual(limits["linkedin_message"]["value"], 100)

    def test_a_team_can_replace_a_limit(self):
        team = {"outreach_limits": {"linkedin_note": {"value": 300, "as_of": "2026-10-31"}}}

        limit = outreach.resolve_limits(team)["linkedin_note"]

        self.assertEqual(limit["value"], 300)
        self.assertEqual(limit["source"], "team")
        self.assertEqual(limit["unit"], "characters")

    def test_unknown_limit_is_explained(self):
        with self.assertRaisesRegex(ValueError, "Unknown outreach limits"):
            outreach.resolve_limits({"outreach_limits": {"sms": {"value": 10}}})


class PlaceholderTests(unittest.TestCase):
    def test_finds_every_format(self):
        tokens = (
            "{{first_name}}",
            "{{ contact.firstname }}",
            "{{first_name|there}}",
            "{{{Recipient.FirstName}}}",
            "{!Contact.FirstName}",
            "[[Company]]",
            "[Company]",
            "<<Company>>",
            "%first_name%",
        )

        self.assertEqual(outreach.find_placeholders(" and ".join(tokens)), set(tokens))

    def test_leaves_percentages_alone(self):
        self.assertEqual(outreach.find_placeholders("50% of stores, or 20% of sales"), set())

    def test_keeping_every_placeholder_passes(self):
        self.assertEqual(checked()["problems"], [])

    def test_rejects_a_changed_spelling(self):
        result = checked(body="{{firstName}}, we sell software to retailers.")

        self.assertEqual(
            texts_of(result, "placeholder_changed"), ["{{firstName}}", "{{first_name}}"]
        )

    def test_rejects_a_dropped_placeholder(self):
        result = checked(body="We sell software to retailers.")

        self.assertEqual(texts_of(result, "placeholder_changed"), ["{{first_name}}"])

    def test_rejects_a_new_placeholder_when_the_original_has_some(self):
        result = checked(body="{{first_name}}, {{company}} sells software to retailers.")

        self.assertEqual(texts_of(result, "placeholder_changed"), ["{{company}}"])

    def test_new_placeholders_go_to_the_manager_when_the_original_has_none(self):
        result = checked_bare(body="{{first_name}}, we sell software to retailers.")

        self.assertEqual(result["problems"], [])
        self.assertEqual(texts_of(result, "new_placeholder", "to_confirm"), ["{{first_name}}"])

    def test_a_placeholder_may_move_to_the_footer(self):
        result = checked(
            original=f"{ORIGINAL}\n{{{{unsubscribe_link}}}}",
            footer=f"{FOOTER}\n{{{{unsubscribe_link}}}}",
        )

        self.assertEqual(result["problems"], [])


class ProtectedTextTests(unittest.TestCase):
    def test_rejects_a_dropped_opt_out(self):
        result = checked(footer=ADDRESS)

        self.assertEqual(texts_of(result, "protected_text_changed"), [OPT_OUT])

    def test_rejects_a_reworded_opt_out(self):
        result = checked(footer=f"Reply if you'd like to stop hearing from us.\n{ADDRESS}")

        self.assertEqual(texts_of(result, "protected_text_changed"), [OPT_OUT])

    def test_rejects_a_dropped_address(self):
        result = checked(footer=OPT_OUT)

        self.assertEqual(texts_of(result, "protected_text_changed"), [ADDRESS])

    def test_rejects_a_dropped_recording_notice(self):
        notice = "This call may be recorded for quality."
        result = checked_bare(kind="call_script", original=f"{notice} Hi there.", body="Hi there.")

        self.assertEqual(texts_of(result, "protected_text_changed"), [notice])

    def test_keeps_only_the_opt_out_sentence_of_a_paragraph(self):
        sentence = "To opt out, reply no."
        original = f"We sell a lot of things. {sentence} Thanks for reading all this."

        self.assertEqual(outreach.protected_text(original), [sentence])

    def test_line_wrapping_does_not_matter(self):
        result = checked(
            footer=f"To stop receiving these\nemails, just reply and say so.\n{ADDRESS}"
        )

        self.assertEqual(result["problems"], [])

    def test_protects_each_kind_of_address(self):
        for line in (
            "P.O. Box 123",
            "PO Box 123",
            "1600 Pennsylvania Avenue",
            "500 W Madison St",
            "Chicago, IL 60606",
            "London SW1A 1AA",
        ):
            self.assertEqual(outreach.protected_text(line), [line], line)

    def test_protects_each_kind_of_opt_out(self):
        for line in (
            "Unsubscribe here",
            "Click to opt-out",
            "Reply STOP to end these",
            "Reply and we'll remove you from this list",
            "Just say remove me",
        ):
            self.assertEqual(outreach.protected_text(line), [line], line)

    def test_ordinary_sentences_are_not_protected(self):
        for line in (
            "Our call recording software helps managers coach.",
            "We keep 3 stores in one place.",
            "A 15 minute drive from the office.",
            "We remove the guesswork from planning.",
        ):
            self.assertEqual(outreach.protected_text(line), [], line)


class NumberTests(unittest.TestCase):
    def test_rejects_new_statistics(self):
        result = checked(body="{{first_name}}, we cut stockouts 40%, or 10x, saving $2M.")

        self.assertEqual(texts_of(result, "new_number"), ["10", "2", "40"])

    def test_allows_numbers_from_approved_sources(self):
        result = checked(
            original=f"{ORIGINAL} We have 2,080 users.",
            body="{{first_name}}, with 2,080 users, we cut stockouts by 18% at 50 to 500 stores.",
        )

        self.assertEqual(texts_of(result, "new_number"), [])

    def test_allows_meeting_lengths_and_clock_times(self):
        for text in ("a 15-minute call", "15 minute call", "30 minutes", "30 seconds", "1 hour"):
            result = checked(body=f"{{{{first_name}}}}, worth {text}?")
            self.assertEqual(texts_of(result, "new_number"), [], text)
        for text in ("2pm", "2 pm", "10:30", "10:30 am"):
            result = checked(body=f"{{{{first_name}}}}, free at {text}?")
            self.assertEqual(texts_of(result, "new_number"), [], text)

    def test_ignores_digits_inside_words_and_placeholders(self):
        result = checked(
            original=f"{ORIGINAL} {{{{custom_2}}}}",
            body="{{first_name}}, we help B2B teams plan Q3. {{custom_2}}",
        )

        self.assertEqual(texts_of(result, "new_number"), [])

    def test_a_length_of_time_in_other_words_is_still_a_number(self):
        result = checked(body="{{first_name}}, we have 30 customers.")

        self.assertEqual(texts_of(result, "new_number"), ["30"])


class LengthTests(unittest.TestCase):
    def test_rejects_a_first_email_over_the_limit(self):
        result = checked_bare(kind="first_email", body=" ".join(["word"] * 81))

        self.assertEqual(texts_of(result, "too_long"), ["81 words, limit 80"])

    def test_passes_a_first_email_at_the_limit(self):
        result = checked_bare(kind="first_email", body=" ".join(["word"] * 80))

        self.assertEqual(rules_of(result), [])

    def test_leaves_the_footer_out(self):
        result = checked_bare(
            kind="first_email", body=" ".join(["word"] * 80), footer=" ".join(["Thanks"] * 40)
        )

        self.assertEqual(rules_of(result), [])

    def test_counts_characters_for_a_linkedin_note(self):
        self.assertEqual(rules_of(checked_bare(kind="linkedin_note", body="x" * 200)), [])
        self.assertEqual(
            texts_of(checked_bare(kind="linkedin_note", body="x" * 201), "too_long"),
            ["201 characters, limit 200"],
        )

    def test_uses_a_team_limit(self):
        team = {**TEAM, "outreach_limits": {"linkedin_note": {"value": 300}}}

        self.assertEqual(rules_of(checked_bare(team, kind="linkedin_note", body="x" * 300)), [])

    def test_reports_the_length_and_its_source(self):
        result = checked()

        self.assertEqual(result["length"]["value"], 6)
        self.assertEqual(result["length"]["limit"], 125)
        self.assertEqual(result["length"]["unit"], "words")
        self.assertTrue(result["length"]["source"])


class FirstContactTests(unittest.TestCase):
    def test_rejects_a_fake_reply_on_a_first_email(self):
        for subject in ("Re: your stores", "RE: your stores", "Fwd: stores", "FW: stores"):
            result = checked(kind="first_email", subject=subject)
            self.assertEqual(texts_of(result, "fake_reply"), [subject], subject)

    def test_allows_a_reply_subject_on_a_follow_up(self):
        self.assertEqual(checked(subject="Re: your stores")["problems"], [])

    def test_a_subject_that_only_contains_re_is_fine(self):
        self.assertEqual(
            checked(kind="first_email", subject="Remember your stores")["problems"], []
        )

    def test_rejects_a_claimed_past_conversation(self):
        for kind in ("first_email", "call_script", "linkedin_note"):
            result = checked(kind=kind, body="{{first_name}}, as we discussed, we sell software.")
            self.assertEqual(rules_of(result), ["false_history"], kind)

    def test_recognizes_other_wordings(self):
        for phrase in (
            "per our conversation",
            "following up on our call",
            "great speaking with you",
            "when we last spoke",
        ):
            result = checked(kind="first_email", body=f"{{{{first_name}}}}, {phrase}, we sell.")
            self.assertEqual(rules_of(result), ["false_history"], phrase)

    def test_allows_a_past_conversation_in_a_follow_up(self):
        result = checked(body="{{first_name}}, as we discussed, we sell software.")

        self.assertEqual(result["problems"], [])

    def test_a_subject_on_a_call_script_is_ignored(self):
        result = checked(kind="call_script", subject="Re: anything")

        self.assertEqual(result["problems"], [])


class WhyItChangedTests(unittest.TestCase):
    def test_rejects_a_statistic(self):
        result = checked(changes=["It cuts 120 words"])

        self.assertEqual(texts_of(result, "statistic"), ["120"])

    def test_rejects_a_gendered_pronoun(self):
        result = checked(changes=["It helps her reply"])

        self.assertEqual(texts_of(result, "pronoun"), ["her"])


class ConfirmTests(unittest.TestCase):
    def body(self, text):
        return checked_bare(body=text, footer="")

    def test_lists_a_new_name_as_one_item(self):
        result = self.body("We work with Acme Corp today.")

        self.assertEqual(texts_of(result, "new_name", "to_confirm"), ["Acme Corp"])

    def test_leaves_approved_names_out(self):
        result = self.body("We helped Northwind Stores, and it's what Example Analytics does.")

        self.assertEqual(texts_of(result, "new_name", "to_confirm"), [])

    def test_accepts_a_possessive_of_an_approved_name(self):
        result = self.body("We admire Northwind's team.")

        self.assertEqual(texts_of(result, "new_name", "to_confirm"), [])

    def test_leaves_out_days_months_and_the_word_i(self):
        result = self.body("Free on Tuesday in November? If so, I'm happy to call, and I can.")

        self.assertEqual(texts_of(result, "new_name", "to_confirm"), [])

    def test_leaves_out_the_first_word_of_a_sentence(self):
        result = self.body("Planning gets easier. Forecasts help.")

        self.assertEqual(texts_of(result, "new_name", "to_confirm"), [])

    def test_lists_spelled_out_numbers(self):
        result = self.body("We doubled replies, with three times more meetings.")

        self.assertEqual(
            sorted(texts_of(result, "number_word", "to_confirm")), ["doubled", "three"]
        )

    def test_a_spelled_out_number_in_the_original_is_fine(self):
        result = checked_bare(original="We have three offices.", body="We have three offices.")

        self.assertEqual(texts_of(result, "number_word", "to_confirm"), [])

    def test_lists_a_missing_opt_out_and_address_for_email(self):
        for kind in ("first_email", "follow_up_email"):
            result = checked_bare(kind=kind, body="We sell software to retailers.")
            self.assertEqual(
                rules_of(result, "to_confirm"), ["no_opt_out", "no_postal_address"], kind
            )

    def test_a_visible_opt_out_and_address_need_no_confirmation(self):
        self.assertEqual(rules_of(checked(), "to_confirm"), [])

    def test_a_placeholder_can_supply_them(self):
        for token in ("{{signature}}", "{{unsubscribe_link}}", "{{sender.footer}}"):
            result = checked_bare(body="We sell.", footer=token)
            self.assertEqual(
                [rule for rule in rules_of(result, "to_confirm") if rule != "new_placeholder"],
                [],
                token,
            )

    def test_calls_and_linkedin_need_neither(self):
        for kind in ("call_script", "linkedin_note", "linkedin_message"):
            result = checked_bare(kind=kind, body="We sell software to retailers.")
            self.assertEqual(rules_of(result, "to_confirm"), [], kind)

    def test_every_item_has_a_message_for_the_manager(self):
        result = checked_bare(body="We doubled sales at Acme. {{first_name}}")

        self.assertGreaterEqual(len(result["to_confirm"]), 4)
        for item in result["to_confirm"]:
            self.assertTrue(item["message"], item)


class BadDraftTests(unittest.TestCase):
    def test_unknown_kind(self):
        with self.assertRaisesRegex(ValueError, "kind"):
            checked(kind="sms")

    def test_missing_or_blank_required_field(self):
        for field in ("name", "original", "body"):
            for value in (None, "", "  "):
                with self.assertRaisesRegex(ValueError, field):
                    checked(**{field: value})

    def test_required_field_left_out_entirely(self):
        draft = {key: value for key, value in make_draft().items() if key != "body"}

        with self.assertRaisesRegex(ValueError, "body"):
            outreach.check_draft(draft, TEAM)

    def test_non_text_subject_or_footer(self):
        for field in ("subject", "footer"):
            with self.assertRaisesRegex(ValueError, field):
                checked(**{field: 5})

    def test_changes_must_be_a_list_of_text(self):
        for value in ("a sentence", [5]):
            with self.assertRaisesRegex(ValueError, "changes"):
                checked(changes=value)

    def test_optional_fields_may_be_left_out(self):
        draft = {
            key: value
            for key, value in make_draft().items()
            if key not in ("subject", "footer", "changes")
        }

        result = outreach.check_draft(draft, TEAM)

        self.assertEqual(rules_of(result), ["protected_text_changed", "protected_text_changed"])

    def test_check_leaves_the_draft_unchanged(self):
        draft = {key: value for key, value in make_draft().items() if key != "subject"}
        before = dict(draft)

        outreach.check_draft(draft, TEAM)

        self.assertEqual(draft, before)


class SavedFileTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.workspace = Path(folder.name)

    def test_lays_out_an_email(self):
        draft = make_draft(kind="first_email", name="Email one", subject="Your stores")
        confirm = [{"rule": "no_opt_out", "message": "Does your sales tool add one?"}]

        text = outreach.render_saved(draft, confirm, DAY)

        self.assertEqual(
            text,
            "Email, first message\n"
            "Name: Email one\n"
            "Saved: 2026-10-31\n"
            "\n"
            "Subject: Your stores\n"
            "\n"
            "{{first_name}}, we sell software to retailers.\n"
            "\n"
            f"{FOOTER}\n"
            "\n"
            "Why it changed\n"
            "- It gets to the point faster\n"
            "\n"
            "Please confirm\n"
            "- Does your sales tool add one?\n",
        )

    def test_a_call_script_has_no_subject_line(self):
        text = outreach.render_saved(make_draft(kind="call_script", subject="Ignored"), [], DAY)

        self.assertTrue(text.startswith("Cold call script\n"))
        self.assertNotIn("Subject:", text)

    def test_leaves_out_empty_sections(self):
        text = outreach.render_saved(bare_draft(changes=[]), [], DAY)

        self.assertNotIn("Why it changed", text)
        self.assertNotIn("Please confirm", text)

    def test_leaves_the_original_out_of_the_file(self):
        draft = make_draft(original=f"{ORIGINAL}\nJane at Acme bought this.")

        path = outreach.save_rewrite(self.workspace, draft, [], DAY)

        self.assertNotIn("Jane", path.read_text(encoding="utf-8"))

    def test_names_the_file_by_date_and_name(self):
        path = outreach.save_rewrite(self.workspace, make_draft(name="New Email: One!"), [], DAY)

        self.assertEqual(path, self.workspace / "outreach" / "2026-10-31-new-email-one.txt")

    def test_a_same_day_save_replaces_the_file(self):
        outreach.save_rewrite(self.workspace, make_draft(body="First version."), [], DAY)
        path = outreach.save_rewrite(self.workspace, make_draft(body="Second version."), [], DAY)

        self.assertIn("Second version.", path.read_text(encoding="utf-8"))
        self.assertEqual(len(list((self.workspace / "outreach").iterdir())), 1)

    def test_another_day_keeps_both_files(self):
        outreach.save_rewrite(self.workspace, make_draft(), [], DAY)
        outreach.save_rewrite(self.workspace, make_draft(), [], date(2026, 11, 2))

        self.assertEqual(len(list((self.workspace / "outreach").iterdir())), 2)


class LoadDraftTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "draft.json"

    def test_reads_a_draft(self):
        self.path.write_text(json.dumps(make_draft()), encoding="utf-8")

        self.assertEqual(outreach.load_draft(self.path), make_draft())

    def test_explains_a_missing_file(self):
        with self.assertRaisesRegex(ValueError, "couldn't be read"):
            outreach.load_draft(self.path)

    def test_explains_invalid_json(self):
        self.path.write_text("{not json", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "isn't a valid draft"):
            outreach.load_draft(self.path)

    def test_explains_json_that_is_not_an_object(self):
        self.path.write_text("[1, 2]", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "isn't a valid draft"):
            outreach.load_draft(self.path)


class CheckOutreachCommandTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.workspace = make_workspace(Path(folder.name), proof_points=TEAM["proof_points"])
        self.draft_path = self.workspace / "outreach" / "draft.json"
        self.draft_path.parent.mkdir()

    def run_check(self, draft):
        self.draft_path.write_text(json.dumps(draft), encoding="utf-8")
        return run_cli(
            "check-outreach", "--workspace", str(self.workspace), "--draft", str(self.draft_path)
        )

    def saved_files(self):
        return list((self.workspace / "outreach").glob("*.txt"))

    def test_a_passing_draft_is_saved_and_removed(self):
        code, output = self.run_check(make_draft())

        self.assertEqual(code, 0)
        self.assertEqual(output["status"], "ok")
        self.assertTrue(Path(output["path"]).exists())
        self.assertFalse(self.draft_path.exists())
        self.assertEqual(output["length"]["limit"], 125)
        self.assertEqual(output["to_confirm"], [])

    def test_a_failing_draft_saves_nothing_and_stays(self):
        code, output = self.run_check(make_draft(body="We grew 40% this year. {{first_name}}"))

        self.assertEqual(code, 2)
        self.assertEqual(output["status"], "needs_input")
        self.assertEqual(rules_of(output), ["new_number"])
        self.assertTrue(output["problems"][0]["fix"])
        self.assertEqual(self.saved_files(), [])
        self.assertTrue(self.draft_path.exists())

    def test_uses_the_teams_proof_points(self):
        code, _ = self.run_check(make_draft(body="{{first_name}}, we cut stockouts by 18%."))

        self.assertEqual(code, 0)

    def test_a_missing_draft_gets_a_plain_message(self):
        code, output = run_cli(
            "check-outreach", "--workspace", str(self.workspace), "--draft", str(self.draft_path)
        )

        self.assertEqual(code, 2)
        self.assertIn("couldn't be read", output["error"])

    def test_an_unknown_kind_gets_a_plain_message(self):
        code, output = self.run_check(make_draft(kind="sms"))

        self.assertEqual(code, 2)
        self.assertIn("kind", output["error"])

    def test_a_missing_team_points_to_setup(self):
        self.draft_path.write_text(json.dumps(make_draft()), encoding="utf-8")
        (self.workspace / "team-profile.json").unlink()

        code, output = run_cli(
            "check-outreach", "--workspace", str(self.workspace), "--draft", str(self.draft_path)
        )

        self.assertEqual(code, 2)
        self.assertIn("setup", output["error"])


class SampleMessageTests(unittest.TestCase):
    def read(self, name):
        return (REPO_ROOT / "sample-data" / "outreach" / name).read_text(encoding="utf-8")

    def unchanged(self, name, kind, **changes):
        """Check a sample as if Claude handed it back untouched."""
        text = self.read(name)
        draft = make_draft(kind=kind, original=text, body=text, footer="", **changes)
        return outreach.check_draft(draft, TEAM)

    def test_the_weak_email_fails_the_checks_if_left_as_it_is(self):
        result = self.unchanged("weak-email.txt", "first_email", subject="Re: our conversation")

        for rule in ("too_long", "fake_reply", "false_history"):
            self.assertIn(rule, rules_of(result), rule)

    def test_the_weak_email_has_text_that_must_survive(self):
        text = self.read("weak-email.txt")

        self.assertEqual(len(outreach.protected_text(text)), 2)
        self.assertTrue(
            {"{{first_name}}", "{{company}}", "{{unsubscribe_link}}"}
            <= outreach.find_placeholders(text)
        )

    def test_the_weak_call_script_has_a_recording_notice(self):
        protected = outreach.protected_text(self.read("weak-call-script.txt"))

        self.assertEqual(protected, ["This call may be recorded for quality purposes."])

    def test_the_weak_call_script_is_over_the_limit(self):
        result = self.unchanged("weak-call-script.txt", "call_script")

        self.assertIn("too_long", rules_of(result))

    def test_the_weak_linkedin_note_is_over_the_limit(self):
        result = self.unchanged("weak-linkedin-note.txt", "linkedin_note")

        self.assertIn("too_long", rules_of(result))

    def test_the_sample_team_has_proof_points(self):
        team = json.loads((REPO_ROOT / "sample-data" / "team-profile.json").read_text())

        self.assertGreaterEqual(len(team["proof_points"]), 2)


if __name__ == "__main__":
    unittest.main()
