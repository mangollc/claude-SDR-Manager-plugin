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


class ProfileError(Exception):
    """Raised when the team profile is missing or invalid. The message is for the manager."""


def _validate(profile: dict) -> None:
    invalid = [item for item in profile.get("channels", []) if item not in VALID_CHANNELS]
    if invalid:
        raise ProfileError(
            f"Unknown channels in {PROFILE_FILE}: {', '.join(invalid)}. "
            "Use call, email, or linkedin."
        )
    for rep in profile.get("reps", []):
        name = str(rep.get("name", "")).strip()
        if not name:
            raise ProfileError(f"Every rep in {PROFILE_FILE} needs a name.")
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
        raise ProfileError(f"No team profile found in {workspace}. Run /sdr-manager:setup first.")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise ProfileError(f"{PROFILE_FILE} isn't valid JSON: {error}") from error
    _validate(profile)
    return profile


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
