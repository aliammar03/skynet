"""Default collection and paired Proxmox evidence freshness for current-state consumers."""

import ctypes
import fcntl
import hashlib
import io
import json
import os
import signal
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TextIO

from skynet import proxmox

REMAINING = (
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
PROXMOX_NODES = (
    ("core", "proxmox-core.json", "collection-core.json"),
    ("network", "proxmox-network.json", "collection-network.json"),
)
READER_TIMEOUT = 120.0
CLEANUP_TIMEOUT = 5.0


class CleanupError(Exception):
    """A reader group could not be confirmed stopped and reaped."""


def receipt_write(lock: TextIO, attempted: str) -> None:
    """Invalidate in place before recording an attempt, independently of atomic rename."""
    lock.seek(0)
    lock.truncate()
    lock.flush()
    os.fsync(lock.fileno())
    lock.write(attempted)
    lock.flush()
    os.fsync(lock.fileno())


def stop_reader(process: subprocess.Popen[bytes]) -> None:
    """Kill only this reader's session group and reap its adopted descendants."""
    deadline = time.monotonic() + CLEANUP_TIMEOUT
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=max(0.001, deadline - time.monotonic()))
    while True:
        try:
            while os.waitpid(-process.pid, os.WNOHANG)[0]:
                pass
        except ChildProcessError:
            pass
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        if time.monotonic() >= deadline:
            raise CleanupError
        time.sleep(0.01)


def run_reader(args: list[str], repo: Path) -> int:
    """Run one synchronous Linux reader with ownership of its process group."""
    # Subreaping lets us wait for orphaned grandchildren rather than relying on PID 1.
    libc = ctypes.CDLL(None, use_errno=True)
    previous = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(previous), 0, 0, 0) != 0:  # PR_GET_CHILD_SUBREAPER
        raise CleanupError
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise CleanupError

    def interrupted(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    prior_term = signal.signal(signal.SIGTERM, interrupted)
    process = None
    try:
        # Block interruptions across spawn so a child cannot exist without its handle.
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        try:
            process = subprocess.Popen(
                args, cwd=repo, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True,
            )
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        try:
            return process.wait(timeout=READER_TIMEOUT)
        except subprocess.TimeoutExpired:
            return 3
    finally:
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        try:
            if process is not None:
                try:
                    stop_reader(process)
                except (OSError, subprocess.TimeoutExpired) as error:
                    raise CleanupError from error
        finally:
            libc.prctl(36, previous.value, 0, 0, 0)
            signal.signal(signal.SIGTERM, prior_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def emit(report: dict[str, Any], json_output: bool, stdout: TextIO) -> None:
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"{report['target']}: {report['outcome']}", file=stdout)
        if "reason" in report:
            print(report["reason"], file=stdout)
        if "collected" in report:
            print(f"Proxmox observations collected: {report['collected']}", file=stdout)
        for result in report.get("collectors", []):
            print(f"{result['target']}: {result['outcome']}", file=stdout)
            if "reason" in result:
                print(result["reason"], file=stdout)


def collect_all(repo: Path, credentials_file: Path, network_credentials_file: Path, *,
                json_output: bool, stdout: TextIO) -> int:
    """Collect both Proxmox node shapes before retaining the remaining shell readers."""
    report: dict[str, Any] = {"target": "collection", "outcome": "failure", "collectors": []}
    try:
        repo = repo.resolve()
        # A failed lock/marker setup cannot proceed to remote reads or bless old evidence.
        (repo / ".cache").mkdir(exist_ok=True)
        with (repo / ".cache/collection.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock.seek(0)
            if lock.read() == "recovery-required":
                raise CleanupError
            attempted = datetime.now(UTC).isoformat(timespec="microseconds")
            receipt_write(lock, attempted)
            code = 0
            credential_files = {"core": credentials_file, "network": network_credentials_file}
            for target, snapshot_name, marker_name in PROXMOX_NODES:
                output = repo / "inventory" / snapshot_name
                status = repo / "inventory" / marker_name
                marker: dict[str, Any] = {
                    "target": f"proxmox-{target}", "outcome": "unavailable", "attempted": attempted,
                    "reason": "refresh incomplete; retained snapshot is previous evidence",
                }
                # A marker is durable before this node's read; a new receipt invalidates either
                # node's preceding success if publication fails before the next marker exists.
                proxmox.publish(status, marker)
                stream = io.StringIO()
                node_code = proxmox.collect(target, output, credential_files[target],
                                            json_output=True, stdout=stream)
                node = json.loads(stream.getvalue())
                marker.update(outcome=node["outcome"])
                if node_code == 0:
                    marker.pop("reason")
                    marker.update(collected=node["collected"],
                                  sha256=hashlib.sha256(output.read_bytes()).hexdigest())
                else:
                    marker["reason"] = node["reason"]
                proxmox.publish(status, marker)
                report["collectors"].append(node)
                if node_code == 1:
                    code = 1
                elif node_code and code == 0:
                    code = node_code
            for name, script, *args in REMAINING:
                try:
                    exit_code = run_reader([str(repo / "scripts" / script), *args], repo)
                except CleanupError:
                    try:
                        receipt_write(lock, "recovery-required")
                    except OSError:
                        report["recovery_recorded"] = False
                        raise CleanupError from None
                    raise
                except OSError:
                    exit_code = 3
                # These legacy readers expose process status, not validated health evidence.
                report["collectors"].append({"target": name, "exit_code": exit_code,
                                            "outcome": "completed" if exit_code == 0 else "failure"})
                if exit_code != 0:
                    code = 1
            if code == 0:
                report["outcome"] = "success"
    except CleanupError:
        report["outcome"] = "recovery-required"
        report["reason"] = "reader cleanup unconfirmed; collection stopped; inspect local processes"
        code = 1
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


def proxmox_status(repo: Path, *, since: str | None, json_output: bool, stdout: TextIO) -> int:
    """Require paired successful Proxmox observations no more than 36 hours old."""
    report: dict[str, Any] = {"target": "proxmox", "outcome": "unavailable"}
    try:
        with (repo / ".cache/collection.lock").open("r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            attempted_receipt = lock.read()
            timestamp(attempted_receipt)
            # Refuse storage that cannot persist invalidation, even if old evidence is readable.
            # Reaffirm only the existing receipt; status can never establish a new attempt.
            receipt_write(lock, attempted_receipt)
            observations = [
                (target, json.loads((repo / "inventory" / marker_name).read_bytes()),
                 (repo / "inventory" / snapshot_name).read_bytes())
                for target, snapshot_name, marker_name in PROXMOX_NODES
            ]
        now = datetime.now(UTC)
        collected_values: dict[str, str] = {}
        for target, evidence, raw in observations:
            snapshot = json.loads(raw)
            if not isinstance(evidence, dict) or not isinstance(snapshot, dict):
                raise ValueError
            collected = timestamp(snapshot.get("collected"))
            attempted = timestamp(evidence.get("attempted"))
            valid = (
                evidence.get("target") == f"proxmox-{target}" and evidence.get("outcome") == "success"
                and attempted_receipt == evidence.get("attempted")
                and snapshot.get("node") == target
                and evidence.get("collected") == snapshot.get("collected")
                and evidence.get("sha256") == hashlib.sha256(raw).hexdigest()
                and now - timedelta(hours=36) <= collected <= now
                and attempted <= now
                and collected - timedelta(hours=1) <= attempted <= collected + timedelta(seconds=1)
                and (since is None or attempted >= timestamp(since))
            )
            if not valid:
                raise ValueError
            collected_values[target] = snapshot["collected"]
    except (OSError, ValueError, TypeError, OverflowError):
        report["reason"] = (
            "Proxmox refresh evidence missing, failed, mismatched or stale; "
            "retained files are historical observations"
        )
        code = 3
    else:
        report.update(outcome="success", collected=collected_values)
        code = 0
    emit(report, json_output, stdout)
    return code
