"""Turn a rep's numbers into step statuses, a rep status, and one coaching focus."""

from __future__ import annotations

from collections.abc import Sequence

ON_TARGET = "On target"
NEAR = "Near"
BELOW = "Below"
NOT_ENOUGH_DATA = "Not enough data"
NOT_AVAILABLE = "Not available"

ONBOARDING = "Onboarding"
ON_TRACK = "On track"
NEEDS_ATTENTION = "Needs attention"
WATCH = "Watch"
REVIEW = "Review"
LIMITED_DATA = "Limited data"

STEP_NAMES = {
    1: "Activity",
    2: "Response",
    3: "Meetings booked",
    4: "Meetings held",
    5: "Meetings accepted",
}
# Each response metric, paired with the count that shows how much data sits behind it.
RESPONSE_METRICS = (
    ("connect_rate", "dials"),
    ("email_reply_rate", "emails"),
    ("li_accept_rate", "li_requests"),
    ("li_reply_rate", "li_messages"),
)
BOUNCE_MINIMUM_EMAILS = 100
PATTERN_MINIMUM_REPS = 3
UNJUDGED_STATUSES = (ONBOARDING, LIMITED_DATA)


def compare(
    actual: float | None,
    target: float | None,
    enough_data: bool = True,
    near_band: float = 0.85,
) -> str:
    """Compare raw values, never rounded ones, so a status can't flip on display rounding."""
    if actual is None or not target:
        return NOT_AVAILABLE
    if not enough_data:
        return NOT_ENOUGH_DATA
    ratio = actual / target
    if ratio >= 1:
        return ON_TARGET
    return NEAR if ratio >= near_band else BELOW


def _step(number: int, status: str, metric: str | None, actual: object, target: object) -> dict:
    return {
        "number": number,
        "name": STEP_NAMES[number],
        "status": status,
        "metric": metric,
        "actual": actual,
        "target": target,
    }


def _response_step(window: dict, targets: dict, minimums: dict, near_band: float) -> dict:
    candidates = []
    has_any_value = False
    for metric, sample_count in RESPONSE_METRICS:
        actual = window["rates"].get(metric)
        target = targets[metric]["value"]
        if actual is None or not target:
            continue
        has_any_value = True
        if window["counts"][sample_count] >= minimums[metric]:
            candidates.append((actual / target, metric, actual, target))
    if candidates:
        _, metric, actual, target = min(candidates)
        return _step(2, compare(actual, target, True, near_band), metric, actual, target)
    return _step(2, NOT_ENOUGH_DATA if has_any_value else NOT_AVAILABLE, None, None, None)


def evaluate_steps(window: dict, targets: dict, minimums: dict, near_band: float) -> list[dict]:
    """Return the status of each funnel step for a rep's four-week window."""
    meetings = window["meetings"] or {}
    touches = window["touches"]
    touch_target = window["targets"]["touches"]
    meeting_rate = window["rates"].get("meeting_rate")
    meeting_target = targets["meeting_rate"]["value"]
    show_rate = meetings.get("show_rate")
    show_target = targets["show_rate"]["value"]
    acceptance = meetings.get("acceptance_rate")
    acceptance_target = targets["acceptance_rate"]["value"]
    reviewed = meetings.get("accepted_yes", 0) + meetings.get("accepted_no", 0)
    enough_conversations = window["conversations"] >= minimums["meeting_rate"]
    enough_due = meetings.get("due", 0) >= minimums["show_rate"]
    enough_reviewed = reviewed >= minimums["acceptance_rate"]
    return [
        _step(
            1,
            compare(touches, touch_target, True, near_band),
            "touches",
            touches,
            touch_target,
        ),
        _response_step(window, targets, minimums, near_band),
        _step(
            3,
            compare(meeting_rate, meeting_target, enough_conversations, near_band),
            "meeting_rate",
            meeting_rate,
            meeting_target,
        ),
        _step(
            4,
            compare(show_rate, show_target, enough_due, near_band),
            "show_rate",
            show_rate,
            show_target,
        ),
        _step(
            5,
            compare(acceptance, acceptance_target, enough_reviewed, near_band),
            "acceptance_rate",
            acceptance,
            acceptance_target,
        ),
    ]


def evaluate_outcome(window: dict, near_band: float) -> dict:
    """Compare meetings held in the window with the rep's count target."""
    meetings = window["meetings"]
    actual = meetings["held"] if meetings else None
    target = window["targets"]["meetings_held"]
    return {
        "actual": actual,
        "target": target,
        "status": compare(actual, target, True, near_band),
    }


def stretch_focus(window: dict, targets: dict, minimums: dict) -> dict | None:
    """Return the metric furthest from its stretch value, for reps already on track."""
    candidates = []
    for metric, sample_count in RESPONSE_METRICS:
        stretch = targets[metric].get("stretch")
        actual = window["rates"].get(metric)
        if not stretch or actual is None or actual >= stretch:
            continue
        if window["counts"][sample_count] >= minimums[metric]:
            candidates.append((actual / stretch, metric, actual, stretch))
    if not candidates:
        return None
    _, metric, actual, stretch = min(candidates)
    return {"step": 2, "metric": metric, "actual": actual, "target": stretch, "kind": "stretch"}


def gap_focus(step: dict) -> dict:
    """Turn a weak step into a coaching focus."""
    return {
        "step": step["number"],
        "metric": step["metric"],
        "actual": step["actual"],
        "target": step["target"],
        "kind": "gap",
    }


def choose_status(
    steps: Sequence[dict], outcome: dict, onboarding: bool, stretch: dict | None
) -> dict:
    """Apply the spec's status rules in order. The first match wins."""
    if onboarding:
        return {"status": ONBOARDING, "focus": None}
    if outcome["status"] == ON_TARGET and steps[4]["status"] != BELOW:
        return {"status": ON_TRACK, "focus": stretch}
    for wanted, status in ((BELOW, NEEDS_ATTENTION), (NEAR, WATCH)):
        for step in steps:
            if step["status"] == wanted:
                return {"status": status, "focus": gap_focus(step)}
    if outcome["status"] in (NEAR, BELOW):
        return {"status": REVIEW, "focus": None}
    return {"status": LIMITED_DATA, "focus": None}


def bounce_flag(window: dict, targets: dict) -> bool:
    """Return True when a rep's bounce rate calls for a deliverability warning."""
    rate = window["rates"].get("bounce_rate")
    if rate is None or window["counts"]["emails"] < BOUNCE_MINIMUM_EMAILS:
        return False
    return rate >= targets["bounce_limit"]["value"]


def team_pattern(reps: Sequence[dict]) -> dict | None:
    """Return a focus step shared by at least half of the judged reps, if there is one."""
    judged = [rep for rep in reps if rep["status"] not in UNJUDGED_STATUSES]
    shared_steps = [
        rep["focus"]["step"] for rep in judged if rep.get("focus") and rep["focus"]["kind"] == "gap"
    ]
    for step in sorted(set(shared_steps)):
        count = shared_steps.count(step)
        if count >= PATTERN_MINIMUM_REPS and count * 2 >= len(judged):
            return {
                "step": step,
                "name": STEP_NAMES[step],
                "reps": count,
                "judged": len(judged),
            }
    return None
