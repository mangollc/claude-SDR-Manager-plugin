"""Assemble a week's metrics, statuses, and coaching focus, then save them."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from . import focus, history, metrics
from .profile import VALID_CHANNELS, active_reps, load_profile, rep_slug
from .reports import focus_text
from .targets import WORKING_DAYS_PER_WEEK, load_defaults, month_in_role, resolve_targets

SCHEMA_VERSION = 1
WINDOW_WEEKS = 4


@dataclass(frozen=True)
class _Context:
    """Everything shared by the calculations for one week's scorecard."""

    week: str
    weeks: tuple[str, ...]
    targets: dict
    settings: dict
    channels: tuple[str, ...]
    time_off: dict
    partial_last_date: date | None


def _rows_in_week(rows: Sequence[dict], week: str) -> list[dict]:
    monday, sunday = history.week_bounds(week)
    return [row for row in rows if monday <= date.fromisoformat(row["date"]) <= sunday]


def _period(rows: Sequence[dict], meetings: list[dict] | None, start: date, end: date) -> dict:
    """Return the counts, rates, and meetings for one stretch of time."""
    counts = metrics.sum_counts(rows)
    summary = None if meetings is None else metrics.meeting_summary(meetings, start, end)
    talked = metrics.conversations(counts)
    rate = metrics.meeting_rate(summary["booked"], talked) if summary else None
    return {
        "counts": counts,
        "touches": metrics.touches(counts),
        "conversations": talked,
        "rates": {**metrics.calculate_rates(counts), "meeting_rate": rate},
        "meetings": summary,
        "days_active": metrics.days_active(rows),
    }


def _trend(rows: Sequence[dict], meetings: list[dict] | None, weeks: Sequence[str]) -> dict:
    periods = [
        _period(_rows_in_week(rows, week), meetings, *history.week_bounds(week)) for week in weeks
    ]
    return {
        "weeks": list(weeks),
        "touches": [period["touches"] for period in periods],
        "connect_rate": [period["rates"]["connect_rate"] for period in periods],
        "email_reply_rate": [period["rates"]["email_reply_rate"] for period in periods],
        "meetings_booked": [
            period["meetings"]["booked"] if period["meetings"] else None for period in periods
        ],
        "meetings_held": [
            period["meetings"]["held"] if period["meetings"] else None for period in periods
        ],
    }


def _month_in_role(rep: dict, week: str) -> int | None:
    start = rep.get("start_date")
    if not start:
        return None
    return month_in_role(date.fromisoformat(start), history.week_bounds(week)[1])


def _rep_window(
    rep: dict, rows: Sequence[dict], meetings: list[dict] | None, context: _Context
) -> dict:
    """Return a rep's four-week numbers and the targets they're measured against."""
    window_start, _ = history.week_bounds(context.weeks[0])
    _, week_end = history.week_bounds(context.week)
    targets_for_window = metrics.window_targets(
        rep,
        context.weeks,
        context.time_off,
        context.targets,
        context.channels,
        context.partial_last_date,
        context.settings["ramp"],
    )
    return {
        **_period(rows, meetings, window_start, week_end),
        "working_days": targets_for_window["working_days"],
        "targets": {
            "touches": targets_for_window["touches"],
            "meetings_held": targets_for_window["meetings_held"],
        },
    }


def _rep_this_week(
    rep: dict, rows: Sequence[dict], meetings: list[dict] | None, context: _Context
) -> dict:
    """Return a rep's numbers for the selected week."""
    week_start, week_end = history.week_bounds(context.week)
    days = metrics.working_days(
        context.week, context.time_off[context.week], rep["name"], context.partial_last_date
    )
    return {
        **_period(_rows_in_week(rows, context.week), meetings, week_start, week_end),
        "working_days": days,
        "out": days == 0,
    }


def _rep_metrics(
    rep: dict, rows: Sequence[dict], meetings: list[dict] | None, context: _Context
) -> dict:
    name = rep["name"]
    settings = context.settings
    window = _rep_window(rep, rows, meetings, context)
    month = _month_in_role(rep, context.week)
    steps = focus.evaluate_steps(
        window, context.targets, settings["minimums"], settings["near_band"]
    )
    outcome = focus.evaluate_outcome(window, settings["near_band"])
    stretch = focus.stretch_focus(window, context.targets, settings["minimums"])
    decision = focus.choose_status(steps, outcome, month == 1, stretch)
    return {
        "name": name,
        "slug": rep_slug(name),
        "status": decision["status"],
        "month_in_role": month,
        "this_week": _rep_this_week(rep, rows, meetings, context),
        "window": window,
        "steps": steps,
        "outcome": outcome,
        "focus": decision["focus"],
        "trend": _trend(rows, meetings, context.weeks),
        "flags": ["bounce_warning"] if focus.bounce_flag(window, context.targets) else [],
        "notes": (
            []
            if rep.get("start_date")
            else ["This rep has no start date, so they're treated as fully ramped."]
        ),
    }


def _team_summary(
    reps: Sequence[dict],
    rows: Sequence[dict],
    meetings: list[dict] | None,
    start: date,
    end: date,
) -> dict:
    period = _period(rows, meetings, start, end)
    return {
        "totals": period["counts"],
        "touches": period["touches"],
        "conversations": period["conversations"],
        "rates": period["rates"],
        "meetings": period["meetings"],
        "targets": {
            "touches": sum(rep["window"]["targets"]["touches"] for rep in reps),
            "meetings_held": sum(rep["window"]["targets"]["meetings_held"] for rep in reps),
        },
        "status_counts": dict(Counter(rep["status"] for rep in reps)),
        "pattern": focus.team_pattern(reps),
    }


def _team_notes(
    stored_channels: set[str],
    team_channels: Sequence[str],
    channels: Sequence[str],
    meetings: list[dict] | None,
) -> list[str]:
    notes = []
    uncounted = sorted(stored_channels - set(team_channels))
    if uncounted:
        notes.append(
            f"{', '.join(uncounted)} activity is stored but not counted, "
            "because the team profile doesn't list that channel."
        )
    missing = [channel for channel in team_channels if channel not in channels]
    if missing:
        notes.append(
            f"No {', '.join(missing)} data was found, so it's left out of this report's targets."
        )
    if meetings is None:
        notes.append(
            "No meetings export has been imported, so meetings booked, held, and accepted "
            "aren't available."
        )
    return notes


def _partial_last_date(rows: Sequence[dict], week: str, team_days_off: int) -> date | None:
    """Return the last date with daily data if it stops before the team's last working day.

    Team holidays are assumed to end the week, so a Thursday and Friday off isn't missing data.
    """
    daily = [date.fromisoformat(row["date"]) for row in rows if row["granularity"] == "day"]
    if not daily:
        return None
    monday, _ = history.week_bounds(week)
    last_working_day = monday + timedelta(days=WORKING_DAYS_PER_WEEK - 1 - team_days_off)
    return max(daily) if max(daily) < last_working_day else None


def _make_context(
    workspace: Path, team: dict, week: str, weeks: tuple[str, ...], activity: Sequence[dict]
) -> _Context:
    present = {row["channel"] for row in activity}
    channels = tuple(channel for channel in VALID_CHANNELS if channel in present)
    time_off = {item: history.read_time_off(workspace, item) for item in weeks}
    return _Context(
        week=week,
        weeks=weeks,
        targets=resolve_targets({**team, "channels": list(channels)}),
        settings=load_defaults(),
        channels=channels,
        time_off=time_off,
        partial_last_date=_partial_last_date(
            _rows_in_week(activity, week), week, time_off[week]["team_days_off"]
        ),
    )


def _assemble(
    context: _Context,
    reps: list[dict],
    activity: Sequence[dict],
    meetings: list[dict] | None,
    sources: list[dict],
    notes: list[str],
    now: datetime,
) -> dict:
    """Put a finished week's results into the shape every report reads."""
    week_start, week_end = history.week_bounds(context.week)
    window_start, _ = history.week_bounds(context.weeks[0])
    return {
        "schema_version": SCHEMA_VERSION,
        "week": context.week,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "window_start": window_start.isoformat(),
        "window_end": week_end.isoformat(),
        "generated_at": now.isoformat(timespec="seconds"),
        "partial_week": context.partial_last_date is not None,
        "last_activity_date": max(row["date"] for row in _rows_in_week(activity, context.week)),
        "channels_present": list(context.channels),
        "sources": sources,
        "targets": context.targets,
        "minimums": context.settings["minimums"],
        "team": _team_summary(reps, activity, meetings, window_start, week_end),
        "reps": reps,
        "notes": notes,
    }


def _only_rep(rows: list[dict] | None, name: str) -> list[dict] | None:
    return None if rows is None else [row for row in rows if row["rep"] == name]


def build_scorecard(workspace: Path, week: str | None = None, now: datetime | None = None) -> dict:
    """Calculate a week's scorecard and save it to the workspace."""
    team = load_profile(workspace)
    selected = week or history.latest_week(workspace)
    if selected is None:
        raise ValueError("There's no stored activity yet. Import some exports first.")
    weeks = tuple(history.previous_weeks(selected, WINDOW_WEEKS))

    reps = active_reps(team)
    names = {rep["name"] for rep in reps}
    stored = [row for row in history.read_activity(workspace, weeks) if row["rep"] in names]
    activity = [row for row in stored if row["channel"] in team["channels"]]
    if not _rows_in_week(activity, selected):
        raise ValueError(f"There's no activity stored for {selected}.")

    saved_meetings = history.read_latest_meetings(workspace)
    meetings = (
        None if saved_meetings is None else [row for row in saved_meetings if row["rep"] in names]
    )
    context = _make_context(workspace, team, selected, weeks, activity)
    rep_results = [
        _rep_metrics(
            rep, _only_rep(activity, rep["name"]), _only_rep(meetings, rep["name"]), context
        )
        for rep in reps
    ]
    notes = _team_notes(
        {row["channel"] for row in stored}, team["channels"], context.channels, meetings
    )
    scorecard = _assemble(
        context,
        rep_results,
        activity,
        meetings,
        history.read_sources(workspace, selected),
        notes,
        now or datetime.now(),
    )
    history.write_metrics(workspace, selected, scorecard)
    return scorecard


def summarize(scorecard: dict, workspace: Path) -> dict:
    """Return a short view of a scorecard for the chat, with the path to the full file."""
    return {
        "status": "ok",
        "week": scorecard["week"],
        "path": str(history.metrics_path(workspace, scorecard["week"])),
        "partial_week": scorecard["partial_week"],
        "channels_present": scorecard["channels_present"],
        "status_counts": scorecard["team"]["status_counts"],
        "team_pattern": scorecard["team"]["pattern"],
        "reps": [
            {
                "name": rep["name"],
                "status": rep["status"],
                "focus_text": focus_text(rep),
                "flags": rep["flags"],
            }
            for rep in scorecard["reps"]
        ],
        "notes": scorecard["notes"],
    }
