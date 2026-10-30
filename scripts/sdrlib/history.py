"""Read and write the team's stored history, and work with ISO weeks."""
from __future__ import annotations

import csv
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Sequence

ACTIVITY_COUNTS = (
    "dials",
    "connected",
    "emails",
    "replies",
    "bounces",
    "li_requests",
    "li_accepted",
    "li_messages",
    "li_replies",
    "li_other",
)
ACTIVITY_FIELDS = ("date", "rep", "channel", "granularity") + ACTIVITY_COUNTS
MEETING_FIELDS = ("rep", "booked_date", "due_date", "status", "accepted")
DAYS_PER_WEEK = 7


def iso_week(day: date) -> str:
    """Return the ISO week name for a date, such as 2026-W44."""
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def week_bounds(week: str) -> tuple[date, date]:
    """Return the Monday and Sunday of an ISO week."""
    match = re.fullmatch(r"(\d{4})-W(\d{2})", week)
    if not match:
        raise ValueError(f"'{week}' isn't a week name like 2026-W44.")
    monday = date.fromisocalendar(int(match.group(1)), int(match.group(2)), 1)
    return monday, monday + timedelta(days=DAYS_PER_WEEK - 1)


def previous_weeks(week: str, count: int) -> list[str]:
    """Return `count` weeks ending in the given week, oldest first."""
    monday, _ = week_bounds(week)
    return [iso_week(monday - timedelta(weeks=back)) for back in range(count - 1, -1, -1)]


def _weeks_between(first: date, last: date) -> list[str]:
    weeks = []
    monday = first - timedelta(days=first.weekday())
    while monday <= last:
        weeks.append(iso_week(monday))
        monday += timedelta(days=DAYS_PER_WEEK)
    return weeks


def _covered_days(rows: Iterable[dict]) -> set[tuple[str, date]]:
    """Return every (channel, date) that an import speaks for."""
    covered: set[tuple[str, date]] = set()
    daily: dict[str, list[date]] = {}
    for row in rows:
        day = date.fromisoformat(row["date"])
        if row["granularity"] == "week":
            monday = day - timedelta(days=day.weekday())
            covered.update(
                (row["channel"], monday + timedelta(days=offset))
                for offset in range(DAYS_PER_WEEK)
            )
        else:
            daily.setdefault(row["channel"], []).append(day)
    for channel, days in daily.items():
        first, last = min(days), max(days)
        covered.update(
            (channel, first + timedelta(days=offset)) for offset in range((last - first).days + 1)
        )
    return covered


def _activity_order(row: dict) -> tuple[str, str, str]:
    return row["date"], row["rep"], row["channel"]


def merge_activity(existing: Sequence[dict], new: Sequence[dict]) -> list[dict]:
    """Return stored rows with an import's channels and dates replaced by the import."""
    covered = _covered_days(new)
    kept = [
        dict(row)
        for row in existing
        if (row["channel"], date.fromisoformat(row["date"])) not in covered
    ]
    return sorted(kept + [dict(row) for row in new], key=_activity_order)


def _folder(workspace: Path, name: str) -> Path:
    return workspace / "history" / name


def _write_csv(path: Path, fields: Sequence[str], rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_activity(workspace: Path, weeks: Iterable[str]) -> list[dict]:
    """Return stored daily counts for the given weeks."""
    rows: list[dict] = []
    for week in weeks:
        path = _folder(workspace, "activity") / f"{week}.csv"
        if not path.exists():
            continue
        for row in _read_csv(path):
            counts = {name: int(row[name]) for name in ACTIVITY_COUNTS}
            rows.append({**row, **counts})
    return rows


def write_activity(workspace: Path, rows: Sequence[dict]) -> None:
    """Merge daily counts into stored history, one file per ISO week."""
    covered = _covered_days(rows)
    if not covered:
        return
    days = [day for _, day in covered]
    weeks = _weeks_between(min(days), max(days))
    merged = merge_activity(read_activity(workspace, weeks), rows)
    for week in weeks:
        path = _folder(workspace, "activity") / f"{week}.csv"
        week_rows = [row for row in merged if iso_week(date.fromisoformat(row["date"])) == week]
        if week_rows:
            _write_csv(path, ACTIVITY_FIELDS, week_rows)
        elif path.exists():
            path.unlink()


def latest_week(workspace: Path) -> str | None:
    """Return the newest week that has stored activity."""
    weeks = sorted(path.stem for path in _folder(workspace, "activity").glob("*.csv"))
    return weeks[-1] if weeks else None


def write_meetings(workspace: Path, week: str, rows: Sequence[dict]) -> None:
    """Save a meeting snapshot. Statuses change after booking, so snapshots stay whole."""
    ordered = sorted(rows, key=lambda row: tuple(row[name] for name in MEETING_FIELDS))
    _write_csv(_folder(workspace, "meetings") / f"{week}.csv", MEETING_FIELDS, ordered)


def read_latest_meetings(workspace: Path) -> list[dict] | None:
    """Return the newest meeting snapshot, or None if there has never been one."""
    snapshots = sorted(_folder(workspace, "meetings").glob("*.csv"))
    return _read_csv(snapshots[-1]) if snapshots else None


def metrics_path(workspace: Path, week: str) -> Path:
    """Return where a week's metrics file lives."""
    return _folder(workspace, "metrics") / f"{week}.json"


def write_metrics(workspace: Path, week: str, metrics: dict) -> None:
    """Save a week's metrics file."""
    path = metrics_path(workspace, week)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def read_metrics(workspace: Path, week: str) -> dict:
    """Return a saved metrics file."""
    path = metrics_path(workspace, week)
    if not path.exists():
        raise ValueError(f"There's no scorecard for {week} yet. Run the scorecard first.")
    return json.loads(path.read_text(encoding="utf-8"))


def latest_metrics_week(workspace: Path) -> str | None:
    """Return the newest week with a saved scorecard."""
    weeks = sorted(path.stem for path in _folder(workspace, "metrics").glob("*.json"))
    return weeks[-1] if weeks else None


def read_sources(workspace: Path, week: str) -> list[dict]:
    """Return the files that fed a week's numbers."""
    path = _folder(workspace, "sources") / f"{week}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def write_sources(workspace: Path, week: str, sources: Sequence[dict]) -> None:
    """Record the files used for a week, replacing any earlier entry for the same file."""
    merged = {item["file"]: item for item in read_sources(workspace, week)}
    merged.update({item["file"]: item for item in sources})
    path = _folder(workspace, "sources") / f"{week}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = [merged[name] for name in sorted(merged)]
    path.write_text(json.dumps(ordered, indent=2), encoding="utf-8")


def read_time_off(workspace: Path, week: str) -> dict:
    """Return the week's time off, or none if nothing was recorded."""
    path = _folder(workspace, "time-off") / f"{week}.json"
    empty = {"team_days_off": 0, "rep_days_off": {}}
    if not path.exists():
        return empty
    return {**empty, **json.loads(path.read_text(encoding="utf-8"))}
