"""Behavioral tests for the static, authored Caddy route collector."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
if os.environ.get("SKYNET_ENTRYPOINT") != "console" and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import skynet.routes as routes  # noqa: E402
from skynet.proxmox import CollectionError  # noqa: E402


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    (path / "compose" / "caddy-apps").mkdir(parents=True)
    (path / "compose" / "books").mkdir(parents=True)
    (path / "compose" / "books" / "compose.yaml").write_text(
        "services:\n  books:\n    networks:\n      macvlan:\n        ipv4_address: 10.10.100.11\n"
    )
    (path / "inventory").mkdir()
    (path / "inventory" / "proxmox-core.json").write_text(json.dumps({
        "resources": [{"type": "qemu", "vmid": 837, "name": "authentik"}],
    }))
    (path / "compose" / "caddy-apps" / "Caddyfile").write_text(
        "auth.aliammar.net {\n"
        "    reverse_proxy 10.10.80.37:9000\n"
        "}\n"
        "books.aliammar.net {\n"
        "    forward_auth 10.10.80.37:9000 {\n"
        "        uri /outpost.goauthentik.io/auth\n"
        "    }\n"
        "    reverse_proxy 10.10.100.11:8080\n"
        "}\n"
        "unknown.aliammar.net {\n"
        "    reverse_proxy 10.10.99.9:1234\n"
        "}\n"
        "landing.aliammar.net {\n"
        "    respond \"ok\"\n"
        "}\n"
    )
    return path


@pytest.fixture
def entity(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def run(*args: Any, **kwargs: Any) -> SimpleNamespace:
        calls.append({"args": args, "kwargs": kwargs})
        return SimpleNamespace(
            returncode=0,
            stdout="10.10.80.37\tguest/authentik-identity-837\n",
            stderr="",
        )

    monkeypatch.setattr(routes.subprocess, "run", run)
    return calls


def test_snapshot_records_static_provenance_and_resolves_auth_backend_service_and_host(
    repo: Path, entity: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(routes.socket, "gethostname", lambda: "ops-vm-vlan90")

    snapshot = routes.snapshot(repo)

    assert snapshot["host"] == "ops-vm-vlan90"
    assert snapshot["source"] == routes.SOURCE
    assert snapshot["counts"] == {"routes": 4}
    assert [route["vhost"] for route in snapshot["routes"]] == [
        "auth.aliammar.net", "books.aliammar.net", "unknown.aliammar.net", "landing.aliammar.net"
    ]
    assert all(route["front_door"] == "svc/caddy-apps" for route in snapshot["routes"])
    assert all(route["front_door_alias"] == "HOST_PROXY_APPS" for route in snapshot["routes"])

    auth, books, unknown, landing = snapshot["routes"]
    assert auth["backend_entity"] == "guest/authentik-identity-837"
    assert auth["auth"] == "identity (authentik)"
    assert books["backend"] == "10.10.100.11:8080"
    assert books["backend_entity"] == "svc/books"
    assert books["auth"] == "forward_auth (authentik)"
    assert unknown["backend_entity"] == "host:10.10.99.9"
    assert unknown["auth"] == "own-auth/plain"
    assert landing["backend"] == ""
    assert landing["backend_entity"] == "—"
    assert landing["auth"] == "own-auth/plain"

    assert len(entity) == 1
    call = entity[0]
    assert call["args"] == (["bash", "-c", routes._ENTITY_SCRIPT, "entity", str(repo)],)
    assert call["kwargs"]["cwd"] == repo
    assert call["kwargs"]["input"] == "837\tauthentik\n"
    assert call["kwargs"]["timeout"] == routes.ENTITY_TIMEOUT
    assert call["kwargs"]["text"] is True and call["kwargs"]["capture_output"] is True


def test_entity_derivation_failure_is_unavailable_and_retains_previous_bytes(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = repo / "routes.json"
    previous = b'{"retained":true}\n'
    output.write_bytes(previous)

    def fail(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="", stderr="synthetic failure")

    monkeypatch.setattr(routes.subprocess, "run", fail)
    stream = io.StringIO()
    code = routes.collect(repo, output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 1 and report["outcome"] == "failure"
    assert "entity derivation failed" in report["reason"]
    assert output.read_bytes() == previous


def test_entity_transport_failure_is_unavailable_and_does_not_leak_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = repo / "routes.json"
    output.write_text('{"retained":true}\n')

    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise subprocess.TimeoutExpired("entity", routes.ENTITY_TIMEOUT)

    monkeypatch.setattr(routes.subprocess, "run", fail)
    stream = io.StringIO()
    code = routes.collect(repo, output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 1 and report["outcome"] == "failure"
    assert "TimeoutExpired" not in report["reason"]
    assert output.read_text() == '{"retained":true}\n'


def test_missing_caddyfile_is_unavailable_and_retains_previous_bytes(
    repo: Path, entity: list[dict[str, Any]]
) -> None:
    del entity
    caddyfile = repo / routes.CADDYFILE
    caddyfile.unlink()
    assert not caddyfile.exists()
    output = repo / "routes.json"
    previous = b'{"retained":true}\n'
    output.write_bytes(previous)
    stream = io.StringIO()

    code = routes.collect(repo, output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 3 and report["outcome"] == "unavailable"
    assert output.read_bytes() == previous


def test_empty_caddyfile_is_failure_and_retains_previous_bytes(
    repo: Path, entity: list[dict[str, Any]]
) -> None:
    del entity
    (repo / routes.CADDYFILE).write_text("")
    output = repo / "routes.json"
    previous = b'{"retained":true}\n'
    output.write_bytes(previous)
    stream = io.StringIO()

    code = routes.collect(repo, output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 1 and report["outcome"] == "failure"
    assert "no supported routes" in report["reason"]
    assert output.read_bytes() == previous


def test_unsupported_caddyfile_is_failure_and_retains_previous_bytes(
    repo: Path, entity: list[dict[str, Any]]
) -> None:
    del entity
    (repo / routes.CADDYFILE).write_text(
        "example.com {\n"
        "    respond \"outside supported route domain\"\n"
        "}\n"
    )
    output = repo / "routes.json"
    previous = b'{"retained":true}\n'
    output.write_bytes(previous)
    stream = io.StringIO()

    code = routes.collect(repo, output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 1 and report["outcome"] == "failure"
    assert "no supported routes" in report["reason"]
    assert output.read_bytes() == previous


def test_unclosed_caddy_route_block_is_failure_and_retains_previous_bytes(
    repo: Path, entity: list[dict[str, Any]]
) -> None:
    del entity
    (repo / routes.CADDYFILE).write_text(
        "complete.aliammar.net {\n"
        "    reverse_proxy 10.10.100.11:8080\n"
        "}\n"
        "truncated.aliammar.net {\n"
        "    reverse_proxy 10.10.99.9:1234\n"
    )
    output = repo / "routes.json"
    previous = b'{"retained":true}\n'
    output.write_bytes(previous)
    stream = io.StringIO()

    code = routes.collect(repo, output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 1 and report["outcome"] == "failure"
    assert "malformed Caddy route block" in report["reason"]
    assert output.read_bytes() == previous


def test_publication_failure_keeps_previous_route_snapshot(
    repo: Path, entity: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    output = repo / "routes.json"
    previous = b'{"retained":true}\n'
    output.write_bytes(previous)

    def fail_publish(_output: Path, _data: dict[str, Any]) -> None:
        raise CollectionError("local snapshot publication failed")

    monkeypatch.setattr(routes, "publish", fail_publish)
    stream = io.StringIO()
    code = routes.collect(repo, output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 1 and report["outcome"] == "failure"
    assert output.read_bytes() == previous
