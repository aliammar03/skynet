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

from skynet import dns, docker, omada, opnsense, pbs, proxmox

REMAINING: tuple[tuple[str, ...], ...] = (
    ("routes", "collect-routes.sh"),
    ("certs", "collect-certs.sh"),
)
PROXMOX_NODES = (
    ("core", "proxmox-core.json", "collection-core.json"),
    ("network", "proxmox-network.json", "collection-network.json"),
)
PROXMOX_ACLS = (
    ("core", "proxmox-core-acl.json", "collection-core-acl.json"),
    ("network", "proxmox-network-acl.json", "collection-network-acl.json"),
)
PBS = ("pbs.json", "collection-pbs.json")
DOCKERS = (("docker-dmz", "docker-docker-dmz.json", "collection-docker-dmz.json"),)
DNS = ("dns-zones.json", "collection-dns.json")
# One live OPNsense collection produces two paired snapshots and two receipt-bound markers.
OPNSENSE = (("firewall", "firewall/firewall.json", "collection-firewall.json"),
            ("opnsense", "opnsense.json", "collection-opnsense.json"))
OMADA = ("network-gear.json", "collection-network-gear.json")
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


def collect_all(repo: Path, credentials_file: Path, network_credentials_file: Path,
                pbs_credentials_file: Path, dns_credentials_file: Path,
                opnsense_credentials_file: Path, omada_credentials_file: Path, *,
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
            for target, snapshot_name, marker_name in PROXMOX_ACLS:
                output = repo / "inventory" / snapshot_name
                status = repo / "inventory" / marker_name
                marker = {
                    "target": f"proxmox-{target}-acl", "outcome": "unavailable", "attempted": attempted,
                    "reason": "refresh incomplete; retained snapshot is previous evidence",
                }
                proxmox.publish(status, marker)
                stream = io.StringIO()
                acl_code = proxmox.collect_acl(target, output, credential_files[target],
                                               json_output=True, stdout=stream)
                acl = json.loads(stream.getvalue())
                marker.update(outcome=acl["outcome"])
                if acl_code == 0:
                    marker.pop("reason")
                    marker.update(collected=acl["collected"],
                                  sha256=hashlib.sha256(output.read_bytes()).hexdigest())
                else:
                    marker["reason"] = acl["reason"]
                proxmox.publish(status, marker)
                report["collectors"].append(acl)
                if acl_code == 1:
                    code = 1
                elif acl_code and code == 0:
                    code = acl_code
            snapshot_name, marker_name = PBS
            output = repo / "inventory" / snapshot_name
            status = repo / "inventory" / marker_name
            marker = {
                "target": "pbs", "outcome": "unavailable", "attempted": attempted,
                "reason": "refresh incomplete; retained snapshot is previous evidence",
            }
            proxmox.publish(status, marker)
            stream = io.StringIO()
            pbs_code = pbs.collect(output, pbs_credentials_file, json_output=True, stdout=stream)
            observation = json.loads(stream.getvalue())
            marker.update(outcome=observation["outcome"])
            if pbs_code == 0:
                marker.pop("reason")
                marker.update(collected=observation["collected"],
                              sha256=hashlib.sha256(output.read_bytes()).hexdigest())
            else:
                marker["reason"] = observation["reason"]
            proxmox.publish(status, marker)
            report["collectors"].append(observation)
            if pbs_code == 1:
                code = 1
            elif pbs_code and code == 0:
                code = pbs_code
            for label, snapshot_name, marker_name in DOCKERS:
                output = repo / "inventory" / snapshot_name
                status = repo / "inventory" / marker_name
                marker = {"target": f"docker-{label}", "outcome": "unavailable", "attempted": attempted,
                          "reason": "refresh incomplete; retained snapshot is previous evidence"}
                proxmox.publish(status, marker)
                stream = io.StringIO()
                try:
                    docker_code = docker.collect(label, output, label, json_output=True, stdout=stream,
                                                 raise_cleanup=True)
                except docker.CleanupError:
                    try:
                        receipt_write(lock, "recovery-required")
                    except OSError:
                        report["recovery_recorded"] = False
                        raise CleanupError from None
                    raise CleanupError
                observation = json.loads(stream.getvalue())
                marker.update(outcome=observation["outcome"])
                if docker_code == 0:
                    marker.pop("reason")
                    marker.update(collected=observation["collected"],
                                  sha256=hashlib.sha256(output.read_bytes()).hexdigest())
                else:
                    marker["reason"] = observation["reason"]
                proxmox.publish(status, marker)
                report["collectors"].append(observation)
                if docker_code == 1:
                    code = 1
                elif docker_code and code == 0:
                    code = docker_code
            snapshot_name, marker_name = DNS
            output = repo / "inventory" / snapshot_name
            status = repo / "inventory" / marker_name
            marker = {
                "target": "dns", "outcome": "unavailable", "attempted": attempted,
                "reason": "refresh incomplete; retained snapshot is previous evidence",
            }
            proxmox.publish(status, marker)
            stream = io.StringIO()
            dns_code = dns.collect(output, dns_credentials_file, json_output=True, stdout=stream)
            observation = json.loads(stream.getvalue())
            marker.update(outcome=observation["outcome"])
            if dns_code == 0:
                marker.pop("reason")
                marker.update(collected=observation["collected"],
                              sha256=hashlib.sha256(output.read_bytes()).hexdigest())
            else:
                marker["reason"] = observation["reason"]
            proxmox.publish(status, marker)
            report["collectors"].append(observation)
            if dns_code == 1:
                code = 1
            elif dns_code and code == 0:
                code = dns_code
            # One live OPNsense read publishes both paired snapshots and both markers, so neither
            # firewall config nor live state can look fresh without the other.
            opnsense_markers = []
            for target, snapshot_name, marker_name in OPNSENSE:
                status = repo / "inventory" / marker_name
                marker = {"target": target, "outcome": "unavailable", "attempted": attempted,
                          "reason": "refresh incomplete; retained snapshot is previous evidence"}
                proxmox.publish(status, marker)
                opnsense_markers.append((repo / "inventory" / snapshot_name, status, marker))
            stream = io.StringIO()
            opnsense_code = opnsense.collect(opnsense_markers[0][0], opnsense_markers[1][0],
                                             opnsense_credentials_file, json_output=True, stdout=stream)
            observation = json.loads(stream.getvalue())
            for snapshot_path, status, marker in opnsense_markers:
                marker.update(outcome=observation["outcome"])
                if opnsense_code == 0:
                    marker.pop("reason")
                    marker.update(collected=observation["collected"],
                                  sha256=hashlib.sha256(snapshot_path.read_bytes()).hexdigest())
                else:
                    marker["reason"] = observation["reason"]
                proxmox.publish(status, marker)
            report["collectors"].append(observation)
            if opnsense_code == 1:
                code = 1
            elif opnsense_code and code == 0:
                code = opnsense_code
            snapshot_name, marker_name = OMADA
            output = repo / "inventory" / snapshot_name
            status = repo / "inventory" / marker_name
            marker = {"target": "network-gear", "outcome": "unavailable", "attempted": attempted,
                      "reason": "refresh incomplete; retained snapshot is previous evidence"}
            proxmox.publish(status, marker)
            stream = io.StringIO()
            omada_code = omada.collect(output, omada_credentials_file, json_output=True, stdout=stream)
            observation = json.loads(stream.getvalue())
            marker.update(outcome=observation["outcome"])
            if omada_code == 0:
                marker.pop("reason")
                marker.update(collected=observation["collected"],
                              sha256=hashlib.sha256(output.read_bytes()).hexdigest())
            else:
                marker["reason"] = observation["reason"]
            proxmox.publish(status, marker)
            report["collectors"].append(observation)
            if omada_code == 1:
                code = 1
            elif omada_code and code == 0:
                code = omada_code
            for name, script, *reader_args in REMAINING:
                args: list[str] = [str(repo / "scripts" / script), *reader_args]
                try:
                    exit_code = run_reader(args, repo)
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


def collection_status(repo: Path, *, since: str | None, json_output: bool, stdout: TextIO) -> int:
    """Require all migrated inventory observations no more than 36 hours old."""
    report: dict[str, Any] = {"target": "collection", "outcome": "unavailable"}
    try:
        with (repo / ".cache/collection.lock").open("r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            attempted_receipt = lock.read()
            timestamp(attempted_receipt)
            # Refuse storage that cannot persist invalidation, even if old evidence is readable.
            # Reaffirm only the existing receipt; status can never establish a new attempt.
            receipt_write(lock, attempted_receipt)
            observations = [
                (f"proxmox-{target}", target, json.loads((repo / "inventory" / marker_name).read_bytes()),
                 (repo / "inventory" / snapshot_name).read_bytes())
                for target, snapshot_name, marker_name in PROXMOX_NODES
            ] + [
                (f"proxmox-{target}-acl", f"server-proxmox-{target}",
                 json.loads((repo / "inventory" / marker_name).read_bytes()),
                 (repo / "inventory" / snapshot_name).read_bytes())
                for target, snapshot_name, marker_name in PROXMOX_ACLS
            ] + [("pbs", None, json.loads((repo / "inventory" / PBS[1]).read_bytes()),
                  (repo / "inventory" / PBS[0]).read_bytes())] + [
                (f"docker-{label}", label, json.loads((repo / "inventory" / marker_name).read_bytes()),
                 (repo / "inventory" / snapshot_name).read_bytes())
                for label, snapshot_name, marker_name in DOCKERS
            ] + [("dns", None, json.loads((repo / "inventory" / DNS[1]).read_bytes()),
                  (repo / "inventory" / DNS[0]).read_bytes())] + [
                (target, None, json.loads((repo / "inventory" / marker_name).read_bytes()),
                 (repo / "inventory" / snapshot_name).read_bytes())
                for target, snapshot_name, marker_name in OPNSENSE
            ] + [("network-gear", None, json.loads((repo / "inventory" / OMADA[1]).read_bytes()),
                  (repo / "inventory" / OMADA[0]).read_bytes())
            ]
        now = datetime.now(UTC)
        collected_values: dict[str, str] = {}
        for evidence_target, node, evidence, raw in observations:
            snapshot = json.loads(raw)
            if not isinstance(evidence, dict) or not isinstance(snapshot, dict):
                raise ValueError
            collected = timestamp(snapshot.get("collected"))
            attempted = timestamp(evidence.get("attempted"))
            valid = (
                evidence.get("target") == evidence_target and evidence.get("outcome") == "success"
                and attempted_receipt == evidence.get("attempted")
                and (node is None or snapshot.get("node") == node or snapshot.get("host") == node)
                and (node is not None or isinstance(snapshot.get("host"), str))
                and evidence.get("collected") == snapshot.get("collected")
                and evidence.get("sha256") == hashlib.sha256(raw).hexdigest()
                and now - timedelta(hours=36) <= collected <= now
                and attempted <= now
                and collected - timedelta(hours=1) <= attempted <= collected + timedelta(seconds=1)
                and (since is None or attempted >= timestamp(since))
            )
            if not valid:
                raise ValueError
            collected_values[evidence_target] = snapshot["collected"]
    except (OSError, ValueError, TypeError, OverflowError):
        report["reason"] = (
            "Inventory refresh evidence missing, failed, mismatched or stale; "
            "retained files are historical observations"
        )
        code = 3
    else:
        report.update(outcome="success", collected=collected_values)
        code = 0
    emit(report, json_output, stdout)
    return code


# Retained only for the P3/P4 in-package import surface; callers use collection_status now that PBS
# freshness is part of the default contract.
proxmox_status = collection_status
