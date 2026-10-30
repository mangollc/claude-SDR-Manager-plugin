"""Pure calculations for rep metrics and window targets."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Sequence

from .history import ACTIVITY_COUNTS, week_bounds
from .targets import (
    WORKING_DAYS_PER_WEEK,
    meetings_per_working_day,
    month_in_role,
    ramp_multiplier,
)

DUE_STATUSES = ("held", "no_show", "cancelled")
NO_TIME_OFF = {"team_days_off": 0, "rep_days_off": {}}


def _ratio(top: int, bottom: int) -> float | None:
    return top / bottom if bottom else None


def sum_counts(rows: Iterable[dict]) -> dict:
    """Add stored rows together into one set of counts."""
    totals = dict.fromkeys(ACTIVITY_COUNTS, 0)
    for row in rows:
        for name in ACTIVITY_COUNTS:
            totals[name] += row[name]
    return totals


def touches(counts: dict) -> int:
    """Return all outreach touches across channels."""
    return (
        counts["dials"]
        + counts["emails"]
        + counts["li_requests"]
        + counts["li_messages"]
        + counts["li_other"]
    )


def conversations(counts: dict) -> int:
    """Return connected calls plus replies across channels."""
    return counts["connected"] + counts["replies"] + counts["li_replies"]


def calculate_rates(counts: dict) -> dict:
    """Return each response rate, or None where nothing was sent."""
    return {
        "connect_rate": _ratio(counts["connected"], counts["dials"]),
        "email_reply_rate": _ratio(counts["replies"], counts["emails"]),
        "bounce_rate": _ratio(counts["bounces"], counts["emails"]),
        "li_accept_rate": _ratio(counts["li_accepted"], counts["li_requests"]),
        "li_reply_rate": _ratio(counts["li_replies"], counts["li_messages"]),
    }


def meeting_rate(booked: int, conversation_count: int) -> float | None:
    """Return meetings booked per conversation."""
    return _ratio(booked, conversation_count)


def _within(day: str, start: date, end: date) -> bool:
    return start <= date.fromisoformat(day) <= end


def meeting_summary(meetings: Iterable[dict], start: date, end: date) -> dict:
    """Count a window's meetings. Booked uses the booked date, the rest use the due date."""
    rows = list(meetings)
    due = [
        row
        for row in rows
        if row["status"] in DUE_STATUSES and _within(row["due_date"], start, end)
    ]
    held = [row for row in due if row["status"] == "held"]
    yes = sum(1 for row in held if row["accepted"] == "yes")
    no = sum(1 for row in held if row["accepted"] == "no")
    return {
        "booked": sum(1 for row in rows if _within(row["booked_date"], start, end)),
        "due": len(due),
        "held": len(held),
        "no_show": sum(1 for row in due if row["status"] == "no_show"),
        "cancelled": sum(1 for row in due if row["status"] == "cancelled"),
        "accepted_yes": yes,
        "accepted_no": no,
        "pending": sum(1 for row in held if row["accepted"] == "pending"),
        "show_rate": _ratio(len(held), len(due)),
        "acceptance_rate": _ratio(yes, yes + no),
    }


def working_days(week: str, time_off: dict, rep: str, last_date: date | None = None) -> int:
    """Return a rep's working days in a week, stopping at the last date with data."""
    monday, _ = week_bounds(week)
    friday = monday + timedelta(days=WORKING_DAYS_PER_WEEK - 1)
    last_day = min(friday, last_date) if last_date else friday
    weekdays = max((last_day - monday).days + 1, 0)
    days_off = time_off["team_days_off"] + time_off["rep_days_off"].get(rep, 0)
    return max(weekdays - days_off, 0)


def days_active(rows: Iterable[dict]) -> int | None:
    """Return working days with at least one touch. Weekly data can't answer this."""
    stored = list(rows)
    if any(row["granularity"] == "week" for row in stored):
        return None
    days = {date.fromisoformat(row["date"]) for row in stored}
    return sum(1 for day in days if day.weekday() < WORKING_DAYS_PER_WEEK)


def touch_target_per_day(targets: dict, channels: Sequence[str]) -> float:
    """Return the daily touch target across the channels in use."""
    per_channel = {
        "call": "dials_per_day",
        "email": "emails_per_day",
        "linkedin": "linkedin_touches_per_day",
    }
    return sum(targets[per_channel[channel]]["value"] for channel in channels)


def _week_multiplier(start_date: str | None, week: str, ramp: dict) -> float:
    if not start_date:
        return 1.0
    _, sunday = week_bounds(week)
    return ramp_multiplier(month_in_role(date.fromisoformat(start_date), sunday), ramp)


def window_targets(
    rep: dict,
    weeks: Sequence[str],
    time_off: dict,
    targets: dict,
    channels: Sequence[str],
    last_date: date | None,
    ramp: dict,
) -> dict:
    """Return a rep's count targets for a window. `time_off` is keyed by week."""
    total_days = 0
    weighted_days = 0.0
    for week in weeks:
        week_last_date = last_date if week == weeks[-1] else None
        days = working_days(week, time_off.get(week, NO_TIME_OFF), rep["name"], week_last_date)
        total_days += days
        weighted_days += days * _week_multiplier(rep.get("start_date"), week, ramp)
    return {
        "working_days": total_days,
        "touches": touch_target_per_day(targets, channels) * weighted_days,
        "meetings_held": meetings_per_working_day(targets) * weighted_days,
    }
