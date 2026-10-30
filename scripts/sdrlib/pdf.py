"""Print an HTML report to PDF with a browser already on the computer."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from .environment import find_browser

PRINT_TIMEOUT_SECONDS = 60


def _is_pdf(path: Path) -> bool:
    if not path.exists():
        return False
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def print_to_pdf(
    html_path: Path,
    pdf_path: Path,
    browser: str | None = None,
    runner: Callable = subprocess.run,
) -> bool:
    """Return True if a real PDF was written. On False, the HTML file is still there."""
    chosen = browser or find_browser()
    if chosen is None:
        return False
    pdf_path.unlink(missing_ok=True)  # An old file must not hide a failed print.
    profile_dir = tempfile.mkdtemp(prefix="sdr-manager-")
    command = [
        chosen,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--user-data-dir={profile_dir}",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    try:
        runner(command, capture_output=True, timeout=PRINT_TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)
    return _is_pdf(pdf_path)
