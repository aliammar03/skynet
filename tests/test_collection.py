"""Default collector, persisted freshness evidence and shell caller boundaries."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from test_proxmox import FakeConnection, TOKEN
from skynet.cli import main
from skynet import collection

ROOT = Path(__file__).parents[1]
pytest_plugins = ["test_proxmox"]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    (path / "inventory").mkdir(parents=True)
    (path / "scripts").mkdir()
    for _, name, *_ in collection.REMAINING:
        script = path / "scripts" / name
        script.write_text(
            f"#!{sys.executable}\nfrom pathlib import Path\n"
            "with Path('calls').open('a') as f: f.write(Path(__file__).name + '\\n')\n"
        )
        script.chmod(0o755)
    return path


def run(repo: Path, credentials: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict]:
    code = main(["collect", "all", "--repo", str(repo),
                 "--credentials-file", str(credentials), "--json"])
    captured = capsys.readouterr()
    assert TOKEN not in captured.out + captured.err
    return code, json.loads(captured.out)


def status(repo: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> int:
    code = main(["collect-status", "--repo", str(repo), "--json", *extra])
    report = json.loads(capsys.readouterr().out)
    assert report["outcome"] == ("success" if code == 0 else "unavailable")
    return code


def test_default_collection_records_matching_evidence_and_runs_remaining_once(
    repo: Path, credentials: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    code, report = run(repo, credentials, capsys)
    assert code == 0 and report["outcome"] == "success"
    assert len(report["collectors"]) == 11
    assert (repo / "calls").read_text().splitlines() == [row[1] for row in collection.REMAINING]
    evidence = json.loads((repo / "inventory/collection-core.json").read_text())
    assert evidence["sha256"] == hashlib.sha256(
        (repo / "inventory/proxmox-core.json").read_bytes()).hexdigest()
    assert status(repo, capsys) == 0


@pytest.mark.parametrize("failure", [TimeoutError(TOKEN), {"data": None}, {"data": [{}]}])
def test_failed_core_refresh_retains_snapshot_but_invalidates_freshness_and_continues(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], failure: object,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    output = repo / "inventory/proxmox-core.json"
    previous = output.read_bytes()
    endpoint = next(path for path in transport.responses if "/tasks?" in path)
    transport.responses[endpoint] = failure
    assert run(repo, credentials, capsys)[0] != 0
    assert output.read_bytes() == previous
    assert status(repo, capsys) == 3
    assert len((repo / "calls").read_text().splitlines()) == 20


def test_interrupted_refresh_leaves_incomplete_marker(
    repo: Path, credentials: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    transport.responses["/api2/json/nodes"] = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        run(repo, credentials, capsys)
    assert status(repo, capsys) == 3


@pytest.mark.parametrize("case", ["missing", "corrupt", "hash", "stale", "future", "naive", "since"])
def test_unusable_evidence_never_reports_fresh(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], case: str,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    marker = repo / "inventory/collection-core.json"
    snapshot = repo / "inventory/proxmox-core.json"
    if case == "missing":
        marker.unlink()
    elif case == "corrupt":
        marker.write_text("[]")
    elif case == "hash":
        snapshot.write_bytes(snapshot.read_bytes() + b"\n")
    elif case in {"stale", "future", "naive"}:
        instant = datetime.now(UTC) + timedelta(hours=-37 if case == "stale" else 1)
        stamp = instant.isoformat() if case != "naive" else "2026-09-07T12:00:00"
        data = json.loads(snapshot.read_text())
        data["collected"] = stamp
        snapshot.write_text(json.dumps(data))
        evidence = json.loads(marker.read_text())
        evidence.update(collected=stamp, attempted=stamp,
                        sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest())
        marker.write_text(json.dumps(evidence))
    extra = ["--since", (datetime.now(UTC) + timedelta(seconds=1)).isoformat()] if case == "since" else []
    assert status(repo, capsys, *extra) == 3


def test_remaining_timeout_is_failure_and_does_not_repeat_core(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def timeout(args: list[str], **kwargs: object) -> None:
        calls.append(args)
        assert kwargs["timeout"] == 120
        raise subprocess.TimeoutExpired(args, 120, output=TOKEN)

    monkeypatch.setattr(collection.subprocess, "run", timeout)
    assert run(repo, credentials, capsys)[0] == 1
    assert len(calls) == 10
    assert len(transport.instances) == 6
    assert status(repo, capsys) == 0  # core success is independent of other readers' exits


def test_missing_credentials_fails_default_path_without_remote_access(
    repo: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(repo, repo / "missing.env", capsys)[0] == 3
    assert not transport.instances
    assert status(repo, capsys) == 3


def test_lock_refuses_overlap_before_remote_reads(
    repo: Path, credentials: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    (repo / ".cache").mkdir()
    with (repo / ".cache/collection.lock").open("a") as lock:
        collection.fcntl.flock(lock, collection.fcntl.LOCK_EX | collection.fcntl.LOCK_NB)
        assert run(repo, credentials, capsys)[0] == 1
    assert not transport.instances


def test_failed_success_marker_publication_keeps_evidence_unavailable(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    from skynet import proxmox
    replace = proxmox.os.replace
    marker_writes = 0

    def fail_final_marker(source: str, destination: Path) -> None:
        nonlocal marker_writes
        if destination.name == "collection-core.json":
            marker_writes += 1
            if marker_writes == 2:
                raise OSError(TOKEN)
        replace(source, destination)

    monkeypatch.setattr(proxmox.os, "replace", fail_final_marker)
    assert run(repo, credentials, capsys)[0] == 1
    assert (repo / "inventory/proxmox-core.json").exists()
    assert status(repo, capsys) == 3
    assert not list((repo / "inventory").glob(".*"))


def test_marker_setup_failure_cannot_satisfy_this_pass_with_previous_success(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    from skynet import proxmox
    assert run(repo, credentials, capsys)[0] == 0
    since = datetime.now(UTC).isoformat()
    previous_requests = len(transport.instances)

    def fail_replace(*args: object) -> None:
        raise OSError(TOKEN)

    monkeypatch.setattr(proxmox.os, "replace", fail_replace)
    assert run(repo, credentials, capsys)[0] == 1
    assert len(transport.instances) == previous_requests
    assert status(repo, capsys, "--since", since) == 3


@pytest.mark.parametrize("entry,args,expected", [
    ("bin/ops", ["collect"], ["collect", "all", "--repo"]),
    ("bin/ops", ["entities"], ["collect-status", "--repo"]),
    ("bin/ops", ["query", "SELECT 1"], ["collect-status", "--repo"]),
    ("scripts/render-docs.sh", [], ["collect-status", "--repo"]),
    ("scripts/collect-proxmox.sh", ["core"], ["collect", "proxmox", "core"]),
])
def test_default_shell_callers_use_offline_package_and_propagate_failure(
    tmp_path: Path, entry: str, args: list[str], expected: list[str],
) -> None:
    for relative in ("bin/ops", "bin/skynet", "scripts/collect-all.sh",
                     "scripts/render-docs.sh", "scripts/collect-proxmox.sh"):
        target = tmp_path / relative
        target.parent.mkdir(exist_ok=True)
        shutil.copy(ROOT / relative, target)
        target.chmod(0o755)
        # The Nix sandbox has no /usr/bin/env; preserve the real script body.
        target.write_text(target.read_text().replace(
            "#!/usr/bin/env bash", f"#!{shutil.which('bash')}", 1))
        target.chmod(0o755)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_nix = fake_bin / "nix"
    fake_nix.write_text(f"#!{sys.executable}\nimport json,sys\n"
                        f"open({str(tmp_path / 'argv')!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
                        "sys.exit(47)\n")
    fake_nix.chmod(0o755)
    environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}
    result = subprocess.run(["bash", str(tmp_path / entry), *args], env=environment,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 47
    argv = json.loads((tmp_path / "argv").read_text())
    assert argv[:3] == ["run", "--offline", "--no-write-lock-file"]
    assert argv[3] == f"git+file://{tmp_path}#skynet"
    assert argv[5:5 + len(expected)] == expected
    assert not (tmp_path / "docs").exists()  # renderer stops before any publication


def test_bin_ops_collection_reaches_real_cli_and_core_collector(
    repo: Path, credentials: Path,
) -> None:
    for relative in ("bin/ops", "bin/skynet", "scripts/collect-all.sh"):
        target = repo / relative
        target.parent.mkdir(exist_ok=True)
        target.write_text((ROOT / relative).read_text().replace(
            "#!/usr/bin/env bash", f"#!{shutil.which('bash')}", 1))
        target.chmod(0o755)
    fake_bin = repo / "fake-bin"
    fake_bin.mkdir()
    launcher = fake_bin / "nix"
    # Substitute package launch/HTTPS boundaries, retaining the actual shell chain and CLI.
    launcher.write_text(
        f"#!{sys.executable}\nimport sys\nsys.path[:] = {sys.path!r}\n"
        "from test_proxmox import FakeConnection, endpoint_data\n"
        "from skynet import proxmox\nfrom skynet.cli import main\n"
        "FakeConnection.responses = endpoint_data()\n"
        "proxmox.http.client.HTTPSConnection = FakeConnection\n"
        "sys.exit(main(sys.argv[6:]))\n"
    )
    launcher.chmod(0o755)
    result = subprocess.run(
        ["bash", str(repo / "bin/ops"), "collect", "--credentials-file", str(credentials), "--json"],
        env=os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["outcome"] == "success"
    assert TOKEN not in result.stdout + result.stderr
    assert (repo / "inventory/proxmox-core.json").exists()
    assert json.loads((repo / "inventory/collection-core.json").read_text())["outcome"] == "success"


def test_failed_cache_rebuild_never_reuses_previous_cache(tmp_path: Path) -> None:
    for directory in ("bin", "scripts", "inventory", ".cache"):
        (tmp_path / directory).mkdir()
    renderer = tmp_path / "scripts/render-docs.sh"
    renderer.write_text((ROOT / "scripts/render-docs.sh").read_text())
    bash = shutil.which("bash")
    (tmp_path / "bin/skynet").write_text(f"#!{bash}\nexit 0\n")
    (tmp_path / "bin/skynet").chmod(0o755)
    (tmp_path / "scripts/build-db.sh").write_text(f"#!{bash}\nexit 1\n")
    (tmp_path / "scripts/build-db.sh").chmod(0o755)
    (tmp_path / "inventory/proxmox-core.json").write_text('{"node":"core","resources":[]}')
    (tmp_path / ".cache/inventory.db").write_text("old cache")
    sqlite = tmp_path / "sqlite"
    sqlite.write_text(
        f"#!{sys.executable}\nimport sys\nfrom pathlib import Path\n"
        f"if '--version' not in sys.argv: Path({str(tmp_path / 'cache-read')!r}).touch()\n"
    )
    sqlite.chmod(0o755)
    subprocess.run(["bash", str(renderer)], env=os.environ | {"SQLITE3": str(sqlite)},
                   capture_output=True, text=True, check=False)
    assert not (tmp_path / "cache-read").exists()
    assert (tmp_path / "docs/generated/10-vlans.md").exists()
