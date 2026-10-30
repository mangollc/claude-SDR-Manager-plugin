"""Shared test helpers."""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import sdr  # noqa: E402


DEFAULT_PROFILE = {
    "company": "Example Co",
    "product": "Example product",
    "ideal_customer": "Example buyers",
    "channels": ["call", "email", "linkedin"],
    "reps": [
        {"name": "Ava Reyes", "start_date": "2025-01-06", "aliases": ["A. Reyes"], "active": True},
        {"name": "Ben Carter", "start_date": "2025-03-03", "aliases": [], "active": True},
    ],
    "ignored_names": ["Morgan Lee"],
    "targets": {},
}


def run_cli(*args: str) -> tuple[int, dict]:
    """Run the command line in-process and return its exit code and JSON output."""
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
        code = sdr.main(list(args))
    return code, json.loads(stdout.getvalue())


def make_workspace(folder: Path, **profile_changes: object) -> Path:
    """Create a minimal workspace with a team profile and a mappings folder."""
    workspace = folder / "workspace"
    (workspace / "mappings").mkdir(parents=True, exist_ok=True)
    profile = {**DEFAULT_PROFILE, **profile_changes}
    (workspace / "team-profile.json").write_text(json.dumps(profile), encoding="utf-8")
    return workspace


def activity_row(
    day: str,
    rep: str = "Ava Reyes",
    channel: str = "call",
    granularity: str = "day",
    **counts: int,
) -> dict:
    """Build one stored activity row, with every unnamed count set to zero."""
    from sdrlib.history import ACTIVITY_COUNTS

    row = {"date": day, "rep": rep, "channel": channel, "granularity": granularity}
    row.update({name: counts.get(name, 0) for name in ACTIVITY_COUNTS})
    return row
