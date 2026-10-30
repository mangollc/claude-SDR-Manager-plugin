"""Checks for what the plugin needs on the manager's computer."""
from __future__ import annotations

import importlib.util
import platform
import shutil
from pathlib import Path
from typing import Sequence

MINIMUM_PYTHON = (3, 9)

BROWSER_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
)
BROWSER_COMMANDS = (
    "google-chrome",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "brave-browser",
)


def python_ok(version_info: Sequence[int]) -> bool:
    """Return True when the given Python version is new enough."""
    return tuple(version_info[:2]) >= MINIMUM_PYTHON


def find_browser() -> str | None:
    """Return the path of a browser that can print PDFs, or None."""
    for candidate in BROWSER_PATHS:
        if Path(candidate).exists():
            return candidate
    for command in BROWSER_COMMANDS:
        found = shutil.which(command)
        if found:
            return found
    return None


def report() -> dict:
    """Describe the current computer for the setup skill."""
    return {
        "python": platform.python_version(),
        "openpyxl": importlib.util.find_spec("openpyxl") is not None,
        "browser": find_browser(),
    }
