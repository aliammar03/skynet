"""The write-path shape: ordering, refusal without change, rollback, reconcile, and the record."""

import io
import json
import threading
import time
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


def _never_started(*_: Any) -> Any:
    raise writepath.NotStarted("program could not be started")


def test_an_execute_that_never_started_is_unavailable_after_its_cleanup(tmp_path: Path) -> None:
    ledger, calls = Ledger(tmp_path), []
    operation = _run(ledger, calls, execute=_never_started,
                     rollback=lambda saved, error: calls.append("cleanup") or "not-needed")
    assert calls[-1] == "cleanup" and "commit" not in calls
    assert (operation.outcome, operation.code) == ("unavailable", writepath.UNAVAILABLE)
    assert _records(ledger)[-1]["phase"] == "final"


def test_not_started_after_execute_ran_is_a_failure(tmp_path: Path) -> None:
    operation = _run(Ledger(tmp_path), [], verify=_never_started)
    assert (operation.outcome, operation.code) == ("rolled-back", 1)


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
    ledger.wait = 0.2
    with ledger.lock():
        operation = _run(ledger, [])
    assert (operation.outcome, operation.code) == ("unavailable", 3)


def test_a_brief_probe_never_fails_a_writer(tmp_path: Path) -> None:
    """An observer's `busy()` holds the lock for an instant; a writer waits it out."""
    ledger, released = Ledger(tmp_path), threading.Event()

    def hold() -> None:
        with Ledger(tmp_path).lock():
            released.wait(0.3)

    holder = threading.Thread(target=hold)
    holder.start()
    time.sleep(0.05)
    operation = _run(ledger, [])
    holder.join()
    assert operation.outcome == "success"


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


@pytest.fixture
def pushed(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, int]]:
    sent: list[tuple[str, str, int]] = []
    monkeypatch.setattr(writepath.alert, "send", lambda title, message, priority=0, path=None:
                        sent.append((title, message, priority)))
    return sent


def test_rollback_failed_alerts_and_records_the_alert(tmp_path: Path,
                                                      pushed: list[tuple[str, str, int]]) -> None:
    operation = _run(Ledger(tmp_path), [], verify=_fail("unhealthy"), rollback=_fail("up failed"))
    assert operation.outcome == "rollback-failed"
    assert pushed == [("skynet: svc/demo rollback-failed",
                       f"svc/demo@{'a' * 12}: rollback-failed — unhealthy; rollback: up failed "
                       "(recovery: rollback-failed)", 1)]
    assert {"step": "alert", "outcome": "ok"} in _records(Ledger(tmp_path))[-1]["steps"]


def test_unrecorded_success_alerts(tmp_path: Path, pushed: list[tuple[str, str, int]]) -> None:
    assert _run(Ledger(tmp_path), [], commit=_fail("host fact not written")).outcome == "unrecorded"
    assert [title for title, _, _ in pushed] == ["skynet: svc/demo unrecorded"]


def test_ordinary_outcomes_do_not_alert(tmp_path: Path, pushed: list[tuple[str, str, int]]) -> None:
    _run(Ledger(tmp_path), [])
    _run(Ledger(tmp_path), [], verify=_fail("unhealthy"))
    _run(Ledger(tmp_path), [], preflight=_fail("bad image"))
    assert pushed == []


def test_refusal_before_start_is_recorded_and_shown_by_log(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    writepath.refuse(Operation("publish", "svc/demo", ""), ledger, "no route for the service")
    _run(ledger, [])
    out = io.StringIO()
    writepath.show_log(ledger, target=None, kind=None, outcome="refused", limit=10,
                       json_output=False, stdout=out)
    assert out.getvalue().count("\n") == 1 and "svc/demo: refused — no route" in out.getvalue()
    out = io.StringIO()
    writepath.show_log(ledger, target="svc/demo", kind="deploy", outcome=None, limit=10,
                       json_output=True, stdout=out)
    assert [json.loads(row)["outcome"] for row in out.getvalue().splitlines()] == ["success"]


def test_busy_reports_a_held_lock(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    assert not ledger.busy()
    with ledger.lock():
        assert ledger.busy()
    assert not ledger.busy()


def test_one_line_format() -> None:
    assert writepath.line({"target": "svc/x", "source": "b" * 40, "outcome": "refused",
                           "reason": "unmerged"}) == f"svc/x@{'b' * 12}: refused — unmerged"


def test_a_lost_final_record_after_a_write_is_unrecorded_and_alerts(
        tmp_path: Path, pushed: list[tuple[str, str, int]], monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, calls = Ledger(tmp_path), []
    real = Ledger.append

    def append(self: Ledger, entry: dict[str, Any]) -> None:
        if entry.get("phase") == "final":
            raise WriteError("operation record unavailable", 3)
        real(self, entry)

    monkeypatch.setattr(Ledger, "append", append)
    operation = _run(ledger, calls)
    assert calls[:4] == ["preflight", "snapshot", "execute", "verify"]
    assert (operation.outcome, operation.code) == ("unrecorded", 3)
    assert "final record lost" in str(operation.reason)
    assert [title for title, _, _ in pushed] == ["skynet: svc/demo unrecorded"]


def test_a_lost_started_record_changes_nothing(
        tmp_path: Path, pushed: list[tuple[str, str, int]], monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(Ledger, "append", lambda self, entry: (_ for _ in ()).throw(
        WriteError("operation record unavailable", 3)))
    operation = _run(Ledger(tmp_path), calls)
    assert operation.outcome == "unavailable" and "execute" not in calls and pushed == []
