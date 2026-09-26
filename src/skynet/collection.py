"""Default collection and paired evidence freshness for current-state consumers."""

import fcntl
import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TextIO

from skynet import certs, common, dns, docker, omada, opnsense, pbs, proxmox, routes


@dataclass(frozen=True)
class CredentialFiles:
    """Literal credential files for the default collection, one per remote source."""

    core: Path = proxmox.DEFAULT_CREDENTIALS["core"]
    network: Path = proxmox.DEFAULT_CREDENTIALS["network"]
    pbs: Path = pbs.DEFAULT_CREDENTIALS
    dns: Path = dns.DEFAULT_CREDENTIALS
    opnsense: Path = opnsense.DEFAULT_CREDENTIALS
    omada: Path = omada.DEFAULT_CREDENTIALS


@dataclass(frozen=True)
class Evidence:
    """One published snapshot, its receipt-bound marker, and the identity the gate expects.

    `identity` is the snapshot's `node` or `host` value; None accepts any string `host`.
    """

    target: str
    snapshot: str
    marker: str
    identity: str | None = None


@dataclass(frozen=True)
class Collector:
    """One collector run in the default collection; it publishes every `evidence` snapshot."""

    evidence: tuple[Evidence, ...]
    run: Callable[[Path, tuple[Path, ...], CredentialFiles], common.Result]


def _proxmox(node: str) -> Collector:
    return Collector(
        (Evidence(f"proxmox-{node}", f"proxmox-{node}.json", f"collection-{node}.json", node),),
        lambda repo, out, files: proxmox.run(node, out[0], getattr(files, node)))


def _proxmox_acl(node: str) -> Collector:
    return Collector(
        (Evidence(f"proxmox-{node}-acl", f"proxmox-{node}-acl.json", f"collection-{node}-acl.json",
                  f"server-proxmox-{node}"),),
        lambda repo, out, files: proxmox.run_acl(node, out[0], getattr(files, node)))


def _docker(label: str) -> Collector:
    return Collector(
        (Evidence(f"docker-{label}", f"docker-{label}.json", f"collection-{label}.json", label),),
        lambda repo, out, files: docker.run(label, out[0], label))


COLLECTORS: tuple[Collector, ...] = (
    _proxmox("core"), _proxmox("network"), _proxmox_acl("core"), _proxmox_acl("network"),
    Collector((Evidence("pbs", "pbs.json", "collection-pbs.json"),),
              lambda repo, out, files: pbs.run(out[0], files.pbs)),
    _docker("docker-dmz"),
    Collector((Evidence("dns", "dns-zones.json", "collection-dns.json"),),
              lambda repo, out, files: dns.run(out[0], files.dns)),
    # One live OPNsense read publishes both paired snapshots and both markers, so neither
    # firewall config nor live state can look fresh without the other.
    Collector((Evidence("firewall", "firewall/firewall.json", "collection-firewall.json"),
               Evidence("opnsense", "opnsense.json", "collection-opnsense.json")),
              lambda repo, out, files: opnsense.run(out[0], out[1], files.opnsense)),
    Collector((Evidence("network-gear", "network-gear.json", "collection-network-gear.json"),),
              lambda repo, out, files: omada.run(out[0], files.omada)),
    Collector((Evidence("certs", "certs.json", "collection-certs.json"),),
              lambda repo, out, files: certs.run(out[0])),
    Collector((Evidence("routes", "routes.json", "collection-routes.json"),),
              lambda repo, out, files: routes.run(repo, out[0])),
)
EVIDENCE: tuple[Evidence, ...] = tuple(item for c in COLLECTORS for item in c.evidence)


class CleanupError(Exception):
    """A reader could not be confirmed stopped; collection must not continue."""


def receipt_write(lock: TextIO, attempted: str) -> None:
    """Invalidate in place before recording an attempt, independently of atomic rename."""
    lock.seek(0)
    lock.truncate()
    lock.flush()
    os.fsync(lock.fileno())
    lock.write(attempted)
    lock.flush()
    os.fsync(lock.fileno())


def emit(report: dict[str, Any], json_output: bool, stdout: TextIO) -> None:
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"{report['target']}: {report['outcome']}", file=stdout)
        if "reason" in report:
            print(report["reason"], file=stdout)
        if "collected" in report:
            print(f"observations collected: {report['collected']}", file=stdout)
        for result in report.get("collectors", []):
            print(f"{result['target']}: {result['outcome']}", file=stdout)
            if "reason" in result:
                print(result["reason"], file=stdout)


def _collect_one(collector: Collector, repo: Path, files: CredentialFiles, attempted: str,
                 lock: TextIO) -> common.Result:
    """Invalidate this collector's markers, run it, then record receipt-bound outcomes."""
    inventory = repo / "inventory"
    markers: list[tuple[Path, Path, dict[str, Any]]] = []
    for evidence in collector.evidence:
        marker: dict[str, Any] = {
            "target": evidence.target, "outcome": "unavailable", "attempted": attempted,
            "reason": "refresh incomplete; retained snapshot is previous evidence",
        }
        # A marker is durable before this read; a new receipt invalidates any preceding success
        # if publication fails before the next marker exists.
        common.publish_json(inventory / evidence.marker, marker)
        markers.append((inventory / evidence.snapshot, inventory / evidence.marker, marker))
    try:
        result = collector.run(repo, tuple(snapshot for snapshot, _, _ in markers), files)
    except docker.CleanupError:
        try:
            receipt_write(lock, "recovery-required")
        except OSError:
            raise CleanupError("unrecorded") from None
        raise CleanupError from None
    for snapshot, status, marker in markers:
        marker["outcome"] = result.outcome
        if result.code == 0:
            marker.pop("reason")
            marker.update(collected=result.collected,
                          sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest())
        else:
            marker["reason"] = result.reason
        common.publish_json(status, marker)
    return result


def collect_all(repo: Path, files: CredentialFiles | None = None, *, json_output: bool,
                stdout: TextIO, collectors: tuple[Collector, ...] = COLLECTORS) -> int:
    """Run every collector under one receipt; each failure is recorded, none stops the rest."""
    files = files or CredentialFiles()
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
            for collector in collectors:
                result = _collect_one(collector, repo, files, attempted, lock)
                report["collectors"].append(result.report())
                if result.code == 1:
                    code = 1
                elif result.code and code == 0:
                    code = result.code
            if code == 0:
                report["outcome"] = "success"
    except CleanupError as error:
        if error.args == ("unrecorded",):
            report["recovery_recorded"] = False
        report["outcome"] = "recovery-required"
        report["reason"] = "reader cleanup unconfirmed; collection stopped; inspect local processes"
        code = 1
    except (OSError, ValueError, common.CollectionError):
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
                (evidence, json.loads((repo / "inventory" / evidence.marker).read_bytes()),
                 (repo / "inventory" / evidence.snapshot).read_bytes())
                for evidence in EVIDENCE
            ]
        now = datetime.now(UTC)
        collected_values: dict[str, str] = {}
        for expected, evidence, raw in observations:
            evidence_target, node = expected.target, expected.identity
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
