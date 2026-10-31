"""Regenerate sample-data/. Every name, number, and company in it is made up.

Run from the repository root:

    python3 tests/make_sample_data.py
"""

from __future__ import annotations

import csv
import io
import json
import random
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED = 44
FIRST_MONDAY = date(2026, 9, 28)  # 2026-W40
WEEKS_OF_DATA = 5
WORKING_DAYS = 5
SCHEDULED_DUE = date(2026, 11, 5)  # The Thursday after the four-week window.
CALL_MISSES = ("No Answer", "Voicemail", "Busy")
MANAGER = "Morgan Lee"
MANAGER_DIALS_PER_WEEK = 5

SAMPLE_PROFILE = {
    "company": "Example Analytics",
    "product": "Forecasting software that helps retailers plan inventory.",
    "ideal_customer": "Operations leaders at retailers with 50 to 500 stores.",
    "proof_points": [
        "Northwind Stores cut stockouts by 18% in its first year.",
        "Harbor Home Goods replaced its planning spreadsheets in under 90 days.",
    ],
    "channels": ["call", "email", "linkedin"],
    "reps": [
        {"name": "Ava Reyes", "start_date": "2025-02-03", "aliases": [], "active": True},
        {
            "name": "Ben Carter",
            "start_date": "2025-06-16",
            "aliases": ["B. Carter"],
            "active": True,
        },
        {"name": "Chloe Nguyen", "start_date": "2025-04-07", "aliases": [], "active": True},
        {"name": "Diego Marin", "start_date": "2025-09-01", "aliases": [], "active": True},
        {"name": "Nina Patel", "start_date": "2026-10-12", "aliases": [], "active": True},
        {"name": "Priya Shah", "start_date": "2025-03-10", "aliases": [], "active": True},
        {"name": "Sam Okafor", "start_date": "2025-08-04", "aliases": [], "active": True},
    ],
    "ignored_names": [MANAGER],
    "targets": {},
}

# Weekly activity for each rep. Each rep shows one problem, so every status can be tried.
ACTIVITY = {
    "Ava Reyes": dict(
        dials=230,
        connected=16,
        emails=210,
        replies=11,
        bounces=2,
        requests=50,
        accepted=15,
        messages=50,
        li_replies=6,
    ),
    "Ben Carter": dict(
        dials=100,
        connected=6,
        emails=100,
        replies=4,
        bounces=1,
        requests=20,
        accepted=6,
        messages=20,
        li_replies=2,
    ),
    "Chloe Nguyen": dict(
        dials=240,
        connected=7,
        emails=230,
        replies=3,
        bounces=7,
        requests=50,
        accepted=15,
        messages=50,
        li_replies=6,
    ),
    "Diego Marin": dict(
        dials=225,
        connected=16,
        emails=210,
        replies=10,
        bounces=2,
        requests=50,
        accepted=15,
        messages=50,
        li_replies=6,
    ),
    "Nina Patel": dict(
        dials=120,
        connected=5,
        emails=100,
        replies=3,
        bounces=1,
        requests=20,
        accepted=5,
        messages=20,
        li_replies=2,
    ),
    "Priya Shah": dict(
        dials=225,
        connected=16,
        emails=210,
        replies=10,
        bounces=2,
        requests=50,
        accepted=15,
        messages=50,
        li_replies=6,
    ),
    "Sam Okafor": dict(
        dials=225,
        connected=16,
        emails=210,
        replies=10,
        bounces=2,
        requests=50,
        accepted=15,
        messages=50,
        li_replies=6,
    ),
}
FIRST_ACTIVE_WEEK = {"Nina Patel": 2}  # Nina started in the third week of data.
NAME_IN_SEQUENCER = {"Ben Carter": "B. Carter"}

# Four-week meeting totals: held, no-show, cancelled, scheduled, and AE decisions on held.
MEETINGS = {
    "Ava Reyes": dict(held=13, no_show=2, cancelled=0, scheduled=2, yes=9, no=3),
    "Ben Carter": dict(held=4, no_show=1, cancelled=0, scheduled=1, yes=3, no=1),
    "Chloe Nguyen": dict(held=6, no_show=1, cancelled=0, scheduled=1, yes=4, no=2),
    "Diego Marin": dict(held=5, no_show=1, cancelled=0, scheduled=0, yes=3, no=1),
    "Nina Patel": dict(held=1, no_show=0, cancelled=0, scheduled=1, yes=0, no=0),
    "Priya Shah": dict(held=7, no_show=7, cancelled=1, scheduled=1, yes=5, no=2),
    "Sam Okafor": dict(held=13, no_show=2, cancelled=0, scheduled=1, yes=4, no=9),
}


class _Contacts:
    """Hands out made-up prospects, using reserved phone numbers and example.com."""

    def __init__(self) -> None:
        self.next_number = 0

    def next(self) -> tuple[str, str, str, str]:
        self.next_number += 1
        number = self.next_number
        return (
            f"Contact {number:05d}",
            f"contact{number:05d}@example.com",
            f"(415) 555-01{number % 100:02d}",
            f"Example Co {number % 400}",
        )


def _week_monday(week_index: int) -> date:
    return FIRST_MONDAY + timedelta(weeks=week_index)


def _touch_days(week_index: int, total: int) -> list[date]:
    """Spread a week's touches evenly across Monday to Friday."""
    monday = _week_monday(week_index)
    return [monday + timedelta(days=touch % WORKING_DAYS) for touch in range(total)]


def _active_weeks(rep: str) -> range:
    return range(FIRST_ACTIVE_WEEK.get(rep, 0), WEEKS_OF_DATA)


def _to_csv(rows: list[list[object]], delimiter: str = ",") -> str:
    buffer = io.StringIO()
    csv.writer(buffer, delimiter=delimiter, lineterminator="\n").writerows(rows)
    return buffer.getvalue()


def _call_rows(rng: random.Random, contacts: _Contacts) -> list[list[object]]:
    rows = []
    for rep, numbers in ACTIVITY.items():
        for week in _active_weeks(rep):
            connected = set(rng.sample(range(numbers["dials"]), numbers["connected"]))
            for touch, day in enumerate(_touch_days(week, numbers["dials"])):
                name, _, phone, company = contacts.next()
                result = "Connected" if touch in connected else rng.choice(CALL_MISSES)
                rows.append([f"{day:%m/%d/%Y}", rep, result, name, phone, company])
    for week in range(WEEKS_OF_DATA):
        for day in _touch_days(week, MANAGER_DIALS_PER_WEEK):
            name, _, phone, company = contacts.next()
            rows.append([f"{day:%m/%d/%Y}", MANAGER, "Connected", name, phone, company])
    return sorted(rows, key=lambda row: (row[0][6:], row[0][:5], row[1]))


def _email_rows(rng: random.Random, contacts: _Contacts) -> list[list[object]]:
    rows = []
    for rep, numbers in ACTIVITY.items():
        owner = NAME_IN_SEQUENCER.get(rep, rep)
        for week in _active_weeks(rep):
            touches = range(numbers["emails"])
            flagged = rng.sample(touches, numbers["replies"] + numbers["bounces"])
            replied = set(flagged[: numbers["replies"]])
            bounced = set(flagged[numbers["replies"] :])
            for touch, day in enumerate(_touch_days(week, numbers["emails"])):
                _, email, _, _ = contacts.next()
                sent = f"{day:%Y-%m-%d} {rng.randint(8, 16):02d}:{rng.randint(0, 59):02d}"
                rows.append(
                    [
                        sent,
                        owner,
                        email,
                        touch % 4 + 1,
                        "Yes" if touch in bounced else "No",
                        "Yes" if touch in replied else "No",
                    ]
                )
    return sorted(rows)


def _linkedin_rows(rng: random.Random, contacts: _Contacts) -> list[list[object]]:
    rows = []
    for rep, numbers in ACTIVITY.items():
        for week in _active_weeks(rep):
            accepted = set(rng.sample(range(numbers["requests"]), numbers["accepted"]))
            for touch, day in enumerate(_touch_days(week, numbers["requests"])):
                name, _, _, _ = contacts.next()
                result = "Accepted" if touch in accepted else "Pending"
                rows.append([f"{day:%Y-%m-%d}", rep, "Connection Request", result, name])
            replied = set(rng.sample(range(numbers["messages"]), numbers["li_replies"]))
            for touch, day in enumerate(_touch_days(week, numbers["messages"])):
                name, _, _, _ = contacts.next()
                result = "Replied" if touch in replied else "No Reply"
                rows.append([f"{day:%Y-%m-%d}", rep, "Message", result, name])
    return sorted(rows)


def _meeting_statuses(plan: dict) -> list[tuple[str, str]]:
    """Return (status, AE decision) for each meeting. Held meetings can be undecided."""
    undecided = plan["held"] - plan["yes"] - plan["no"]
    return (
        [("Completed", "Accepted")] * plan["yes"]
        + [("Completed", "Rejected")] * plan["no"]
        + [("Completed", "")] * undecided
        + [("No Show", "")] * plan["no_show"]
        + [("Cancelled", "")] * plan["cancelled"]
        + [("Scheduled", "")] * plan["scheduled"]
    )


def _meeting_rows(rng: random.Random, contacts: _Contacts) -> list[list[object]]:
    rows = []
    for rep, plan in MEETINGS.items():
        weeks = [week for week in _active_weeks(rep) if week > 0]
        statuses = _meeting_statuses(plan)
        rng.shuffle(statuses)
        for index, (status, decision) in enumerate(statuses):
            monday = _week_monday(weeks[index % len(weeks)])
            booked = monday + timedelta(days=1)
            due = SCHEDULED_DUE if status == "Scheduled" else monday + timedelta(days=3)
            _, _, _, company = contacts.next()
            rows.append([rep, f"{booked:%m/%d/%Y}", f"{due:%m/%d/%Y}", status, decision, company])
    rng.shuffle(rows)
    return rows


def build_exports() -> dict[str, str]:
    """Return each sample export's name and text. The same seed gives the same files."""
    rng = random.Random(SEED)
    contacts = _Contacts()
    calls = _call_rows(rng, contacts)
    call_report = [["Call Activity Report"], ["Prepared for the sales team"]]
    call_report.append(
        ["Activity Date", "Assigned To", "Call Result", "Contact Name", "Contact Phone", "Company"]
    )
    call_report += calls
    call_report.append([f"Total rows: {len(calls)}"])
    emails = [["Sent At", "Owner", "Recipient Email", "Step", "Bounced", "Replied"]]
    emails += _email_rows(rng, contacts)
    linkedin = [["Date", "Rep", "Action", "Result", "Prospect"]]
    linkedin += _linkedin_rows(rng, contacts)
    meetings = [
        ["Owner Name", "Date Booked", "Meeting Date", "Meeting Status", "AE Decision", "Account"]
    ]
    meetings += _meeting_rows(rng, contacts)
    return {
        "crm-calls.csv": _to_csv(call_report),
        "sequencer-emails.csv": _to_csv(emails, delimiter=";"),
        "linkedin-activity.csv": _to_csv(linkedin),
        "crm-meetings.csv": _to_csv(meetings),
    }


def main() -> None:
    folder = REPO_ROOT / "sample-data" / "exports"
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in build_exports().items():
        (folder / name).write_text(text, encoding="utf-8")
    profile = json.dumps(SAMPLE_PROFILE, indent=2) + "\n"
    (REPO_ROOT / "sample-data" / "team-profile.json").write_text(profile, encoding="utf-8")


if __name__ == "__main__":
    main()
