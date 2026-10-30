"""Keep a dated coaching history for each rep."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .profile import rep_slug

REQUIRED_FIELDS = ("focus", "agreed", "check_by")


def coaching_path(workspace: Path, rep: str) -> Path:
    """Return where a rep's coaching history lives."""
    return workspace / "coaching" / f"{rep_slug(rep)}.md"


def read_history(workspace: Path, rep: str) -> str:
    """Return a rep's coaching history, or an empty string if there is none."""
    path = coaching_path(workspace, rep)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _format_entry(entry: dict, today: date) -> str:
    lines = [f"## {today.isoformat()}", f"- Focus: {entry['focus']}"]
    lines += [f"- Agreed: {item}" for item in entry["agreed"]]
    lines.append(f"- Check by: {entry['check_by']}")
    if entry.get("notes"):
        lines.append(f"- Notes: {entry['notes']}")
    return "\n".join(lines) + "\n"


def append_entry(workspace: Path, rep: str, entry: dict, today: date) -> Path:
    """Add a dated entry to the end of a rep's coaching history."""
    missing = [name for name in REQUIRED_FIELDS if not entry.get(name)]
    if missing:
        raise ValueError(f"A coaching entry needs: {', '.join(missing)}.")
    path = coaching_path(workspace, rep)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_history(workspace, rep)
    separator = "\n" if existing else ""
    path.write_text(existing + separator + _format_entry(entry, today), encoding="utf-8")
    return path
