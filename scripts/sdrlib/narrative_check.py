"""Confirm that every number in Claude's written text came from the calculator."""

from __future__ import annotations

import re
from collections.abc import Iterator

MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
IGNORED_TEXT = re.compile(
    "|".join(
        (
            r"\b\d{4}-\d{2}-\d{2}\b",  # 2026-10-30
            r"\b\d{4}-W\d{2}\b",  # 2026-W44
            r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",  # 10/30 and 10/30/2026
            rf"\b{MONTHS}\s+\d{{1,2}}(?:,\s*\d{{4}})?\b",  # Oct 30 and October 30, 2026
            rf"\b\d{{1,2}}\s+{MONTHS}(?:\s+\d{{4}})?\b",  # 30 October 2026
            r"\b[Ss]tep\s+\d\b",  # Step 3
            r"\b1:1s?\b",  # the term 1:1
        )
    )
)
NUMBER = re.compile(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?%?(?!\w)")
SKIPPED_KEYS = ("generated_at", "schema_version")


def extract_numbers(text: str) -> list[str]:
    """Return every number in the text, leaving out dates, step numbers, and 1:1."""
    return NUMBER.findall(IGNORED_TEXT.sub(" ", text))


def _normal(token: str) -> str:
    """Make `2,080` match `2080`, and `80.0%` match `80%`."""
    return re.sub(r"\.0+(?=%?$)", "", token.replace(",", ""))


def _display_forms(value: float) -> set[str]:
    forms = {f"{value:.1f}", f"{value:.2f}", f"{value:.0f}" if float(value).is_integer() else ""}
    if 0 <= value <= 1:
        percent = value * 100
        forms |= {f"{percent:.1f}", f"{percent:.1f}%", f"{percent:.2f}%"}
    return {_normal(form) for form in forms if form}


def _numbers_in(value: object) -> Iterator[float]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in SKIPPED_KEYS:
                yield from _numbers_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from _numbers_in(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield value


def allowed_numbers(metrics: dict, coaching_text: str = "") -> set[str]:
    """Return every number the written text may use, in its displayed forms."""
    allowed: set[str] = set()
    for value in _numbers_in(metrics):
        allowed |= _display_forms(value)
    return allowed | {_normal(token) for token in extract_numbers(coaching_text)}


def _strings(value: object, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(item, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}[{index}]")


def check_narrative(narrative: dict, metrics: dict, coaching_text: str = "") -> list[dict]:
    """Return a problem for each written number that has no source."""
    allowed = allowed_numbers(metrics, coaching_text)
    return [
        {"field": field, "text": text, "number": token}
        for field, text in _strings(narrative)
        for token in extract_numbers(text)
        if _normal(token) not in allowed
    ]
