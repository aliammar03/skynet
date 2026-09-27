"""`skynet watch`: the live health monitor (T1 read only), run every 5 minutes by a timer.

Each pass runs the deployment verifier (`deploy.observe`: the running revision, healthy, routed)
for every non-manual service on `origin/main`, and alerts on **state change** only:

- healthy → unhealthy after two consecutive failed passes (one alert; a flap never alerts);
- unhealthy → healthy on the first good pass (one recovery alert, only if a down alert went out;
  an unsent recovery is retried);
- still down: at most one reminder a day.

A pass that cannot observe at all (no fetch, no Docker, no state) is the pseudo-target `monitor`,
which runs through the same rule, and pings the dead-man's switch `/fail`; a normal pass pings it
healthy. A pass while a write holds the lock is skipped: a deploy mid-flight is not an outage.
An alert that could not be sent is retried on the next pass. State lives in `state/watch.json`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, TextIO

from skynet import alert, common, deploy, writepath
from skynet.writepath import FAILED, OK, UNAVAILABLE, Ledger, WriteError

FAILURES_TO_ALERT = 2
REMINDER_SECONDS = 24 * 3600
MONITOR = "monitor"


def _stamp(now: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(now))


def transition(entry: dict[str, Any] | None, healthy: bool, reason: str | None,
               now: float) -> tuple[dict[str, Any], str | None]:
    """Advance one target's state; return it and the message to push (None: stay quiet)."""
    state = dict(entry or {"status": "healthy", "failures": 0})
    if healthy:
        told = state.get("status") == "unhealthy" and state.get("alerted")
        down_since, unsent = state.get("since"), state.get("recovery_pending")
        state = {"status": "healthy", "failures": 0}
        if told:
            since = now if down_since is None else float(down_since)
            unsent = f"recovered (down since {_stamp(since)})"
        if unsent:  # kept until `_push` confirms it went out
            state["recovery_pending"] = unsent
        return state, unsent or None
    state.pop("recovery_pending", None)  # a new failure supersedes an unsent recovery
    state["failures"] = int(state.get("failures", 0)) + 1
    state["reason"] = reason
    if state.get("status") != "unhealthy":
        if state["failures"] < FAILURES_TO_ALERT:
            return state, None
        state.update(status="unhealthy", since=now, alerted=False)
    if not state.get("alerted"):
        return state, f"DOWN — {reason}"
    if now - float(state.get("reminded_at", now)) >= REMINDER_SECONDS:
        return state, f"still down since {_stamp(float(state['since']))} — {reason}"
    return state, None


def _push(target: str, state: dict[str, Any], message: str | None, now: float) -> str | None:
    """Send one state-change message; record that it went out (or retry next pass)."""
    if message is None:
        return None
    failure = alert.send(f"skynet: {target}", message, priority=1 if "DOWN" in message else 0)
    if failure is None and state.get("status") == "unhealthy":
        state.update(alerted=True, reminded_at=now)
    elif failure is None:
        state.pop("recovery_pending", None)
    return failure


def load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except ValueError:
        return {}  # a corrupt state restarts the counts; it never hides a failure for long
    except (OSError, UnicodeError):
        raise WriteError("watch state unreadable", UNAVAILABLE) from None
    return data if isinstance(data, dict) else {}


def observe(repo: Path, context: str) -> dict[str, tuple[bool, str | None, str | None]]:
    """service → (healthy, reason, running revision). Raises WriteError if nothing is observable."""
    deploy.fetch(repo)
    results: dict[str, tuple[bool, str | None, str | None]] = {}
    unavailable = 0
    for service in deploy.services(repo):
        if deploy.manual(repo, service, deploy.MAIN):
            continue
        try:
            evidence = deploy.observe(repo, service, context)
        except WriteError as error:
            unavailable += error.code == UNAVAILABLE
            results[service] = (False, error.reason, None)
        else:
            results[service] = (True, None, str(evidence.get("revision", "")))
    if results and unavailable == len(results):
        raise WriteError("no service could be observed (Docker host unavailable?)", UNAVAILABLE)
    return results


def run(repo: Path, *, context: str, state_dir: Path, json_output: bool, stdout: TextIO,
        now: float | None = None) -> int:
    now = time.time() if now is None else now
    ledger = Ledger(state_dir)
    if ledger.busy():
        writepath.emit({"target": "watch", "outcome": "skipped", "reason": "a write holds the lock"},
                       json_output, stdout)
        alert.ping(True)
        return OK
    path = state_dir / "watch.json"
    code, lines = OK, []
    states: dict[str, Any] = {}
    try:
        states = load(path)
        observed = observe(repo, context)
    except WriteError as error:
        monitor, message = transition(states.get(MONITOR), False, error.reason, now)
        failure = _push(MONITOR, monitor, message, now)
        states[MONITOR] = monitor
        lines.append({"target": MONITOR, "outcome": "unavailable", "reason": error.reason,
                      **({"alert": failure or "sent"} if message else {})})
        code = UNAVAILABLE
    else:
        monitor, message = transition(states.get(MONITOR), True, None, now)
        _push(MONITOR, monitor, message, now)
        fresh: dict[str, Any] = {MONITOR: monitor}
        for service, (healthy, reason, revision) in sorted(observed.items()):
            target = f"svc/{service}"
            entry, message = transition(states.get(target), healthy, reason, now)
            failure = _push(target, entry, message, now)
            fresh[target] = entry  # services gone from main drop out here
            row = {"target": target, "source": revision, "outcome": entry["status"],
                   "reason": reason}
            if message:
                row["alert"] = failure or "sent"
            lines.append(row)
            if not healthy:
                code = FAILED
        states = fresh
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        common.atomic_write_text(path, json.dumps(states, indent=2, sort_keys=True) + "\n")
    except OSError:
        lines.append({"target": MONITOR, "outcome": "unavailable", "reason": "watch state unwritable"})
        code = UNAVAILABLE
    ping_failure = alert.ping(code != UNAVAILABLE)
    if ping_failure:
        lines.append({"target": "dead-man", "outcome": "unavailable", "reason": ping_failure})
    for row in lines:
        writepath.emit(row, json_output, stdout)
    return code
