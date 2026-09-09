"""Behavioral tests for bounded, unprivileged host reconnaissance."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
if os.environ.get("SKYNET_ENTRYPOINT") != "console" and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skynet import recon  # noqa: E402


FIXTURES = Path(__file__).parent / "fixtures" / "recon"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def fake_run_factory(
    output: str,
    calls: list[tuple[list[str], dict[str, Any]]],
):
    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

    return fake_run


def test_local_probe_uses_bash_stdin_without_ssh_or_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []
    monkeypatch.setattr(
        recon.subprocess, "run", fake_run_factory(fixture("complete.marker"), calls)
    )
    output = StringIO()

    assert recon.run("local", json_output=True, stdout=output) == 0

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == ["bash", "-s"]
    assert kwargs["input"] == recon.PROBE
    assert kwargs.get("shell", False) is False
    assert kwargs["timeout"] == recon.SESSION_TIMEOUT
    assert not any(word in args for word in ("ssh", "sudo", "su", "doas"))


def test_bare_remote_target_is_forced_to_svc_ops_over_argument_array_ssh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []
    monkeypatch.setattr(
        recon.subprocess, "run", fake_run_factory(fixture("complete.marker"), calls)
    )

    assert recon.run("10.10.100.15", json_output=True, stdout=StringIO()) == 0

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
        "svc-ops@10.10.100.15", "bash", "-s",
    ]
    assert kwargs["input"] == recon.PROBE
    assert kwargs.get("shell", False) is False
    assert "root@" not in args
    assert not any(word in args for word in ("sudo", "su", "doas", "grant"))


@pytest.mark.parametrize("target", ["root@10.10.100.15", "svc-ops@docker-dmz", "-oProxyCommand=x"])
def test_user_and_option_targets_are_rejected_before_any_subprocess(
    monkeypatch: pytest.MonkeyPatch, target: str,
) -> None:
    monkeypatch.setattr(recon.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("ran"))
    output = StringIO()

    assert recon.run(target, json_output=True, stdout=output) == 3
    assert json.loads(output.getvalue())["outcome"] == "unavailable"


def test_user_supplied_ssh_identity_is_rejected_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []
    monkeypatch.setattr(
        recon.subprocess, "run", fake_run_factory(fixture("complete.marker"), calls)
    )
    output = StringIO()

    assert recon.run("root@10.10.100.15", json_output=True, stdout=output) == 3

    report = json.loads(output.getvalue())
    assert report["outcome"] == "unavailable"
    assert calls == []


def test_timeout_is_bounded_and_partial_probe_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeout_calls: list[tuple[list[str], dict[str, Any]]] = []

    def timeout(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        timeout_calls.append((args, kwargs))
        raise subprocess.TimeoutExpired(
            args, recon.SESSION_TIMEOUT, output=fixture("partial.marker")
        )

    monkeypatch.setattr(recon.subprocess, "run", timeout)
    output = StringIO()

    assert recon.run("local", json_output=True, stdout=output) == 3

    report = json.loads(output.getvalue())
    assert report["target"] == "recon"
    assert report["outcome"] == "unavailable"
    assert "TimeoutExpired" not in output.getvalue()
    assert "partial.marker" not in output.getvalue()
    assert timeout_calls[0][1]["timeout"] == recon.SESSION_TIMEOUT


def test_partial_marker_stream_is_not_rendered_as_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []
    monkeypatch.setattr(
        recon.subprocess, "run", fake_run_factory(fixture("partial.marker"), calls)
    )
    output = StringIO()

    assert recon.run("local", json_output=True, stdout=output) == 3
    report = json.loads(output.getvalue())
    assert report["outcome"] == "unavailable"


@pytest.mark.parametrize("json_output", [True, False])
def test_renderers_keep_machine_and_human_output_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    json_output: bool,
) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []
    monkeypatch.setattr(
        recon.subprocess, "run", fake_run_factory(fixture("complete.marker"), calls)
    )
    output = StringIO()

    assert recon.run("local", json_output=json_output, stdout=output) == 0
    rendered = output.getvalue()

    if json_output:
        report = json.loads(rendered)
        assert report["target"] == "recon"
        assert report["outcome"] == "success"
        assert report["host"] == "worker.example.test"
        assert report["as"] == "svc-ops@worker.example.test"
        assert set(report["sections"]) == {
            "Host", "Load / memory / CPU", "Disk — usage then inodes",
            "systemd — failed units", "Listening sockets (TCP/UDP)",
            "Containers (docker, unprivileged)", "Recent warnings/errors (journal, last boot)",
            "Recent config changes — /etc modified in last 7 days",
            "Recent package changes (last 20)",
        }
        assert not rendered.startswith("# recon:")
    else:
        assert rendered.startswith("# recon: worker.example.test\n")
        assert "collected: 2026-09-09T12:00:00+00:00   as: svc-ops@worker.example.test" in rendered
        assert "## Host\n\n```\nkernel : Linux 6.12.0 synthetic" in rendered
        assert "_recon complete — T1 read-only." in rendered
        assert '"sections"' not in rendered
