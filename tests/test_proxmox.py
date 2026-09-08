"""Behavioral tests for the isolated core Proxmox collector."""

from __future__ import annotations

import json
import os
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest

# Source tests import the checkout; the console check imports the installed package.
ROOT = Path(__file__).parents[1]
if os.environ.get("SKYNET_ENTRYPOINT") != "console" and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skynet.cli import main  # noqa: E402 — select source/installed path before import
import skynet.proxmox as proxmox  # noqa: E402


FIXTURES = Path(__file__).parent / "fixtures" / "proxmox"
TOKEN = "svc-ops@pve!readonly=synthetic-token"


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def endpoint_data() -> dict[str, Any]:
    node = "server core/1"
    pool = "ops managed/blue"
    return {
        "/api2/json/nodes": fixture("nodes.json"),
        "/api2/json/cluster/resources": fixture("resources.json"),
        "/api2/json/pools": fixture("pools.json"),
        f"/api2/json/pools/{quote(pool, safe='')}": fixture("pool-detail.json"),
        "/api2/json/cluster/backup": fixture("backup.json"),
        (
            f"/api2/json/nodes/{quote(node, safe='')}/tasks"
            "?typefilter=vzdump&limit=5"
        ): fixture("tasks.json"),
    }


class FakeResponse:
    def __init__(self, payload: Any, status: int = 200, headers: dict[str, str] | None = None):
        self.status = status
        self._payload = payload
        self.headers = headers or {}

    def read(self) -> bytes:
        if isinstance(self._payload, bytes):
            return self._payload
        return json.dumps(self._payload).encode()

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name, default)


class FakeConnection:
    instances: list["FakeConnection"] = []
    responses: dict[str, Any] = {}
    contexts: list[ssl.SSLContext | None] = []

    def __init__(self, host: str, port: int, *, context: ssl.SSLContext | None, timeout: int):
        assert host == "pve.example.test"
        assert port == 8006
        assert timeout == 15
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.closed = False
        self.context = context
        self.instances.append(self)
        self.contexts.append(context)

    def request(self, method: str, path: str, *, headers: dict[str, str]) -> None:
        assert method == "GET"
        assert headers == {"Authorization": f"PVEAPIToken={TOKEN}"}
        self.requests.append((method, path, headers))

    def getresponse(self) -> FakeResponse:
        path = self.requests[-1][1]
        response = self.responses[path]
        if isinstance(response, BaseException):
            raise response
        if callable(response):
            response = response()
        if isinstance(response, FakeResponse):
            return response
        return FakeResponse(response)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> type[FakeConnection]:
    FakeConnection.instances = []
    FakeConnection.responses = endpoint_data()
    FakeConnection.contexts = []
    monkeypatch.setattr(proxmox.http.client, "HTTPSConnection", FakeConnection)
    return FakeConnection


@pytest.fixture
def credentials(tmp_path: Path) -> Path:
    cafile = ssl.get_default_verify_paths().cafile
    assert cafile is not None and Path(cafile).is_file()
    path = tmp_path / "proxmox-core.env"
    path.write_text(
        "# synthetic test credentials\n"
        "PVE_HOST='pve.example.test'\n"
        f"PVE_TOKEN=\"{TOKEN}\" # token\n"
        "PVE_TOKEN_OPERATE='synthetic-operate-token'\n"
        f"PVE_CACERT={cafile}\n"
    )
    return path


def test_shared_credentials_keep_operate_optional_and_never_substitute_it(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    shared = credentials.read_text()
    assert collect(tmp_path, credentials, capsys)[0] == 0
    credentials.write_text(shared.replace("PVE_TOKEN_OPERATE='synthetic-operate-token'\n", ""))
    assert collect(tmp_path, credentials, capsys)[0] == 0
    credentials.write_text("\n".join(line for line in shared.splitlines()
                                     if not line.startswith("PVE_TOKEN=")))
    before = len(transport.instances)
    assert collect(tmp_path, credentials, capsys)[0] == 3
    assert len(transport.instances) == before


@pytest.mark.parametrize("assignment", [
    "PVE_TOKEN_OPERATE=duplicate", "PVE_TOKEN_OPERATE=$(invalid)",
    "PVE_TOKEN_OPERATE=", "UNSUPPORTED=synthetic-operate-token",
])
def test_shared_credential_invalid_assignments_remain_refused(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], assignment: str,
) -> None:
    contents = credentials.read_text()
    if assignment != "PVE_TOKEN_OPERATE=duplicate":
        contents = contents.replace("PVE_TOKEN_OPERATE='synthetic-operate-token'\n", "")
    credentials.write_text(contents + assignment + "\n")
    code, _, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=True)
    assert code == 3 and not transport.instances
    assert "synthetic-operate-token" not in stdout + stderr


def collect(
    tmp_path: Path,
    credentials: Path,
    capsys: pytest.CaptureFixture[str],
    *,
    json_output: bool = False,
) -> tuple[int, dict[str, Any] | None, str, str]:
    output = tmp_path / "snapshot.json"
    args = [
        "collect",
        "proxmox",
        "core",
        "--output",
        str(output),
        "--credentials-file",
        str(credentials),
    ]
    if json_output:
        args.append("--json")
    code = main(args)
    captured = capsys.readouterr()
    assert "synthetic-operate-token" not in captured.out + captured.err
    report = json.loads(captured.out) if json_output and captured.out.strip() else None
    return code, report, captured.out, captured.err


def test_success_human_summary_and_snapshot_projection(
    tmp_path: Path,
    credentials: Path,
    transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, report, stdout, stderr = collect(tmp_path, credentials, capsys)

    assert code == 0
    assert report is None
    assert stderr == ""
    assert "proxmox-core: success" in stdout
    assert "nodes: 1" in stdout
    assert "guests: 2" in stdout
    assert "pools: 1" in stdout
    snapshot = json.loads((tmp_path / "snapshot.json").read_text())
    assert set(snapshot) == {
        "node",
        "collected",
        "nodes",
        "resources",
        "pools",
        "backup_jobs",
        "backup_last",
    }
    assert snapshot["node"] == "core"
    assert isinstance(snapshot["collected"], str) and snapshot["collected"]
    assert [member.keys() for member in snapshot["pools"][0]["members"]] == [
        {"id", "type", "vmid", "node"},
        {"id", "type", "vmid", "node"},
    ]
    assert snapshot["backup_jobs"][0]["vmid"] is None
    assert snapshot["backup_jobs"][0]["pool"] is None
    assert snapshot["backup_jobs"][0]["node"] is None
    # These are the fields projected by build-db.sh and render-docs.sh.
    guests = [r for r in snapshot["resources"] if r["type"] in {"qemu", "lxc"}]
    assert [(r["vmid"], r["name"], r["status"], r.get("template", 0), r.get("pool", ""))
            for r in guests] == [
        (10015, "vm-docker-dmz", "running", 0, ""),
        (731, "lxc-adguard-core", "running", 0, ""),
    ]
    assert snapshot["pools"][0]["members"] == [
        {"id": "qemu/10015", "type": "qemu", "vmid": 10015, "node": "server core/1"},
        {"id": "lxc/731", "type": "lxc", "vmid": 731, "node": "server core/1"},
    ]
    assert snapshot["backup_jobs"][0] == fixture("backup.json")["data"][0]
    assert snapshot["backup_last"] == [
        {"node": "server core/1", "starttime": 1788561001, "status": "OK"},
    ]
    assert len(transport.instances) == 6
    assert all(connection.closed for connection in transport.instances)
    assert all(context is not None and context.check_hostname for context in transport.contexts)
    assert all(
        context is not None and context.verify_mode == ssl.CERT_REQUIRED
        for context in transport.contexts
    )


def test_success_json_report_agrees_with_human_contract(
    tmp_path: Path,
    credentials: Path,
    transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, report, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=True)

    assert code == 0
    assert stderr == ""
    assert report is not None
    assert report["outcome"] == "success"
    assert report["target"] == "proxmox-core"
    assert report["output"] == str(tmp_path / "snapshot.json")
    assert isinstance(report["collected"], str) and report["collected"]
    assert report["counts"] == {"nodes": 1, "guests": 2, "pools": 1}
    assert TOKEN not in stdout


def test_url_paths_are_encoded_and_authorization_is_not_forwarded(
    tmp_path: Path,
    credentials: Path,
    transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, _, _, _ = collect(tmp_path, credentials, capsys)

    assert code == 0
    paths = [request[1] for connection in transport.instances for request in connection.requests]
    assert f"/api2/json/pools/{quote('ops managed/blue', safe='')}" in paths
    assert (
        f"/api2/json/nodes/{quote('server core/1', safe='')}/tasks"
        "?typefilter=vzdump&limit=5"
    ) in paths


def test_failed_refresh_after_earlier_reads_preserves_prior_snapshot(
    tmp_path: Path,
    credentials: Path,
    transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "snapshot.json"
    previous = b'{"previous": true, "collected": "old"}\n'
    output.write_bytes(previous)
    transport.responses["/api2/json/cluster/resources"] = TimeoutError("timed out")

    code, report, stdout, _ = collect(tmp_path, credentials, capsys, json_output=True)

    assert code == 3
    assert report is not None
    assert report["outcome"] in {"failure", "unavailable"}
    assert "reason" in report
    assert "previous evidence" in report["reason"].lower()
    assert "collected" not in report
    assert output.read_bytes() == previous
    assert TOKEN not in stdout
    assert {path for path in tmp_path.iterdir()} == {credentials, output}


@pytest.mark.parametrize(
    "failure",
    [
        ssl.SSLError(f"certificate verify failed {TOKEN}"),
        TimeoutError(f"timed out {TOKEN}"),
        FakeResponse({"error": TOKEN}, status=500),
        FakeResponse({}, status=302, headers={"Location": "https://elsewhere.test/"}),
    ],
    ids=["tls-refusal", "timeout", "http-failure", "redirect-refusal"],
)
def test_remote_failures_are_unavailable_and_do_not_publish(
    tmp_path: Path,
    credentials: Path,
    transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
    failure: Any,
) -> None:
    output = tmp_path / "snapshot.json"
    previous = b"retained evidence\n"
    output.write_bytes(previous)
    transport.responses["/api2/json/nodes"] = failure

    code, report, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=True)

    assert code == 3
    assert report is not None
    assert report["outcome"] in {"failure", "unavailable"}
    assert "collected" not in report
    assert output.read_bytes() == previous
    assert TOKEN not in stdout + stderr
    if isinstance(failure, FakeResponse) and failure.status in {301, 302, 303, 307, 308}:
        assert len(transport.instances[0].requests) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("nodes", None),
        ("nodes", []),
        ("resources", None),
        ("resources", []),
    ],
)
def test_absent_null_or_empty_required_data_is_malformed(
    tmp_path: Path,
    credentials: Path,
    transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
    field: str,
    value: Any,
) -> None:
    endpoint = "/api2/json/nodes" if field == "nodes" else "/api2/json/cluster/resources"
    transport.responses[endpoint] = {"data": value}

    code, report, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=True)

    assert code == 1
    assert report is not None
    assert report["outcome"] == "failure"
    assert "reason" in report and "previous evidence" in report["reason"].lower()
    assert "collected" not in report
    assert not (tmp_path / "snapshot.json").exists()
    assert TOKEN not in stdout + stderr


@pytest.mark.parametrize(
    "endpoint,payload",
    [
        ("/api2/json/nodes", b"not-json"),
        ("/api2/json/nodes", []),
        ("/api2/json/nodes", {"data": [42]}),
        ("/api2/json/nodes", {"unexpected": []}),
        ("/api2/json/nodes", {"data": [{"type": "node"}]}),
        ("/api2/json/cluster/resources", {"data": [{"type": "qemu"}]}),
        ("/api2/json/pools", {"data": [{"comment": "missing identity"}]}),
    ],
)
def test_malformed_envelopes_or_entries_fail_closed(
    tmp_path: Path,
    credentials: Path,
    transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
    endpoint: str,
    payload: Any,
) -> None:
    transport.responses[endpoint] = payload

    code, report, _, _ = collect(tmp_path, credentials, capsys, json_output=True)

    assert code == 1
    assert report is not None
    assert report["outcome"] == "failure"
    assert "collected" not in report
    assert not (tmp_path / "snapshot.json").exists()


@pytest.mark.parametrize(
    "contents",
    [
        "",
        "PVE_HOST=pve.example.test\nPVE_CACERT=/etc/ssl/certs/ca-certificates.crt\n",
        "PVE_HOST=$(echo pve.example.test)\n"
        "PVE_TOKEN=secret\nPVE_CACERT=/etc/ssl/certs/ca-certificates.crt\n",
        "PVE_HOST=pve.example.test\nPVE_TOKEN=secret\n"
        "PVE_CACERT=/etc/ssl/certs/ca-certificates.crt\nBAD=1+2\n",
    ],
    ids=["empty", "missing-token", "expression", "unknown-expression"],
)
def test_missing_or_malformed_credentials_are_unavailable(
    tmp_path: Path,
    transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
    contents: str,
) -> None:
    credentials = tmp_path / "bad.env"
    credentials.write_text(contents)
    code, report, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=True)

    assert code == 3
    assert report is not None
    assert report["outcome"] in {"failure", "unavailable"}
    assert "collected" not in report
    assert not (tmp_path / "snapshot.json").exists()
    assert not transport.instances
    assert TOKEN not in stdout + stderr


def test_missing_credentials_file_is_unavailable(
    tmp_path: Path,
    transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    credentials = tmp_path / "does-not-exist.env"

    code, report, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=True)

    assert code == 3
    assert report is not None
    assert "reason" in report
    assert TOKEN not in stdout + stderr
    assert not transport.instances


def test_atomic_replacement_failure_preserves_previous_and_leaves_no_temp(
    tmp_path: Path,
    credentials: Path,
    transport: type[FakeConnection],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "snapshot.json"
    previous = b'{"previous": true}\n'
    output.write_bytes(previous)

    def fail_replace(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(proxmox.os, "replace", fail_replace)
    code, report, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=True)

    assert code == 1
    assert report is not None
    assert report["outcome"] == "failure"
    assert "previous evidence" in report["reason"].lower()
    assert "collected" not in report
    assert output.read_bytes() == previous
    assert {path for path in tmp_path.iterdir()} == {credentials, output}
    assert TOKEN not in stdout + stderr


@pytest.mark.parametrize("json_output", [False, True])
def test_last_endpoint_failure_retains_timestamp_and_redacts_both_modes(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], json_output: bool,
) -> None:
    output = tmp_path / "snapshot.json"
    previous = b'{"collected":"2000-01-01T00:00:00+00:00"}\n'
    output.write_bytes(previous)
    old_stat = output.stat()
    task_path = next(path for path in transport.responses if "/tasks?" in path)
    transport.responses[task_path] = TimeoutError(TOKEN)
    code, report, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=json_output)
    assert code == 3
    assert len(transport.instances) == 6
    assert output.read_bytes() == previous
    assert output.stat().st_mtime_ns == old_stat.st_mtime_ns
    assert "previous evidence" in stdout
    assert TOKEN not in stdout + stderr
    if report:
        assert "collected" not in report
        assert "counts" not in report


def test_empty_optional_lists_publish_unknown_backup_result(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    for path in transport.responses:
        if path.endswith(("/pools", "/cluster/backup")) or "/tasks?" in path:
            transport.responses[path] = {"data": []}
    code, report, _, _ = collect(tmp_path, credentials, capsys, json_output=True)
    assert code == 0
    assert report is not None and report["counts"]["pools"] == 0
    data = json.loads((tmp_path / "snapshot.json").read_text())
    assert data["pools"] == data["backup_jobs"] == []
    assert data["backup_last"] == [{"node": "server core/1", "starttime": None, "status": None}]


@pytest.mark.parametrize("endpoint,key,value", [
    ("resources", "vmid", "10015"),
    ("resources", "vmid", True),
    ("resources", "id", "qemu/999"),
    ("resources", "status", None),
    ("resources", "template", "0"),
    ("resources", "node", "unobserved"),
    ("backup", "enabled", "1"),
    ("backup", "all", True),
    ("backup", "vmid", 10015),
    ("tasks", "starttime", "1000"),
    ("tasks", "status", 1),
])
def test_wrong_entry_field_types_do_not_publish(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], endpoint: str, key: str, value: Any,
) -> None:
    path = next(path for path in transport.responses if endpoint in path)
    transport.responses[path]["data"][0][key] = value
    code, report, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=True)
    assert code == 1
    assert report is not None and report["outcome"] == "failure"
    assert not (tmp_path / "snapshot.json").exists()
    assert TOKEN not in stdout + stderr


@pytest.mark.parametrize("members", [None, {}, [None], [{"id": "qemu/1", "type": "qemu"}]])
def test_unreadable_or_malformed_pool_members_never_become_empty(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], members: Any,
) -> None:
    path = next(path for path in transport.responses if "/pools/" in path)
    transport.responses[path]["data"]["members"] = members
    code, report, _, _ = collect(tmp_path, credentials, capsys, json_output=True)
    assert code == 1
    assert report is not None and report["outcome"] == "failure"
    assert not (tmp_path / "snapshot.json").exists()


@pytest.mark.parametrize("ca_state", ["absent", "invalid"])
def test_ca_unavailable_fails_before_any_request(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], ca_state: str,
) -> None:
    ca = tmp_path / "synthetic-ca.crt"
    if ca_state == "invalid":
        ca.write_text("not a certificate")
    credentials.write_text(f"PVE_HOST=pve.example.test\nPVE_TOKEN='{TOKEN}'\nPVE_CACERT={ca}\n")
    code, report, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=True)
    assert code == 3
    assert report is not None and report["outcome"] == "unavailable"
    assert not transport.instances
    assert TOKEN not in stdout + stderr


@pytest.mark.parametrize("operation", ["fsync", "NamedTemporaryFile"])
def test_local_write_failures_are_redacted_and_leave_no_residue(
    tmp_path: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, operation: str,
) -> None:
    output = tmp_path / "snapshot.json"
    output.write_bytes(b"old snapshot")

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise OSError(TOKEN)

    boundary = proxmox.os if operation == "fsync" else proxmox.tempfile
    monkeypatch.setattr(boundary, operation, fail)
    code, report, stdout, stderr = collect(tmp_path, credentials, capsys, json_output=True)
    assert code == 1
    assert report is not None and report["outcome"] == "failure"
    assert output.read_bytes() == b"old snapshot"
    assert set(tmp_path.iterdir()) == {credentials, output}
    assert TOKEN not in stdout + stderr
