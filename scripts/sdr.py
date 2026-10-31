#!/usr/bin/env python3
"""Command-line tool behind the sdr-manager plugin. Every command prints JSON.

This file skips `from __future__ import annotations` on purpose: the version check
below has to run before anything that a very old Python can't compile.
"""

import sys

if sys.version_info < (3, 9):  # noqa: UP036  Deliberately checks for an unsupported Python.
    sys.stdout.write('{"status": "error", "error": "sdr-manager needs Python 3.9 or newer."}\n')
    sys.exit(3)

import argparse
import json
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sdrlib import (
    coaching,
    environment,
    file_reader,
    history,
    narrative_check,
    normalize,
    outreach,
    pdf,
    profile,
    reports,
    scorecard,
    targets,
)
from sdrlib.workspace import describe_workspace, find_workspaces, init_workspace

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NEEDS_INPUT = 2
# Problems the manager can fix, so skills get a plain message rather than a failure.
EXPECTED_ERRORS = (file_reader.UnsupportedFile, profile.ProfileError, ValueError, OSError)


class UsageError(Exception):
    """Raised when a command line can't be understood."""


class JsonArgumentParser(argparse.ArgumentParser):
    """Argument parser that reports problems as JSON instead of printing usage text."""

    def error(self, message: str) -> None:
        raise UsageError(message)


def run_check_env(_args: argparse.Namespace) -> tuple[int, dict]:
    return EXIT_OK, environment.report()


def run_init_workspace(args: argparse.Namespace) -> tuple[int, dict]:
    return EXIT_OK, init_workspace(Path(args.path), args.sample)


def run_status(args: argparse.Namespace) -> tuple[int, dict]:
    found = [Path(args.workspace)] if args.workspace else find_workspaces(Path.cwd())
    if not found:
        message = "There's no team workspace in this folder. Run the SDR Manager setup first."
        return EXIT_NEEDS_INPUT, {"status": "needs_input", "error": message}
    others = [str(path) for path in found[1:]]
    return EXIT_OK, {**describe_workspace(found[0], datetime.now()), "other_workspaces": others}


def run_inspect(args: argparse.Namespace) -> tuple[int, dict]:
    mappings_dir = Path(args.workspace) / "mappings" if args.workspace else None
    return EXIT_OK, file_reader.inspect_file(Path(args.file), args.header_row, mappings_dir)


def run_targets(args: argparse.Namespace) -> tuple[int, dict]:
    team = profile.load_profile(Path(args.workspace))
    return EXIT_OK, {"status": "ok", "targets": targets.resolve_targets(team)}


def run_normalize(args: argparse.Namespace) -> tuple[int, dict]:
    files = [Path(item) for item in args.files]
    report = normalize.normalize_files(Path(args.workspace), files, args.week)
    return (EXIT_OK if report["status"] == "ok" else EXIT_NEEDS_INPUT), report


def run_metrics(args: argparse.Namespace) -> tuple[int, dict]:
    workspace = Path(args.workspace)
    week = args.week or history.latest_week(workspace)
    if week and not history.has_time_off(workspace, week):
        # Otherwise a rep who was out gets judged against a full week.
        message = f"Ask the manager about holidays and time off in {week}, then save the answer."
        return EXIT_NEEDS_INPUT, {
            "status": "needs_input",
            "time_off_missing": week,
            "error": message,
        }
    return EXIT_OK, scorecard.summarize(scorecard.build_scorecard(workspace, week), workspace)


def _read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _known_rep(workspace: Path, name: str) -> str:
    """Return the rep's name from the team profile, accepting aliases."""
    rep = profile.rep_lookup(profile.load_profile(workspace)).get(name.strip().lower())
    if rep is None:
        raise ValueError(f"{name} isn't a rep in the team profile.")
    return rep


def _number_problems(args: argparse.Namespace) -> list:
    workspace = Path(args.workspace)
    rep = _known_rep(workspace, args.rep) if args.rep else None
    coaching_text = coaching.read_history(workspace, rep) if rep else ""
    return narrative_check.check_narrative(_read_json(args.narrative), coaching_text)


def run_check_narrative(args: argparse.Namespace) -> tuple[int, dict]:
    problems = _number_problems(args)
    if problems:
        return EXIT_NEEDS_INPUT, {"status": "needs_input", "problems": problems}
    return EXIT_OK, {"status": "ok", "problems": []}


def _render_report(args: argparse.Namespace, workspace: Path) -> tuple[str, str]:
    """Return a report's HTML and its file name without the extension."""
    metrics_file = history.read_metrics(workspace, args.week)
    narrative = _read_json(args.narrative)
    if args.kind == "team":
        return reports.render_team(metrics_file, narrative), "team-report"
    rep = _known_rep(workspace, args.rep)
    text = reports.render_one_on_one(
        metrics_file, rep, narrative, coaching.read_history(workspace, rep)
    )
    return text, f"one-on-one-{profile.rep_slug(rep)}-{date.today().isoformat()}"


def run_report(args: argparse.Namespace) -> tuple[int, dict]:
    if args.kind == "one-on-one" and not args.rep:
        raise UsageError("A one-on-one report needs --rep with the rep's name.")
    problems = _number_problems(args)
    if problems:
        return EXIT_NEEDS_INPUT, {"status": "needs_input", "problems": problems}
    workspace = Path(args.workspace)
    text, name = _render_report(args, workspace)
    folder = workspace / "reports" / args.week
    folder.mkdir(parents=True, exist_ok=True)
    html_path = folder / f"{name}.html"
    pdf_path = folder / f"{name}.pdf"
    html_path.write_text(text, encoding="utf-8")
    printed = pdf.print_to_pdf(html_path, pdf_path)
    return EXIT_OK, {
        "status": "ok",
        "html": str(html_path),
        "pdf": str(pdf_path) if printed else None,
        "fallback": not printed,
    }


def run_log_coaching(args: argparse.Namespace) -> tuple[int, dict]:
    workspace = Path(args.workspace)
    rep = _known_rep(workspace, args.rep)
    path = coaching.append_entry(workspace, rep, _read_json(args.entry_file), date.today())
    return EXIT_OK, {"status": "ok", "path": str(path)}


def run_check_outreach(args: argparse.Namespace) -> tuple[int, dict]:
    workspace = Path(args.workspace)
    team = profile.load_profile(workspace)
    draft_path = Path(args.draft)
    draft = outreach.load_draft(draft_path)
    result = outreach.check_draft(draft, team)
    if result["problems"]:
        return EXIT_NEEDS_INPUT, {"status": "needs_input", "problems": result["problems"]}
    path = outreach.save_rewrite(workspace, draft, result["to_confirm"], date.today())
    # The draft holds the pasted original, which may have prospect details in it.
    draft_path.unlink()
    return EXIT_OK, {
        "status": "ok",
        "path": str(path),
        "length": result["length"],
        "to_confirm": result["to_confirm"],
    }


def full_path(value: str) -> Path:
    """Expand a short folder name, because skills save files beside the paths reported here."""
    return Path(value).absolute()


WORKSPACE = (("--workspace",), {"required": True, "type": full_path})
OPTIONAL_WORKSPACE = (("--workspace",), {"type": full_path})
WEEK = (("--week",), {"required": True})
OPTIONAL_WEEK = (("--week",), {})
NARRATIVE = (("--narrative",), {"required": True})
OPTIONAL_REP = (("--rep",), {})

# Each command: name, handler, help text, and its arguments.
COMMANDS = (
    ("check-env", run_check_env, "Check Python, openpyxl, and browser", ()),
    (
        "init-workspace",
        run_init_workspace,
        "Create a workspace for a team",
        (
            (("--path",), {"required": True, "type": full_path}),
            (("--sample",), {"action": "store_true"}),
        ),
    ),
    (
        "status",
        run_status,
        "Find the workspace and its latest scorecard",
        (OPTIONAL_WORKSPACE,),
    ),
    (
        "inspect",
        run_inspect,
        "Preview an export safely",
        ((("file",), {}), (("--header-row",), {"type": int}), OPTIONAL_WORKSPACE),
    ),
    ("targets", run_targets, "Check the profile and print targets", (WORKSPACE,)),
    (
        "normalize",
        run_normalize,
        "Store counts from exports",
        (WORKSPACE, (("--files",), {"nargs": "+", "required": True}), OPTIONAL_WEEK),
    ),
    ("metrics", run_metrics, "Build and save a week's scorecard data", (WORKSPACE, OPTIONAL_WEEK)),
    (
        "check-narrative",
        run_check_narrative,
        "Check that Claude's text states no statistics",
        (WORKSPACE, NARRATIVE, OPTIONAL_REP),
    ),
    (
        "report",
        run_report,
        "Build a team or one-on-one PDF",
        (
            (("kind",), {"choices": ["team", "one-on-one"]}),
            WORKSPACE,
            WEEK,
            NARRATIVE,
            OPTIONAL_REP,
        ),
    ),
    (
        "log-coaching",
        run_log_coaching,
        "Add a coaching history entry",
        (WORKSPACE, (("--rep",), {"required": True}), (("--entry-file",), {"required": True})),
    ),
    (
        "check-outreach",
        run_check_outreach,
        "Check a rewritten message, and save it if it passes",
        (WORKSPACE, (("--draft",), {"required": True, "type": full_path})),
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="sdr.py", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler, help_text, arguments in COMMANDS:
        command = commands.add_parser(name, help=help_text)
        for flags, options in arguments:
            command.add_argument(*flags, **options)
        command.set_defaults(handler=handler)
    return parser


def main(argv: "list[str] | None" = None) -> int:
    """Run one command, print its JSON result, and return the exit code."""
    try:
        args = build_parser().parse_args(argv)
        code, payload = args.handler(args)
    except (UsageError, *EXPECTED_ERRORS) as error:
        code, payload = EXIT_NEEDS_INPUT, {"status": "error", "error": str(error)}
    except Exception as error:  # noqa: BLE001  A last resort, so skills never see a traceback.
        code, payload = EXIT_ERROR, {"status": "error", "error": f"{type(error).__name__}: {error}"}
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
