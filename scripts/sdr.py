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

from sdrlib import environment  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NEEDS_INPUT = 2


class UsageError(Exception):
    """Raised when a command line can't be understood."""


class JsonArgumentParser(argparse.ArgumentParser):
    """Argument parser that reports problems as JSON instead of printing usage text."""

    def error(self, message: str) -> None:
        raise UsageError(message)


def run_check_env(_args: argparse.Namespace) -> tuple[int, dict]:
    return EXIT_OK, environment.report()


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="sdr.py", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    check_env = commands.add_parser("check-env", help="Check Python, openpyxl, and browser")
    check_env.set_defaults(handler=run_check_env)

    return parser


def main(argv: "list[str] | None" = None) -> int:
    """Run one command, print its JSON result, and return the exit code."""
    try:
        args = build_parser().parse_args(argv)
        code, payload = args.handler(args)
    except UsageError as error:
        code, payload = EXIT_NEEDS_INPUT, {"status": "error", "error": str(error)}
    except Exception as error:  # A last resort, so skills never see a raw traceback.
        code, payload = EXIT_ERROR, {"status": "error", "error": f"{type(error).__name__}: {error}"}
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
