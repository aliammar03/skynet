"""Behavioral tests for the isolated PBS collector and its trust/failure boundary."""

from __future__ import annotations

import json
import hashlib
import os
import socket
import ssl
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest

ROOT = Path(__file__).parents[1]
if os.environ.get("SKYNET_ENTRYPOINT") != "console" and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skynet.cli import main  # noqa: E402
import skynet.pbs as pbs  # noqa: E402

TOKEN = "svc-ops@pbs!readonly:synthetic-pbs-token"
FIXTURES = Path(__file__).parent / "fixtures" / "pbs"


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def endpoint_data() -> dict[str, Any]:
    return {
        "/api2/json/admin/datastore": fixture("datastores.json"),
        "/api2/json/admin/datastore/unraid/status": fixture("status.json"),
        "/api2/json/admin/datastore/unraid/namespace": fixture("namespaces.json"),
        "/api2/json/admin/datastore/unraid/snapshots": fixture("root-snapshots.json"),
        "/api2/json/admin/datastore/unraid/snapshots?ns=network": fixture("network-snapshots.json"),
        "/api2/json/admin/datastore/unraid/snapshots?ns=core": fixture("core-snapshots.json"),
    }


def _tls_material(tmp_path: Path, name: str = "pbs.example.test") -> tuple[Path, Path, bytes]:
    certificate = tmp_path / "pbs.crt"
    key = tmp_path / "pbs.key"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(certificate), "-days", "1",
        "-subj", f"/CN={name}", "-addext", f"subjectAltName=DNS:{name}",
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    der = ssl.PEM_cert_to_DER_cert(certificate.read_text())
    return certificate, key, hashlib.sha256(der).digest()


@contextmanager
def _tls_server(
    certificate: Path, key: Path, response: bytes = b"", connections: int = 1,
) -> Iterator[int]:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    errors: list[BaseException] = []

    def serve() -> None:
        try:
            for _ in range(connections):
                connection, _ = listener.accept()
                try:
                    with context.wrap_socket(connection, server_side=True) as wrapped:
                        wrapped.recv(4096)
                        if response:
                            wrapped.sendall(response)
                except (ConnectionError, ssl.SSLError):
                    # A client that rejects the certificate can abort its TLS
                    # socket before sending an HTTP request.
                    continue
        except BaseException as error:  # pragma: no cover - re-raised by the context manager
            errors.append(error)

    worker = threading.Thread(target=serve)
    worker.start()
    try:
        yield listener.getsockname()[1]
    finally:
        listener.close()
        worker.join(timeout=5)
        if worker.is_alive():
            raise AssertionError("synthetic TLS server did not stop")
        if errors:
            raise errors[0]


def _tls_credentials(path: Path, port: int, **extra: str) -> None:
    values = {
        "PBS_HOST": "127.0.0.1",
        "PBS_PORT": str(port),
        "PBS_TOKEN": TOKEN,
        **extra,
    }
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))


class FakeResponse:
    def __init__(self, payload: Any, status: int = 200):
        self.payload = payload
        self.status = status

    def read(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode()


class FakeConnection:
    instances: list["FakeConnection"] = []
    responses: dict[str, Any] = {}

    def __init__(self, host: str, port: int, context: ssl.SSLContext, sni: str, timeout: int):
        assert host == "10.10.20.40"
        assert port == 8007
        assert sni == "pbs.example.test"
        assert timeout == 20
        self.context = context
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.closed = False
        self.instances.append(self)

    def request(self, method: str, path: str, *, headers: dict[str, str]) -> None:
        assert method == "GET"
        assert headers == {"Authorization": "PBSAPIToken=" + TOKEN}
        self.requests.append((method, path, headers))

    def getresponse(self) -> FakeResponse:
        response = self.responses[self.requests[-1][1]]
        if isinstance(response, BaseException):
            raise response
        if isinstance(response, FakeResponse):
            return response
        return FakeResponse(response)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> type[FakeConnection]:
    FakeConnection.instances = []
    FakeConnection.responses = endpoint_data()
    monkeypatch.setattr(pbs, "HTTPSConnection", FakeConnection)
    return FakeConnection


@pytest.fixture
def credentials(tmp_path: Path) -> Path:
    cafile = ssl.get_default_verify_paths().cafile
    assert cafile is not None and Path(cafile).is_file()
    path = tmp_path / "pbs.env"
    path.write_text(
        "PBS_HOST=10.10.20.40\n"
        f"PBS_TOKEN={TOKEN.replace(':', '=', 1)}\n"
        "PBS_PORT=8007\n"
        f"PBS_CACERT={cafile}\n"
        "PBS_SNI=pbs.example.test\n"
    )
    return path


def collect(tmp_path: Path, credentials: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, Any], Path]:
    output = tmp_path / "pbs.json"
    code = main(["collect", "pbs", "--output", str(output), "--credentials-file",
                 str(credentials), "--json"])
    captured = capsys.readouterr()
    assert TOKEN not in captured.out + captured.err
    return code, json.loads(captured.out), output


def test_cli_projects_groups_and_latest_verification(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    code, report, output = collect(tmp_path, credentials, capsys)
    assert code == 0 and report["outcome"] == "success"
    snapshot = json.loads(output.read_text())
    store = snapshot["datastores"][0]
    assert snapshot["host"] == "10.10.20.40"
    assert store["status"] == {"used": 400, "total": 1000}
    assert store["group_count"] == 2 and store["snapshot_total"] == 3 and store["unverified"] == 1
    assert next(group for group in store["groups"] if group["backup_id"] == "10015") == {
        "ns": "core", "backup_type": "vm", "backup_id": "10015", "owner": "svc-ops@pbs",
        "backup_count": 2, "last_backup": 200, "verify_state": None,
    }
    assert all(connection.closed for connection in transport.instances)


@pytest.mark.parametrize("status", [
    {"used": 400},
    {"total": 1000},
    {"used": -1, "total": 1000},
    {"used": 400, "total": -1},
    {"used": 1100, "total": 1000},
    {"used": True, "total": 1000},
    {"used": 400, "total": False},
    {"used": float("nan"), "total": 1000},
    {"used": 10**4000, "total": 1000},
])
def test_datastore_status_requires_finite_nonnegative_bounded_usage(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], status: dict[str, Any],
) -> None:
    transport.responses["/api2/json/admin/datastore/unraid/status"] = {"data": status}
    code, report, output = collect(tmp_path, credentials, capsys)
    assert code == 1 and report["outcome"] == "failure"
    assert not output.exists()


def test_failed_unknown_and_missing_latest_verification_are_not_verified(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    snapshots = transport.responses["/api2/json/admin/datastore/unraid/snapshots?ns=core"]["data"]
    snapshots[0]["verification"] = {"state": "ok"}
    snapshots[1]["verification"] = {"state": "failed"}
    snapshots[2]["verification"] = {"state": "unknown"}
    snapshots.append({"backup-type": "ct", "backup-id": "102", "backup-time": 250,
                      "owner": "svc-ops@pbs", "verification": None})
    code, _, output = collect(tmp_path, credentials, capsys)
    assert code == 0
    store = json.loads(output.read_text())["datastores"][0]
    assert store["unverified"] == 3
    assert {group["verify_state"] for group in store["groups"]} == {"failed", "unknown", None}


def test_rendered_pbs_block_names_each_unverified_state(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "inventory").mkdir(parents=True)
    (repo / "bin").mkdir()
    (repo / "scripts").mkdir()
    (repo / "docs" / "generated").mkdir(parents=True)
    (repo / "lab.json").write_text("{}\n")
    (repo / "bin" / "skynet").write_text("#!/bin/sh\nexit 0\n")
    (repo / "bin" / "skynet").chmod(0o755)
    (repo / "scripts" / "render-docs.sh").write_text(
        (ROOT / "scripts" / "render-docs.sh").read_text()
    )
    (repo / "scripts" / "render-docs.sh").chmod(0o755)
    (repo / "inventory" / "pbs.json").write_text(json.dumps({
        "datastores": [{
            "store": "unraid", "status": {"used": 1, "total": 2},
            "groups": [
                {"verify_state": "ok"}, {"verify_state": "failed"},
                {"verify_state": "unknown"}, {"verify_state": None},
            ], "group_count": 4, "snapshot_total": 4, "unverified": 3,
        }],
    }))
    rendered_run = subprocess.run(
        ["bash", str(repo / "scripts" / "render-docs.sh")], check=True,
        cwd=repo, env={**os.environ, "SQLITE3": "/nonexistent"},
        capture_output=True, text=True,
    )
    assert rendered_run.stderr == ""
    rendered = (repo / "docs" / "generated" / "90-backup-status.md").read_text()
    assert "failed=1" in rendered and "unknown=1" in rendered and "unverified=1" in rendered
    assert "verified: 1" in rendered and "failed: 1" in rendered
    assert "[!success]" not in rendered
    snapshot = repo / "inventory" / "pbs.json"
    data = json.loads(snapshot.read_text())
    for group in data["datastores"][0]["groups"]:
        group["verify_state"] = "ok"
    data["datastores"][0].update(unverified=0, snapshot_total=40)
    snapshot.write_text(json.dumps(data))
    result = subprocess.run(["bash", str(repo / "scripts" / "render-docs.sh")], check=True,
                            cwd=repo, env={**os.environ, "SQLITE3": "/nonexistent"},
                            capture_output=True, text=True)
    assert result.stderr == ""
    rendered = (repo / "docs" / "generated" / "90-backup-status.md").read_text()
    assert "All 4 backup groups have a verified latest snapshot (state `ok`)" in rendered


def test_empty_snapshots_are_a_valid_zero_backup_observation(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    transport.responses["/api2/json/admin/datastore/unraid/namespace"] = {"data": []}
    code, _, output = collect(tmp_path, credentials, capsys)
    assert code == 0
    store = json.loads(output.read_text())["datastores"][0]
    assert store["groups"] == [] and store["snapshot_total"] == 0 and store["unverified"] == 0


@pytest.mark.parametrize("response", [{"data": None}, {"data": [{}]}, b"not json", TimeoutError("late")])
def test_malformed_or_unavailable_endpoint_retains_prior_bytes(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str], response: Any,
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    output = tmp_path / "pbs.json"
    previous = output.read_bytes()
    transport.responses["/api2/json/admin/datastore/unraid/snapshots?ns=core"] = response
    code, report, _ = collect(tmp_path, credentials, capsys)
    assert code != 0 and report["outcome"] in {"failure", "unavailable"}
    assert output.read_bytes() == previous


def test_ca_and_configured_fingerprint_trust_keep_sni_separate(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    called: dict[str, object] = {}

    def bootstrap(host: str, port: int, sni: str, fingerprint: bytes) -> tuple[ssl.SSLContext, bytes]:
        called.update(host=host, port=port, sni=sni, fingerprint=fingerprint)
        return ssl.create_default_context(), b"unused when PBS_SNI is configured"

    monkeypatch.setattr(pbs, "_bootstrap_context", bootstrap)
    credentials.write_text(
        "PBS_HOST=10.10.20.40\nPBS_TOKEN=" + TOKEN + "\nPBS_SNI=pbs.example.test\n"
        "PBS_FINGERPRINT=" + "AA:" * 31 + "AA\n"
    )
    assert collect(tmp_path, credentials, capsys)[0] == 0
    assert called["host"] == "10.10.20.40" and called["sni"] == "pbs.example.test"
    assert called["fingerprint"] == bytes.fromhex("AA" * 32)


def test_certificate_name_prefers_san_then_common_name() -> None:
    assert pbs._certificate_name(
        {"subjectAltName": [("DNS", "san.example.test")],
         "subject": [(("commonName", "cn.example.test"),)]},
        "fallback.example.test",
    ) == "san.example.test"
    assert pbs._certificate_name(
        {"subject": [(("commonName", "cn.example.test"),)]},
        "fallback.example.test",
    ) == "cn.example.test"


def test_real_tls_ca_trust_and_sni_verify(tmp_path: Path) -> None:
    certificate, key, _ = _tls_material(tmp_path)
    response = b'HTTP/1.1 200 OK\r\nContent-Length: 17\r\n\r\n{"data":{"ok":1}}'
    credentials_file = tmp_path / "pbs.env"
    with _tls_server(certificate, key, response) as port:
        _tls_credentials(credentials_file, port, PBS_CACERT=str(certificate), PBS_SNI="pbs.example.test")
        settings = pbs.credentials(credentials_file)
        assert settings.sni == "pbs.example.test"
        assert pbs.get(settings, "status") == {"ok": 1}


def test_real_tls_fingerprint_trust_and_no_sni_certificate_fallback(tmp_path: Path) -> None:
    certificate, key, fingerprint = _tls_material(tmp_path)
    credentials_file = tmp_path / "pbs.env"
    response = b'HTTP/1.1 200 OK\r\nContent-Length: 17\r\n\r\n{"data":{"ok":1}}'
    with _tls_server(certificate, key, response, connections=2) as port:
        _tls_credentials(credentials_file, port, PBS_FINGERPRINT=fingerprint.hex())
        settings = pbs.credentials(credentials_file)
        assert settings.sni == "pbs.example.test"
        assert pbs.get(settings, "status") == {"ok": 1}


def test_real_tls_wrong_pin_and_name_are_rejected(tmp_path: Path) -> None:
    certificate, key, fingerprint = _tls_material(tmp_path)
    credentials_file = tmp_path / "pbs.env"
    with _tls_server(certificate, key) as port:
        _tls_credentials(credentials_file, port, PBS_FINGERPRINT=(b"\x00" * 32).hex())
        with pytest.raises(pbs.CollectionError, match="fingerprint mismatch"):
            pbs.credentials(credentials_file)

    response = b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}'
    with _tls_server(certificate, key, response, connections=2) as port:
        _tls_credentials(credentials_file, port, PBS_FINGERPRINT=fingerprint.hex(), PBS_SNI="wrong.example.test")
        settings = pbs.credentials(credentials_file)
        with pytest.raises(pbs.CollectionError, match="remote transport unavailable"):
            pbs.get(settings, "status")


@pytest.mark.parametrize("ca_contents", [None, "not a certificate"])
def test_real_tls_missing_or_invalid_ca_fails_before_connect(
    tmp_path: Path, ca_contents: str | None,
) -> None:
    ca = tmp_path / "missing-or-invalid-ca.crt"
    if ca_contents is not None:
        ca.write_text(ca_contents)
    credentials_file = tmp_path / "pbs.env"
    _tls_credentials(credentials_file, 1, PBS_CACERT=str(ca), PBS_SNI="pbs.example.test")
    with pytest.raises(pbs.CollectionError, match="CA unavailable or invalid"):
        pbs.credentials(credentials_file)


@pytest.mark.parametrize("assignment", ["PBS_TOKEN=$(bad)", "PBS_TOKEN=", "UNKNOWN=value"])
def test_literal_credentials_refuse_shell_syntax_and_missing_values(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str], assignment: str,
) -> None:
    contents = credentials.read_text()
    if assignment != "UNKNOWN=value":
        contents = "\n".join(line for line in contents.splitlines() if not line.startswith("PBS_TOKEN=")) + "\n"
    credentials.write_text(contents + assignment + "\n")
    code, report, output = collect(tmp_path, credentials, capsys)
    assert code == 3 and report["outcome"] == "unavailable" and not output.exists()
    assert not transport.instances
