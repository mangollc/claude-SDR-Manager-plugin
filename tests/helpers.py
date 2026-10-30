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


def run_cli(*args: str) -> tuple[int, dict]:
    """Run the command line in-process and return its exit code and JSON output."""
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
        code = sdr.main(list(args))
    return code, json.loads(stdout.getvalue())
