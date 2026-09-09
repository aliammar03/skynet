"""Behavioral tests for the live OPNsense collector: user view, pairing, vantage, trust."""

from __future__ import annotations

import base64
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

import pytest

ROOT = Path(__file__).parents[1]
if os.environ.get("SKYNET_ENTRYPOINT") != "console" and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skynet.cli import main  # noqa: E402
import skynet.opnsense as opnsense  # noqa: E402

# Interior '@' keeps these synthetic secrets out of the plaintext-secret scanner's run.
KEY = "opn-key@synthetic"
SECRET = "opn-secret@synthetic"
AUTHORIZATION = "Basic " + base64.b64encode(f"{KEY}:{SECRET}".encode()).decode()
FIXTURES = Path(__file__).parent / "fixtures" / "opnsense"


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def endpoint_data() -> dict[str, Any]:
    return {
        "/api/core/firmware/status": fixture("firmware.json"),
        "/api/firewall/alias/get": fixture("alias-get.json"),
        "/api/firewall/filter/get": fixture("filter-get.json"),
        "/api/interfaces/overview/interfacesInfo": fixture("interfaces.json"),
        "/api/firewall/filter/searchRule": fixture("search-rule.json"),
        "/api/dnsmasq/settings/searchHost": fixture("search-host.json"),
        "/api/diagnostics/interface/searchArp": fixture("search-arp.json"),
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
    responses: dict[str, Any] = {}

    def __init__(self, host: str, port: int, context: ssl.SSLContext, sni: str, timeout: int):
        assert host == "10.10.60.1"
        assert port == 443
        assert sni == "opnsense.example.test"
        assert timeout == 25
        self.context = context
        self.path = ""
        self.method = ""
        self.headers: dict[str, str] = {}
        self.closed = False
        self.instances.append(self)

    def request(self, method: str, url: str, *, body: bytes | None = None,
                headers: dict[str, str] | None = None) -> None:
        self.method = method
        self.path = url
        self.headers = headers or {}

    def getresponse(self) -> FakeResponse:
        response = self.responses[self.path]
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
    monkeypatch.setattr(opnsense, "HTTPSConnection", FakeConnection)
    # Deterministic presence: ICMP available; only the one ARP-silent switch answers.
    monkeypatch.setattr(opnsense, "_ping_available", lambda: True)
    monkeypatch.setattr(opnsense, "_ping", lambda ip: ip == "10.10.50.3")
    return FakeConnection


@pytest.fixture
def credentials(tmp_path: Path) -> Path:
    cafile = ssl.get_default_verify_paths().cafile
    assert cafile is not None and Path(cafile).is_file()
    path = tmp_path / "opnsense.env"
    path.write_text(
        "OPN_HOST=10.10.60.1\n"
        f"OPN_KEY='{KEY}'\n"
        f"OPN_SECRET='{SECRET}'\n"
        "OPN_PORT=443\n"
        f"OPN_CACERT={cafile}\n"
        "OPN_SNI=opnsense.example.test\n"
    )
    return path


def collect(tmp_path: Path, credentials: Path,
            capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, Any], Path, Path]:
    firewall = tmp_path / "firewall.json"
    state = tmp_path / "opnsense.json"
    code = main(["collect", "opnsense", "--firewall-output", str(firewall),
                 "--state-output", str(state), "--credentials-file", str(credentials), "--json"])
    captured = capsys.readouterr()
    assert KEY not in captured.out + captured.err
    assert SECRET not in captured.out + captured.err
    assert AUTHORIZATION not in captured.out + captured.err
    return code, json.loads(captured.out), firewall, state


def test_cli_projects_paired_config_and_state(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, report, firewall, state = collect(tmp_path, credentials, capsys)
    assert code == 0 and report["outcome"] == "success"
    config = json.loads(firewall.read_text())
    assert config["host"] == "10.10.60.1"
    assert config["source"] == "opnsense-api (live, T1 read-only; user view)"
    # Built-ins dropped (__lan_network, bogons); user aliases kept with resolved type/content.
    names = [alias["name"] for alias in config["aliases"]]
    assert names == ["HOST_ADMIN_WORKSTATION", "ROLE_INFRASTRUCTURE_SWITCHES", "NET_SKYNET"]
    switches = next(a for a in config["aliases"] if a["name"] == "ROLE_INFRASTRUCTURE_SWITCHES")
    assert switches["type"] == "host" and switches["content"] == "10.10.50.2\n10.10.50.3"
    net = next(a for a in config["aliases"] if a["name"] == "NET_SKYNET")
    assert net["type"] == "network" and net["content"] == "10.10.0.0/16"
    # Rule intersection: the internal auto rule (absent from filter/get) is excluded; sequences applied.
    assert [rule["uuid"] for rule in config["rules"]] == ["uuid-rule-dns", "uuid-rule-web"]
    dns_rule = config["rules"][0]
    assert dns_rule["sequence"] == "100" and dns_rule["enabled"] is True
    assert config["rules"][1]["enabled"] is False and config["rules"][1]["interface"] == "lan"
    assert dns_rule["interface"] is None
    assert config["counts"] == {"aliases": 3, "rules": 2, "reservations": 1}
    assert config["reservations"][0]["ip"] == "10.10.10.50"

    live = json.loads(state.read_text())
    assert live["host"] == "10.10.60.1"
    assert live["firmware"] == {"status": "update", "product": "OPNsense 26.7", "needs_upgrade": True}
    assert live["counts"] == {"arp": 2, "interfaces": 2, "live": 3, "silent": 0}
    assert {p["ip"]: p["via"] for p in live["presence"]} == {
        "10.10.10.50": "arp", "10.10.50.2": "arp", "10.10.50.3": "icmp"}
    assert all(connection.closed for connection in transport.instances)
    assert all(c.headers.get("Authorization") == AUTHORIZATION for c in transport.instances)


def test_only_read_endpoints_are_requested(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    assert {c.path for c in transport.instances} <= set(endpoint_data())
    methods = {c.path: c.method for c in transport.instances}
    assert methods["/api/firewall/alias/get"] == "GET"
    assert methods["/api/firewall/filter/searchRule"] == "POST"


def test_presence_marks_icmp_unavailable_when_probe_cannot_run(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(opnsense, "_ping_available", lambda: False)
    code, _, _, state = collect(tmp_path, credentials, capsys)
    assert code == 0
    live = json.loads(state.read_text())
    silent = next(p for p in live["presence"] if p["ip"] == "10.10.50.3")
    assert silent == {"ip": "10.10.50.3", "live": False, "via": "no-arp,icmp-unavailable"}
    assert live["counts"]["silent"] == 1 and live["counts"]["live"] == 2


def test_incomplete_search_page_fails_and_retains_both_files(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    firewall = (tmp_path / "firewall.json").read_bytes()
    state = (tmp_path / "opnsense.json").read_bytes()
    truncated = fixture("search-rule.json")
    truncated["total"] = 9
    transport.responses["/api/firewall/filter/searchRule"] = truncated
    code, report, _, _ = collect(tmp_path, credentials, capsys)
    assert code == 1 and report["outcome"] == "failure"
    assert (tmp_path / "firewall.json").read_bytes() == firewall
    assert (tmp_path / "opnsense.json").read_bytes() == state


@pytest.mark.parametrize("path,response", [
    ("/api/core/firmware/status", {"status_msg": "no status field"}),
    ("/api/firewall/alias/get", {"alias": {"aliases": {"alias": []}}}),
    ("/api/firewall/filter/searchRule", {"rows": None}),
    ("/api/diagnostics/interface/searchArp", FakeResponse(b"{}", status=500)),
    ("/api/interfaces/overview/interfacesInfo", b"not json"),
    ("/api/core/firmware/status", TimeoutError("late")),
])
def test_malformed_or_unavailable_endpoint_retains_prior_bytes(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], path: str, response: Any,
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    firewall = (tmp_path / "firewall.json").read_bytes()
    state = (tmp_path / "opnsense.json").read_bytes()
    transport.responses[path] = response
    code, report, _, _ = collect(tmp_path, credentials, capsys)
    assert code != 0 and report["outcome"] in {"failure", "unavailable"}
    assert (tmp_path / "firewall.json").read_bytes() == firewall
    assert (tmp_path / "opnsense.json").read_bytes() == state


def test_missing_credentials_fails_without_transport(
    tmp_path: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["collect", "opnsense", "--firewall-output", str(tmp_path / "firewall.json"),
                 "--state-output", str(tmp_path / "opnsense.json"),
                 "--credentials-file", str(tmp_path / "missing.env"), "--json"])
    report = json.loads(capsys.readouterr().out)
    assert code == 3 and report["outcome"] == "unavailable"
    assert not transport.instances
    assert not (tmp_path / "firewall.json").exists()


@pytest.mark.parametrize("assignment", ["OPN_KEY=", "UNKNOWN=value", "OPN_HOST=extra.example"])
def test_literal_credentials_refuse_missing_values_unknown_and_duplicate_keys(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], assignment: str,
) -> None:
    contents = credentials.read_text()
    drop = assignment.split("=", 1)[0]
    if drop == "OPN_KEY":
        # An empty value must be rejected even though the original assignment is removed first.
        contents = "\n".join(line for line in contents.splitlines()
                             if not line.startswith(drop + "=")) + "\n"
    credentials.write_text(contents + assignment + "\n")
    code, report, firewall, _ = collect(tmp_path, credentials, capsys)
    assert code == 3 and report["outcome"] == "unavailable" and not firewall.exists()
    assert not transport.instances


# ── Real TLS: pinned-cert SNI derivation and CA verification, no insecure fallback ───────────────

def _tls_material(tmp_path: Path, name: str = "opnsense.internal") -> tuple[Path, Path]:
    certificate = tmp_path / "opn.crt"
    key = tmp_path / "opn.key"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(certificate), "-days", "1",
        "-subj", "/CN=opnsense", "-addext", f"subjectAltName=DNS:{name}",
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


def _tls_credentials(path: Path, port: int, cacert: Path, **extra: str) -> None:
    values = {"OPN_HOST": "127.0.0.1", "OPN_PORT": str(port), "OPN_KEY": KEY,
              "OPN_SECRET": SECRET, "OPN_CACERT": str(cacert), **extra}
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))


def test_real_tls_derives_sni_from_pinned_cert_and_reads(tmp_path: Path) -> None:
    certificate, key = _tls_material(tmp_path, name="127.0.0.1-alt.internal")
    # Pin the leaf as its own CA and add the connect IP so the derived SNI still verifies.
    certificate2, key2 = tmp_path / "opn2.crt", tmp_path / "opn2.key"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key2), "-out", str(certificate2), "-days", "1", "-subj", "/CN=opnsense",
        "-addext", "subjectAltName=DNS:opnsense.internal,IP:127.0.0.1",
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    body = b'{"status":"none"}'
    response = b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%b" % (len(body), body)
    credentials_file = tmp_path / "opnsense.env"
    with _tls_server(certificate2, key2, response) as port:
        _tls_credentials(credentials_file, port, certificate2)
        settings = opnsense.credentials(credentials_file)
        assert settings.sni == "opnsense.internal"
        assert opnsense.get(settings, "core/firmware/status") == {"status": "none"}


def test_real_tls_wrong_ca_is_rejected(tmp_path: Path) -> None:
    certificate, key = _tls_material(tmp_path)
    (tmp_path / "other").mkdir()
    other_cert, _ = _tls_material(tmp_path / "other")
    body = b'{"status":"none"}'
    response = b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%b" % (len(body), body)
    credentials_file = tmp_path / "opnsense.env"
    with _tls_server(certificate, key, response) as port:
        _tls_credentials(credentials_file, port, other_cert, OPN_SNI="opnsense.internal")
        settings = opnsense.credentials(credentials_file)
        with pytest.raises(opnsense.CollectionError, match="remote transport unavailable"):
            opnsense.get(settings, "core/firmware/status")


@pytest.mark.parametrize("ca_contents", [None, "not a certificate"])
def test_real_tls_missing_or_invalid_ca_fails_before_connect(
    tmp_path: Path, ca_contents: str | None,
) -> None:
    ca = tmp_path / "missing-or-invalid-ca.crt"
    if ca_contents is not None:
        ca.write_text(ca_contents)
    credentials_file = tmp_path / "opnsense.env"
    _tls_credentials(credentials_file, 1, ca, OPN_SNI="opnsense.internal")
    with pytest.raises(opnsense.CollectionError, match="CA unavailable or invalid"):
        opnsense.credentials(credentials_file)
