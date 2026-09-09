"""Behavioral tests for the isolated, unverified TLS certificate collector."""

from __future__ import annotations

import json
import io
import os
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
if os.environ.get("SKYNET_ENTRYPOINT") != "console" and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import skynet.certs as certs  # noqa: E402
from skynet.proxmox import CollectionError  # noqa: E402


class FakeRaw:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeWrapped:
    def __init__(self, certificate: bytes) -> None:
        self.certificate = certificate
        self.closed = False

    def __enter__(self) -> "FakeWrapped":
        return self

    def __exit__(self, *_args: object) -> None:
        self.closed = True

    def getpeercert(self, *, binary_form: bool) -> bytes:
        assert binary_form is True
        return self.certificate


class FakeContext:
    def __init__(self, certificates: dict[tuple[str, int], bytes]) -> None:
        self.certificates = certificates
        self.handshakes: list[tuple[str, int, str | None]] = []

    def wrap_socket(self, raw: FakeRaw, *, server_hostname: str | None) -> FakeWrapped:
        del raw
        endpoint = self.current_endpoint
        self.handshakes.append((*endpoint, server_hostname))
        return FakeWrapped(self.certificates[endpoint])

    current_endpoint: tuple[str, int]


def decoded(label: str) -> dict[str, Any]:
    return {
        "issuer": ((('commonName', f"issuer-{label}"), ('organizationName', "Synthetic CA")),),
        "subject": ((('commonName', f"subject-{label}"),),),
        "subjectAltName": (("DNS", f"{label}.example.test"), ("IP Address", "192.0.2.10")),
        "notAfter": "Jan 01 00:00:00 2030 GMT",
    }


@pytest.fixture
def fake_tls(monkeypatch: pytest.MonkeyPatch) -> tuple[FakeContext, list[tuple[str, int, int]]]:
    endpoints = {(host, port): label.encode() for label, host, port, _sni in certs.ENDPOINTS}
    context = FakeContext(endpoints)
    connections: list[tuple[str, int, int]] = []

    def connect(address: tuple[str, int], timeout: int) -> FakeRaw:
        host, port = address
        connections.append((host, port, timeout))
        context.current_endpoint = (host, port)
        return FakeRaw()

    monkeypatch.setattr(certs.ssl, "_create_unverified_context", lambda: context)
    monkeypatch.setattr(certs.socket, "create_connection", connect)
    monkeypatch.setattr(certs, "_decode", lambda certificate: decoded(certificate.decode()))
    return context, connections


def test_snapshot_probes_fixed_endpoints_from_explicit_ops_vantage(
    fake_tls: tuple[FakeContext, list[tuple[str, int, int]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, connections = fake_tls
    monkeypatch.setattr(certs.socket, "gethostname", lambda: "ops-vm-vlan90")

    snapshot = certs.snapshot()

    assert snapshot["host"] == "ops-vm-vlan90"
    assert snapshot["source"] == certs.SOURCE
    assert snapshot["counts"] == {"probed": 7, "reachable": 7}
    assert connections == [(host, port, certs.TIMEOUT) for _label, host, port, _sni in certs.ENDPOINTS]
    assert context.handshakes == [
        (host, port, sni) for _label, host, port, sni in certs.ENDPOINTS
    ]
    first = snapshot["certs"][0]
    assert first["issuer"] == "CN=issuer-opnsense, O=Synthetic CA"
    assert first["subject"] == "CN=subject-opnsense"
    assert first["sans"] == ["opnsense.example.test", "192.0.2.10"]
    assert first["not_after"] == "Jan 01 00:00:00 2030 GMT"
    assert isinstance(first["days_left"], int)


def test_unreachable_handshakes_are_recorded_without_skipping_other_endpoints(
    fake_tls: tuple[FakeContext, list[tuple[str, int, int]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, connections = fake_tls
    unreachable = {("10.10.50.25", 8043), ("10.10.20.40", 8007)}
    real_connect = certs.socket.create_connection

    def connect(address: tuple[str, int], timeout: int) -> FakeRaw:
        if address in unreachable:
            raise OSError("synthetic unreachable endpoint")
        return real_connect(address, timeout)

    monkeypatch.setattr(certs.socket, "create_connection", connect)

    snapshot = certs.snapshot()

    assert snapshot["counts"] == {"probed": 7, "reachable": 5}
    assert [row["label"] for row in snapshot["certs"] if not row["reachable"]] == [
        "omada", "pbs"
    ]
    assert len(connections) == 5
    assert len(context.handshakes) == 5


def test_malformed_leaf_fails_and_retains_previous_bytes(
    tmp_path: Path,
    fake_tls: tuple[FakeContext, list[tuple[str, int, int]]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "certs.json"
    previous = b'{"retained":true}\n'
    output.write_bytes(previous)
    monkeypatch.setattr(certs, "_decode", lambda _certificate: {})

    stream = io.StringIO()
    code = certs.collect(output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 1 and report["outcome"] == "failure"
    assert "malformed certificate expiry" in report["reason"]
    assert output.read_bytes() == previous


def test_publication_failure_is_reported_without_replacing_previous_bytes(
    tmp_path: Path,
    fake_tls: tuple[FakeContext, list[tuple[str, int, int]]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "certs.json"
    previous = b'{"retained":true}\n'
    output.write_bytes(previous)

    def fail_publish(_output: Path, _data: dict[str, Any]) -> None:
        raise CollectionError("local snapshot publication failed")

    monkeypatch.setattr(certs, "publish", fail_publish)
    stream = io.StringIO()
    code = certs.collect(output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 1 and report["outcome"] == "failure"
    assert output.read_bytes() == previous


def test_probe_transport_error_is_not_exposed_in_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "certs.json"
    output.write_text('{"retained":true}\n')
    def unavailable(*_args: object) -> None:
        raise OSError("credential-like transport detail")

    monkeypatch.setattr(certs.socket, "create_connection", unavailable)

    stream = io.StringIO()
    code = certs.collect(output, json_output=True, stdout=stream)

    report = json.loads(stream.getvalue())
    assert code == 0 and report["outcome"] == "success"
    assert json.loads(output.read_text())["counts"] == {"probed": 7, "reachable": 0}
    assert "credential-like" not in stream.getvalue()
