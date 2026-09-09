"""Behavioral tests for the isolated Docker collector."""

from __future__ import annotations

import json
import io
import os
import signal
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
if os.environ.get("SKYNET_ENTRYPOINT") != "console" and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skynet.cli import main  # noqa: E402
from skynet import docker  # noqa: E402


def test_cli_preserves_empty_host_and_rejects_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[list[str]] = []
    def run(args: list[str]) -> str:
        calls.append(args)
        output = ""
        if "ps" in args:
            output = '{"ID":"a","Names":"web","Image":"web:1","State":"running","Status":"Up","Labels":"x","Platform":null}\n'
        if "image" in args:
            output = '{"ID":"i","Repository":"web","Tag":"1","Size":"1MB","Platform":null}\n'
        return output
    monkeypatch.setattr(docker, "_run", run)
    output = tmp_path / "docker.json"
    assert main(["collect", "docker", "docker-dmz", "--output", str(output), "--json"]) == 0
    snapshot = json.loads(output.read_text())
    assert snapshot["host"] == "docker-dmz" and len(snapshot["containers"]) == 1
    assert snapshot["images"][0]["Platform"] is None
    previous = output.read_bytes()
    monkeypatch.setattr(docker, "_run", lambda args: "not-json\n")
    assert main(["collect", "docker", "docker-dmz", "--output", str(output), "--json"]) != 0
    assert output.read_bytes() == previous
    assert calls[0] == ["docker", "context", "inspect", "docker-dmz"]


def test_empty_lists_are_valid_but_required_fields_are_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outputs = iter(["", "", ""])
    monkeypatch.setattr(docker, "_run", lambda args: next(outputs))
    snapshot = docker.snapshot("docker-dmz", "docker-dmz")
    assert snapshot["containers"] == [] and snapshot["images"] == []

    for field, value in (("ID", None), ("Names", []), ("Image", ""), ("Labels", None)):
        row = {"ID": "a", "Names": "web", "Image": "web:1", "State": "running",
               "Status": "Up", "Labels": "", "Platform": None}
        row[field] = value
        with pytest.raises(docker.CollectionError):
            docker._lines(json.dumps(row), {"ID", "Names", "Image", "State", "Status", "Labels"})


def test_timeout_kills_owned_docker_descendants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent, ready, destination = _write_child_process(tmp_path)
    monkeypatch.setattr(docker, "TIMEOUT", 0.3)
    monkeypatch.setattr(docker, "CLEANUP_TIMEOUT", 1.0)
    with pytest.raises(docker.CollectionError):
        docker._run([sys.executable, str(parent)])
    _assert_child_stopped(ready, destination)


def _write_child_process(tmp_path: Path, *, early_exit: bool = False) -> tuple[Path, Path, Path]:
    ready = tmp_path / "ready"
    destination = tmp_path / "late-write"
    child = tmp_path / "child.py"
    parent = tmp_path / "parent.py"
    child.write_text(
        "import os, signal, time\n"
        "from pathlib import Path\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        f"Path({str(ready)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(10)\n"
        f"Path({str(destination)!r}).touch()\n"
    )
    parent.write_text(
        "import subprocess, sys, time\n"
        "from pathlib import Path\n"
        f"subprocess.Popen([sys.executable, {str(child)!r}], stdout=subprocess.DEVNULL, "
        "stderr=subprocess.DEVNULL)\n"
        f"while not Path({str(ready)!r}).exists(): time.sleep(0.001)\n"
        + ("raise SystemExit(0)\n" if early_exit else "time.sleep(10)\n")
    )
    return parent, ready, destination


def _assert_child_stopped(ready: Path, destination: Path) -> None:
    assert ready.exists()
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        try:
            os.kill(int(ready.read_text()), 0)
        except ProcessLookupError:
            break
        time.sleep(0.01)
    else:
        pytest.fail("Docker descendant survived cleanup")
    time.sleep(0.5)
    assert not destination.exists()


def test_early_exit_kills_owned_docker_descendants(tmp_path: Path) -> None:
    parent, ready, destination = _write_child_process(tmp_path, early_exit=True)
    assert docker._run([sys.executable, str(parent)]) == ""
    _assert_child_stopped(ready, destination)


@pytest.mark.parametrize("interruption", [signal.SIGINT, signal.SIGTERM])
def test_signal_interrupts_docker_and_reaps_descendant(
    tmp_path: Path, interruption: signal.Signals,
) -> None:
    parent, ready, destination = _write_child_process(tmp_path)
    timer = threading.Timer(0.2, os.kill, (os.getpid(), interruption))
    timer.start()
    try:
        with pytest.raises(KeyboardInterrupt):
            docker._run([sys.executable, str(parent)])
    finally:
        timer.cancel()
    _assert_child_stopped(ready, destination)


def test_standalone_cleanup_failure_is_json_recovery_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docker, "snapshot", lambda label, context: (_ for _ in ()).throw(
        docker.CleanupError("synthetic cleanup failure")))
    output = io.StringIO()
    code = docker.collect("docker-dmz", tmp_path / "docker.json", "docker-dmz",
                          json_output=True, stdout=output)
    report = json.loads(output.getvalue())
    assert code == 1 and report["outcome"] == "recovery-required"
