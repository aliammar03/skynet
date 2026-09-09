"""T1 Docker observations through an explicit read-only context."""

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from skynet.proxmox import CollectionError, publish

TIMEOUT = 20


def _label(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise CollectionError("invalid Docker host label", 3)
    return value


def _run(args: list[str]) -> str:
    try:
        completed = subprocess.run(args, check=True, capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise CollectionError("Docker context or command unavailable", 3) from None
    return completed.stdout


def _lines(raw: str, required: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            raise CollectionError("malformed Docker JSON output") from None
        if not isinstance(row, dict) or not required <= row.keys() or any(
                not isinstance(key, str) or value is not None and not isinstance(value, str)
                for key, value in row.items()):
            raise CollectionError("malformed Docker JSON output")
        rows.append(row)
    return rows


def snapshot(label: str, context: str) -> dict[str, Any]:
    """Require a configured context plus complete container and image JSON-line responses."""
    label = _label(label)
    _label(context)
    _run(["docker", "context", "inspect", context])
    containers = _lines(_run(["docker", "--context", context, "ps", "--all", "--format", "{{json .}}"]),
                        {"ID", "Names", "Image", "State", "Status", "Labels"})
    images = _lines(_run(["docker", "--context", context, "image", "ls", "--format", "{{json .}}"]),
                    {"ID", "Repository", "Tag", "Size"})
    return {"host": label, "collected": datetime.now(UTC).isoformat(timespec="seconds"),
            "containers": containers, "images": images}


def collect(label: str, output: Path, context: str, *, json_output: bool, stdout: TextIO) -> int:
    """Collect one atomic Docker host snapshot; failure retains destination bytes."""
    report: dict[str, Any] = {"target": f"docker-{label}", "output": str(output)}
    try:
        data = snapshot(label, context)
        publish(output, data)
    except CollectionError as error:
        report.update(outcome="unavailable" if error.code == 3 else "failure",
                      reason=f"{error}; refresh failed; any retained snapshot is previous evidence")
        code = error.code
    else:
        report.update(outcome="success", collected=data["collected"],
                      counts={"containers": len(data["containers"]), "images": len(data["images"])})
        code = 0
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"{report['target']}: {report['outcome']} → {report['output']}", file=stdout)
        if code:
            print(report["reason"], file=stdout)
    return code
