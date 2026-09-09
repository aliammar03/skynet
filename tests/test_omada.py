"""Synthetic behavioral tests for the Omada read-only collection boundary."""

from __future__ import annotations

import copy
import json
import os
import ssl
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
if os.environ.get("SKYNET_ENTRYPOINT") != "console" and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skynet.cli import main  # noqa: E402
import skynet.omada as omada  # noqa: E402


HOST = "10.10.50.25"
PORT = 8043
SNI = "omada.example.test"
USER = "svc-ops"
PASSWORD = 'p@ss; & "quoted"'
COOKIE = "TPOMADA_SESSION=synthetic-cookie"
CSRF = "csrf-synthetic-token"
FIXTURES = Path(__file__).parent / "fixtures" / "omada"
INFO_PATH = "/api/info"
LOGIN_PATH = "/controller1/api/v2/login"
SITES_PATH = "/controller1/api/v2/sites?currentPage=1&currentPageSize=1000"
DEVICES_A = "/controller1/api/v2/sites/site-a/devices"
DEVICES_B = "/controller1/api/v2/sites/site-b/devices"
PORTS_A = "/controller1/api/v2/sites/site-a/switches/AA%3ABB%3ACC%3ADD%3AEE%3A01/ports"


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def endpoint_data() -> dict[str, Any]:
    return {
        INFO_PATH: fixture("info.json"),
        LOGIN_PATH: fixture("login.json"),
        SITES_PATH: fixture("sites.json"),
        DEVICES_A: fixture("devices-site-a.json"),
        DEVICES_B: fixture("devices-site-b.json"),
        PORTS_A: fixture("ports-switch-a.json"),
    }


class FakeResponse:
    def __init__(self, payload: Any, status: int = 200, cookie: str | None = None):
        self.payload = payload
        self.status = status
        self.cookie = cookie

    def read(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode()

    def getheader(self, name: str) -> str | None:
        return self.cookie if name.lower() == "set-cookie" else None


class FakeConnection:
    instances: list["FakeConnection"] = []
    responses: dict[str, Any] = {}

    def __init__(self, host: str, port: int, context: ssl.SSLContext, sni: str, timeout: int):
        assert host == HOST
        assert port == PORT
        assert sni == SNI
        assert timeout == 20
        self.context = context
        self.method = ""
        self.path = ""
        self.body: bytes | None = None
        self.headers: dict[str, str] = {}
        self.closed = False
        self.instances.append(self)

    def request(self, method: str, path: str, *, body: bytes | None = None,
                headers: dict[str, str] | None = None) -> None:
        self.method = method
        self.path = path
        self.body = body
        self.headers = headers or {}

    def getresponse(self) -> FakeResponse:
        response = self.responses[self.path]
        if isinstance(response, BaseException):
            raise response
        if isinstance(response, FakeResponse):
            return response
        cookie = COOKIE if self.path == LOGIN_PATH else None
        return FakeResponse(response, cookie=cookie)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> type[FakeConnection]:
    FakeConnection.instances = []
    FakeConnection.responses = endpoint_data()
    monkeypatch.setattr(omada, "HTTPSConnection", FakeConnection)
    monkeypatch.setattr(omada, "_sni_from_certificate", lambda _path, _host: SNI)
    return FakeConnection


@pytest.fixture
def credentials(tmp_path: Path) -> Path:
    cafile = ssl.get_default_verify_paths().cafile
    assert cafile is not None and Path(cafile).is_file()
    path = tmp_path / "omada.env"
    path.write_text(
        f"OMADA_HOST={HOST}\n"
        f"OMADA_PORT={PORT}\n"
        f"OMADA_SNI={SNI}\n"
        f"OMADA_USER='{USER}'\n"
        f"OMADA_PASS='{PASSWORD}'\n"
        f"OMADA_CACERT={cafile}\n"
    )
    return path


def collect(tmp_path: Path, credentials: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, Any], Path]:
    output = tmp_path / "network-gear.json"
    code = main(["collect", "omada", "--output", str(output), "--credentials-file",
                 str(credentials), "--json"])
    captured = capsys.readouterr()
    assert PASSWORD not in captured.out + captured.err
    assert COOKIE not in captured.out + captured.err
    assert CSRF not in captured.out + captured.err
    return code, json.loads(captured.out), output


def test_success_projects_schema_and_collects_all_switch_ports(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, report, output = collect(tmp_path, credentials, capsys)
    assert code == 0 and report["outcome"] == "success"
    snapshot = json.loads(output.read_text())
    assert snapshot["controller"] == {
        "host": HOST, "version": "5.15.8", "omadacId": "controller1",
    }
    assert snapshot["sites"] == [
        {"id": "site-a", "name": "Downstairs"},
        {"id": "site-b", "name": "Upstairs"},
    ]
    assert snapshot["collected"]
    switch = next(device for device in snapshot["devices"] if device["type"] == "switch")
    assert switch == {
        "entity_id": "net/alis-switch", "class": "net", "site": "Downstairs",
        "type": "switch", "name": "Ali’s Switch", "model": "SG3428X",
        "mac": "AA:BB:CC:DD:EE:01", "ip": "10.10.50.2", "firmware": "1.0.7",
        "needs_upgrade": True, "status": 1, "connected": True, "uptime_s": 86400,
        "clients": 12, "poe": {"support": True, "remain_w": 83.5, "total_w": 192},
        "ports": [
            {"port": 1, "name": "uplink", "profile": "All", "link": 1,
             "speed": 1000, "poe": 0, "disabled": False},
            {"port": 8, "name": "U6-AP", "profile": "LAN", "link": 1,
             "speed": 100, "poe": 12.5, "disabled": False},
            {"port": 24, "name": "unused", "profile": "Default", "link": 0,
             "speed": 0, "poe": 0, "disabled": True},
        ],
    }
    ap = next(device for device in snapshot["devices"] if device["type"] == "ap")
    assert ap["entity_id"] == "net/lobby-ap" and ap["firmware"] == "1.2.3"
    assert ap["ports"] is None
    assert all(connection.closed for connection in transport.instances)


def test_only_info_login_and_authenticated_read_endpoints_are_requested(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    paths = [connection.path for connection in transport.instances]
    assert set(paths) == {INFO_PATH, LOGIN_PATH, SITES_PATH, DEVICES_A, DEVICES_B, PORTS_A}
    assert paths.count(INFO_PATH) == paths.count(LOGIN_PATH) == 1
    assert all(connection.method == "GET" for connection in transport.instances if connection.path != LOGIN_PATH)
    assert next(connection for connection in transport.instances if connection.path == LOGIN_PATH).method == "POST"
    login = next(connection for connection in transport.instances if connection.path == LOGIN_PATH)
    assert json.loads(login.body or b"{}") == {"username": USER, "password": PASSWORD}
    info = next(connection for connection in transport.instances if connection.path == INFO_PATH)
    assert info.headers == {"Content-Type": "application/json"} or info.headers == {}
    authenticated = [connection for connection in transport.instances
                     if connection.path not in {INFO_PATH, LOGIN_PATH}]
    assert all(connection.headers.get("Cookie") == COOKIE for connection in authenticated)
    assert all(connection.headers.get("Csrf-Token") == CSRF for connection in authenticated)


def test_valid_empty_site_listing_and_non_switch_without_ports(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    transport.responses[SITES_PATH] = fixture("empty-sites.json")
    code, report, output = collect(tmp_path, credentials, capsys)
    assert code == 0 and report["outcome"] == "success"
    snapshot = json.loads(output.read_text())
    assert snapshot["sites"] == [] and snapshot["devices"] == []
    assert DEVICES_A not in [connection.path for connection in transport.instances]


@pytest.mark.parametrize("path,payload", [
    (INFO_PATH, {"errorCode": 0, "result": None}),
    (INFO_PATH, b"not-json"),
    (LOGIN_PATH, {"errorCode": 7, "msg": "secret-login-error"}),
    (SITES_PATH, {"errorCode": 0, "result": {"data": None, "totalRows": 0}}),
    (DEVICES_A, {"errorCode": 0, "result": None}),
    (PORTS_A, {"errorCode": 0, "result": None}),
    (PORTS_A, FakeResponse({"errorCode": 0, "result": []}, status=502)),
])
def test_malformed_null_api_error_or_partial_required_read_fails_without_publication(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], path: str, payload: Any,
) -> None:
    transport.responses[path] = payload
    code, report, output = collect(tmp_path, credentials, capsys)
    assert code in (1, 3)
    assert report["outcome"] in ("failure", "unavailable")
    assert not output.exists()
    assert "secret-login-error" not in json.dumps(report)
    assert PASSWORD not in json.dumps(report)


def test_site_pagination_mismatch_fails_and_retains_previous_bytes(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    output = tmp_path / "network-gear.json"
    previous = output.read_bytes()
    transport.responses[SITES_PATH]["result"]["totalRows"] = 3
    code, report, _ = collect(tmp_path, credentials, capsys)
    assert code in (1, 3) and report["outcome"] in ("failure", "unavailable")
    assert output.read_bytes() == previous


def test_partial_site_failure_retains_previous_bytes(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    output = tmp_path / "network-gear.json"
    previous = output.read_bytes()
    transport.responses[DEVICES_B] = OSError("remote device error contains secret-login-error")
    code, report, _ = collect(tmp_path, credentials, capsys)
    assert code == 3 and report["outcome"] == "unavailable"
    assert output.read_bytes() == previous
    assert "remote device error" not in json.dumps(report)


def test_duplicate_entity_identity_is_rejected_and_retains_previous_bytes(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    output = tmp_path / "network-gear.json"
    previous = output.read_bytes()
    transport.responses[DEVICES_B]["result"][0]["name"] = "Ali’s Switch"
    code, report, _ = collect(tmp_path, credentials, capsys)
    assert code == 1 and report["outcome"] == "failure"
    assert output.read_bytes() == previous


def test_transport_unavailable_is_redacted_and_preserves_existing_snapshot(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert collect(tmp_path, credentials, capsys)[0] == 0
    output = tmp_path / "network-gear.json"
    previous = output.read_bytes()
    transport.responses[INFO_PATH] = OSError("TLS failed with p@ss; & secret-login-error")
    code, report, _ = collect(tmp_path, credentials, capsys)
    assert code == 3 and report["outcome"] == "unavailable"
    assert output.read_bytes() == previous
    assert all(secret not in json.dumps(report) for secret in (PASSWORD, COOKIE, CSRF, "secret-login-error"))


def test_credentials_parser_reads_literal_values_without_shell_evaluation(
    credentials: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(omada, "_sni_from_certificate", lambda _path, _host: SNI)
    settings = omada.credentials(credentials)
    assert settings.host == HOST and settings.port == PORT and settings.sni == SNI
    assert settings.username == USER and settings.password == PASSWORD


def test_invalid_credentials_are_rejected_without_transport(
    tmp_path: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    credentials = tmp_path / "bad.env"
    credentials.write_text("OMADA_HOST=10.10.50.25\nOMADA_PASS=$(touch /tmp/pwned)\n")
    code, report, output = collect(tmp_path, credentials, capsys)
    assert code == 3 and report["outcome"] == "unavailable"
    assert not output.exists() and transport.instances == []


def test_fixture_mutations_do_not_leak_between_calls(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    baseline = copy.deepcopy(transport.responses[SITES_PATH])
    transport.responses[SITES_PATH]["result"]["totalRows"] = 99
    assert collect(tmp_path, credentials, capsys)[0] != 0
    assert baseline["result"]["totalRows"] == 2
