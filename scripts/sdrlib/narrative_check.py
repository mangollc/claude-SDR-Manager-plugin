"""Keep statistics out of Claude's written text, so only the calculator states them.

A check that a number exists somewhere in the data isn't enough. A real test run wrote
"960 this week" for a four-week total, and "Thirteen held" as a word. Both passed that kind
of check, and both were wrong. So written text carries judgment, and numbers come from the
report's own tables.
"""

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
            r"\bfour[- ]weeks?\b",  # the fixed reporting window
        )
    ),
    re.IGNORECASE,
)
NUMBER = re.compile(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?%?(?!\w)")
NUMBER_WORD = re.compile(
    r"\b(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen"
    r"|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy"
    r"|eighty|ninety|hundred|thousand|half|twice|dozen)\b",
    re.IGNORECASE,
)
# Reports describe real people, and a name says nothing certain about anyone's gender.
PRONOUN = re.compile(r"\b(?:he|she|him|her|hers|his|himself|herself)\b", re.IGNORECASE)
# These fields hold suggestions rather than claims, so "two calling blocks" is fine there.
SUGGESTION_FIELDS = ("questions", "agenda")


def extract_numbers(text: str) -> list[str]:
    """Return every number in the text, leaving out dates, step numbers, and 1:1."""
    return NUMBER.findall(IGNORED_TEXT.sub(" ", text))


def extract_number_words(text: str) -> list[str]:
    """Return every spelled-out count. `one` is allowed, because it's rarely a statistic."""
    return NUMBER_WORD.findall(IGNORED_TEXT.sub(" ", text))


def _normal(token: str) -> str:
    return token.replace(",", "").lower()


def _strings(value: object, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(item, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}[{index}]")


def _is_suggestion(field: str) -> bool:
    return field.split("[")[0] in SUGGESTION_FIELDS


def check_narrative(narrative: dict, coaching_text: str = "") -> list[dict]:
    """Return a problem for each statistic or gendered pronoun in the text.

    Only the rep's own coaching history may be quoted.
    """
    allowed = {
        _normal(token)
        for token in extract_numbers(coaching_text) + extract_number_words(coaching_text)
    }
    problems = []
    for field, text in _strings(narrative):
        found = extract_numbers(text)
        if not _is_suggestion(field):
            found = found + extract_number_words(text)
        problems += [
            {"field": field, "text": text, "number": token, "kind": "statistic"}
            for token in found
            if _normal(token) not in allowed
        ]
        problems += [
            {"field": field, "text": text, "number": token, "kind": "pronoun"}
            for token in PRONOUN.findall(text)
        ]
    return problems
