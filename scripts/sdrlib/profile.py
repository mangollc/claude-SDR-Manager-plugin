"""Load the team profile and match the names found in exports."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

PROFILE_FILE = "team-profile.json"
VALID_CHANNELS = ("call", "email", "linkedin")
DEFAULT_BRAND = "SDR Manager"
MAX_BRAND_LENGTH = 60


class ProfileError(Exception):
    """Raised when the team profile is missing or invalid. The message is for the manager."""


def _validate_brand(profile: dict) -> None:
    if "brand" not in profile:
        return
    brand = profile["brand"]
    if not isinstance(brand, str) or not brand.strip() or len(brand) > MAX_BRAND_LENGTH:
        raise ProfileError(
            f"brand in {PROFILE_FILE} must be a name of up to {MAX_BRAND_LENGTH} characters."
        )


def _validate_outreach(profile: dict) -> None:
    points = profile.get("proof_points", [])
    if not isinstance(points, list) or not all(
        isinstance(item, str) and item.strip() for item in points
    ):
        raise ProfileError(f"proof_points in {PROFILE_FILE} must be a list of short sentences.")
    limits = profile.get("outreach_limits", {})
    if not isinstance(limits, dict):
        raise ProfileError(f"outreach_limits in {PROFILE_FILE} must list each limit by name.")
    for kind, limit in limits.items():
        value = limit.get("value") if isinstance(limit, dict) else None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ProfileError(f"The {kind} limit in {PROFILE_FILE} must be a positive number.")


def _validate(profile: dict) -> None:
    _validate_brand(profile)
    _validate_outreach(profile)
    invalid = [item for item in profile.get("channels", []) if item not in VALID_CHANNELS]
    if invalid:
        raise ProfileError(
            f"Unknown channels in {PROFILE_FILE}: {', '.join(invalid)}. "
            "Use call, email, or linkedin."
        )
    file_names: dict[str, str] = {}
    for rep in profile.get("reps", []):
        name = str(rep.get("name", "")).strip()
        if not name:
            raise ProfileError(f"Every rep in {PROFILE_FILE} needs a name.")
        slug = rep_slug(name)
        if slug in file_names:
            raise ProfileError(
                f"{file_names[slug]} and {name} would share one coaching file. "
                f"Tell them apart in {PROFILE_FILE}, for example with a middle initial."
            )
        file_names[slug] = name
        start = rep.get("start_date")
        if not start:
            continue
        try:
            date.fromisoformat(start)
        except (TypeError, ValueError) as error:
            raise ProfileError(
                f"{name} has a start date in {PROFILE_FILE} that isn't in YYYY-MM-DD format."
            ) from error


def load_profile(workspace: Path) -> dict:
    """Read and validate the team profile."""
    path = workspace / PROFILE_FILE
    if not path.exists():
        raise ProfileError(
            f"No team profile found in {workspace}. Run the SDR Manager setup first."
        )
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise ProfileError(f"{PROFILE_FILE} isn't valid JSON: {error}") from error
    _validate(profile)
    return profile


def report_brand(profile: dict) -> str:
    """Return the name on a team's reports. A team that was never asked shows its company."""
    for value in (profile.get("brand"), profile.get("company")):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return DEFAULT_BRAND


def rep_lookup(profile: dict) -> dict[str, str | None]:
    """Map lowercased names and aliases to the rep's name, and ignored names to None."""
    lookup: dict[str, str | None] = {
        name.strip().lower(): None for name in profile.get("ignored_names", [])
    }
    for rep in profile.get("reps", []):
        for name in (rep["name"], *rep.get("aliases", [])):
            lookup[name.strip().lower()] = rep["name"]
    return lookup


def active_reps(profile: dict) -> list[dict]:
    """Return the reps still on the team, sorted by name."""
    active = [rep for rep in profile.get("reps", []) if rep.get("active", True)]
    return sorted(active, key=lambda rep: rep["name"].lower())


def rep_slug(name: str) -> str:
    """Turn a rep's name into a safe file name."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", plain.replace("'", "").lower()).strip("-")
    return slug or hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
