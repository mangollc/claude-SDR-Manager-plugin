#!/usr/bin/env python3
"""Command-line tool behind the sdr-manager plugin. Every command prints JSON.

This file skips `from __future__ import annotations` on purpose: the version check
below has to run before anything that a very old Python can't compile.
"""
import sys

if sys.version_info < (3, 9):
    sys.stdout.write('{"status": "error", "error": "sdr-manager needs Python 3.9 or newer."}\n')
    sys.exit(3)

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sdrlib import environment, file_reader, normalize, profile, scorecard, targets  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NEEDS_INPUT = 2
# Problems the manager can fix, so skills get a plain message rather than a failure.
EXPECTED_ERRORS = (file_reader.UnsupportedFile, profile.ProfileError, ValueError)


class UsageError(Exception):
    """Raised when a command line can't be understood."""


class JsonArgumentParser(argparse.ArgumentParser):
    """Argument parser that reports problems as JSON instead of printing usage text."""

    def error(self, message: str) -> None:
        raise UsageError(message)


def run_check_env(_args: argparse.Namespace) -> tuple[int, dict]:
    return EXIT_OK, environment.report()


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
    return EXIT_OK, scorecard.summarize(scorecard.build_scorecard(workspace, args.week), workspace)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="sdr.py", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    check_env = commands.add_parser("check-env", help="Check Python, openpyxl, and browser")
    check_env.set_defaults(handler=run_check_env)

    inspect = commands.add_parser("inspect", help="Preview an export safely")
    inspect.add_argument("file")
    inspect.add_argument("--header-row", type=int)
    inspect.add_argument("--workspace")
    inspect.set_defaults(handler=run_inspect)

    show_targets = commands.add_parser("targets", help="Check the profile and print targets")
    show_targets.add_argument("--workspace", required=True)
    show_targets.set_defaults(handler=run_targets)

    normalize_exports = commands.add_parser("normalize", help="Store counts from exports")
    normalize_exports.add_argument("--workspace", required=True)
    normalize_exports.add_argument("--files", nargs="+", required=True)
    normalize_exports.add_argument("--week")
    normalize_exports.set_defaults(handler=run_normalize)

    build_metrics = commands.add_parser("metrics", help="Build and save a week's scorecard data")
    build_metrics.add_argument("--workspace", required=True)
    build_metrics.add_argument("--week")
    build_metrics.set_defaults(handler=run_metrics)

    return parser


def main(argv: "list[str] | None" = None) -> int:
    """Run one command, print its JSON result, and return the exit code."""
    try:
        args = build_parser().parse_args(argv)
        code, payload = args.handler(args)
    except (UsageError, *EXPECTED_ERRORS) as error:
        code, payload = EXIT_NEEDS_INPUT, {"status": "error", "error": str(error)}
    except Exception as error:  # A last resort, so skills never see a raw traceback.
        code, payload = EXIT_ERROR, {"status": "error", "error": f"{type(error).__name__}: {error}"}
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
