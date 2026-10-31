#!/usr/bin/env python3
"""Install the SDR Manager skills globally for Claude, Codex, Cursor, and other agent tools.

This is the route the README uses. See docs/technical-guide.md for the plugin route.

This file skips `from __future__ import annotations` on purpose: the version check below has
to run before anything that a very old Python can't compile.
"""

import sys

if sys.version_info < (3, 9):  # noqa: UP036  Deliberately checks for an unsupported Python.
    sys.stderr.write("SDR Manager needs Python 3.9 or newer. Get it from python.org/downloads\n")
    sys.exit(3)

import argparse
import re
import shutil
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SKILLS = ("setup", "scorecard", "one-on-one", "rewrite")
SKILL_PREFIX = "sdr-"
RUNTIME_FOLDERS = ("scripts", "assets", "references", "sample-data")
RUNTIME_FOLDER_NAME = ".sdr-manager"
PLUGIN_ROOT_PLACEHOLDER = "${CLAUDE_PLUGIN_ROOT}"
MINIMUM_PYTHON = (3, 9)

# Where each kind of tool looks for global skills, relative to the home folder. Codex, Cursor,
# and VS Code Copilot all read the shared agents folder.
TOOL_FOLDERS = {
    "agents": (".agents", "skills"),
    "claude": (".claude", "skills"),
}


def python_ok(version_info: Sequence[int]) -> bool:
    """Return True when the given Python version is new enough."""
    return tuple(version_info[:2]) >= MINIMUM_PYTHON


def adapt_skill(text: str, skill: str, runtime: Path) -> str:
    """Turn a plugin skill into a standalone one that any agent tool can load."""
    adapted = text.replace(PLUGIN_ROOT_PLACEHOLDER, runtime.as_posix())
    adapted = re.sub(
        rf"^name: {re.escape(skill)}$",
        f"name: {SKILL_PREFIX}{skill}",
        adapted,
        count=1,
        flags=re.MULTILINE,
    )
    return re.sub(r"^argument-hint: .*\n", "", adapted, count=1, flags=re.MULTILINE)


def _copy_runtime(runtime: Path) -> None:
    runtime.mkdir(parents=True, exist_ok=True)
    for folder in RUNTIME_FOLDERS:
        destination = runtime / folder
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(
            REPO_ROOT / folder,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )


def install_skills(skills_dir: Path, runtime: Path) -> None:
    """Copy the program to `runtime`, then write the skills into `skills_dir`."""
    if runtime.resolve() == REPO_ROOT:
        raise ValueError("Choose a program folder other than this source folder.")
    _copy_runtime(runtime)
    for skill in SKILLS:
        source = (REPO_ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        folder = skills_dir / f"{SKILL_PREFIX}{skill}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SKILL.md").write_text(adapt_skill(source, skill, runtime), encoding="utf-8")


def uninstall_skills(skills_dir: Path, runtime: Path) -> None:
    """Remove only what the installer added. Team workspaces live elsewhere and stay."""
    for skill in SKILLS:
        shutil.rmtree(skills_dir / f"{SKILL_PREFIX}{skill}", ignore_errors=True)
    for folder in RUNTIME_FOLDERS:
        shutil.rmtree(runtime / folder, ignore_errors=True)
    if runtime.exists() and not any(runtime.iterdir()):
        runtime.rmdir()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--tool",
        choices=sorted(TOOL_FOLDERS),
        default="agents",
        help="agents: Codex, Cursor, and VS Code Copilot. claude: Claude Code without the plugin.",
    )
    parser.add_argument("--skills-dir", help="Install into this skills folder instead.")
    parser.add_argument("--home", help="Use this folder as the home folder.")
    parser.add_argument("--uninstall", action="store_true", help="Remove the skills and program.")
    return parser


def main(argv: "list[str] | None" = None) -> int:
    args = build_parser().parse_args(argv)
    home = Path(args.home) if args.home else Path.home()
    skills_dir = (
        Path(args.skills_dir) if args.skills_dir else home.joinpath(*TOOL_FOLDERS[args.tool])
    )
    runtime = home / RUNTIME_FOLDER_NAME
    names = ", ".join(f"{SKILL_PREFIX}{skill}" for skill in SKILLS)
    if args.uninstall:
        uninstall_skills(skills_dir, runtime)
        sys.stdout.write("Removed SDR Manager. Your team workspaces weren't touched.\n")
        return 0
    install_skills(skills_dir, runtime)
    sys.stdout.write(
        "SDR Manager is installed.\n\n"
        f"  Skills:  {skills_dir} ({names})\n"
        f"  Program: {runtime}\n\n"
        "Restart your AI tool, then ask it to set up SDR Manager with the sample team.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
