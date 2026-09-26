"""The one write-path shape every Skynet write reuses.

    plan → preflight → snapshot → execute → verify → rollback or stop → record

The caller supplies plain functions for each step; this module owns ordering, the single write
lock, and the append-only operation record. `commit` runs only after a verified success, to make
the result durable where the next write finds it (a rollback target, a state branch). A preflight or snapshot failure changes nothing and
stops. An execute or verify failure hands the snapshot to the caller's rollback. A `started`
record without its final record (a crash or timeout) is reconciled, by observing and recording
what is live, before the next write on that target. Records hold identities and fixed reasons,
never secret values or remote error text.
"""

from __future__ import annotations

import fcntl
import json
import os
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

DEFAULT_STATE_DIR = Path("/opt/skynet-ops/state")
T = TypeVar("T")

# Exit codes shared by every write path.
OK, FAILED, USAGE, UNAVAILABLE, ROLLBACK_FAILED = 0, 1, 2, 3, 4


class WriteError(Exception):
    """A fixed, safe reason and exit code; never carries remote or secret text."""

    def __init__(self, reason: str, code: int = FAILED):
        super().__init__(reason)
        self.reason = reason
        self.code = code


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Operation:
    """One write: what it targets, which source identity it applies, and what happened."""

    kind: str
    target: str
    source: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    steps: list[dict[str, Any]] = field(default_factory=list)
    outcome: str = "pending"
    recovery: str = "not-needed"
    reason: str | None = None
    verification: dict[str, Any] | None = None
    code: int = OK

    def step(self, name: str, action: Callable[[], T]) -> T:
        """Run one named step and record its outcome; a WriteError propagates after recording."""
        try:
            value = action()
        except WriteError as error:
            self.steps.append({"step": name, "outcome": "failed", "reason": error.reason})
            raise
        self.steps.append({"step": name, "outcome": "ok"})
        return value

    def note(self, name: str, outcome: str, detail: str | None = None) -> None:
        entry = {"step": name, "outcome": outcome}
        if detail is not None:
            entry["detail"] = detail
        self.steps.append(entry)

    def record(self, phase: str) -> dict[str, Any]:
        return {"ts": _now(), "phase": phase, **asdict(self)}


class Ledger:
    """The local operation record and the one lock serializing all write paths."""

    def __init__(self, state_dir: Path = DEFAULT_STATE_DIR):
        self.state_dir = state_dir
        self.path = state_dir / "operations.jsonl"

    @contextmanager
    def lock(self) -> Iterator[None]:
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            handle = open(self.state_dir / "write.lock", "a")
        except OSError:
            raise WriteError("write state directory unavailable", UNAVAILABLE) from None
        with handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise WriteError("another write holds the lock", UNAVAILABLE) from None
            yield

    def append(self, entry: dict[str, Any]) -> None:
        """Append one flushed line; a record that cannot be kept stops the write."""
        try:
            line = json.dumps(entry, sort_keys=True, allow_nan=False) + "\n"
            with open(self.path, "a", encoding="utf-8") as stream:
                stream.write(line)
                stream.flush()
                os.fsync(stream.fileno())
        except (OSError, TypeError, ValueError):
            raise WriteError("operation record unavailable", UNAVAILABLE) from None

    def entries(self) -> list[dict[str, Any]]:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        except (OSError, UnicodeError):
            raise WriteError("operation record unavailable", UNAVAILABLE) from None
        entries = []
        for line in lines:
            try:
                value = json.loads(line)
            except ValueError:
                raise WriteError("operation record malformed", UNAVAILABLE) from None
            if isinstance(value, dict):
                entries.append(value)
        return entries

    def dangling(self, kind: str, target: str) -> dict[str, Any] | None:
        """The newest `started` entry for this target that never got a final or reconciled line."""
        closed: set[str] = set()
        for entry in reversed(self.entries()):
            if entry.get("kind") != kind or entry.get("target") != target:
                continue
            if entry.get("phase") in {"final", "reconciled"}:
                closed.add(str(entry.get("id")))
            elif entry.get("phase") == "started" and entry.get("id") not in closed:
                return entry
        return None


def run(
    operation: Operation,
    ledger: Ledger,
    *,
    preflight: Callable[[], Any],
    snapshot: Callable[[], T],
    execute: Callable[[T], Any],
    verify: Callable[[T], dict[str, Any]],
    rollback: Callable[[T, WriteError], str],
    reconcile: Callable[[], dict[str, Any]],
    commit: Callable[[T], Any] = lambda saved: None,
) -> Operation:
    """Drive one write through the shape and record it. Never raises WriteError."""
    try:
        with ledger.lock():
            _run_locked(operation, ledger, preflight, snapshot, execute, verify, rollback, reconcile,
                        commit)
    except WriteError as error:  # the lock or the record itself is unavailable
        operation.outcome, operation.reason, operation.code = "unavailable", error.reason, error.code
    return operation


def _run_locked(operation: Operation, ledger: Ledger, preflight: Callable[[], Any],
                snapshot: Callable[[], T], execute: Callable[[T], Any],
                verify: Callable[[T], dict[str, Any]], rollback: Callable[[T, WriteError], str],
                reconcile: Callable[[], dict[str, Any]], commit: Callable[[T], Any]) -> None:
    dangling = ledger.dangling(operation.kind, operation.target)
    if dangling is not None:
        try:
            observed = reconcile()
        except WriteError as error:
            operation.note("reconcile", "failed", error.reason)
            _stop(operation, ledger, "refused", error)
            return
        ledger.append({"ts": _now(), "phase": "reconciled", "kind": operation.kind,
                       "target": operation.target, "id": dangling.get("id"), "observed": observed})
        operation.note("reconcile", "ok", f"closed interrupted operation {dangling.get('id')}")
    try:
        operation.step("preflight", preflight)
        saved = operation.step("snapshot", snapshot)
    except WriteError as error:
        _stop(operation, ledger, "refused", error)
        return
    ledger.append(operation.record("started"))
    try:
        operation.step("execute", lambda: execute(saved))
        operation.verification = operation.step("verify", lambda: verify(saved))
    except WriteError as error:
        failure = error
        operation.reason = failure.reason
        try:
            operation.recovery = operation.step("rollback", lambda: rollback(saved, failure))
        except WriteError as rollback_error:
            operation.recovery = "rollback-failed"
            operation.outcome, operation.code = "rollback-failed", ROLLBACK_FAILED
            operation.reason = f"{failure.reason}; rollback: {rollback_error.reason}"
        else:
            operation.outcome = "rolled-back" if operation.recovery == "rolled-back" else "failed"
            operation.code = FAILED
        ledger.append(operation.record("final"))
        return
    operation.outcome = "success"
    try:
        operation.step("record", lambda: commit(saved))
    except WriteError as error:  # live and verified, but the next write cannot find it
        operation.outcome, operation.reason, operation.code = "unrecorded", error.reason, UNAVAILABLE
    ledger.append(operation.record("final"))


def _stop(operation: Operation, ledger: Ledger, outcome: str, error: WriteError) -> None:
    operation.outcome, operation.reason, operation.code = outcome, error.reason, error.code
    ledger.append(operation.record("final"))


def report(operation: Operation) -> dict[str, Any]:
    """The JSON-ready view printed by a CLI."""
    return {key: value for key, value in asdict(operation).items() if value is not None}
