"""Default collection: one receipt, per-collector markers, and no failure hides or stops another."""

import hashlib
import io
import json
from pathlib import Path

from skynet import collection, common, docker
from skynet.collection import Collector, Evidence


def _collector(name: str, code: int = 0, *, pair: bool = False) -> Collector:
    evidence = (Evidence(name, f"{name}.json", f"collection-{name}.json"),)
    if pair:
        evidence += (Evidence(f"{name}-b", f"{name}-b.json", f"collection-{name}-b.json"),)

    def run(repo: Path, outputs: tuple[Path, ...], files: collection.CredentialFiles) -> common.Result:
        def read() -> tuple[dict[str, str], ...]:
            if code:
                raise common.CollectionError("down", code)
            return tuple({"collected": "2026-01-01T00:00:00+00:00", "host": name} for _ in outputs)

        return common.run(name, outputs, read, lambda *snapshots: {"snapshots": len(snapshots)})
    return Collector(evidence, run)


def _collect(repo: Path, collectors: tuple[Collector, ...]) -> tuple[int, dict[str, object]]:
    (repo / "inventory").mkdir(parents=True, exist_ok=True)
    stream = io.StringIO()
    code = collection.collect_all(repo, json_output=True, stdout=stream, collectors=collectors)
    return code, json.loads(stream.getvalue())


def _marker(repo: Path, name: str) -> dict[str, object]:
    return json.loads((repo / "inventory" / f"collection-{name}.json").read_text())


def test_success_binds_markers_to_receipt_and_bytes(tmp_path: Path) -> None:
    code, report = _collect(tmp_path, (_collector("a"), _collector("b", pair=True)))
    assert code == 0 and report["outcome"] == "success"
    receipt = (tmp_path / ".cache/collection.lock").read_text()
    for name in ("a", "b", "b-b"):
        marker = _marker(tmp_path, name)
        raw = (tmp_path / "inventory" / f"{name}.json").read_bytes()
        assert marker["outcome"] == "success" and marker["attempted"] == receipt
        assert marker["sha256"] == hashlib.sha256(raw).hexdigest()


def test_one_failure_is_recorded_and_the_rest_still_run(tmp_path: Path) -> None:
    code, report = _collect(tmp_path, (_collector("a", 3), _collector("b", 1), _collector("c")))
    assert code == 1 and report["outcome"] == "failure"
    assert [c["outcome"] for c in report["collectors"]] == ["unavailable", "failure", "success"]  # type: ignore[attr-defined]
    assert _marker(tmp_path, "a")["outcome"] == "unavailable" and "sha256" not in _marker(tmp_path, "a")
    assert _marker(tmp_path, "c")["outcome"] == "success"


def test_only_unavailable_reports_code_three(tmp_path: Path) -> None:
    code, _ = _collect(tmp_path, (_collector("a", 3), _collector("b")))
    assert code == 3


def test_unconfirmed_cleanup_stops_and_blocks_the_next_run(tmp_path: Path) -> None:
    def stuck(repo: Path, outputs: tuple[Path, ...], files: collection.CredentialFiles) -> common.Result:
        raise docker.CleanupError

    after = _collector("after")
    code, report = _collect(tmp_path, (Collector((Evidence("d", "d.json", "collection-d.json"),), stuck),
                                       after))
    assert code == 1 and report["outcome"] == "recovery-required"
    assert not (tmp_path / "inventory/collection-after.json").exists()
    assert (tmp_path / ".cache/collection.lock").read_text() == "recovery-required"
    code, report = _collect(tmp_path, (after,))
    assert code == 1 and report["outcome"] == "recovery-required"


def test_default_collectors_cover_every_evidence_file_once() -> None:
    markers = [e.marker for e in collection.EVIDENCE]
    snapshots = [e.snapshot for e in collection.EVIDENCE]
    assert len(set(markers)) == len(markers) and len(set(snapshots)) == len(snapshots)
    assert "collection-docker-dmz.json" in markers and "firewall/firewall.json" in snapshots
