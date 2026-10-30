"""Shared test helpers."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import sdr

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_PROFILE = {
    "company": "Example Co",
    "product": "Example product",
    "ideal_customer": "Example buyers",
    "channels": ["call", "email", "linkedin"],
    "reps": [
        {"name": "Ava Reyes", "start_date": "2025-01-06", "aliases": ["A. Reyes"], "active": True},
        {"name": "Ben Carter", "start_date": "2025-03-03", "aliases": [], "active": True},
    ],
    "ignored_names": ["Morgan Lee"],
    "targets": {},
}


# Hand-worked fixture: one rep with 20 working days from 2026-W41 to 2026-W44.
WINDOW_COUNTS = {
    "dials": 880,
    "connected": 48,
    "emails": 820,
    "replies": 28,
    "bounces": 10,
    "li_requests": 190,
    "li_accepted": 57,
    "li_messages": 190,
    "li_replies": 19,
    "li_other": 0,
}


def meeting(
    status: str,
    accepted: str = "",
    booked: str = "2026-10-13",
    due: str = "2026-10-15",
    rep: str = "Ava Reyes",
) -> dict:
    """Build one stored meeting row."""
    return {
        "rep": rep,
        "booked_date": booked,
        "due_date": due,
        "status": status,
        "accepted": accepted,
    }


def window_meetings() -> list[dict]:
    """Return the fixture's 12 meetings: 9 held (6 yes, 3 no), 2 no-show, 1 cancelled."""
    return (
        [meeting("held", "yes") for _ in range(6)]
        + [meeting("held", "no") for _ in range(3)]
        + [meeting("no_show", "pending") for _ in range(2)]
        + [meeting("cancelled", "pending")]
    )


def run_cli(*args: str) -> tuple[int, dict]:
    """Run the command line in-process and return its exit code and JSON output."""
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
        code = sdr.main(list(args))
    return code, json.loads(stdout.getvalue())


def make_workspace(folder: Path, **profile_changes: object) -> Path:
    """Create a minimal workspace with a team profile and a mappings folder."""
    workspace = folder / "workspace"
    (workspace / "mappings").mkdir(parents=True, exist_ok=True)
    profile = {**DEFAULT_PROFILE, **profile_changes}
    (workspace / "team-profile.json").write_text(json.dumps(profile), encoding="utf-8")
    return workspace


def activity_row(
    day: str,
    rep: str = "Ava Reyes",
    channel: str = "call",
    granularity: str = "day",
    **counts: int,
) -> dict:
    """Build one stored activity row, with every unnamed count set to zero."""
    from sdrlib.history import ACTIVITY_COUNTS

    row = {"date": day, "rep": rep, "channel": channel, "granularity": granularity}
    row.update({name: counts.get(name, 0) for name in ACTIVITY_COUNTS})
    return row
