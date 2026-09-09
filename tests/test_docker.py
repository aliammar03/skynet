"""Behavioral tests for the isolated Docker collector."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skynet.cli import main  # noqa: E402
from skynet import docker  # noqa: E402


def test_cli_preserves_empty_host_and_rejects_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[list[str]] = []
    def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        output = "" if args[-3:] != ["ps", "--all", "--format"] else ""
        if "ps" in args:
            output = '{"ID":"a","Names":"web","Image":"web:1","State":"running","Status":"Up","Labels":"x"}\n'
        if "image" in args:
            output = '{"ID":"i","Repository":"web","Tag":"1","Size":"1MB"}\n'
        return subprocess.CompletedProcess(args, 0, output, "")
    monkeypatch.setattr(docker.subprocess, "run", run)
    output = tmp_path / "docker.json"
    assert main(["collect", "docker", "docker-dmz", "--output", str(output), "--json"]) == 0
    snapshot = json.loads(output.read_text())
    assert snapshot["host"] == "docker-dmz" and len(snapshot["containers"]) == 1
    previous = output.read_bytes()
    monkeypatch.setattr(docker, "_run", lambda args: "not-json\n")
    assert main(["collect", "docker", "docker-dmz", "--output", str(output), "--json"]) != 0
    assert output.read_bytes() == previous
    assert calls[0] == ["docker", "context", "inspect", "docker-dmz"]
