"""The write-path shape: ordering, refusal without change, rollback, reconcile, and the record."""

import json
from pathlib import Path
from typing import Any

import pytest

from skynet import writepath
from skynet.writepath import Ledger, Operation, WriteError


def _fail(reason: str, code: int = 1) -> Any:
    def action(*_: Any) -> Any:
        raise WriteError(reason, code)
    return action


def _run(ledger: Ledger, calls: list[str], **overrides: Any) -> Operation:
    def step(name: str, value: Any = None) -> Any:
        def action(*_: Any) -> Any:
            calls.append(name)
            return value
        return action
    hooks: dict[str, Any] = {
        "preflight": step("preflight"), "snapshot": step("snapshot", "saved"),
        "execute": step("execute"), "verify": step("verify", {"ok": True}),
        "rollback": step("rollback", "rolled-back"), "reconcile": step("reconcile", {"seen": 1}),
        "commit": step("commit"),
    }
    hooks.update(overrides)
    return writepath.run(Operation("deploy", "svc/demo", "a" * 40), ledger, **hooks)


def _records(ledger: Ledger) -> list[dict[str, Any]]:
    return [json.loads(line) for line in ledger.path.read_text().splitlines()]


def test_success_runs_every_step_in_order_and_records(tmp_path: Path) -> None:
    ledger, calls = Ledger(tmp_path), []
    operation = _run(ledger, calls)
    assert calls == ["preflight", "snapshot", "execute", "verify", "commit"]
    assert (operation.outcome, operation.code, operation.recovery) == ("success", 0, "not-needed")
    assert [record["phase"] for record in _records(ledger)] == ["started", "final"]


def test_preflight_refusal_changes_nothing(tmp_path: Path) -> None:
    ledger, calls = Ledger(tmp_path), []
    operation = _run(ledger, calls, preflight=_fail("image missing"))
    assert calls == [] and operation.outcome == "refused" and operation.code == 1
    assert [record["phase"] for record in _records(ledger)] == ["final"]  # never `started`


def test_verify_failure_rolls_back_and_is_not_success(tmp_path: Path) -> None:
    ledger, calls = Ledger(tmp_path), []
    operation = _run(ledger, calls, verify=_fail("container is not healthy"))
    assert calls[-1] == "rollback" and "commit" not in calls
    assert (operation.outcome, operation.recovery, operation.code) == ("rolled-back", "rolled-back", 1)
    assert operation.reason == "container is not healthy"


def test_failed_rollback_is_the_hard_checkpoint(tmp_path: Path) -> None:
    operation = _run(Ledger(tmp_path), [], execute=_fail("compose up failed"),
                     rollback=_fail("compose up failed"))
    assert (operation.outcome, operation.code) == ("rollback-failed", writepath.ROLLBACK_FAILED)
    assert operation.reason == "compose up failed; rollback: compose up failed"


def test_no_rollback_target_is_a_plain_failure(tmp_path: Path) -> None:
    operation = _run(Ledger(tmp_path), [], execute=_fail("x"), rollback=lambda *_: "no-rollback-target")
    assert (operation.outcome, operation.recovery, operation.code) == ("failed", "no-rollback-target", 1)


def test_unwritable_record_after_success_is_unrecorded(tmp_path: Path) -> None:
    operation = _run(Ledger(tmp_path), [], commit=_fail("host fact not written", 3))
    assert (operation.outcome, operation.code) == ("unrecorded", 3)


def test_interrupted_write_is_reconciled_before_retry(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    ledger.append(Operation("deploy", "svc/demo", "b" * 40, id="dead").record("started"))
    calls: list[str] = []
    operation = _run(ledger, calls)
    assert calls[0] == "reconcile" and operation.outcome == "success"
    reconciled = [r for r in _records(ledger) if r["phase"] == "reconciled"]
    assert reconciled == [{**reconciled[0], "id": "dead", "observed": {"seen": 1}}]
    assert ledger.dangling("deploy", "svc/demo") is None


def test_unobservable_interrupted_write_refuses(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    ledger.append(Operation("deploy", "svc/demo", "b" * 40).record("started"))
    calls: list[str] = []
    operation = _run(ledger, calls, reconcile=_fail("Docker host unavailable", 3))
    assert calls == [] and operation.outcome == "refused" and operation.code == 3


def test_other_targets_do_not_block(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    ledger.append(Operation("deploy", "svc/other", "b" * 40).record("started"))
    assert ledger.dangling("deploy", "svc/demo") is None


def test_a_held_lock_refuses_a_second_writer(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    with ledger.lock():
        operation = _run(ledger, [])
    assert (operation.outcome, operation.code) == ("unavailable", 3)


def test_unavailable_state_dir_is_unavailable(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("")
    operation = _run(Ledger(blocker / "state"), [])
    assert operation.outcome == "unavailable"


def test_step_failure_is_recorded(tmp_path: Path) -> None:
    operation = _run(Ledger(tmp_path), [], execute=_fail("compose up failed"))
    assert {"step": "execute", "outcome": "failed", "reason": "compose up failed"} in operation.steps


def test_malformed_record_is_unavailable(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    ledger.path.write_text("{not json\n")
    with pytest.raises(WriteError):
        ledger.entries()
