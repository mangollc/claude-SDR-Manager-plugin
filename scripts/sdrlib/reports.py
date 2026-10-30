"""Fill the report templates. Every value from data passes through escape()."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from html import escape
from string import Template

from .focus import (
    BELOW,
    LIMITED_DATA,
    NEAR,
    NEEDS_ATTENTION,
    NOT_AVAILABLE,
    NOT_ENOUGH_DATA,
    ON_TARGET,
    ON_TRACK,
    ONBOARDING,
    REVIEW,
    STEP_NAMES,
    WATCH,
    compare,
)
from .targets import ASSETS_DIR

TEMPLATES_DIR = ASSETS_DIR / "templates"
MAX_OBSERVATIONS = 3
AGENDA_MINUTES = (5, 10, 10, 5)
# These caps help the 1:1 prep stay on one page.
MAX_WRITTEN_WINS = 3
MAX_QUESTIONS = 5
SPARK_WIDTH = 96
SPARK_HEIGHT = 24
SPARK_PADDING = 3

RATE_METRICS = {
    "connect_rate",
    "email_reply_rate",
    "bounce_rate",
    "li_accept_rate",
    "li_reply_rate",
    "meeting_rate",
    "show_rate",
    "acceptance_rate",
}
METRIC_LABELS = {
    "touches": "Touches",
    "connect_rate": "Connect rate",
    "email_reply_rate": "Email reply rate",
    "li_accept_rate": "LinkedIn acceptance rate",
    "li_reply_rate": "LinkedIn reply rate",
    "meeting_rate": "Meeting rate",
    "show_rate": "Show rate",
    "acceptance_rate": "Acceptance rate",
}
STEP_SYMBOLS = {
    ON_TARGET: ("●", "good"),
    NEAR: ("◐", "near"),
    BELOW: ("○", "bad"),
    NOT_ENOUGH_DATA: ("–", "neutral"),
    NOT_AVAILABLE: ("–", "neutral"),
}
REP_STATUS_STYLES = {
    ON_TRACK: "good",
    WATCH: "near",
    NEEDS_ATTENTION: "bad",
    REVIEW: "near",
    ONBOARDING: "neutral",
    LIMITED_DATA: "neutral",
}
NO_FOCUS_TEXT = {
    ONBOARDING: "In onboarding. Numbers are shown without judgment.",
    ON_TRACK: "On track, with no stretch focus this period.",
    REVIEW: "No step explains the gap. Check for timing, such as meetings booked but not held.",
    LIMITED_DATA: "There isn't enough data for a focus. See the notes on this page.",
}


def load_brand() -> str:
    """Return the brand name shown on every report."""
    return json.loads((ASSETS_DIR / "brand.json").read_text(encoding="utf-8"))["name"]


def _load_template(name: str) -> Template:
    return Template((TEMPLATES_DIR / name).read_text(encoding="utf-8"))


def _load_css() -> str:
    return (TEMPLATES_DIR / "report.css").read_text(encoding="utf-8")


def format_value(metric: str, value: float | None) -> str:
    """Format a number for display, showing missing data as words, never as zero."""
    if value is None:
        return NOT_AVAILABLE
    if metric in RATE_METRICS:
        return f"{value * 100:.1f}%"
    rounded = round(float(value), 1)
    return f"{int(rounded):,}" if rounded.is_integer() else f"{rounded:,.1f}"


def format_target(metric: str, value: float | None) -> str:
    """Format a target exactly, so 3.41% against 3.43% can't both read as 3.4%."""
    if value is None or metric not in RATE_METRICS:
        return format_value(metric, value)
    return f"{value * 100:.2f}".rstrip("0").rstrip(".") + "%"


def _chart_point(index: int, value: float, low: float, span: float, step: float) -> tuple:
    x = SPARK_PADDING + index * step
    if span == 0:
        return round(x, 1), SPARK_HEIGHT / 2
    drawable = SPARK_HEIGHT - 2 * SPARK_PADDING
    y = SPARK_HEIGHT - SPARK_PADDING - (value - low) / span * drawable
    return round(x, 1), round(y, 1)


def _line_runs(values: Sequence[float | None]) -> list[list[tuple[int, float]]]:
    """Split a series into unbroken runs, so missing weeks show as gaps."""
    runs: list[list[tuple[int, float]]] = [[]]
    for index, value in enumerate(values):
        if value is None:
            runs.append([])
        else:
            runs[-1].append((index, value))
    return [run for run in runs if run]


def _chart_shape(run: list[tuple[int, float]], low: float, span: float, step: float) -> str:
    points = [_chart_point(index, value, low, span, step) for index, value in run]
    if len(points) == 1:
        x, y = points[0]
        return f'<circle cx="{x}" cy="{y}" r="1.6" fill="currentColor"/>'
    joined = " ".join(f"{x},{y}" for x, y in points)
    return f'<polyline points="{joined}" fill="none" stroke="currentColor" stroke-width="1.4"/>'


def sparkline(values: Sequence[float | None]) -> str:
    """Return a small inline chart. Missing values leave a gap."""
    known = [value for value in values if value is not None]
    shapes = ""
    if known:
        low = min(known)
        span = max(known) - low
        step = (SPARK_WIDTH - 2 * SPARK_PADDING) / max(len(values) - 1, 1)
        shapes = "".join(_chart_shape(run, low, span, step) for run in _line_runs(values))
    return (
        f'<svg viewBox="0 0 {SPARK_WIDTH} {SPARK_HEIGHT}" role="img" '
        f'aria-label="Weekly trend">{shapes}</svg>'
    )


def _status_html(status: str) -> str:
    symbol, style = STEP_SYMBOLS[status]
    return f'<span class="status status-{style}">{symbol} {escape(status)}</span>'


def _rep_status_html(status: str) -> str:
    style = REP_STATUS_STYLES[status]
    return f'<span class="status status-{style}">{escape(status)}</span>'


def _masthead(brand: str, document: str) -> str:
    return (
        '<header class="masthead">'
        f'<p class="wordmark">{escape(brand)}</p>'
        f'<p class="doc-type">{escape(document)}</p>'
        "</header>"
    )


def _footer(*parts: str) -> str:
    text = " | ".join(escape(part) for part in parts)
    return f'<footer class="page-footer">{text}</footer>'


def _list_items(values: Sequence[str]) -> str:
    return "".join(f"<li>{escape(value)}</li>" for value in values)


def _short_date(day: date) -> str:
    return f"{day:%b} {day.day}"


def _date_range(metrics: dict) -> str:
    start = date.fromisoformat(metrics["week_start"])
    end = date.fromisoformat(metrics["week_end"])
    return f"{_short_date(start)} to {_short_date(end)}, {end.year}"


def focus_text(rep: dict) -> str:
    """Describe a rep's coaching focus in one sentence, in words shared by reports and chat."""
    focus = rep["focus"]
    if focus is None:
        return NO_FOCUS_TEXT.get(rep["status"], "")
    metric = focus["metric"]
    label = METRIC_LABELS[metric]
    step = STEP_NAMES[focus["step"]]
    actual = format_value(metric, focus["actual"])
    target = format_target(metric, focus["target"])
    if focus["kind"] == "stretch":
        return f"Stretch: {label} is {actual}. Top performers reach {target}."
    if metric == "touches":
        return f"{step}: {actual} touches in four weeks against a target of {target}."
    return f"{step}: {label} is {actual} against a target of {target}."


def _team_row(label: str, metric: str, actual: float | None, target: float | None) -> str:
    return (
        f"<tr><td>{escape(label)}</td>"
        f'<td class="number">{format_value(metric, actual)}</td>'
        f'<td class="number">{format_target(metric, target)}</td>'
        f"<td>{_status_html(compare(actual, target))}</td></tr>"
    )


def _team_numbers(metrics: dict) -> str:
    team = metrics["team"]
    targets = metrics["targets"]
    meetings = team["meetings"] or {}
    rows = [
        _team_row("Touches", "touches", team["touches"], team["targets"]["touches"]),
        *(
            _team_row(METRIC_LABELS[name], name, team["rates"][name], targets[name]["value"])
            for name in ("connect_rate", "email_reply_rate", "li_accept_rate", "li_reply_rate")
        ),
        _team_row(
            "Meeting rate",
            "meeting_rate",
            team["rates"]["meeting_rate"],
            targets["meeting_rate"]["value"],
        ),
        _team_row(
            "Meetings held",
            "meetings_held",
            meetings.get("held"),
            team["targets"]["meetings_held"],
        ),
        _team_row(
            "Show rate", "show_rate", meetings.get("show_rate"), targets["show_rate"]["value"]
        ),
        _team_row(
            "Acceptance rate",
            "acceptance_rate",
            meetings.get("acceptance_rate"),
            targets["acceptance_rate"]["value"],
        ),
    ]
    return (
        '<table class="ledger"><tr><th>Metric</th><th class="number">Actual</th>'
        f'<th class="number">Target</th><th>Status</th></tr>{"".join(rows)}</table>'
    )


def _held_against_target(outcome: dict) -> str:
    target = format_value("held", outcome["target"]) if outcome["target"] else "none"
    return f'{format_value("held", outcome["actual"])} / {target}'


def _rep_overview(metrics: dict) -> str:
    rows = "".join(
        f"<tr><td>{escape(rep['name'])}</td><td>{_rep_status_html(rep['status'])}</td>"
        f"<td>{escape(focus_text(rep))}</td>"
        f'<td class="number">{_held_against_target(rep["outcome"])}</td></tr>'
        for rep in metrics["reps"]
    )
    return (
        '<table class="ledger"><tr><th>Rep</th><th>Status</th><th>Coaching focus</th>'
        f'<th class="number">Held / target</th></tr>{rows}</table>'
    )


def _coverage(metrics: dict) -> str:
    rows = "".join(
        f"<tr><td>{escape(item['file'])}</td>"
        f'<td class="number">{item["rows_read"]:,}</td>'
        f'<td class="number">{item["rows_rejected"]:,}</td>'
        f"<td>{escape(str(item.get('first_date')))} to {escape(str(item.get('last_date')))}</td>"
        "</tr>"
        for item in metrics["sources"]
    )
    notes = _list_items(metrics["notes"])
    table = (
        '<table class="ledger small"><tr><th>File</th><th class="number">Rows read</th>'
        f'<th class="number">Rejected</th><th>Dates</th></tr>{rows}</table>'
    )
    return table + (f'<ul class="small">{notes}</ul>' if notes else "")


def _status_tally(metrics: dict) -> str:
    counts = metrics["team"]["status_counts"]
    items = "".join(
        f"<li><strong>{counts[status]}</strong> {escape(status)}</li>"
        for status in REP_STATUS_STYLES
        if counts.get(status)
    )
    return f'<ul class="tally">{items}</ul>'


def _pattern_section(metrics: dict) -> str:
    pattern = metrics["team"]["pattern"]
    if not pattern:
        return ""
    return (
        '<p class="pattern"><strong>Team pattern:</strong> '
        f'{pattern["reps"]} of {pattern["judged"]} reps share the same focus: '
        f'{escape(pattern["name"])}. A shared problem usually points to the list, the '
        "messaging, or the targets rather than to each rep.</p>"
    )


def _summary_page(metrics: dict, narrative: dict, brand: str) -> str:
    banner = (
        '<p class="banner"><strong>Partial week:</strong> the data stops at '
        f'{escape(metrics["last_activity_date"])}, so targets cover working days up to then.</p>'
        if metrics["partial_week"]
        else ""
    )
    observations = narrative.get("observations", [])[:MAX_OBSERVATIONS]
    return (
        '<section class="page">'
        f'{_masthead(brand, "SDR team report")}'
        f'<p class="eyebrow">{escape(metrics["week"])} | {escape(_date_range(metrics))}</p>'
        f'<p class="headline">{escape(narrative.get("headline", ""))}</p>'
        f"{banner}<ul>{_list_items(observations)}</ul>{_status_tally(metrics)}"
        f"{_pattern_section(metrics)}"
        f"<h2>Team numbers, last four weeks</h2>{_team_numbers(metrics)}"
        f"<h2>Reps</h2>{_rep_overview(metrics)}"
        f"<h2>Data used</h2>{_coverage(metrics)}"
        f'{_footer(brand, "Team report", metrics["week"])}'
        "</section>"
    )


def _step_detail(step: dict) -> str:
    if step["metric"] is None:
        return "No data to compare"
    label = METRIC_LABELS[step["metric"]]
    actual = format_value(step["metric"], step["actual"])
    target = format_target(step["metric"], step["target"])
    return f"{label}: {actual} against {target}"


def _steps_list(rep: dict) -> str:
    items = "".join(
        f'<li><span class="step-number">{step["number"]}</span>'
        f'<span>{escape(step["name"])}</span>{_status_html(step["status"])}'
        f'<span class="step-detail">{escape(_step_detail(step))}</span></li>'
        for step in rep["steps"]
    )
    outcome = rep["outcome"]
    detail = (
        f'Meetings held: {format_value("held", outcome["actual"])} '
        f'against {format_value("held", outcome["target"])}'
    )
    return (
        f'<ol class="steps">{items}<li><span class="step-number">=</span>'
        f'<span>Outcome</span>{_status_html(outcome["status"])}'
        f'<span class="step-detail">{escape(detail)}</span></li></ol>'
    )


def _number_row(label: str, metric: str, this_week: object, window: object, target: str) -> str:
    return (
        f"<tr><td>{escape(label)}</td>"
        f'<td class="number">{format_value(metric, this_week)}</td>'
        f'<td class="number">{format_value(metric, window)}</td>'
        f'<td class="number">{escape(target)}</td></tr>'
    )


def _rate_rows(rep: dict, targets: dict) -> list[str]:
    this_rates, window_rates = rep["this_week"]["rates"], rep["window"]["rates"]
    return [
        _number_row(
            METRIC_LABELS[name],
            name,
            this_rates[name],
            window_rates[name],
            format_target(name, targets[name]["value"]),
        )
        for name in (
            "connect_rate",
            "email_reply_rate",
            "li_accept_rate",
            "li_reply_rate",
            "meeting_rate",
        )
    ]


def _meeting_rows(rep: dict, targets: dict) -> list[str]:
    this_week = rep["this_week"]["meetings"] or {}
    window = rep["window"]["meetings"] or {}
    held_target = format_value("held", rep["window"]["targets"]["meetings_held"])
    return [
        _number_row("Meetings booked", "booked", this_week.get("booked"), window.get("booked"), ""),
        _number_row(
            "Meetings held", "held", this_week.get("held"), window.get("held"), held_target
        ),
        _number_row(
            "Show rate",
            "show_rate",
            this_week.get("show_rate"),
            window.get("show_rate"),
            format_target("show_rate", targets["show_rate"]["value"]),
        ),
        _number_row(
            "Acceptance rate",
            "acceptance_rate",
            this_week.get("acceptance_rate"),
            window.get("acceptance_rate"),
            format_target("acceptance_rate", targets["acceptance_rate"]["value"]),
        ),
    ]


def _numbers_table(rep: dict, targets: dict) -> str:
    this_week, window = rep["this_week"], rep["window"]
    touch_target = format_value("touches", window["targets"]["touches"])
    rows = [
        _number_row("Touches", "touches", this_week["touches"], window["touches"], touch_target),
        *_rate_rows(rep, targets),
        *_meeting_rows(rep, targets),
        _number_row("Days active", "days", this_week["days_active"], window["days_active"], ""),
    ]
    return (
        '<table class="ledger"><tr><th>Metric</th><th class="number">This week</th>'
        '<th class="number">Last four weeks</th><th class="number">Four-week target</th></tr>'
        f'{"".join(rows)}</table>'
    )


def _trend_cell(label: str, metric: str, values: Sequence[float | None]) -> str:
    known = [value for value in values if value is not None]
    latest = format_value(metric, known[-1] if known else None)
    return (
        f'<div class="trend"><span class="trend-label">{escape(label)}</span>'
        f'{sparkline(values)}<span class="trend-last">{latest}</span></div>'
    )


def _trends(rep: dict) -> str:
    trend = rep["trend"]
    return (
        '<div class="trends">'
        f'{_trend_cell("Touches", "touches", trend["touches"])}'
        f'{_trend_cell("Connect rate", "connect_rate", trend["connect_rate"])}'
        f'{_trend_cell("Email reply rate", "email_reply_rate", trend["email_reply_rate"])}'
        f'{_trend_cell("Meetings booked", "booked", trend["meetings_booked"])}'
        f'{_trend_cell("Meetings held", "held", trend["meetings_held"])}'
        "</div>"
    )


def _rep_meta(rep: dict, metrics: dict) -> str:
    month = rep["month_in_role"]
    role = f"Month {month} in role | " if month else ""
    out = " (out this week)" if rep["this_week"]["out"] else ""
    return (
        f'{metrics["week"]} | {role}{rep["this_week"]["working_days"]} working days'
        f'{out}, {rep["window"]["working_days"]} in four weeks'
    )


def _rep_page(rep: dict, metrics: dict, narrative: dict, brand: str) -> str:
    note = narrative.get("rep_notes", {}).get(rep["name"], "")
    warning = (
        '<p class="warning">Deliverability warning: bounce rate is '
        f'{format_value("bounce_rate", rep["window"]["rates"]["bounce_rate"])}. '
        "Check list quality before coaching on replies.</p>"
        if "bounce_warning" in rep["flags"]
        else ""
    )
    notes = _list_items(rep["notes"])
    return (
        '<section class="page"><div class="rep-head"><div>'
        f'<p class="eyebrow">{escape(_rep_meta(rep, metrics))}</p>'
        f'<h1>{escape(rep["name"])}</h1></div>'
        f'<p class="rep-status">{_rep_status_html(rep["status"])}</p></div>'
        '<div class="split"><div class="focus-panel"><h2>Coaching focus</h2>'
        f'<p class="focus-line">{escape(focus_text(rep))}</p>'
        f'<p class="rep-note">{escape(note)}</p>{warning}</div>'
        f"<div><h2>The five steps</h2>{_steps_list(rep)}</div></div>"
        f'<h2>Numbers</h2>{_numbers_table(rep, metrics["targets"])}'
        f"<h2>Weekly trend</h2>{_trends(rep)}"
        f'{f"""<ul class="small">{notes}</ul>""" if notes else ""}'
        f'{_footer(brand, "Team report", metrics["week"], rep["name"])}'
        "</section>"
    )


def _target_value(key: str, entry: dict) -> str:
    value = entry["value"]
    if value is None:
        return NOT_AVAILABLE
    if key == "bounce_limit":
        return f'Under {format_target("bounce_rate", value)}'
    return format_target("bounce_rate", value) if value < 1 else format_value("count", value)


def _targets_page(metrics: dict, brand: str) -> str:
    rows = "".join(
        f'<tr><td>{escape(entry["label"])}</td>'
        f'<td class="number">{_target_value(key, entry)}</td>'
        f'<td>{escape(entry["source"])}</td><td>{escape(str(entry["as_of"]))}</td></tr>'
        for key, entry in metrics["targets"].items()
    )
    return (
        '<section class="page">'
        f'{_masthead(brand, "Targets and sources")}'
        '<p class="headline">Where these targets come from</p>'
        "<p>Starting targets are published figures, so being on target means typical, not "
        "excellent. Most come from vendors reporting their own data, and definitions vary. "
        "Each team should replace them with its own numbers.</p>"
        '<table class="ledger"><tr><th>Target</th><th class="number">Value</th>'
        f"<th>Source</th><th>As of</th></tr>{rows}</table>"
        f'{_footer(brand, "Team report", metrics["week"], "Targets")}'
        "</section>"
    )


def render_team(metrics: dict, narrative: dict) -> str:
    """Return the full team report as HTML."""
    brand = load_brand()
    pages = [
        _summary_page(metrics, narrative, brand),
        *(_rep_page(rep, metrics, narrative, brand) for rep in metrics["reps"]),
        _targets_page(metrics, brand),
    ]
    return _load_template("team-report.html").substitute(
        title=escape(f'{brand}: Team report {metrics["week"]}'),
        css=_load_css(),
        pages="\n".join(pages),
    )


def _latest_commitments(coaching_text: str) -> list[str]:
    latest = coaching_text.split("## ")[-1] if "## " in coaching_text else ""
    prefix = "- Agreed: "
    return [line[len(prefix) :].strip() for line in latest.splitlines() if line.startswith(prefix)]


def _agenda_rows(topics: Sequence[str]) -> str:
    return "".join(
        f"<tr><td>{minutes} min</td><td>{escape(topic)}</td></tr>"
        for minutes, topic in zip(AGENDA_MINUTES, topics)
    )


def _win_lines(rep: dict) -> list[str]:
    """Return the steps that are on target. New hires' numbers aren't judged."""
    if rep["status"] == ONBOARDING:
        return []
    return [_step_detail(step) for step in rep["steps"] if step["status"] == ON_TARGET]


def _evidence_lines(rep: dict) -> list[str]:
    """Return the calculator's facts behind the coaching focus."""
    lines = []
    focus = rep["focus"]
    if focus:
        metric = focus["metric"]
        label = METRIC_LABELS[metric]
        actual = format_value(metric, focus["actual"])
        lines.append(f'{label}: {actual} against {format_target(metric, focus["target"])}')
        weekly = rep["trend"].get(metric)
        if weekly:
            shown = ", ".join(format_value(metric, value) for value in weekly)
            lines.append(f"{label} by week: {shown}")
    outcome = rep["outcome"]
    lines.append(
        f'Meetings held: {format_value("held", outcome["actual"])} '
        f'against {format_value("held", outcome["target"])}'
    )
    return lines


def render_one_on_one(metrics: dict, rep: str, narrative: dict, coaching_text: str) -> str:
    """Return the one-page 1:1 prep as HTML."""
    match = next((item for item in metrics["reps"] if item["name"] == rep), None)
    if match is None:
        raise ValueError(f"{rep} isn't in the scorecard for {metrics['week']}.")
    brand = load_brand()
    commitments = _latest_commitments(coaching_text) or ["No earlier commitments on file."]
    return _load_template("one-on-one.html").substitute(
        title=escape(f'{brand}: 1:1 prep for {rep} {metrics["week"]}'),
        css=_load_css(),
        masthead=_masthead(brand, "1:1 prep"),
        meta=escape(_rep_meta(match, metrics)),
        rep=escape(rep),
        status=_rep_status_html(match["status"]),
        focus=escape(focus_text(match)),
        focus_summary=escape(narrative.get("focus_summary", "")),
        evidence=_list_items(_evidence_lines(match)),
        wins=_list_items(_win_lines(match) + narrative.get("wins", [])[:MAX_WRITTEN_WINS]),
        commitments=_list_items(commitments),
        progress=_list_items(narrative.get("commitment_progress", [])),
        questions=_list_items(narrative.get("questions", [])[:MAX_QUESTIONS]),
        agenda=_agenda_rows(narrative.get("agenda", [])),
        footer=_footer(brand, "1:1 prep", rep, metrics["week"]),
    )
