"""Check a rewritten outreach message, and save it once it passes.

Claude writes the new version. These checks protect what a rewrite can quietly break: the
placeholders a sales tool fills in, the lines a law may require, and the team's approved facts.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from .file_reader import EMAIL_PATTERN, PHONE_PATTERN
from .narrative_check import check_narrative, extract_number_words
from .profile import rep_slug
from .targets import ASSETS_DIR

KINDS = ("first_email", "follow_up_email", "call_script", "linkedin_note", "linkedin_message")
EMAIL_KINDS = ("first_email", "follow_up_email")
FIRST_CONTACT_KINDS = ("first_email", "call_script", "linkedin_note")
KIND_TITLES = {
    "first_email": "Email, first message",
    "follow_up_email": "Email, follow-up",
    "call_script": "Cold call script",
    "linkedin_note": "LinkedIn connection note",
    "linkedin_message": "LinkedIn message",
}
OUTREACH_FOLDER = "outreach"
DRAFT_FILE = "draft.json"
LIMITS_FILE = "outreach-limits.json"
MAX_FILE_NAME = 60

# Each sales tool writes these differently, so a rewrite has to copy them exactly.
PLACEHOLDER = re.compile(
    r"\{\{\{.+?\}\}\}"  # {{{Recipient.FirstName}}}
    r"|\{\{.+?\}\}"  # {{first_name}} and {{first_name|there}}
    r"|\{!.+?\}"  # {!Contact.FirstName}
    r"|\$\{.+?\}"  # ${Leads.First Name}
    r"|\{[A-Za-z_][\w. ]*\}"  # {first_name}
    r"|\[\[.+?\]\]"  # [[first name]]
    r"|\[[^\[\]\n]{1,100}\]"  # [Company]
    r"|<<.+?>>"  # <<First Name>>
    r"|\*\|.+?\|\*"  # *|FNAME|*
    r"|%%[A-Za-z_][\w.]*%%"  # %%first_name%%
    r"|%[A-Za-z_][\w.]*%"  # %first_name%
)
# These may fill in a line when the email is sent. {{company.address}} is the prospect's own.
OPT_OUT_PLACEHOLDER = re.compile(r"unsub|opt[ _-]?out", re.IGNORECASE)
POSTAL_PLACEHOLDER = re.compile(r"postal|mailing", re.IGNORECASE)
GENERAL_FOOTER_PLACEHOLDER = re.compile(r"signature|footer", re.IGNORECASE)

# Only a lowercase letter or digit ends a sentence, so "P.O. Box" stays in one piece.
SENTENCE_BREAK = re.compile(r"(?<=[a-z0-9)\"'][.!?])\s+|\n+")
SUBJECT_LINE = re.compile(r"^\s*subject:.*$", re.IGNORECASE | re.MULTILINE)
# Each rule asks for wording aimed at the reader, so "Stop getting surprised by stockouts" and
# "unsubscribe rates" stay free to change.
OPT_OUT = re.compile(
    r"\bunsubscrib(?:e|ing)\b(?!\s+(?:numbers?|rates?|requests?|trends?)\b)"
    r"|\bopt(?:ing)?[ -]?out\b(?!\s+of\b)"
    r"|\bopt(?:ing)?[ -]?out of (?:all|any|emails?|future|further|marketing|messages|our|these|this)\b"
    r"|\bstop (?:getting|hearing|receiving)\b[^.!?\n]*\b(?:calls?|emails?|mail|messages?|from (?:me|us))\b"
    r"|\b(?:don['’]?t want|do not want|no longer (?:want|wish)|prefer not|rather not)(?: to)?"
    r" (?:be contacted|get|hear|receive)\b"
    r"|\bremove (?:me|you) from\b[^.!?\n]*\b(?:emails?|lists?|mailing|sequence)\b"
    r"|\bremove me\b|\breply stop\b",
    re.IGNORECASE,
)
# Each rule names this call, so a product that records calls isn't caught.
RECORDING = re.compile(
    r"\b(?:our|the|this|your) (?:call|conversation|line)\b[^.!?\n]*\brecorded\b"
    r"|\bcalls? (?:may|might|will) be\b[^.!?\n]*\brecorded\b"
    r"|\brecord(?:ing)? (?:our|the|this) (?:call|conversation)\b"
    r"|\bconsent to (?:being |the )?record(?:ed|ing)\b",
    re.IGNORECASE,
)
US_STATE = (
    r"(?:A[KLRZ]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI"
    r"|S[CD]|T[NX]|UT|V[AT]|W[AIVY])"
)
# Street words are case-sensitive and must end the address, so "3 stores in one place" and
# "5 Ways To Drive Sales" aren't taken for one.
ADDRESS = re.compile(
    r"(?i:\bp\.?\s?o\.?\s+box\b)"
    r"|\b\d{1,6}\s+(?:[A-Z0-9][\w.'-]*\s+){0,4}"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Highway|Hwy"
    r"|Parkway|Pkwy|Plaza|Place|Pl|Square|Sq|Circle|Cir|Terrace|Ter)\b(?=\s*(?:[,.\n]|$))"
    r"|\b(?:Suite|Ste|Unit|Floor)\s+#?\d+\b"
    rf"|\b{US_STATE}\s+\d{{5}}(?:-\d{{4}})?\b"  # IL 60606
    r"|\b[A-Z]{1,2}\d[A-Z\d]?\s\d[A-Z]{2}\b"  # SW1A 1AA
)
PROTECTED = (OPT_OUT, RECORDING, ADDRESS)

# narrative_check's number finder misses "10x" and "$2M", the claims most likely to be made up.
NUMBER = re.compile(r"(?:(?<![A-Za-z0-9._])|(?<=\b[xX]))\d[\d,]*(?:\.\d+)?")
# Only time the rep asks for is exempt. "Saves 40 hours a week" is a claim, and needs a source.
MEETING_WORD = r"(?:call|chat|conversation|demo|intro|introduction|meeting|session|walkthrough)"
ASK_WORD = r"(?:borrow|for|get|give me|got|grab|have|spare|take|worth)"
MEETING_TIME = re.compile(
    rf"\b\d{{1,3}}[- ]?(?:min(?:ute)?s?|hours?|hrs?)[- ]{MEETING_WORD}\b"
    rf"|\b{ASK_WORD}\s+(?:about\s+|just\s+|only\s+)?\d{{1,2}}[- ]?(?:min(?:ute)?s?|sec(?:ond)?s?)\b"
    r"|\b\d{1,2}:\d{2}(?:\s?(?:am|pm))?\b"
    r"|\b\d{1,2}\s?(?:am|pm)\b",
    re.IGNORECASE,
)
QUANTITY_WORD = re.compile(
    r"\b(?:doubl|tripl|quadrupl)\w*"
    r"|\b(?:two|three|four|five|six|seven|eight|nine|ten|hundred)fold\b"
    r"|\b(?:billions?|dozens|hundreds|millions?|thousands|zero)\b",
    re.IGNORECASE,
)

FAKE_REPLY = re.compile(r"\s*(?:re|fwd?)\s*:", re.IGNORECASE)
PAST_CONTACT = (
    r"(?:\w+ )?(?:call|chat|conversation|discussion|email|meeting|message|note|voicemail)"
)
FALSE_HISTORY = re.compile(
    r"\bas (?:i |we )?(?:discussed|mentioned|spoke|talked)\b"
    rf"|\bper (?:my|our) {PAST_CONTACT}\b"
    rf"|\bfollowing up (?:after|from|on) (?:my|our|the) {PAST_CONTACT}\b"
    rf"|\b(?:based on|following) our {PAST_CONTACT}\b"
    r"|\b(?:good|great|lovely|nice) (?:chatting|meeting|speaking|talking)\b"
    r"|\b(?:good|great|lovely|nice) to (?:chat|speak|talk)\b"
    r"|\benjoyed (?:chatting|meeting|our|speaking|talking)\b"
    r"|\bwe (?:last )?(?:met|spoke|talked)\b",
    re.IGNORECASE,
)

NAME = re.compile(r"[A-Z][\w'&-]*(?:\s+[A-Z][\w'&-]*)*")
NAME_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")
WORD = re.compile(r"[A-Za-z0-9][\w'&-]*")
ALWAYS_CAPITALIZED = re.compile(
    r"i(?:'m|'d|'ll|'ve)?|(?:mon|tues|wednes|thurs|fri|satur|sun)day"
    r"|january|february|march|april|may|june|july|august|september|october|november|december"
)

FIXES = {
    "placeholder_changed": "Use the original's placeholders exactly as written, and add no others.",
    "protected_text_changed": "Put this back word for word, because it may be a legal requirement.",
    "new_number": "Remove this number, or ask the manager to add it as a proof point.",
    "too_long": "Shorten the message to fit the limit.",
    "fake_reply": "Remove this from the subject, because the prospect has never had an email.",
    "false_history": "Remove this, because there hasn't been a past conversation.",
    "contact_detail": "Remove this, because it could belong to a prospect.",
    "statistic": "Say this in words, without a number.",
    "pronoun": 'Use "they" or a name.',
}
CONFIRM_MESSAGES = {
    "new_name": '"{text}" is new in this version. Is that accurate?',
    "number_word": '"{text}" is new in this version. Is that accurate?',
    "new_placeholder": "{text} is new. Does it match how your sales tool writes it?",
    "contact_detail": "{text} is in this message. Is it yours, and not a prospect's?",
    "no_opt_out": "I can't see an opt-out line. Does your sales tool add one?",
    "no_postal_address": "I can't see a postal address. Does your sales tool add one?",
    "assumed_footer": "I'm assuming {text} adds your opt-out line and postal address. Is that right?",
}


def resolve_limits(team: dict) -> dict:
    """Merge a team's message limits over the starting limits."""
    base = json.loads((ASSETS_DIR / LIMITS_FILE).read_text(encoding="utf-8"))
    overrides = team.get("outreach_limits", {})
    unknown = sorted(set(overrides) - set(base))
    if unknown:
        raise ValueError(f"Unknown outreach limits in the team profile: {', '.join(unknown)}")
    return {
        kind: {**entry, "source": "team", **overrides[kind]} if kind in overrides else dict(entry)
        for kind, entry in base.items()
    }


def find_placeholders(text: str) -> set[str]:
    """Return every placeholder a sales tool would fill in."""
    return set(PLACEHOLDER.findall(text))


def _sentences(text: str) -> list[str]:
    pieces = (" ".join(piece.split()) for piece in SENTENCE_BREAK.split(text))
    return [piece for piece in pieces if piece]


def protected_text(original: str) -> list[str]:
    """Return each sentence or line that holds an opt-out, recording notice, or address.

    A pasted subject line is left out, because a subject is never a legal line.
    """
    pieces = _sentences(SUBJECT_LINE.sub("", original))
    return [item for item in pieces if any(rule.search(item) for rule in PROTECTED)]


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _plain_word(word: str) -> str:
    return word.lower().removesuffix("'s")


def _words(text: str) -> set[str]:
    return {_plain_word(word) for word in WORD.findall(text)}


def _numbers(text: str, placeholders: Iterable[str] = ()) -> set[str]:
    """Return the numbers in the text, leaving out the given placeholders and asks for time."""
    spare = text
    for token in placeholders:
        spare = spare.replace(token, " ")
    return {item.replace(",", "") for item in NUMBER.findall(MEETING_TIME.sub(" ", spare))}


def _contact_details(text: str) -> list[str]:
    return _unique(EMAIL_PATTERN.findall(text) + PHONE_PATTERN.findall(text))


def _new_names(message: str, known: set[str]) -> list[str]:
    """Return capitalized names that appear in no approved source, past the start of a sentence."""
    found = []
    # A stand-in word, so a sentence that ends in a placeholder still ends.
    for sentence in NAME_SENTENCE_BREAK.split(PLACEHOLDER.sub("x", message)):
        for match in NAME.finditer(sentence.strip()):
            words = match.group().split()
            checked = words[1:] if match.start() == 0 else words
            plain = [_plain_word(word) for word in checked]
            if any(word not in known and not ALWAYS_CAPITALIZED.fullmatch(word) for word in plain):
                found.append(" ".join(checked))
    return _unique(found)


def _new_number_words(message: str, known: set[str]) -> list[str]:
    spare = PLACEHOLDER.sub(" ", message)
    spoken = extract_number_words(spare) + QUANTITY_WORD.findall(spare)
    return _unique(word.lower() for word in spoken if _plain_word(word) not in known)


def _validated(draft: dict) -> dict:
    """Return a complete copy of the draft, or explain what's wrong with it.

    Every problem raises ValueError, because the command line reports that in plain words.
    """
    if draft.get("kind") not in KINDS:
        raise ValueError(f"The draft's kind must be one of: {', '.join(KINDS)}.")
    for field in ("name", "original", "body"):
        value = draft.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"The draft's {field} can't be blank.")
    for field in ("subject", "footer"):
        if not isinstance(draft.get(field, ""), str):
            raise ValueError(f"The draft's {field} must be text.")  # noqa: TRY004
    changes = draft.get("changes", [])
    if not isinstance(changes, list) or not all(isinstance(item, str) for item in changes):
        raise ValueError("The draft's changes must be a list of short sentences.")
    subject = draft.get("subject", "") if draft["kind"] in EMAIL_KINDS else ""
    return {"footer": "", **draft, "subject": subject, "changes": changes}


def _message(draft: dict) -> str:
    return "\n".join(part for part in (draft["subject"], draft["body"], draft["footer"]) if part)


def _approved_text(draft: dict, team: dict) -> str:
    fields = (team.get(key) for key in ("company", "product", "ideal_customer"))
    known = [field for field in fields if isinstance(field, str)]
    return "\n".join((draft["original"], *known, *team.get("proof_points", [])))


def _measure(body: str, unit: str) -> int:
    return len(body.strip()) if unit == "characters" else len(body.split())


def _problem(rule: str, text: str) -> dict:
    return {"rule": rule, "text": text, "fix": FIXES[rule]}


def _confirm(rule: str, text: str = "") -> dict:
    item = {"rule": rule, "message": CONFIRM_MESSAGES[rule].format(text=text)}
    return {**item, "text": text} if text else item


def _placeholder_problems(draft: dict, message: str) -> list[dict]:
    before = find_placeholders(draft["original"])
    if not before:
        return []
    changed = before ^ find_placeholders(message)
    return [_problem("placeholder_changed", token) for token in sorted(changed)]


def _first_contact_problems(draft: dict) -> list[dict]:
    if draft["kind"] not in FIRST_CONTACT_KINDS:
        return []
    fake = [draft["subject"]] if FAKE_REPLY.match(draft["subject"]) else []
    history = _unique(FALSE_HISTORY.findall(_message(draft)))
    return [_problem("fake_reply", text) for text in fake] + [
        _problem("false_history", text) for text in history
    ]


def _problems(draft: dict, approved: str, limit: dict, length: int) -> list[dict]:
    message = _message(draft)
    flat = " ".join(message.split())
    problems = _placeholder_problems(draft, message)
    problems += [
        _problem("protected_text_changed", item)
        for item in protected_text(draft["original"])
        if item not in flat
    ]
    kept = find_placeholders(draft["original"])
    new_numbers = _numbers(message, kept) - _numbers(approved)
    problems += [_problem("new_number", token) for token in sorted(new_numbers)]
    if length > limit["value"]:
        size = f"{length} {limit['unit']}, limit {limit['value']}"
        problems.append(_problem("too_long", size))
    problems += _first_contact_problems(draft)
    labels = "\n".join((draft["name"], *draft["changes"]))
    problems += [_problem("contact_detail", item) for item in _contact_details(labels)]
    return problems + [
        _problem(item["kind"], item["number"])
        for item in check_narrative({"changes": draft["changes"]})
    ]


def _footer_confirmations(message: str) -> list[dict]:
    tokens = sorted(find_placeholders(message))
    needed = (
        ("no_opt_out", OPT_OUT, OPT_OUT_PLACEHOLDER),
        ("no_postal_address", ADDRESS, POSTAL_PLACEHOLDER),
    )
    missing = [
        rule
        for rule, visible, supplied in needed
        if not visible.search(message) and not any(supplied.search(item) for item in tokens)
    ]
    general = [item for item in tokens if GENERAL_FOOTER_PLACEHOLDER.search(item)]
    if missing and general:
        return [_confirm("assumed_footer", general[0])]
    return [_confirm(rule) for rule in missing]


def _confirmations(draft: dict, approved: str) -> list[dict]:
    message = _message(draft)
    known = _words(approved)
    items = [_confirm("new_name", name) for name in _new_names(message, known)]
    items += [_confirm("number_word", word) for word in _new_number_words(message, known)]
    if not find_placeholders(draft["original"]):
        tokens = sorted(find_placeholders(message))
        items += [_confirm("new_placeholder", token) for token in tokens]
    # A signature in the footer is normal. In the message itself, it may be a prospect's.
    typed = PLACEHOLDER.sub(" ", f"{draft['subject']}\n{draft['body']}")
    items += [_confirm("contact_detail", item) for item in _contact_details(typed)]
    if draft["kind"] in EMAIL_KINDS:
        items += _footer_confirmations(message)
    return items


def check_draft(draft: dict, team: dict) -> dict:
    """Return what must be fixed, what the manager must confirm, and the message's length."""
    clean = _validated(draft)
    limit = resolve_limits(team)[clean["kind"]]
    length = _measure(clean["body"], limit["unit"])
    approved = _approved_text(clean, team)
    return {
        "problems": _problems(clean, approved, limit, length),
        "to_confirm": _confirmations(clean, approved),
        "length": {
            "value": length,
            "limit": limit["value"],
            "unit": limit["unit"],
            "source": limit["source"],
        },
    }


def load_draft(path: Path) -> dict:
    """Read Claude's draft file, explaining any problem in plain words."""
    problem = f"The draft at {path} isn't a valid draft. Write it again."
    try:
        draft = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"The draft at {path} couldn't be read. Write it again.") from error
    except ValueError as error:
        raise ValueError(problem) from error
    if not isinstance(draft, dict):
        raise ValueError(problem)  # noqa: TRY004
    return draft


def render_saved(draft: dict, confirm: list[dict], day: date) -> str:
    """Return the text file a manager copies from. The original is left out on purpose."""
    clean = _validated(draft)
    title = KIND_TITLES[clean["kind"]]
    lines = [title, f"Name: {clean['name'].strip()}", f"Saved: {day.isoformat()}", ""]
    if clean["subject"].strip():
        lines += [f"Subject: {clean['subject'].strip()}", ""]
    lines += [clean["body"].strip(), ""]
    if clean["footer"].strip():
        lines += [clean["footer"].strip(), ""]
    if clean["changes"]:
        lines += ["Why it changed", *[f"- {item}" for item in clean["changes"]], ""]
    if confirm:
        lines += ["Please confirm", *[f"- {item['message']}" for item in confirm], ""]
    return "\n".join(lines).rstrip() + "\n"


def save_rewrite(workspace: Path, draft: dict, confirm: list[dict], day: date) -> Path:
    """Save the new version. The same name on the same day replaces the earlier file."""
    folder = workspace / OUTREACH_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    slug = rep_slug(draft["name"])[:MAX_FILE_NAME].rstrip("-")
    path = folder / f"{day.isoformat()}-{slug}.txt"
    path.write_text(render_saved(draft, confirm, day), encoding="utf-8")
    return path


def draft_path(workspace: Path) -> Path:
    """Return where Claude keeps a draft while it's being checked."""
    return workspace / OUTREACH_FOLDER / DRAFT_FILE


def discard_draft(workspace: Path) -> bool:
    """Delete a draft that won't be finished, because it may hold a pasted email."""
    path = draft_path(workspace)
    if not path.exists():
        return False
    path.unlink()
    return True
