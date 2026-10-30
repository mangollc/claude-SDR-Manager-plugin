"""Starting targets, team overrides, derived targets, and new-hire ramp."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
WEEKS_PER_MONTH = 52 / 12
WORKING_DAYS_PER_WEEK = 5
DAYS_PER_ROLE_MONTH = 30
# Assumes half of LinkedIn touches are messages, and the rest are connection requests.
LINKEDIN_MESSAGE_SHARE = 0.5


def load_defaults() -> dict:
    """Return the plugin's starting targets, minimum samples, and ramp table."""
    return json.loads((ASSETS_DIR / "default-targets.json").read_text(encoding="utf-8"))


def derive_meeting_rate(targets: dict, channels: list[str]) -> float | None:
    """Return the meeting rate that makes the funnel add up to the meeting goal."""
    value = {key: entry["value"] for key, entry in targets.items()}
    conversations_per_day = 0.0
    if "call" in channels:
        conversations_per_day += value["dials_per_day"] * value["connect_rate"]
    if "email" in channels:
        conversations_per_day += value["emails_per_day"] * value["email_reply_rate"]
    if "linkedin" in channels:
        conversations_per_day += (
            value["linkedin_touches_per_day"] * LINKEDIN_MESSAGE_SHARE * value["li_reply_rate"]
        )
    if conversations_per_day <= 0 or value["show_rate"] <= 0:
        return None
    booked_per_week = (value["meetings_held_per_month"] / value["show_rate"]) / WEEKS_PER_MONTH
    return booked_per_week / (WORKING_DAYS_PER_WEEK * conversations_per_day)


def resolve_targets(profile: dict, defaults: dict | None = None) -> dict:
    """Merge a team's targets over the defaults and calculate the derived ones."""
    base = (defaults or load_defaults())["targets"]
    overrides = profile.get("targets", {})
    unknown = sorted(set(overrides) - set(base))
    if unknown:
        raise ValueError(f"Unknown targets in the team profile: {', '.join(unknown)}")

    resolved = {key: dict(entry) for key, entry in base.items()}
    for key, override in overrides.items():
        resolved[key] = {**resolved[key], "source": "team", "derived": False, **override}

    if resolved["meeting_rate"]["value"] is None:
        rate = derive_meeting_rate(resolved, profile.get("channels", []))
        resolved["meeting_rate"] = {**resolved["meeting_rate"], "value": rate}
    return resolved


def meetings_per_working_day(targets: dict) -> float:
    """Convert the monthly meeting target into a daily one."""
    return targets["meetings_held_per_month"]["value"] / (WEEKS_PER_MONTH * WORKING_DAYS_PER_WEEK)


def month_in_role(start: date, on: date) -> int:
    """Return the rep's month in role, where month 1 is the first 30 days."""
    return max((on - start).days, 0) // DAYS_PER_ROLE_MONTH + 1


def ramp_multiplier(month: int, ramp: dict) -> float:
    """Return the share of count targets that applies in a given month in role."""
    return float(ramp.get(str(month), 1.0))
