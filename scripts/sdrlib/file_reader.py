"""Read exported tables and preview them without exposing prospect details."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

PREVIEW_LINES = 10
MAX_DISTINCT_VALUES = 30
MASK = "[masked]"
TEXT_SUFFIXES = (".csv", ".tsv", ".txt")
EXCEL_SUFFIXES = (".xlsx", ".xlsm")
DELIMITERS = (",", ";", "\t")

MASKED_WORDS = (
    "email",
    "phone",
    "mobile",
    "contact",
    "prospect",
    "lead",
    "name",
    "recipient",
    "customer",
    "company",
    "account",
    "organization",
    "org",
    "subject",
    "notes",
    "note",
    "description",
    "comment",
    "comments",
    "body",
    "message",
    "title",
    "url",
    "link",
    "profile",
)
VISIBLE_WORDS = (
    "owner",
    "rep",
    "representative",
    "sdr",
    "user",
    "assigned",
    "agent",
    "status",
    "result",
    "outcome",
    "disposition",
    "type",
    "date",
    "sent",
    "replied",
    "bounced",
    "opened",
    "stage",
    "step",
)

HEADER_FILL_SHARE = 0.8
DATE_LIKE = re.compile(r"\b\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}\b")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_PATTERN = re.compile(
    r"(?<![\w.-])(?:"
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?|\d{2,4}[\s.-])\d{3,4}[\s.-]?\d{3,4}"
    r"|\+?\d{10,15}"
    r"|\d{3}[\s.-]\d{4}"
    r")(?![\w-])"
)


class UnsupportedFile(Exception):
    """Raised when a file can't be read as a table. The message is for the manager."""


@dataclass(frozen=True)
class Table:
    headers: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


def _decode(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def _choose_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:PREVIEW_LINES])
    return max(DELIMITERS, key=sample.count)


def _read_text_rows(path: Path) -> list[list[str]]:
    text = _decode(path.read_bytes())
    try:
        return list(csv.reader(io.StringIO(text), delimiter=_choose_delimiter(text)))
    except csv.Error as error:
        raise UnsupportedFile(f"{path.name} couldn't be read as a table: {error}") from error


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        is_midnight = value.hour == value.minute == value.second == 0
        return value.date().isoformat() if is_midnight else value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _read_excel_rows(path: Path) -> list[list[str]]:
    if importlib.util.find_spec("openpyxl") is None:
        raise UnsupportedFile(
            f"{path.name} is an Excel file, and this computer can't read those yet. "
            "Save it as CSV from Excel, then try again."
        )
    import openpyxl

    try:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as error:
        raise UnsupportedFile(f"{path.name} couldn't be opened as Excel: {error}") from error
    try:
        sheet = workbook.worksheets[0]
        return [[_cell_text(cell) for cell in row] for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()


def read_rows(path: Path) -> list[list[str]]:
    """Return every row of a file as text cells, including any lines above the header."""
    if not path.exists():
        raise UnsupportedFile(f"Can't find {path}.")
    suffix = path.suffix.lower()
    if suffix in EXCEL_SUFFIXES:
        return _read_excel_rows(path)
    if suffix in TEXT_SUFFIXES:
        return _read_text_rows(path)
    raise UnsupportedFile(f"{path.name} isn't a CSV or Excel file.")


def _clean_headers(cells: Sequence[str]) -> tuple[str, ...]:
    seen: dict[str, int] = {}
    headers = []
    for position, cell in enumerate(cells, start=1):
        name = cell.strip() or f"Column {position}"
        seen[name] = seen.get(name, 0) + 1
        headers.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return tuple(headers)


def _record(headers: Sequence[str], cells: Sequence[str]) -> dict[str, str]:
    padded = [cell.strip() for cell in cells] + [""] * len(headers)
    return dict(zip(headers, padded))


def table_from_rows(rows: Sequence[Sequence[str]], header_row: int = 1) -> Table:
    """Build a table from raw rows, using the 1-based header row."""
    if not rows:
        raise UnsupportedFile("This file is empty.")
    if header_row < 1 or header_row > len(rows):
        raise UnsupportedFile(f"This file has no line {header_row}.")
    headers = _clean_headers(rows[header_row - 1])
    records = tuple(
        _record(headers, cells)
        for cells in rows[header_row:]
        if any(cell.strip() for cell in cells)
    )
    return Table(headers, records)


def read_table(path: Path, header_row: int = 1) -> Table:
    """Read a CSV or Excel file into a table."""
    return table_from_rows(read_rows(path), header_row)


def header_signature(headers: Sequence[str]) -> str:
    """Return a fingerprint of a file's columns, used to reuse saved mappings."""
    joined = "\n".join(header.strip().lower() for header in headers)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _plain_words(name: str) -> str:
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    words = re.sub(r"[-_]+", " ", spaced).lower()
    return re.sub(r"\be mail\b", "email", words)


def _contains_word(text: str, words: Sequence[str]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def is_masked_column(name: str) -> bool:
    """Return True when a column probably holds prospect details."""
    words = _plain_words(name)
    return _contains_word(words, MASKED_WORDS) and not _contains_word(words, VISIBLE_WORDS)


def mask_text(value: str) -> str:
    """Replace anything that looks like an email address or phone number."""
    return PHONE_PATTERN.sub(MASK, EMAIL_PATTERN.sub(MASK, value))


def guess_header_row(rows: Sequence[Sequence[str]]) -> int:
    """Return the first opening row that's nearly full and holds no dates.

    Getting this wrong would treat a row of prospect details as column names. "Nearly full"
    allows for an unnamed first column, which is common in exports from data tools.
    """
    opening = rows[:PREVIEW_LINES]
    filled = [sum(1 for cell in row if cell.strip()) for row in opening]
    if not filled or max(filled) == 0:
        return 1
    needed = max(filled) * HEADER_FILL_SHARE
    for line, (row, count) in enumerate(zip(opening, filled), start=1):
        if count >= needed and not any(DATE_LIKE.search(cell) for cell in row):
            return line
    return filled.index(max(filled)) + 1


def _preview(
    rows: Sequence[Sequence[str]], header_row: int, masked_positions: set[int]
) -> list[list[str]]:
    preview = []
    for line, cells in enumerate(rows[:PREVIEW_LINES], start=1):
        is_data = line > header_row
        preview.append(
            [
                MASK if is_data and position in masked_positions and cell else mask_text(cell)
                for position, cell in enumerate(cells)
            ]
        )
    return preview


def _distinct_values(table: Table, visible_headers: Sequence[str]) -> dict[str, list[str]]:
    distinct = {}
    for header in visible_headers:
        values = {row[header] for row in table.rows if row[header]}
        if len(values) <= MAX_DISTINCT_VALUES:
            distinct[mask_text(header)] = sorted(mask_text(value) for value in values)
    return distinct


def find_mapping_file(rows: Sequence[Sequence[str]], mappings_dir: Path) -> Path | None:
    """Return the saved mapping whose columns match these rows, if there is one."""
    for candidate in sorted(mappings_dir.glob("*.json")):
        mapping = json.loads(candidate.read_text(encoding="utf-8"))
        header_row = mapping.get("header_row", 1)
        if len(rows) < header_row:
            continue
        if header_signature(_clean_headers(rows[header_row - 1])) == mapping.get("signature"):
            return candidate
    return None


def inspect_file(
    path: Path, header_row: int | None = None, mappings_dir: Path | None = None
) -> dict:
    """Describe a file for Claude while keeping prospect details out of the result."""
    rows = read_rows(path)
    chosen_row = header_row or guess_header_row(rows)
    table = table_from_rows(rows, chosen_row)
    masked = [header for header in table.headers if is_masked_column(header)]
    masked_positions = {table.headers.index(header) for header in masked}
    visible = [header for header in table.headers if header not in masked]
    matched = find_mapping_file(rows, mappings_dir) if mappings_dir else None
    return {
        "file": path.name,
        "rows": len(table.rows),
        "header_row": chosen_row,
        "headers": [mask_text(header) for header in table.headers],
        "signature": header_signature(table.headers),
        "preview": _preview(rows, chosen_row, masked_positions),
        "distinct": _distinct_values(table, visible),
        "masked_columns": [mask_text(header) for header in masked],
        "matched_mapping": matched.name if matched else None,
    }
