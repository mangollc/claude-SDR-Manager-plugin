"""Apply saved mappings to exports, then store counts without prospect details."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Sequence

from . import history
from .file_reader import (
    MASK,
    Table,
    find_mapping_file,
    is_masked_column,
    mask_text,
    read_rows,
    read_table,
)
from .history import ACTIVITY_COUNTS
from .profile import load_profile, rep_lookup

SKIP_ACTION = "skip"
ACTION_COUNTS = {
    "dial": ("call", "dials"),
    "email": ("email", "emails"),
    "email_reply": ("email", "replies"),
    "email_bounce": ("email", "bounces"),
    "li_request": ("linkedin", "li_requests"),
    "li_accept": ("linkedin", "li_accepted"),
    "li_message": ("linkedin", "li_messages"),
    "li_reply": ("linkedin", "li_replies"),
    "li_other": ("linkedin", "li_other"),
}
FLAG_COUNTS = {
    "dial": {"connected": "connected"},
    "email": {"replied": "replies", "bounced": "bounces"},
    "li_request": {"accepted": "li_accepted"},
    "li_message": {"replied": "li_replies"},
}
CHANNEL_COUNTS = {
    "call": ("dials", "connected"),
    "email": ("emails", "replies", "bounces"),
    "linkedin": ("li_requests", "li_accepted", "li_messages", "li_replies", "li_other"),
}
STATUS_VALUES = ("held", "no_show", "cancelled", "rescheduled", "scheduled")
ACCEPTED_VALUES = ("yes", "no", "pending")
REQUIRED_COLUMNS = {
    "activities": ("date", "rep"),
    "rep_summary": ("week_start", "rep"),
    "meetings": ("rep", "booked_date", "status"),
}
MAX_REJECTED_SHARE = 0.05
MAX_EXAMPLES = 3


@dataclass
class _Problems:
    """What a file's rows turned up that the manager may need to resolve."""

    rejected: list[dict] = field(default_factory=list)
    unknown_reps: Counter = field(default_factory=Counter)
    unmapped: dict[str, set[str]] = field(default_factory=dict)
    notes: set[str] = field(default_factory=set)

    def add_unmapped(self, column: str, value: str) -> None:
        self.unmapped.setdefault(column, set()).add(value)


@dataclass(frozen=True)
class FileResult:
    file: str
    kind: str
    rows_read: int
    rows_rejected: int
    activity: tuple[dict, ...]
    meetings: tuple[dict, ...]
    unknown_reps: dict
    unmapped: dict
    rejected_examples: tuple[str, ...]
    notes: tuple[str, ...] = ()


def _parse_date(raw: str, date_format: str) -> date | None:
    try:
        return datetime.strptime(raw, date_format).date()
    except (TypeError, ValueError):
        return None


def _parse_count(raw: str) -> int | None:
    if not raw:
        return 0
    try:
        return int(float(raw.replace(",", "")))
    except (OverflowError, ValueError):
        return None


def _rep_for(row: dict, mapping: dict, reps: dict, problems: _Problems) -> str | None:
    """Return the rep's name, or None when the row shouldn't be counted."""
    raw = row[mapping["columns"]["rep"]]
    if not raw:
        problems.rejected.append(row)
        return None
    if raw.lower() not in reps:
        problems.unknown_reps[raw] += 1
        return None
    return reps[raw.lower()]


def _action_for(row: dict, mapping: dict, problems: _Problems) -> str | None:
    """Return the row's standard action, or None when it shouldn't be counted."""
    fixed = mapping.get("fixed", {}).get("action")
    if fixed:
        return None if fixed == SKIP_ACTION else fixed
    column = mapping["columns"]["action"]
    raw = row[column]
    if not raw:
        problems.rejected.append(row)
        return None
    action = mapping.get("values", {}).get("action", {}).get(raw, raw)
    if action == SKIP_ACTION:
        return None
    if action not in ACTION_COUNTS:
        problems.add_unmapped(column, raw)
        return None
    return action


def _flag_is_set(row: dict, spec: dict | None, problems: _Problems) -> bool:
    if not spec:
        return False
    raw = row[spec["column"]]
    if not raw:
        return False
    if spec.get("any") or raw in spec.get("true", ()):
        return True
    if raw not in spec.get("false", ()):
        problems.add_unmapped(spec["column"], raw)
    return False


def _activity_row(day: str, rep: str, channel: str, granularity: str, counts: dict) -> dict:
    row = {"date": day, "rep": rep, "channel": channel, "granularity": granularity}
    row.update({name: counts.get(name, 0) for name in ACTIVITY_COUNTS})
    return row


def _read_activities(table: Table, mapping: dict, reps: dict, problems: _Problems) -> list[dict]:
    date_column = mapping["columns"]["date"]
    flags = mapping.get("flags", {})
    totals: dict[tuple[str, str, str], Counter] = {}
    for row in table.rows:
        rep = _rep_for(row, mapping, reps, problems)
        if rep is None:
            continue
        day = _parse_date(row[date_column], mapping["date_format"])
        if day is None:
            problems.rejected.append(row)
            continue
        action = _action_for(row, mapping, problems)
        if action is None:
            continue
        channel, count_name = ACTION_COUNTS[action]
        bucket = totals.setdefault((day.isoformat(), rep, channel), Counter())
        bucket[count_name] += 1
        for flag, flag_count in FLAG_COUNTS.get(action, {}).items():
            if _flag_is_set(row, flags.get(flag), problems):
                bucket[flag_count] += 1
    return [
        _activity_row(day, rep, channel, "day", counts)
        for (day, rep, channel), counts in sorted(totals.items())
    ]


def _summary_counts(row: dict, columns: dict) -> dict | None:
    names = [name for name in ACTIVITY_COUNTS if name in columns]
    counts = {name: _parse_count(row[columns[name]]) for name in names}
    return None if None in counts.values() else counts


def _read_summary(table: Table, mapping: dict, reps: dict, problems: _Problems) -> list[dict]:
    columns = mapping["columns"]
    channels = {
        channel: names
        for channel, names in CHANNEL_COUNTS.items()
        if any(name in columns for name in names)
    }
    rows: list[dict] = []
    for row in table.rows:
        rep = _rep_for(row, mapping, reps, problems)
        if rep is None:
            continue
        day = _parse_date(row[columns["week_start"]], mapping["date_format"])
        counts = _summary_counts(row, columns)
        if day is None or counts is None:
            problems.rejected.append(row)
            continue
        monday = (day - timedelta(days=day.weekday())).isoformat()
        for channel, names in channels.items():
            channel_counts = {name: counts.get(name, 0) for name in names}
            rows.append(_activity_row(monday, rep, channel, "week", channel_counts))
    return rows


def _standard_value(raw: str, column: str, translations: dict, allowed: Sequence[str],
                    problems: _Problems) -> str | None:
    value = translations.get(raw, raw)
    if value in allowed:
        return value
    problems.add_unmapped(column, raw)
    return None


def _accepted_value(row: dict, mapping: dict, problems: _Problems) -> str:
    column = mapping["columns"].get("accepted")
    if column is None:
        return ""
    raw = row[column]
    if not raw:
        return "pending"
    translations = mapping.get("values", {}).get("accepted", {})
    return _standard_value(raw, column, translations, ACCEPTED_VALUES, problems) or "pending"


def _meeting_dates(row: dict, mapping: dict, problems: _Problems) -> tuple[date, date] | None:
    """Return the booked and due dates, or None when the row must be rejected."""
    columns = mapping["columns"]
    booked = _parse_date(row[columns["booked_date"]], mapping["date_format"])
    if booked is None:
        return None
    raw_due = row[columns["due_date"]] if "due_date" in columns else ""
    if not raw_due:
        problems.notes.add("Some meetings have no due date, so their booked date was used.")
        return booked, booked
    due = _parse_date(raw_due, mapping["date_format"])
    return None if due is None else (booked, due)


def _read_meetings(table: Table, mapping: dict, reps: dict, problems: _Problems) -> list[dict]:
    status_column = mapping["columns"]["status"]
    translations = mapping.get("values", {}).get("status", {})
    meetings: list[dict] = []
    for row in table.rows:
        rep = _rep_for(row, mapping, reps, problems)
        if rep is None:
            continue
        dates = _meeting_dates(row, mapping, problems)
        if dates is None or not row[status_column]:
            problems.rejected.append(row)
            continue
        status = _standard_value(
            row[status_column], status_column, translations, STATUS_VALUES, problems
        )
        if status is None:
            continue
        meetings.append(
            {
                "rep": rep,
                "booked_date": dates[0].isoformat(),
                "due_date": dates[1].isoformat(),
                "status": status,
                "accepted": _accepted_value(row, mapping, problems),
            }
        )
    return meetings


def _check_mapping(path: Path, mapping: dict, table: Table) -> None:
    kind = mapping["kind"]
    columns = mapping.get("columns", {})
    needed = [name for name in REQUIRED_COLUMNS[kind] if name not in columns]
    if needed:
        raise ValueError(f"The mapping for {path.name} needs: {', '.join(needed)}.")
    if not mapping.get("date_format"):
        raise ValueError(f"The mapping for {path.name} needs a date_format.")
    fixed_action = mapping.get("fixed", {}).get("action")
    if kind == "activities" and not fixed_action and "action" not in columns:
        raise ValueError(f"The mapping for {path.name} needs an action.")
    if fixed_action and fixed_action != SKIP_ACTION and fixed_action not in ACTION_COUNTS:
        raise ValueError(f"The mapping for {path.name} has an unknown action: {fixed_action}.")
    wanted = list(columns.values()) + [
        spec["column"] for spec in mapping.get("flags", {}).values()
    ]
    missing = [name for name in wanted if name not in table.headers]
    if missing:
        raise ValueError(f"{path.name} has no column named: {', '.join(missing)}.")


def _safe_example(row: dict) -> str:
    cells = (
        f"{name}: {MASK if is_masked_column(name) else mask_text(value)}"
        for name, value in row.items()
        if value
    )
    return "; ".join(cells)


def normalize_file(path: Path, mapping: dict, reps: dict) -> FileResult:
    """Translate one export into standard rows and report anything unresolved."""
    kind = mapping.get("kind")
    if kind not in REQUIRED_COLUMNS:
        raise ValueError(
            f"The mapping for {path.name} has an unknown kind: {kind}. "
            "Use activities, rep_summary, or meetings."
        )
    table = read_table(path, mapping.get("header_row", 1))
    _check_mapping(path, mapping, table)
    problems = _Problems()
    activity: list[dict] = []
    meetings: list[dict] = []
    if kind == "activities":
        activity = _read_activities(table, mapping, reps, problems)
    elif kind == "rep_summary":
        activity = _read_summary(table, mapping, reps, problems)
    else:
        meetings = _read_meetings(table, mapping, reps, problems)
    return FileResult(
        file=path.name,
        kind=kind,
        rows_read=len(table.rows),
        rows_rejected=len(problems.rejected),
        activity=tuple(activity),
        meetings=tuple(meetings),
        unknown_reps=dict(problems.unknown_reps),
        unmapped={column: tuple(sorted(values)) for column, values in problems.unmapped.items()},
        rejected_examples=tuple(_safe_example(row) for row in problems.rejected[:MAX_EXAMPLES]),
        notes=tuple(sorted(problems.notes)),
    )


def find_mapping(path: Path, mappings_dir: Path) -> dict | None:
    """Return the saved mapping that fits a file, if there is one."""
    match = find_mapping_file(read_rows(path), mappings_dir)
    return json.loads(match.read_text(encoding="utf-8")) if match else None


def channel_conflicts(results: Sequence[FileResult]) -> dict[str, list[str]]:
    """Return channels covered by more than one file, which would double count."""
    files_by_channel: dict[str, list[str]] = {}
    for result in results:
        for channel in sorted({row["channel"] for row in result.activity}):
            files_by_channel.setdefault(channel, []).append(result.file)
    return {channel: files for channel, files in files_by_channel.items() if len(files) > 1}


def _result_dates(result: FileResult) -> list[str]:
    if result.activity:
        return [row["date"] for row in result.activity]
    return [meeting["booked_date"] for meeting in result.meetings]


def _week_label(results: Sequence[FileResult], week: str | None) -> str | None:
    if week:
        history.week_bounds(week)
        return week
    activity_days = [row["date"] for result in results for row in result.activity]
    days = activity_days or [day for result in results for day in _result_dates(result)]
    return history.iso_week(date.fromisoformat(max(days))) if days else None


def _source_entry(result: FileResult) -> dict:
    dates = _result_dates(result)
    return {
        "file": result.file,
        "kind": result.kind,
        "rows_read": result.rows_read,
        "rows_rejected": result.rows_rejected,
        "first_date": min(dates) if dates else None,
        "last_date": max(dates) if dates else None,
    }


def _build_report(results: Sequence[FileResult], without_mapping: Sequence[str],
                  week: str | None) -> dict:
    unknown: Counter = Counter()
    unmapped: dict[str, set[str]] = {}
    for result in results:
        unknown.update(result.unknown_reps)
        for column, values in result.unmapped.items():
            unmapped.setdefault(column, set()).update(values)
    conflicts = channel_conflicts(results)
    too_many = [
        result.file
        for result in results
        if result.rows_read and result.rows_rejected / result.rows_read > MAX_REJECTED_SHARE
    ]
    blocked = bool(without_mapping or unknown or unmapped or conflicts or too_many)
    return {
        "status": "needs_input" if blocked else "ok",
        "week": _week_label(results, week),
        "files": [_source_entry(result) for result in results],
        "files_without_mapping": list(without_mapping),
        "unknown_reps": dict(unknown),
        "unmapped_values": {column: sorted(values) for column, values in unmapped.items()},
        "too_many_rejected": too_many,
        "rejected_examples": [
            f"{result.file}: {example}"
            for result in results
            for example in result.rejected_examples
        ],
        "channel_conflicts": conflicts,
        "notes": sorted({note for result in results for note in result.notes}),
    }


def _store(workspace: Path, results: Sequence[FileResult], week: str | None) -> None:
    activity = [row for result in results for row in result.activity]
    history.write_activity(workspace, activity)
    meetings = [meeting for result in results for meeting in result.meetings]
    if meetings and week:
        history.write_meetings(workspace, week, meetings)
    if week:
        history.write_sources(workspace, week, [_source_entry(result) for result in results])


def normalize_files(workspace: Path, files: Sequence[Path], week: str | None = None) -> dict:
    """Check every file, and store the results only if all of them pass."""
    reps = rep_lookup(load_profile(workspace))
    mappings_dir = workspace / "mappings"
    results: list[FileResult] = []
    without_mapping: list[str] = []
    for path in files:
        mapping = find_mapping(path, mappings_dir)
        if mapping is None:
            without_mapping.append(path.name)
        else:
            results.append(normalize_file(path, mapping, reps))
    report = _build_report(results, without_mapping, week)
    if report["status"] == "ok":
        _store(workspace, results, report["week"])
    return report
