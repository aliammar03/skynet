"""The small command-line interface for Skynet."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from skynet import installed_version
from skynet.doctor import write_report
from skynet.proxmox import DEFAULT_CREDENTIALS, collect


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser shared by both supported entry points."""
    parser = argparse.ArgumentParser(
        prog="skynet",
        description="Skynet operations engine.",
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
    collection = commands.add_parser("collect", help="collect observations, not service health")
    sources = collection.add_subparsers(dest="source", required=True)
    proxmox = sources.add_parser("proxmox", help="collect Proxmox observations")
    targets = proxmox.add_subparsers(dest="target", required=True)
    core = targets.add_parser(
        "core", help="collect core-node observations, not service health",
        description="Collect core-node observations; this does not verify service health.",
    )
    core.add_argument("--output", type=Path, required=True,
                      help="explicit snapshot destination; publish only on complete success")
    core.add_argument("--credentials-file", type=Path, default=DEFAULT_CREDENTIALS,
                      help="literal PVE_HOST/PVE_TOKEN/PVE_CACERT assignments")
    core.add_argument("--json", action="store_true", dest="json_output",
                      help="write one collection outcome object as JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run Skynet's CLI and return its process exit status."""
    arguments = build_parser().parse_args(argv)
    if arguments.command == "doctor":
        write_report(json_output=arguments.json_output, stdout=sys.stdout)
        return 0
    if arguments.command == "collect":
        return collect(arguments.output, arguments.credentials_file,
                       json_output=arguments.json_output, stdout=sys.stdout)
    return _unreachable_command(arguments.command)


def _unreachable_command(command: str) -> NoReturn:
    """Make an unexpected parser result a loud programming error."""
    raise RuntimeError(f"unhandled command: {command}")
