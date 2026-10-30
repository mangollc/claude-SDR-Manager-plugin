"""Create team workspaces and load the sample team."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from . import coaching, history
from .profile import PROFILE_FILE, VALID_CHANNELS, active_reps, load_profile, rep_slug

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = PLUGIN_ROOT / "sample-data"
SAMPLE_WEEK = "2026-W44"
FOLDERS = ("imports", "mappings", "history", "reports", "coaching")
# A real team comes first, so sample data is never picked over it.
USUAL_FOLDERS = ("sdr-workspace", "sdr-demo", ".")
STARTER_PROFILE = {
    "company": "",
    "product": "",
    "ideal_customer": "",
    "channels": list(VALID_CHANNELS),
    "reps": [],
    "ignored_names": [],
    "targets": {},
}


def _load_sample(path: Path) -> Path:
    shutil.copy(SAMPLE_DIR / "team-profile.json", path / PROFILE_FILE)
    imports = path / "imports" / SAMPLE_WEEK
    imports.mkdir(parents=True)
    for export in (SAMPLE_DIR / "exports").iterdir():
        shutil.copy(export, imports / export.name)
    return imports


def init_workspace(path: Path, sample: bool = False) -> dict:
    """Create a workspace, leaving any existing one untouched."""
    if (path / PROFILE_FILE).exists():
        return {"status": "ok", "path": str(path), "already_exists": True}
    for name in FOLDERS:
        (path / name).mkdir(parents=True, exist_ok=True)
    # Coaching notes and exports are sensitive, so Git ignores the whole workspace.
    if not (path / ".gitignore").exists():
        (path / ".gitignore").write_text("*\n", encoding="utf-8")
    profile = json.dumps(STARTER_PROFILE, indent=2) + "\n"
    (path / PROFILE_FILE).write_text(profile, encoding="utf-8")
    result = {"status": "ok", "path": str(path), "already_exists": False}
    if sample:
        return {**result, "imports": str(_load_sample(path)), "week": SAMPLE_WEEK}
    return result


def find_workspaces(start: Path) -> list[Path]:
    """Return the workspaces in a folder. Search tools can't do this, because each
    workspace has a .gitignore that hides its contents from them."""
    found = [(start / name).resolve() for name in USUAL_FOLDERS]
    return [path for path in found if (path / PROFILE_FILE).exists()]


def _rep_summaries(path: Path, team: dict, scorecard: dict | None) -> list[dict]:
    statuses = {rep["name"]: rep["status"] for rep in (scorecard or {}).get("reps", [])}
    return [
        {
            "name": rep["name"],
            "slug": rep_slug(rep["name"]),
            "status": statuses.get(rep["name"]),
            "coaching_file": str(coaching.coaching_path(path, rep["name"])),
            "has_coaching_history": bool(coaching.read_history(path, rep["name"])),
        }
        for rep in active_reps(team)
    ]


def _waiting_exports(path: Path) -> dict[str, list[str]]:
    folders = sorted(item for item in (path / "imports").glob("*") if item.is_dir())
    return {folder.name: sorted(item.name for item in folder.iterdir()) for folder in folders}


def describe_workspace(path: Path, now: datetime) -> dict:
    """Return what the skills need to know about a workspace before they start."""
    team = load_profile(path)
    week = history.latest_metrics_week(path)
    scorecard = history.read_metrics(path, week) if week else None
    age = None
    if scorecard:
        age = (now - datetime.fromisoformat(scorecard["generated_at"])).days
    return {
        "status": "ok",
        "workspace": str(path),
        "latest_week": week,
        "metrics_path": str(history.metrics_path(path, week)) if week else None,
        "metrics_age_days": age,
        "reps": _rep_summaries(path, team, scorecard),
        "imports": _waiting_exports(path),
    }
