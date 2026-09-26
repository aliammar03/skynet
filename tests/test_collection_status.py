"""Freshness gate: only complete, receipt-bound, hash-matching, recent evidence reports success."""

import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from skynet import collection

# (evidence target, snapshot file, marker file, node/host value the gate expects)
OBSERVATIONS = (
    [(f"proxmox-{t}", s, m, {"node": t}) for t, s, m in collection.PROXMOX_NODES]
    + [(f"proxmox-{t}-acl", s, m, {"node": f"server-proxmox-{t}"})
       for t, s, m in collection.PROXMOX_ACLS]
    + [("pbs", *collection.PBS, {"host": "pbs"})]
    + [(f"docker-{label}", s, m, {"host": label}) for label, s, m in collection.DOCKERS]
    + [("dns", *collection.DNS, {"host": "dns"})]
    + [(t, s, m, {"host": "opnsense"}) for t, s, m in collection.OPNSENSE]
    + [("network-gear", *collection.OMADA, {"host": "omada"})]
    + [("certs", *collection.CERTS, {"host": "ops"}), ("routes", *collection.ROUTES, {"host": "ops"})]
)


def _evidence(repo: Path, *, age: timedelta = timedelta(minutes=5)) -> None:
    attempted = (datetime.now(UTC) - age).isoformat(timespec="microseconds")
    (repo / ".cache").mkdir(parents=True, exist_ok=True)
    (repo / ".cache/collection.lock").write_text(attempted)
    for target, snapshot_name, marker_name, identity in OBSERVATIONS:
        snapshot = (repo / "inventory" / snapshot_name)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(json.dumps({"collected": attempted, **identity}))
        marker = {"target": target, "outcome": "success", "attempted": attempted,
                  "collected": attempted, "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest()}
        (repo / "inventory" / marker_name).write_text(json.dumps(marker))


def _status(repo: Path) -> int:
    return collection.collection_status(repo, since=None, json_output=True, stdout=io.StringIO())


def test_complete_fresh_evidence_succeeds(tmp_path: Path) -> None:
    _evidence(tmp_path)
    assert _status(tmp_path) == 0


def test_missing_evidence_is_unavailable(tmp_path: Path) -> None:
    assert _status(tmp_path) == 3


def test_stale_evidence_is_unavailable(tmp_path: Path) -> None:
    _evidence(tmp_path, age=timedelta(hours=37))
    assert _status(tmp_path) == 3


@pytest.mark.parametrize("index", range(len(OBSERVATIONS)))
def test_any_tampered_snapshot_is_unavailable(tmp_path: Path, index: int) -> None:
    _evidence(tmp_path)
    snapshot = tmp_path / "inventory" / OBSERVATIONS[index][1]
    snapshot.write_text(snapshot.read_text().replace("}", ', "edited": true}'))
    assert _status(tmp_path) == 3


def test_failed_collector_is_unavailable(tmp_path: Path) -> None:
    _evidence(tmp_path)
    marker = tmp_path / "inventory" / OBSERVATIONS[0][2]
    marker.write_text(marker.read_text().replace('"success"', '"failure"'))
    assert _status(tmp_path) == 3
