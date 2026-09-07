"""The small local command-line interface for Skynet."""

import argparse
import sys
from collections.abc import Sequence
from typing import NoReturn

from skynet import installed_version
from skynet.doctor import write_report


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser shared by both supported entry points."""
    parser = argparse.ArgumentParser(
        prog="skynet",
        description="Skynet operations engine local runtime commands.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {installed_version()}")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="report the local application runtime")
    doctor.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="write one runtime report object as JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run Skynet's local CLI and return its process exit status."""
    arguments = build_parser().parse_args(argv)
    if arguments.command == "doctor":
        write_report(json_output=arguments.json_output, stdout=sys.stdout)
        return 0
    return _unreachable_command(arguments.command)


def _unreachable_command(command: str) -> NoReturn:
    """Make an unexpected parser result a loud programming error."""
    raise RuntimeError(f"unhandled command: {command}")
