"""Runtime-only diagnostics for the installed Skynet application."""

import json
import sys
from typing import TextIO

from skynet import installed_version


def runtime_report() -> dict[str, str]:
    """Describe this process, without inspecting the lab or local runtime state."""
    return {
        "outcome": "success",
        "scope": "runtime",
        "version": installed_version(),
        "python_version": sys.version.split()[0],
    }


def write_report(*, json_output: bool, stdout: TextIO) -> None:
    """Write the runtime report in the requested representation."""
    report = runtime_report()
    if json_output:
        print(json.dumps(report, sort_keys=True), file=stdout)
        return

    print("Skynet runtime doctor", file=stdout)
    for key in ("outcome", "scope", "version", "python_version"):
        print(f"{key}: {report[key]}", file=stdout)
