"""Behavioral tests for the isolated PBS collector and its trust/failure boundary."""

from __future__ import annotations

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
        "/api2/json/admin/datastore/unraid/snapshots?ns=core": fixture("core-snapshots.json"),
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
