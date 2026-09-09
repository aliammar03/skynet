"""Default collector, persisted freshness evidence and shell caller boundaries."""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from test_proxmox import (FakeConnection, NETWORK_OPERATE_TOKEN, NETWORK_TOKEN, OPERATE_TOKEN,
                          network_endpoint_data, TOKEN)
from skynet.cli import main
from skynet import collection, dns, docker, opnsense, pbs, proxmox

ROOT = Path(__file__).parents[1]
pytest_plugins = ["test_proxmox"]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    (path / "inventory" / "firewall").mkdir(parents=True)
    (path / "scripts").mkdir()
    for _, name, *_ in collection.REMAINING:
        script = path / "scripts" / name
        script.write_text(
            f"#!{sys.executable}\nfrom pathlib import Path\n"
            "with Path('calls').open('a') as f: f.write(Path(__file__).name + '\\n')\n"
        )
        script.chmod(0o755)
    return path


@pytest.fixture(autouse=True)
def pbs_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep Proxmox receipt tests focused; PBS transport is covered in test_pbs."""
    def collect(output: Path, credentials_file: Path, *, json_output: bool, stdout: object) -> int:
        data = {"collected": datetime.now(UTC).isoformat(timespec="seconds"), "host": "pbs.test",
                "datastores": [{"store": "unraid", "status": {"used": 1, "total": 2},
                                "groups": [], "group_count": 0, "snapshot_total": 0,
                                "unverified": 0}]}
        proxmox.publish(output, data)
        report = {"target": "pbs", "outcome": "success", "collected": data["collected"],
                  "counts": {"datastores": 1, "snapshots": 0}}
        if json_output:
            print(json.dumps(report), file=stdout)  # type: ignore[arg-type]
        return 0
    monkeypatch.setattr(pbs, "collect", collect)
    def docker_collect(label: str, output: Path, context: str, *, json_output: bool, stdout: object,
                       raise_cleanup: bool = False) -> int:
        data = {"collected": datetime.now(UTC).isoformat(timespec="seconds"), "host": label,
                "containers": [], "images": []}
        proxmox.publish(output, data)
        report = {"target": f"docker-{label}", "outcome": "success", "collected": data["collected"],
                  "counts": {"containers": 0, "images": 0}}
        if json_output:
            print(json.dumps(report), file=stdout)  # type: ignore[arg-type]
        return 0
    monkeypatch.setattr(docker, "collect", docker_collect)
    def dns_collect(output: Path, credentials_file: Path, *, json_output: bool, stdout: object) -> int:
        data = {"collected": datetime.now(UTC).isoformat(timespec="seconds"), "host": "10.10.70.50",
                "zones": [{"name": "aliammar.net"}],
                "records": [{"zone": "aliammar.net", "records": []}]}
        proxmox.publish(output, data)
        report = {"target": "dns", "outcome": "success", "collected": data["collected"],
                  "counts": {"zones": 1, "records": 0}}
        if json_output:
            print(json.dumps(report), file=stdout)  # type: ignore[arg-type]
        return 0
    monkeypatch.setattr(dns, "collect", dns_collect)
    def opnsense_collect(firewall_output: Path, state_output: Path, credentials_file: Path, *,
                         json_output: bool, stdout: object) -> int:
        collected = datetime.now(UTC).isoformat(timespec="seconds")
        proxmox.publish(firewall_output, {"collected": collected, "source": "stub",
                                          "host": "10.10.60.1",
                                          "counts": {"aliases": 0, "rules": 0, "reservations": 0},
                                          "aliases": [], "rules": [], "reservations": []})
        proxmox.publish(state_output, {"collected": collected, "source": "stub", "host": "10.10.60.1",
                                       "firmware": {"status": "none", "product": None,
                                                    "needs_upgrade": False},
                                       "counts": {"arp": 0, "interfaces": 0, "live": 0, "silent": 0},
                                       "arp": [], "interfaces": [], "presence": []})
        report = {"target": "opnsense", "outcome": "success", "collected": collected,
                  "counts": {"aliases": 0, "rules": 0, "arp": 0, "interfaces": 0}}
        if json_output:
            print(json.dumps(report), file=stdout)  # type: ignore[arg-type]
        return 0
    monkeypatch.setattr(opnsense, "collect", opnsense_collect)


def run(
    repo: Path, credentials: Path, capsys: pytest.CaptureFixture[str],
    network_credentials: Path | None = None,
) -> tuple[int, dict]:
    network_credentials = credentials if network_credentials is None else network_credentials
    code = main(["collect", "all", "--repo", str(repo),
                 "--credentials-file", str(credentials),
                 "--network-credentials-file", str(network_credentials), "--json"])
    captured = capsys.readouterr()
    assert TOKEN not in captured.out + captured.err
    return code, json.loads(captured.out)


def status(repo: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> int:
    code = main(["collect-status", "--repo", str(repo), "--json", *extra])
    report = json.loads(capsys.readouterr().out)
    assert report["outcome"] == ("success" if code == 0 else "unavailable")
    return code


def network_credentials(path: Path, credentials: Path) -> Path:
    network = path / "proxmox-network.env"
    network.write_text(credentials.read_text().replace(TOKEN, NETWORK_TOKEN))
    return network


def test_default_collection_records_matching_evidence_and_runs_remaining_once(
    repo: Path, credentials: Path, transport: type[FakeConnection], capsys: pytest.CaptureFixture[str],
) -> None:
    transport.responses_by_token = dict([
        (TOKEN, transport.responses), (OPERATE_TOKEN, transport.responses),
        (NETWORK_TOKEN, network_endpoint_data()), (NETWORK_OPERATE_TOKEN, network_endpoint_data()),
    ])
    code, report = run(repo, credentials, capsys, network_credentials(repo, credentials))
    assert code == 0 and report["outcome"] == "success"
    assert len(report["collectors"]) == 11
    calls = (repo / "calls").read_text().splitlines()
    assert calls == [row[1] for row in collection.REMAINING]
    assert "collect-docker.sh" not in calls
    assert "collect-dns.sh" not in calls
    assert "collect-opnsense.sh" not in calls
    evidence = json.loads((repo / "inventory/collection-core.json").read_text())
    assert evidence["sha256"] == hashlib.sha256(
        (repo / "inventory/proxmox-core.json").read_bytes()).hexdigest()
    assert status(repo, capsys) == 0
    network_evidence = json.loads((repo / "inventory/collection-network.json").read_text())
    assert network_evidence["attempted"] == evidence["attempted"]
    assert network_evidence["sha256"] == hashlib.sha256(
        (repo / "inventory/proxmox-network.json").read_bytes()).hexdigest()
    network_snapshot = json.loads((repo / "inventory/proxmox-network.json").read_text())
    assert network_snapshot["pools"] == []
    assert [guest["vmid"] for guest in network_snapshot["resources"]] == [5001, 635, 837]


def test_failed_default_docker_refresh_retains_snapshot_and_recovers(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    snapshot = repo / "inventory/docker-docker-dmz.json"
    previous = snapshot.read_bytes()
    real_collect = docker.collect

    def unavailable_docker(label: str, output: Path, context: str, *,
                           json_output: bool, stdout: object, raise_cleanup: bool = False) -> int:
        report = {"target": f"docker-{label}", "outcome": "unavailable",
                  "reason": "synthetic Docker read failure"}
        if json_output:
            print(json.dumps(report), file=stdout)  # type: ignore[arg-type]
        return 3

    monkeypatch.setattr(docker, "collect", unavailable_docker)
    assert run(repo, credentials, capsys)[0] == 3
    assert snapshot.read_bytes() == previous
    assert status(repo, capsys) == 3

    monkeypatch.setattr(docker, "collect", real_collect)
    assert run(repo, credentials, capsys)[0] == 0
    assert status(repo, capsys) == 0


def test_failed_docker_marker_publication_retains_bytes_refuses_freshness_and_recovers(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    snapshot = repo / "inventory/docker-docker-dmz.json"
    previous = snapshot.read_bytes()
    real_collect = docker.collect

    def unavailable_docker(label: str, output: Path, context: str, *,
                           json_output: bool, stdout: object, raise_cleanup: bool = False) -> int:
        if json_output:
            print(json.dumps({"target": f"docker-{label}", "outcome": "unavailable",
                              "reason": "synthetic Docker read failure"}),
                  file=stdout)  # type: ignore[arg-type]
        return 3

    replace = proxmox.os.replace
    marker_writes = 0

    def fail_final_docker_marker(source: str, destination: Path) -> None:
        nonlocal marker_writes
        if destination.name == "collection-docker-dmz.json":
            marker_writes += 1
            if marker_writes == 2:
                raise OSError(TOKEN)
        replace(source, destination)

    monkeypatch.setattr(docker, "collect", unavailable_docker)
    monkeypatch.setattr(proxmox.os, "replace", fail_final_docker_marker)
    assert run(repo, credentials, capsys)[0] == 1
    assert snapshot.read_bytes() == previous
    assert status(repo, capsys) == 3

    monkeypatch.setattr(proxmox.os, "replace", replace)
    monkeypatch.setattr(docker, "collect", real_collect)
    assert run(repo, credentials, capsys)[0] == 0
    assert status(repo, capsys) == 0


def test_failed_network_refresh_invalidates_paired_status_and_retains_network_snapshot(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    previous = (repo / "inventory/proxmox-network.json").read_bytes()
    from skynet import proxmox
    real_collect = proxmox.collect

    def unavailable_network(target: str, *args: object, **kwargs: object) -> int:
        if target == "network":
            stream = kwargs["stdout"]
            stream.write(json.dumps({"target": "proxmox-network", "outcome": "unavailable",
                                     "reason": "synthetic network timeout"}))
            return 3
        return real_collect(target, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(proxmox, "collect", unavailable_network)
    assert run(repo, credentials, capsys)[0] == 3
    assert (repo / "inventory/proxmox-network.json").read_bytes() == previous
    assert status(repo, capsys) == 3
    monkeypatch.setattr(proxmox, "collect", real_collect)
    assert run(repo, credentials, capsys)[0] == 0
    assert status(repo, capsys) == 0


def test_failed_acl_refresh_invalidates_status_and_retains_acl_snapshot(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    previous = (repo / "inventory/proxmox-network-acl.json").read_bytes()
    from skynet import proxmox
    real_collect_acl = proxmox.collect_acl

    def unavailable_acl(target: str, *args: object, **kwargs: object) -> int:
        if target == "network":
            kwargs["stdout"].write(json.dumps({"target": "proxmox-network-acl", "outcome": "unavailable",
                                                "reason": "synthetic ACL timeout"}))
            return 3
        return real_collect_acl(target, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(proxmox, "collect_acl", unavailable_acl)
    assert run(repo, credentials, capsys)[0] == 3
    assert (repo / "inventory/proxmox-network-acl.json").read_bytes() == previous
    assert status(repo, capsys) == 3


def test_failed_pbs_refresh_invalidates_status_and_retains_snapshot(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    previous = (repo / "inventory/pbs.json").read_bytes()

    def unavailable(output: Path, credentials_file: Path, *, json_output: bool, stdout: object) -> int:
        print(json.dumps({"target": "pbs", "outcome": "unavailable",
                          "reason": "synthetic PBS timeout"}), file=stdout)  # type: ignore[arg-type]
        return 3

    monkeypatch.setattr(pbs, "collect", unavailable)
    assert run(repo, credentials, capsys)[0] == 3
    assert (repo / "inventory/pbs.json").read_bytes() == previous
    assert status(repo, capsys) == 3


def test_failed_dns_refresh_invalidates_status_and_retains_snapshot(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    previous = (repo / "inventory/dns-zones.json").read_bytes()
    real_collect = dns.collect

    def unavailable(output: Path, credentials_file: Path, *, json_output: bool, stdout: object) -> int:
        print(json.dumps({"target": "dns", "outcome": "unavailable",
                          "reason": "synthetic DNS timeout"}), file=stdout)  # type: ignore[arg-type]
        return 3

    monkeypatch.setattr(dns, "collect", unavailable)
    assert run(repo, credentials, capsys)[0] == 3
    assert (repo / "inventory/dns-zones.json").read_bytes() == previous
    assert status(repo, capsys) == 3

    monkeypatch.setattr(dns, "collect", real_collect)
    assert run(repo, credentials, capsys)[0] == 0
    assert status(repo, capsys) == 0


def test_failed_opnsense_refresh_invalidates_paired_status_and_retains_both_snapshots(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    firewall = (repo / "inventory/firewall/firewall.json").read_bytes()
    state = (repo / "inventory/opnsense.json").read_bytes()
    real_collect = opnsense.collect

    def unavailable(firewall_output: Path, state_output: Path, credentials_file: Path, *,
                    json_output: bool, stdout: object) -> int:
        print(json.dumps({"target": "opnsense", "outcome": "unavailable",
                          "reason": "synthetic OPNsense timeout"}), file=stdout)  # type: ignore[arg-type]
        return 3

    monkeypatch.setattr(opnsense, "collect", unavailable)
    assert run(repo, credentials, capsys)[0] == 3
    assert (repo / "inventory/firewall/firewall.json").read_bytes() == firewall
    assert (repo / "inventory/opnsense.json").read_bytes() == state
    assert status(repo, capsys) == 3

    monkeypatch.setattr(opnsense, "collect", real_collect)
    assert run(repo, credentials, capsys)[0] == 0
    assert status(repo, capsys) == 0


@pytest.mark.parametrize("marker_name", [
    "collection-dns.json", "collection-firewall.json", "collection-opnsense.json",
])
@pytest.mark.parametrize("failed_write", [1, 2])
def test_p6_marker_failure_refuses_freshness_and_recovers(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
    marker_name: str, failed_write: int,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    assert status(repo, capsys) == 0
    replace = proxmox.os.replace
    writes = 0

    def fail_marker(source: str, destination: Path) -> None:
        nonlocal writes
        if Path(destination).name == marker_name:
            writes += 1
            if writes == failed_write:
                raise OSError("synthetic marker storage failure")
        replace(source, destination)

    monkeypatch.setattr(proxmox.os, "replace", fail_marker)
    assert run(repo, credentials, capsys)[0] == 1
    assert status(repo, capsys) == 3
    monkeypatch.setattr(proxmox.os, "replace", replace)
    assert run(repo, credentials, capsys)[0] == 0
    assert status(repo, capsys) == 0


def test_out_of_band_firewall_overwrite_invalidates_existing_live_receipt(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A DR config restore or manual edit that rewrites firewall.json without the receipt
    # cannot pass as fresh: the marker's sha256 no longer matches the file on disk.
    assert run(repo, credentials, capsys)[0] == 0
    assert status(repo, capsys) == 0
    output = repo / "inventory/firewall/firewall.json"
    output.write_bytes(output.read_bytes() + b"\n")
    assert status(repo, capsys) == 3
    assert run(repo, credentials, capsys)[0] == 0
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
    assert len((repo / "calls").read_text().splitlines()) == 2 * len(collection.REMAINING)


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


def test_initial_marker_failure_invalidates_default_consumers_and_recovers(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0
    snapshot = repo / "inventory/proxmox-core.json"
    previous = snapshot.read_bytes()
    marker_writes = 0

    from skynet import proxmox
    replace = proxmox.os.replace

    def fail_initial_marker(source: str, destination: Path) -> None:
        nonlocal marker_writes
        if destination.name == "collection-core.json":
            marker_writes += 1
            if marker_writes == 1:
                raise OSError(TOKEN)
        replace(source, destination)

    monkeypatch.setattr(proxmox.os, "replace", fail_initial_marker)
    before_requests = len(transport.instances)
    assert run(repo, credentials, capsys)[0] == 1
    assert snapshot.read_bytes() == previous
    assert len(transport.instances) == before_requests
    assert status(repo, capsys) == 3

    # Exercise the real shell callers through only the offline package-launch boundary.
    ops = repo / "bin/ops"
    skynet = repo / "bin/skynet"
    render = repo / "scripts/render-docs.sh"
    ops.parent.mkdir(exist_ok=True)
    shutil.copy(ROOT / "bin/ops", ops)
    shutil.copy(ROOT / "bin/skynet", skynet)
    shutil.copy(ROOT / "scripts/render-docs.sh", render)
    for target in (ops, skynet, render):
        target.chmod(0o755)
        target.write_text(target.read_text().replace(
            "#!/usr/bin/env bash", f"#!{shutil.which('bash')}", 1))
        target.chmod(0o755)
    pages = repo / "docs/generated"
    pages.mkdir(parents=True)
    page = pages / "factual.md"
    page.write_text("unchanged factual page\n")
    fake_bin = repo / "fake-bin"
    fake_bin.mkdir()
    launcher = fake_bin / "nix"
    launcher.write_text(
        f"#!{sys.executable}\nimport sys\nsys.path[:] = {sys.path!r}\n"
        "from skynet.cli import main\nsys.exit(main(sys.argv[6:]))\n"
    )
    launcher.chmod(0o755)
    environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}
    for args in ((str(ops), "entities"), (str(ops), "query", "SELECT 1"), (str(render),)):
        result = subprocess.run(["bash", *args], env=environment,
                                capture_output=True, text=True, check=False)
        assert result.returncode == 3
        assert TOKEN not in result.stdout + result.stderr
    assert page.read_text() == "unchanged factual page\n"

    monkeypatch.setattr(proxmox.os, "replace", replace)
    assert run(repo, credentials, capsys)[0] == 0
    assert status(repo, capsys) == 0


def _write_delayed_reader(repo: Path, *, detached: bool = False) -> tuple[Path, Path, Path]:
    """Create a reader and child that would write after cleanup if left alive."""
    child = repo / ("detached-writer.py" if detached else "delayed-writer.py")
    ready = repo / ("detached-ready" if detached else "delayed-ready")
    destination = repo / "inventory/late-write"
    child.write_text(
        "import os, signal, time\n"
        "from pathlib import Path\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        f"Path({str(ready)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(0.45)\n"
        f"Path({str(destination)!r}).touch()\n"
    )
    reader = repo / "scripts" / ("detached-reader.sh" if detached else "slow-reader.sh")
    launch = f"{sys.executable} {child}"
    suffix = (
        f" &\nwhile [[ ! -e {ready} ]]; do :; done\nexit 0\n"
        if detached else "\nwait\n"
    )
    reader.write_text(f"#!{shutil.which('bash')}\n{launch}{suffix}")
    reader.chmod(0o755)
    return reader, ready, destination


def test_remaining_timeout_kills_descendants_before_next_reader_and_releases_lock(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, ready, destination = _write_delayed_reader(repo)
    remaining = collection.REMAINING
    next_reader = repo / "scripts" / remaining[0][1]
    body = next_reader.read_text().split("\n", 1)[1]
    next_reader.write_text(
        f"#!{sys.executable}\nimport os\nfrom pathlib import Path\n"
        f"try: os.kill(int(Path({str(ready)!r}).read_text()), 0)\n"
        "except ProcessLookupError: pass\n"
        "else: Path('survivor-at-next').touch()\n" + body
    )
    cleanup = collection.stop_reader

    def locked_cleanup(process: subprocess.Popen[bytes]) -> None:
        with (repo / ".cache/collection.lock").open("r+") as other_lock:
            with pytest.raises(BlockingIOError):
                collection.fcntl.flock(
                    other_lock, collection.fcntl.LOCK_EX | collection.fcntl.LOCK_NB)
        cleanup(process)

    monkeypatch.setattr(collection, "stop_reader", locked_cleanup)
    monkeypatch.setattr(collection, "REMAINING", (("slow", reader.name), *remaining))
    monkeypatch.setattr(collection, "READER_TIMEOUT", 0.25)
    monkeypatch.setattr(collection, "CLEANUP_TIMEOUT", 0.12)
    started = time.monotonic()
    code, report = run(repo, credentials, capsys)
    assert time.monotonic() - started < 5
    assert code == 1
    assert next(item for item in report["collectors"] if item["target"] == "slow")["outcome"] == "failure"
    assert ready.exists()
    assert not destination.exists()
    assert not (repo / "survivor-at-next").exists()
    with pytest.raises(ProcessLookupError):
        os.kill(int(ready.read_text()), 0)
    assert (repo / "calls").read_text().splitlines() == [row[1] for row in remaining]
    time.sleep(0.55)
    assert not destination.exists()
    assert TOKEN not in json.dumps(report)

    # A second complete attempt proves timeout cleanup happened before lock release.
    before_requests = len(transport.instances)
    assert run(repo, credentials, capsys)[0] == 1
    assert len(transport.instances) == before_requests + 14
    assert (repo / "calls").read_text().splitlines() == [row[1] for row in remaining] * 2
    assert status(repo, capsys) == 0  # core success is independent of other readers' exits


@pytest.mark.parametrize("interruption", [signal.SIGINT, signal.SIGTERM])
def test_signal_interrupts_reader_and_reaps_child(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], interruption: signal.Signals,
) -> None:
    reader, ready, destination = _write_delayed_reader(repo)
    runner = repo / "runner.py"
    runner.write_text(
        f"import json,sys\nsys.path[:] = {sys.path!r}\n"
        "from pathlib import Path\n"
        "from test_proxmox import FakeConnection, endpoint_data\n"
        "from skynet import collection, dns, docker, opnsense, pbs, proxmox\nfrom skynet.cli import main\n"
        "FakeConnection.responses = endpoint_data()\n"
        "proxmox.http.client.HTTPSConnection = FakeConnection\n"
        "def pbs_collect(output, credentials_file, *, json_output, stdout):\n"
        "  data = {'collected':'2026-09-09T00:00:00+00:00','host':'pbs.test','datastores':[]}\n"
        "  proxmox.publish(output, data)\n"
        "  stdout.write(json.dumps({'target':'pbs','outcome':'success','collected':data['collected']}))\n"
        "  return 0\n"
        "pbs.collect = pbs_collect\n"
        "def docker_collect(label, output, context, *, json_output, stdout, raise_cleanup=False):\n"
        "  data = {'collected':'2026-09-09T00:00:00+00:00','host':label,'containers':[],'images':[]}\n"
        "  proxmox.publish(output, data)\n"
        "  stdout.write(json.dumps({'target':'docker-'+label,'outcome':'success','collected':data['collected']}))\n"
        "  return 0\n"
        "docker.collect = docker_collect\n"
        "def dns_collect(output, credentials_file, *, json_output, stdout):\n"
        "  data = {'collected':'2026-09-09T00:00:00+00:00','host':'10.10.70.50','zones':[],'records':[]}\n"
        "  proxmox.publish(output, data)\n"
        "  stdout.write(json.dumps({'target':'dns','outcome':'success','collected':data['collected']}))\n"
        "  return 0\n"
        "dns.collect = dns_collect\n"
        "def opnsense_collect(firewall_output, state_output, credentials_file, *, json_output, stdout):\n"
        "  c = '2026-09-09T00:00:00+00:00'\n"
        "  proxmox.publish(firewall_output, {'collected':c,'source':'stub','host':'10.10.60.1','counts':{},'aliases':[],'rules':[],'reservations':[]})\n"
        "  proxmox.publish(state_output, {'collected':c,'source':'stub','host':'10.10.60.1','firmware':{},'counts':{},'arp':[],'interfaces':[],'presence':[]})\n"
        "  stdout.write(json.dumps({'target':'opnsense','outcome':'success','collected':c}))\n"
        "  return 0\n"
        "opnsense.collect = opnsense_collect\n"
        f"collection.REMAINING = (('slow', {reader.name!r}),)\n"
        f"args = ['collect', 'all', '--repo', {str(repo)!r}, "
        f"'--credentials-file', {str(credentials)!r}, "
        f"'--network-credentials-file', {str(credentials)!r}, '--json']\n"
        "try: sys.exit(main(args))\nexcept KeyboardInterrupt: sys.exit(130)\n"
    )
    process = subprocess.Popen([sys.executable, str(runner)], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists()
        process.send_signal(interruption)
        stdout, stderr = process.communicate(timeout=6)
        assert process.returncode == 130
        assert TOKEN not in stdout + stderr
        with pytest.raises(ProcessLookupError):
            os.kill(int(ready.read_text()), 0)
        time.sleep(0.55)
        assert not destination.exists()
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=6)
    assert run(repo, credentials, capsys)[0] == 0


def test_normal_reader_exit_reaps_detached_descendant(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, ready, destination = _write_delayed_reader(repo, detached=True)
    monkeypatch.setattr(collection, "REMAINING", (("detached", reader.name),))
    monkeypatch.setattr(collection, "READER_TIMEOUT", 0.5)
    monkeypatch.setattr(collection, "CLEANUP_TIMEOUT", 0.12)
    assert run(repo, credentials, capsys)[0] == 0
    assert ready.exists()
    assert not destination.exists()
    time.sleep(0.55)
    assert not destination.exists()


def test_interrupted_reader_is_cleaned_and_lock_is_released(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, ready, destination = _write_delayed_reader(repo)
    remaining = collection.REMAINING
    monkeypatch.setattr(collection, "REMAINING", (("interrupted", reader.name),))
    real_popen = collection.subprocess.Popen

    def interrupting_popen(*args: object, **kwargs: object) -> subprocess.Popen[bytes]:
        process = real_popen(*args, **kwargs)
        wait = process.wait
        interrupted = False

        def wait_once(*wait_args: object, **wait_kwargs: object) -> int:
            nonlocal interrupted
            if not interrupted:
                interrupted = True
                deadline = time.monotonic() + 1
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                raise KeyboardInterrupt
            return wait(*wait_args, **wait_kwargs)

        process.wait = wait_once  # type: ignore[method-assign]
        return process

    monkeypatch.setattr(collection.subprocess, "Popen", interrupting_popen)
    try:
        code = run(repo, credentials, capsys)[0]
    except KeyboardInterrupt:
        code = 1
    assert code != 0
    assert ready.exists()
    assert not destination.exists()
    time.sleep(0.55)
    assert not destination.exists()
    monkeypatch.setattr(collection.subprocess, "Popen", real_popen)
    monkeypatch.setattr(collection, "REMAINING", remaining)
    before_requests = len(transport.instances)
    assert run(repo, credentials, capsys)[0] == 0
    assert len(transport.instances) == before_requests + 14


def test_cleanup_failure_quarantines_receipt_and_stops_remaining_readers(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fail_cleanup(*args: object, **kwargs: object) -> None:
        calls.append("reader")
        raise collection.CleanupError("synthetic cleanup failure")

    real_reader = collection.run_reader
    monkeypatch.setattr(collection, "run_reader", fail_cleanup)
    monkeypatch.setattr(collection, "REMAINING", (collection.REMAINING[0], collection.REMAINING[1]))
    assert run(repo, credentials, capsys)[0] == 1
    assert calls == ["reader"]
    assert not (repo / "calls").exists()
    assert status(repo, capsys) == 3

    # The recovery-required receipt is a hard stop before another core remote read.
    before_requests = len(transport.instances)
    monkeypatch.setattr(collection, "run_reader", real_reader)
    assert run(repo, credentials, capsys)[0] == 1
    assert len(transport.instances) == before_requests
    assert status(repo, capsys) == 3


def test_docker_cleanup_failure_quarantines_receipt_and_stops_collection(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_cleanup(*args: object, **kwargs: object) -> int:
        raise docker.CleanupError("synthetic cleanup failure")

    monkeypatch.setattr(docker, "collect", fail_cleanup)
    assert run(repo, credentials, capsys)[0] == 1
    assert (repo / ".cache/collection.lock").read_text() == "recovery-required"
    assert not (repo / "calls").exists()
    assert status(repo, capsys) == 3


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
        if destination.name == "collection-network.json":
            marker_writes += 1
            if marker_writes == 2:
                raise OSError(TOKEN)
        replace(source, destination)

    monkeypatch.setattr(proxmox.os, "replace", fail_final_marker)
    assert run(repo, credentials, capsys)[0] == 1
    assert (repo / "inventory/proxmox-core.json").exists()
    assert (repo / "inventory/proxmox-network.json").exists()
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


def test_status_fails_closed_when_receipt_cannot_be_reaffirmed(
    repo: Path, credentials: Path, transport: type[FakeConnection],
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(repo, credentials, capsys)[0] == 0

    def fail_receipt_write(*args: object, **kwargs: object) -> None:
        raise OSError(TOKEN)

    monkeypatch.setattr(collection, "receipt_write", fail_receipt_write)
    code = main(["collect-status", "--repo", str(repo), "--json"])
    output = capsys.readouterr()
    assert code == 3
    assert TOKEN not in output.out + output.err


@pytest.mark.parametrize("entry,args,expected", [
    ("bin/ops", ["collect"], ["collect", "all", "--repo"]),
    ("bin/ops", ["entities"], ["collect-status", "--repo"]),
    ("bin/ops", ["query", "SELECT 1"], ["collect-status", "--repo"]),
    ("scripts/render-docs.sh", [], ["collect-status", "--repo"]),
    ("scripts/collect-proxmox.sh", ["core"], ["collect", "proxmox", "core"]),
    ("scripts/collect-pbs.sh", [], ["collect", "pbs", "--output"]),
    ("scripts/collect-dns.sh", [], ["collect", "dns", "--output"]),
    ("scripts/collect-opnsense.sh", [], ["collect", "opnsense", "--firewall-output"]),
])
def test_default_shell_callers_use_offline_package_and_propagate_failure(
    tmp_path: Path, entry: str, args: list[str], expected: list[str],
) -> None:
    for relative in ("bin/ops", "bin/skynet", "scripts/collect-all.sh",
                     "scripts/render-docs.sh", "scripts/collect-proxmox.sh", "scripts/collect-pbs.sh",
                     "scripts/collect-dns.sh", "scripts/collect-opnsense.sh"):
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
        "from skynet import dns, docker, opnsense, pbs, proxmox\nfrom skynet.cli import main\n"
        "FakeConnection.responses = endpoint_data()\n"
        "proxmox.http.client.HTTPSConnection = FakeConnection\n"
        "pbs.collect = lambda output, credentials_file, json_output, stdout: ("
        "proxmox.publish(output, {'collected':'2026-09-09T00:00:00+00:00','host':'pbs.test','datastores':[]}) or "
        "stdout.write('{\\\"target\\\":\\\"pbs\\\",\\\"outcome\\\":\\\"success\\\",\\\"collected\\\":\\\"2026-09-09T00:00:00+00:00\\\"}') and 0)\n"
        "docker.collect = lambda label, output, context, json_output, stdout, raise_cleanup=False: ("
        "proxmox.publish(output, {'collected':'2026-09-09T00:00:00+00:00','host':label,'containers':[],'images':[]}) or "
        "stdout.write('{\\\"target\\\":\\\"docker-dmz\\\",\\\"outcome\\\":\\\"success\\\",\\\"collected\\\":\\\"2026-09-09T00:00:00+00:00\\\"}') and 0)\n"
        "dns.collect = lambda output, credentials_file, json_output, stdout: ("
        "proxmox.publish(output, {'collected':'2026-09-09T00:00:00+00:00','host':'10.10.70.50','zones':[],'records':[]}) or "
        "stdout.write('{\\\"target\\\":\\\"dns\\\",\\\"outcome\\\":\\\"success\\\",\\\"collected\\\":\\\"2026-09-09T00:00:00+00:00\\\"}') and 0)\n"
        "opnsense.collect = lambda firewall_output, state_output, credentials_file, json_output, stdout: ("
        "proxmox.publish(firewall_output, {'collected':'2026-09-09T00:00:00+00:00','source':'stub','host':'10.10.60.1','counts':{},'aliases':[],'rules':[],'reservations':[]}) or "
        "proxmox.publish(state_output, {'collected':'2026-09-09T00:00:00+00:00','source':'stub','host':'10.10.60.1','firmware':{},'counts':{},'arp':[],'interfaces':[],'presence':[]}) or "
        "stdout.write('{\\\"target\\\":\\\"opnsense\\\",\\\"outcome\\\":\\\"success\\\",\\\"collected\\\":\\\"2026-09-09T00:00:00+00:00\\\"}') and 0)\n"
        "sys.exit(main(sys.argv[6:]))\n"
    )
    launcher.chmod(0o755)
    result = subprocess.run(
        ["bash", str(repo / "bin/ops"), "collect", "--credentials-file", str(credentials),
         "--network-credentials-file", str(credentials), "--json"],
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
