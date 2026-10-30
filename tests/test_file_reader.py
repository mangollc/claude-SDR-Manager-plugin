from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sdrlib import file_reader
from sdrlib.file_reader import (
    UnsupportedFile,
    header_signature,
    inspect_file,
    is_masked_column,
    mask_text,
    read_table,
)
from tests.helpers import run_cli


class TempFileTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def write(self, name, text, encoding="utf-8"):
        path = self.folder / name
        path.write_bytes(text.encode(encoding))
        return path


class ReadTableTests(TempFileTest):
    def test_removes_byte_order_mark(self):
        path = self.write("a.csv", "Date,Rep\n2026-10-26,Ava\n", encoding="utf-8-sig")

        self.assertEqual(read_table(path).headers[0], "Date")

    def test_falls_back_for_windows_encoded_text(self):
        path = self.write("a.csv", "Name,Rep\nJosé,Ava\n", encoding="cp1252")

        self.assertEqual(read_table(path).rows[0]["Name"], "José")

    def test_reads_semicolon_separated_files(self):
        path = self.write("a.csv", "Date;Rep\n2026-10-26;Ava\n")

        self.assertEqual(read_table(path).rows[0], {"Date": "2026-10-26", "Rep": "Ava"})

    def test_reads_tab_separated_files(self):
        path = self.write("a.tsv", "Date\tRep\n2026-10-26\tAva\n")

        self.assertEqual(read_table(path).rows[0]["Rep"], "Ava")

    def test_reads_header_below_report_lines(self):
        path = self.write("a.csv", "Call Report\nRun today\nDate,Rep\n2026-10-26,Ava\n")

        table = read_table(path, header_row=3)

        self.assertEqual(table.headers, ("Date", "Rep"))
        self.assertEqual(len(table.rows), 1)

    def test_pads_short_rows_trims_long_rows_and_skips_blank_lines(self):
        path = self.write("a.csv", "Date,Rep\n2026-10-26\n\n2026-10-27,Ava,extra\n")

        rows = read_table(path).rows

        self.assertEqual(rows[0], {"Date": "2026-10-26", "Rep": ""})
        self.assertEqual(rows[1], {"Date": "2026-10-27", "Rep": "Ava"})
        self.assertEqual(len(rows), 2)

    def test_strips_space_around_headers_and_values(self):
        path = self.write("a.csv", " Date , Rep \n 2026-10-26 , Ava \n")

        table = read_table(path)

        self.assertEqual(table.headers, ("Date", "Rep"))
        self.assertEqual(table.rows[0]["Rep"], "Ava")

    def test_rejects_other_file_types(self):
        path = self.write("a.pdf", "not a table")

        with self.assertRaises(UnsupportedFile):
            read_table(path)

    def test_excel_without_openpyxl_explains_the_fix(self):
        path = self.write("a.xlsx", "binary")

        with mock.patch.object(file_reader.importlib.util, "find_spec", return_value=None):
            with self.assertRaisesRegex(UnsupportedFile, "CSV"):
                read_table(path)

    def test_excel_is_read_when_openpyxl_is_available(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl is not installed")
        from datetime import datetime

        workbook = openpyxl.Workbook()
        workbook.active.append(["Date", "Rep"])
        workbook.active.append([datetime(2026, 10, 26), "Ava"])
        path = self.folder / "a.xlsx"
        workbook.save(path)

        rows = read_table(path).rows

        self.assertEqual(rows[0], {"Date": "2026-10-26", "Rep": "Ava"})


class MaskingTests(unittest.TestCase):
    def test_masks_columns_that_describe_prospects(self):
        for name in ("Email", "Contact Name", "Company", "Prospect", "Recipient Email", "Account"):
            self.assertTrue(is_masked_column(name), name)

    def test_keeps_columns_that_name_the_rep(self):
        names = (
            "Contact Owner",
            "Account Owner",
            "Assigned To",
            "Lead Rep",
            "Lead Representative",
            "Call Result",
        )
        for name in names:
            self.assertFalse(is_masked_column(name), name)

    def test_keeps_columns_that_describe_events(self):
        for name in ("Email Status", "Lead Status", "Phone Disposition", "Email Sent Date"):
            self.assertFalse(is_masked_column(name), name)

    def test_masks_free_text_columns(self):
        for name in ("Subject", "Notes", "Organization", "LinkedIn URL", "Description", "Title"):
            self.assertTrue(is_masked_column(name), name)

    def test_masks_lowercase_hyphenated_headers(self):
        for name in ("last-name", "contact-email", "E-mail", "first_name"):
            self.assertTrue(is_masked_column(name), name)

    def test_removes_emails_and_phone_numbers_from_text(self):
        masked = mask_text("reach me at a.b@c.co or 415-555-0100 today")

        self.assertNotIn("a.b@c.co", masked)
        self.assertNotIn("415-555-0100", masked)
        self.assertIn("reach me at", masked)

    def test_removes_international_and_bracketed_phone_numbers(self):
        for text in ("+44 20 7946 0958", "(415) 555-0100"):
            self.assertEqual(mask_text(text), "[masked]", text)

    def test_leaves_dates_and_short_numbers_alone(self):
        for text in ("2026-10-26", "10/26/2026", "2026-10-26 09:30", "12", "Step 3"):
            self.assertEqual(mask_text(text), text)


class SignatureTests(unittest.TestCase):
    def test_ignores_case(self):
        self.assertEqual(header_signature(["Date", "Rep"]), header_signature(["DATE", "rep"]))

    def test_depends_on_column_order(self):
        self.assertNotEqual(header_signature(["Date", "Rep"]), header_signature(["Rep", "Date"]))


class InspectFileTests(TempFileTest):
    def test_never_shows_masked_columns_or_personal_values(self):
        path = self.write(
            "a.csv",
            "Activity Date,Owner,Contact Name,Notes\n"
            "2026-10-26,Ava,Jane Doe,call jane@acme.io back\n",
        )

        output = json.dumps(inspect_file(path))

        self.assertNotIn("Jane Doe", output)
        self.assertNotIn("jane@acme.io", output)
        self.assertIn("Ava", output)

    def test_masks_values_above_the_header_row(self):
        path = self.write("a.csv", "Owner jane@acme.io\nDate,Rep\n2026-10-26,Ava\n")

        output = json.dumps(inspect_file(path, header_row=2))

        self.assertNotIn("jane@acme.io", output)

    def test_finds_the_header_below_report_lines(self):
        path = self.write(
            "a.csv",
            "Call Report\nRun by a manager\nDate,Rep,Contact Name\n2026-10-26,Ava,Jane Doe\n",
        )

        result = inspect_file(path)

        self.assertEqual(result["header_row"], 3)
        self.assertNotIn("Jane Doe", json.dumps(result))

    def test_finds_a_header_with_an_unnamed_first_column(self):
        path = self.write(
            "a.csv",
            ",Date,Rep,Outcome,Contact Name,Company\n"
            "0,2026-10-26,Ava,Connected,Jane Doe,Acme Corp\n",
        )

        result = inspect_file(path)

        self.assertEqual(result["header_row"], 1)
        self.assertNotIn("Jane Doe", json.dumps(result))
        self.assertNotIn("Acme Corp", json.dumps(result))

    def test_never_takes_a_row_with_a_date_for_the_header(self):
        path = self.write("a.csv", "Calls\n2026-10-26,Ava,Jane Doe\nDate,Rep,Contact Name\n")

        self.assertEqual(inspect_file(path)["header_row"], 3)

    def test_masks_personal_values_used_as_headers(self):
        path = self.write("a.csv", "Date,jane@acme.io\n2026-10-26,x\n")

        self.assertNotIn("jane@acme.io", json.dumps(inspect_file(path)))

    def test_explicit_header_row_wins_over_the_guess(self):
        path = self.write("a.csv", "Date,Rep\nnote only\n2026-10-26,Ava\n")

        self.assertEqual(inspect_file(path, header_row=1)["header_row"], 1)

    def test_empty_file_is_reported(self):
        with self.assertRaisesRegex(UnsupportedFile, "empty"):
            inspect_file(self.write("a.csv", ""))

    def test_duplicate_and_blank_headers_stay_distinct(self):
        table = read_table(self.write("a.csv", "Date,Date,\n2026-10-26,2026-10-27,x\n"))

        self.assertEqual(table.headers, ("Date", "Date (2)", "Column 3"))

    def test_reports_shape_of_the_file(self):
        path = self.write("a.csv", "Date,Rep\n2026-10-26,Ava\n2026-10-27,Ben\n")

        result = inspect_file(path)

        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["headers"], ["Date", "Rep"])
        self.assertEqual(result["signature"], header_signature(["Date", "Rep"]))

    def test_lists_distinct_values_for_small_columns(self):
        rows = "".join(f"2026-10-26,Value {index}\n" for index in range(30))
        path = self.write("a.csv", "Date,Result\n" + rows)

        self.assertEqual(len(inspect_file(path)["distinct"]["Result"]), 30)

    def test_skips_distinct_values_for_large_columns(self):
        rows = "".join(f"2026-10-26,Value {index}\n" for index in range(31))
        path = self.write("a.csv", "Date,Result\n" + rows)

        self.assertNotIn("Result", inspect_file(path)["distinct"])

    def test_keeps_masked_columns_out_of_distinct_values(self):
        path = self.write("a.csv", "Date,Company\n2026-10-26,Acme\n2026-10-27,Globex\n")

        result = inspect_file(path)

        self.assertNotIn("Company", result["distinct"])
        self.assertEqual(result["masked_columns"], ["Company"])

    def test_masks_personal_values_in_distinct_lists(self):
        path = self.write("a.csv", "Date,Notes\n2026-10-26,jane@acme.io\n")

        self.assertNotIn("jane@acme.io", json.dumps(inspect_file(path)["distinct"]))

    def test_finds_a_saved_mapping_at_its_own_header_row(self):
        path = self.write("a.csv", "Report\nDate,Rep\n2026-10-26,Ava\n")
        mappings = self.folder / "mappings"
        mappings.mkdir()
        mapping = {"signature": header_signature(["Date", "Rep"]), "header_row": 2}
        (mappings / "calls.json").write_text(json.dumps(mapping))

        self.assertEqual(inspect_file(path, mappings_dir=mappings)["matched_mapping"], "calls.json")

    def test_reports_no_match_without_a_saved_mapping(self):
        path = self.write("a.csv", "Date,Rep\n2026-10-26,Ava\n")
        mappings = self.folder / "mappings"
        mappings.mkdir()

        self.assertIsNone(inspect_file(path, mappings_dir=mappings)["matched_mapping"])


class InspectCommandTests(TempFileTest):
    def test_prints_the_preview(self):
        path = self.write("a.csv", "Date,Rep\n2026-10-26,Ava\n")

        code, output = run_cli("inspect", str(path))

        self.assertEqual(code, 0)
        self.assertEqual(output["rows"], 1)

    def test_unsupported_file_needs_the_manager(self):
        path = self.write("a.pdf", "x")

        code, output = run_cli("inspect", str(path))

        self.assertEqual(code, 2)
        self.assertIn("error", output)

    def test_missing_file_needs_the_manager(self):
        code, output = run_cli("inspect", str(self.folder / "nope.csv"))

        self.assertEqual(code, 2)
        self.assertIn("error", output)


if __name__ == "__main__":
    unittest.main()
