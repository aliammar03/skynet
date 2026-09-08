"""Default collection and core evidence freshness for current-state consumers."""

import fcntl
import hashlib
import io
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TextIO

from skynet import proxmox

REMAINING = (
    ("proxmox-network", "collect-proxmox.sh", "network"),
    ("proxmox-acl-core", "collect-proxmox-acl.sh", "core"),
    ("proxmox-acl-network", "collect-proxmox-acl.sh", "network"),
    ("pbs", "collect-pbs.sh"),
    ("docker-dmz", "collect-docker.sh", "docker-dmz"),
    ("dns", "collect-dns.sh"),
    ("opnsense", "collect-opnsense.sh"),
    ("network-gear", "collect-network-gear.sh"),
    ("routes", "collect-routes.sh"),
    ("certs", "collect-certs.sh"),
)


def emit(report: dict[str, Any], json_output: bool, stdout: TextIO) -> None:
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"{report['target']}: {report['outcome']}", file=stdout)
        if "reason" in report:
            print(report["reason"], file=stdout)
        if "collected" in report:
            print(f"core observations collected: {report['collected']}", file=stdout)
        for result in report.get("collectors", []):
            print(f"{result['target']}: {result['outcome']}", file=stdout)
            if "reason" in result:
                print(result["reason"], file=stdout)


def collect_all(repo: Path, credentials_file: Path, *, json_output: bool, stdout: TextIO) -> int:
    """Collect core in Python, retaining shell readers until their owning phases."""
    report: dict[str, Any] = {"target": "collection", "outcome": "failure", "collectors": []}
    try:
        repo = repo.resolve()
        # A failed lock/marker setup cannot proceed to remote reads or bless old evidence.
        (repo / ".cache").mkdir(exist_ok=True)
        with (repo / ".cache/collection.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            output = repo / "inventory/proxmox-core.json"
            status = repo / "inventory/collection-core.json"
            marker: dict[str, Any] = {
                "target": "proxmox-core", "outcome": "unavailable",
                "attempted": datetime.now(UTC).isoformat(timespec="microseconds"),
                "reason": "refresh incomplete; retained snapshot is previous evidence",
            }
            proxmox.publish(status, marker)
            stream = io.StringIO()
            code = proxmox.collect(output, credentials_file, json_output=True, stdout=stream)
            core = json.loads(stream.getvalue())
            marker.update(outcome=core["outcome"])
            if code == 0:
                marker.pop("reason")
                marker.update(collected=core["collected"],
                              sha256=hashlib.sha256(output.read_bytes()).hexdigest())
            else:
                marker["reason"] = core["reason"]
            proxmox.publish(status, marker)
            report["collectors"].append(core)
            for name, script, *args in REMAINING:
                try:
                    result = subprocess.run(
                        [str(repo / "scripts" / script), *args], cwd=repo,
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=120, check=False,
                    )
                    exit_code = result.returncode
                except (OSError, subprocess.TimeoutExpired):
                    exit_code = 3
                # These legacy readers expose process status, not validated health evidence.
                report["collectors"].append({"target": name, "exit_code": exit_code,
                                            "outcome": "completed" if exit_code == 0 else "failure"})
                if exit_code != 0:
                    code = 1
            if code == 0:
                report["outcome"] = "success"
    except (OSError, ValueError, proxmox.CollectionError):
        report["reason"] = "collection setup or evidence publication failed; no fresh result established"
        code = 1
    emit(report, json_output, stdout)
    return code


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None:
        raise ValueError
    return instant


def core_status(repo: Path, *, since: str | None, json_output: bool, stdout: TextIO) -> int:
    """Require a matching successful core refresh no more than 36 hours old."""
    report: dict[str, Any] = {"target": "proxmox-core", "outcome": "unavailable"}
    try:
        evidence = json.loads((repo / "inventory/collection-core.json").read_bytes())
        raw = (repo / "inventory/proxmox-core.json").read_bytes()
        snapshot = json.loads(raw)
        if not isinstance(evidence, dict) or not isinstance(snapshot, dict):
            raise ValueError
        now = datetime.now(UTC)
        collected = timestamp(snapshot.get("collected"))
        attempted = timestamp(evidence.get("attempted"))
        valid = (
            evidence.get("target") == "proxmox-core" and evidence.get("outcome") == "success"
            and snapshot.get("node") == "core"
            and evidence.get("collected") == snapshot.get("collected")
            and evidence.get("sha256") == hashlib.sha256(raw).hexdigest()
            and now - timedelta(hours=36) <= collected <= now
            and attempted <= now
            and collected - timedelta(hours=1) <= attempted <= collected + timedelta(seconds=1)
            and (since is None or attempted >= timestamp(since))
        )
        if not valid:
            raise ValueError
    except (OSError, ValueError, TypeError, OverflowError):
        report["reason"] = (
            "core refresh evidence missing, failed, mismatched or stale; "
            "retained files are historical observations"
        )
        code = 3
    else:
        report.update(outcome="success", collected=snapshot["collected"])
        code = 0
    emit(report, json_output, stdout)
    return code
