"""Create team workspaces and load the sample team."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .profile import PROFILE_FILE, VALID_CHANNELS

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = PLUGIN_ROOT / "sample-data"
SAMPLE_WEEK = "2026-W44"
FOLDERS = ("imports", "mappings", "history", "reports", "coaching")
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
    (path / ".gitignore").write_text("*\n", encoding="utf-8")
    profile = json.dumps(STARTER_PROFILE, indent=2) + "\n"
    (path / PROFILE_FILE).write_text(profile, encoding="utf-8")
    result = {"status": "ok", "path": str(path), "already_exists": False}
    if sample:
        return {**result, "imports": str(_load_sample(path)), "week": SAMPLE_WEEK}
    return result
