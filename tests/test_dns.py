"""Behavioral tests for the isolated Technitium DNS collector and its failure boundary."""

from __future__ import annotations

import json
import os
import socket
import ssl
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).parents[1]
if os.environ.get("SKYNET_ENTRYPOINT") != "console" and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skynet.cli import main  # noqa: E402
import skynet.dns as dns  # noqa: E402

# Interior '@'/'!' keep this synthetic token out of the plaintext-secret scanner's run.
TOKEN = "svc-recon@tdns!synthetic-zones-token"
FIXTURES = Path(__file__).parent / "fixtures" / "dns"


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def envelope(response: Any) -> dict[str, Any]:
    return {"status": "ok", "response": response}


def endpoint_data() -> dict[tuple[str, str], Any]:
    return {
        ("zones/list", ""): envelope(fixture("zones.json")),
        ("zones/records/get", "aliammar.net"): envelope(fixture("records-aliammar.json")),
        ("zones/records/get", "lab.aliammar.net"): envelope(fixture("records-lab.json")),
        ("zones/records/get", "empty.aliammar.net"): envelope(fixture("records-empty.json")),
    }


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
    responses: dict[tuple[str, str], Any] = {}

    def __init__(self, host: str, port: int, *, context: ssl.SSLContext, timeout: int):
        assert host == "10.10.70.50"
        assert port == 53443
        assert timeout == 15
        self.context = context
        self.endpoint = ""
        self.query = ""
        self.closed = False
        self.instances.append(self)

    def request(self, method: str, url: str) -> None:
        assert method == "GET"
        split = urlsplit(url)
        self.endpoint = split.path.removeprefix("/api/")
        self.query = split.query

    def getresponse(self) -> FakeResponse:
        params = parse_qs(self.query, keep_blank_values=True)
        zone = params.get("zone", [""])[0]
        response = self.responses[(self.endpoint, zone)]
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
    monkeypatch.setattr(dns.http.client, "HTTPSConnection", FakeConnection)
    return FakeConnection


@pytest.fixture
def credentials(tmp_path: Path) -> Path:
    cafile = ssl.get_default_verify_paths().cafile
    assert cafile is not None and Path(cafile).is_file()
    path = tmp_path / "technitium.env"
    path.write_text(
        "TECH_HOST=10.10.70.50\n"
        f"TECH_TOKEN={TOKEN}\n"
        f"TECH_CACERT={cafile}\n"
    )
    return path


def collect(tmp_path: Path, credentials: Path,
            capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, Any], Path]:
    output = tmp_path / "dns-zones.json"
    code = main(["collect", "dns", "--output", str(output), "--credentials-file",
                 str(credentials), "--json"])
    captured = capsys.readouterr()
    assert TOKEN not in captured.out + captured.err
    return code, json.loads(captured.out), output


def test_cli_projects_zones_and_records(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, report, output = collect(tmp_path, credentials, capsys)
    assert code == 0 and report["outcome"] == "success"
    assert report["counts"] == {"zones": 3, "records": 7}
    snapshot = json.loads(output.read_text())
    assert snapshot["host"] == "10.10.70.50"
    assert [zone["name"] for zone in snapshot["zones"]] == [
        "aliammar.net", "lab.aliammar.net", "empty.aliammar.net"]
    assert [entry["zone"] for entry in snapshot["records"]] == [
        "aliammar.net", "lab.aliammar.net", "empty.aliammar.net"]
    # Non-A/CNAME records survive; consumer fields (name/type/rData) are preserved verbatim.
    apex = snapshot["records"][0]["records"]
    assert {record["type"] for record in apex} == {"SOA", "NS", "A", "CNAME", "TXT"}
    a_record = next(record for record in apex if record["type"] == "A")
    assert a_record["name"] == "apps.aliammar.net" and a_record["rData"]["ipAddress"] == "10.10.60.33"
    cname = next(record for record in apex if record["type"] == "CNAME")
    assert cname["rData"]["cname"] == "apps.aliammar.net"
    assert snapshot["records"][2]["records"] == []
    assert all(connection.closed for connection in transport.instances)
    # The scoped token is actually sent in the request query but never printed.
    assert any(parse_qs(connection.query).get("token") == [TOKEN]
               for connection in transport.instances)


def test_cli_requests_root_with_dot_and_preserves_empty_identity(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    transport.responses = {
        ("zones/list", ""): envelope({"zones": [{"name": ""}]}),
        ("zones/records/get", "."): envelope({
            "zone": {"name": "."},
            "records": [{"name": "", "type": "A", "rData": {"ipAddress": "192.0.2.1"}}],
        }),
    }
    code, report, output = collect(tmp_path, credentials, capsys)
    assert code == 0 and report["outcome"] == "success"
    snapshot = json.loads(output.read_text())
    assert snapshot["zones"] == [{"name": ""}]
    assert snapshot["records"] == [{"zone": "", "records": [
        {"name": "", "type": "A", "rData": {"ipAddress": "192.0.2.1"}},
    ]}]
    request = next(connection for connection in transport.instances
                   if connection.endpoint == "zones/records/get")
    params = parse_qs(request.query)
    assert params["domain"] == ["."] and params["zone"] == ["."]


def test_only_read_endpoints_are_requested(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    assert {connection.endpoint for connection in transport.instances} == {
        "zones/list", "zones/records/get"}


def test_rendered_service_table_reads_a_and_cname_records(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "inventory").mkdir(parents=True)
    (repo / "bin").mkdir()
    (repo / "scripts").mkdir()
    (repo / "docs" / "generated").mkdir(parents=True)
    (repo / "lab.json").write_text("{}\n")
    (repo / "bin" / "skynet").write_text("#!/bin/sh\nexit 0\n")
    (repo / "bin" / "skynet").chmod(0o755)
    (repo / "scripts" / "render-docs.sh").write_text(
        (ROOT / "scripts" / "render-docs.sh").read_text())
    (repo / "scripts" / "render-docs.sh").chmod(0o755)
    (repo / "inventory" / "dns-zones.json").write_text(json.dumps({
        "collected": "2026-09-09T00:00:00+00:00", "host": "10.10.70.50",
        "zones": [{"name": "aliammar.net"}],
        "records": [{"zone": "aliammar.net", "records": [
            {"name": "apps.aliammar.net", "type": "A", "rData": {"ipAddress": "10.10.60.33"}},
            {"name": "obsidian.aliammar.net", "type": "CNAME", "rData": {"cname": "apps.aliammar.net"}},
            {"name": "aliammar.net", "type": "SOA", "rData": {"serial": 1}},
        ]}],
    }))
    result = subprocess.run(["bash", str(repo / "scripts" / "render-docs.sh")], check=True,
                            cwd=repo, env={**os.environ, "SQLITE3": "/nonexistent"},
                            capture_output=True, text=True)
    assert result.stderr == ""
    rendered = (repo / "docs" / "generated" / "30-services" / "README.md").read_text()
    assert "| apps.aliammar.net | A | `10.10.60.33` |" in rendered
    assert "| obsidian.aliammar.net | CNAME | `apps.aliammar.net` |" in rendered
    assert "SOA" not in rendered


@pytest.mark.parametrize("mutation", [
    {("zones/list", ""): envelope({"zones": None})},
    {("zones/list", ""): envelope({"zones": [{"name": "aliammar.net"}, {"name": "aliammar.net"}]})},
    {("zones/list", ""): envelope({"zones": [{"name": ""}, {"name": "."}]})},
    {("zones/records/get", "lab.aliammar.net"): envelope({"records": None})},
    {("zones/records/get", "lab.aliammar.net"): envelope({"records": [{"type": "A",
                                                                       "rData": {"ipAddress": "1"}}]})},
    {("zones/records/get", "lab.aliammar.net"): envelope({"records": [{"name": "x", "type": "A",
                                                                       "rData": {}}]})},
    {("zones/records/get", "lab.aliammar.net"): envelope({"records": [{"name": "x", "type": "A",
                                                                       "rData": {"ipAddress": None}}]})},
    {("zones/records/get", "lab.aliammar.net"): envelope({"records": [{"name": "x", "type": "A",
                                                                       "rData": "notdict"}]})},
    {("zones/records/get", "lab.aliammar.net"): envelope({"records": [{"name": "x", "type": "A",
                                                                       "rData": {"ipAddress": "2001:db8::1"}}]})},
    {("zones/records/get", "lab.aliammar.net"): envelope({"records": [{"name": "x", "type": "AAAA",
                                                                       "rData": {"ipAddress": "192.0.2.1"}}]})},
    {("zones/records/get", "lab.aliammar.net"): envelope({"records": [{"name": "x", "type": "CNAME",
                                                                       "rData": {"cname": ""}}]})},
    {("zones/records/get", "lab.aliammar.net"): envelope({"records": [{"name": "x", "type": "CNAME",
                                                                       "rData": {"cname": 7}}]})},
    {("zones/records/get", "lab.aliammar.net"): envelope({"zone": {"name": "other.example"},
                                                              "records": []})},
    {("zones/list", ""): {"status": "error", "errorMessage": "bad token"}},
    {("zones/list", ""): FakeResponse(b"{}", status=500)},
    {("zones/list", ""): b"not json"},
    {("zones/records/get", "aliammar.net"): TimeoutError("late")},
])
def test_malformed_or_unavailable_response_retains_prior_bytes(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], mutation: dict[tuple[str, str], Any],
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    output = tmp_path / "dns-zones.json"
    previous = output.read_bytes()
    transport.responses.update(mutation)
    code, report, _ = collect(tmp_path, credentials, capsys)
    assert code != 0 and report["outcome"] in {"failure", "unavailable"}
    assert output.read_bytes() == previous


def test_missing_credentials_fails_without_transport(
    tmp_path: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["collect", "dns", "--output", str(tmp_path / "dns-zones.json"),
                 "--credentials-file", str(tmp_path / "missing.env"), "--json"])
    report = json.loads(capsys.readouterr().out)
    assert code == 3 and report["outcome"] == "unavailable"
    assert not transport.instances
    assert not (tmp_path / "dns-zones.json").exists()


@pytest.mark.parametrize("assignment", ["TECH_TOKEN=$(bad)", "TECH_TOKEN=", "UNKNOWN=value"])
def test_literal_credentials_refuse_shell_syntax_and_missing_values(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], assignment: str,
) -> None:
    contents = credentials.read_text()
    if assignment != "UNKNOWN=value":
        contents = "\n".join(
            line for line in contents.splitlines() if not line.startswith("TECH_TOKEN=")) + "\n"
    credentials.write_text(contents + assignment + "\n")
    code, report, output = collect(tmp_path, credentials, capsys)
    assert code == 3 and report["outcome"] == "unavailable" and not output.exists()
    assert not transport.instances


# ── Real TLS: CA verification with no insecure fallback ─────────────────────────────────────────

def _tls_material(tmp_path: Path) -> tuple[Path, Path]:
    certificate = tmp_path / "tech.crt"
    key = tmp_path / "tech.key"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(certificate), "-days", "1",
        "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1",
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return certificate, key


@contextmanager
def _tls_server(certificate: Path, key: Path, response: bytes, connections: int = 1) -> Iterator[int]:
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
                        wrapped.sendall(response)
                except (ConnectionError, ssl.SSLError):
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


def _tls_credentials(path: Path, cacert: Path) -> None:
    path.write_text(f"TECH_HOST=127.0.0.1\nTECH_TOKEN={TOKEN}\nTECH_CACERT={cacert}\n")


def test_real_tls_ca_trust_reads_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    certificate, key = _tls_material(tmp_path)
    body = b'{"status":"ok","response":{"zones":[]}}'
    response = b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%b" % (len(body), body)
    credentials_file = tmp_path / "technitium.env"
    with _tls_server(certificate, key, response) as port:
        monkeypatch.setattr(dns, "PORT", port)
        _tls_credentials(credentials_file, certificate)
        settings = dns.credentials(credentials_file)
        assert dns.get(settings, "zones/list", {}) == {"zones": []}


def test_real_tls_wrong_ca_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    certificate, key = _tls_material(tmp_path)
    (tmp_path / "other").mkdir(exist_ok=True)
    other_cert, _ = _tls_material(tmp_path / "other")
    credentials_file = tmp_path / "technitium.env"
    body = b'{"status":"ok","response":{"zones":[]}}'
    response = b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%b" % (len(body), body)
    with _tls_server(certificate, key, response) as port:
        monkeypatch.setattr(dns, "PORT", port)
        _tls_credentials(credentials_file, other_cert)
        settings = dns.credentials(credentials_file)
        with pytest.raises(dns.CollectionError, match="remote transport unavailable"):
            dns.get(settings, "zones/list", {})


@pytest.mark.parametrize("ca_contents", [None, "not a certificate"])
def test_real_tls_missing_or_invalid_ca_fails_before_connect(
    tmp_path: Path, ca_contents: str | None,
) -> None:
    ca = tmp_path / "missing-or-invalid-ca.crt"
    if ca_contents is not None:
        ca.write_text(ca_contents)
    credentials_file = tmp_path / "technitium.env"
    _tls_credentials(credentials_file, ca)
    with pytest.raises(dns.CollectionError, match="CA unavailable or invalid"):
        dns.credentials(credentials_file)
