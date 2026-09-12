"""Behavioral tests for the static, authored Caddy route collector."""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path
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


def test_snapshot_records_static_provenance_and_resolves_auth_backend_service_and_host(
    repo: Path, monkeypatch: pytest.MonkeyPatch
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


def test_snapshot_resolves_ambiguous_guest_from_committed_firewall_fact(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "inventory" / "proxmox-core.json").write_text(json.dumps({
        "resources": [{"type": "qemu", "vmid": 1035, "name": "edge"}],
    }))
    (repo / "inventory" / "firewall").mkdir()
    (repo / "inventory" / "firewall" / "firewall.json").write_text(json.dumps({
        "aliases": [{"type": "host", "content": "10.10.100.35"}], "reservations": [],
    }))
    (repo / "compose" / "caddy-apps" / "Caddyfile").write_text(
        "edge.aliammar.net {\n reverse_proxy 10.10.100.35:8080\n}\n"
    )
    monkeypatch.setattr(routes.socket, "gethostname", lambda: "ops-vm-vlan90")

    snapshot = routes.snapshot(repo)

    assert snapshot["routes"][0]["backend_entity"] == "guest/edge-1035"

def test_malformed_guest_inventory_is_unavailable_and_retains_previous_bytes(
    repo: Path
) -> None:
    output = repo / "routes.json"
    previous = b'{"retained":true}\n'
    output.write_bytes(previous)

    (repo / "inventory" / "proxmox-core.json").write_text("{")
    stream = io.StringIO()
    code = routes.collect(repo, output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 3 and report["outcome"] == "unavailable"
    assert "guest inventory unavailable" in report["reason"]
    assert output.read_bytes() == previous


def test_malformed_guest_shape_fails_and_does_not_replace_previous_snapshot(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = repo / "routes.json"
    output.write_text('{"retained":true}\n')

    (repo / "inventory" / "proxmox-core.json").write_text(json.dumps({"resources": {}}))
    stream = io.StringIO()
    code = routes.collect(repo, output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 1 and report["outcome"] == "failure"
    assert "malformed guest inventory" in report["reason"]
    assert output.read_text() == '{"retained":true}\n'


def test_missing_caddyfile_is_unavailable_and_retains_previous_bytes(
    repo: Path
) -> None:
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
    repo: Path
) -> None:
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
    repo: Path
) -> None:
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
    repo: Path
) -> None:
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
    repo: Path, monkeypatch: pytest.MonkeyPatch
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
