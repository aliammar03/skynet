"""`skynet watch`: the live health monitor (T1 read only); a timer starts a pass every 3 minutes.

Each pass runs the deployment verifier (`deploy.observe`: the running revision, healthy, routed)
for every non-manual service on `origin/main`, and alerts on **state change** only:

- healthy → unhealthy after two consecutive failed passes (one alert; a flap never alerts);
- unhealthy → healthy on the first good pass (one recovery alert, only if a down alert went out;
  an unsent recovery is retried);
- still down: at most one reminder a day.

A pass that cannot observe at all (no fetch, no Docker, no state) is the pseudo-target `monitor`,
which runs through the same rule; once it is unhealthy (two failed passes) the pass pings the
dead-man's switch `/fail`, otherwise healthy. While a write holds the lock, only the target it is
changing is skipped (a deploy mid-flight is not an outage); every other service is still checked.
An alert that could not be sent is retried on the next pass. State lives in `state/watch.json`.
"""

from __future__ import annotations

import json
import signal
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from skynet import alert, common, deploy, deployment, writepath
from skynet.writepath import FAILED, OK, UNAVAILABLE, Ledger, WriteError

FAILURES_TO_ALERT = 2
# The latency budget (observability spoke): passes start ≤ 181 s apart (OnUnitActiveSec=3m,
# AccuracySec=1s); a pass starts no new observation after PASS_BUDGET_SECONDS, caps each at
# OBSERVE_MAX_SECONDS, and pushes at once (alert.TIMEOUT), so it ends within one interval.
PASS_BUDGET_SECONDS = 75.0
OBSERVE_MAX_SECONDS = 60.0
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
    state["failures"] = int(state.get("failures", 0)) + 1
    state["reason"] = reason
    if state.get("status") != "unhealthy":
        if state["failures"] < FAILURES_TO_ALERT:
            return state, None  # a blip: an unsent recovery stays pending
        state.pop("recovery_pending", None)  # down again: the DOWN alert supersedes it
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


def writes_in_flight(ledger: Ledger) -> set[str]:
    """Targets a write is changing right now. Only while the lock is held: a `started` record
    left by a crash must never hide a service for good."""
    return ledger.in_flight() if ledger.busy() else set()


def docker_reachable(context: str) -> None:
    """One cheap probe first, so a Docker host that is down is one `monitor` alert, never a
    storm of per-service ones."""
    try:
        deployment._docker(["docker", "--context", context, "version", "--format",
                            "{{.Server.Version}}"], 15.0)
    except deployment.VerificationError:
        raise WriteError("Docker host unreachable", UNAVAILABLE) from None


class _Overrun(Exception):
    pass


def _bounded(action: Callable[[], dict[str, Any]], seconds: float) -> dict[str, Any]:
    """Run one observation under a hard wall-clock cap (SIGALRM; subprocess.run kills its child
    when interrupted). An observation that overruns is a failure of that service."""
    def expire(signum: int, frame: Any) -> None:
        raise _Overrun

    previous = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return action()
    except _Overrun:
        raise WriteError(f"observation exceeded {int(seconds)} s", FAILED) from None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def targets(repo: Path, states: dict[str, Any], skip: set[str]) -> list[str]:
    """Services to observe, least recently observed first, so a pass that runs out of budget
    never starves the same tail. An empty declaration is refused: nothing observed is not
    healthy."""
    deploy.fetch(repo)
    declared = deploy.services(repo)
    if not declared:
        raise WriteError("origin/main declares no services", UNAVAILABLE)
    wanted = [service for service in declared
              if not deploy.manual(repo, service, deploy.MAIN) and f"svc/{service}" not in skip]
    return sorted(wanted, key=lambda service: (
        float(states.get(f"svc/{service}", {}).get("observed_at", 0.0)), service))


def run(repo: Path, *, context: str, state_dir: Path, json_output: bool, stdout: TextIO,
        now: float | None = None, clock: Callable[[], float] = time.monotonic) -> int:
    """One pass. Its time is bounded (budget + one capped observation + one push), and each
    service's alert goes out as soon as it is observed: see the latency budget in the
    observability spoke."""
    started = clock()

    def wall() -> float:
        return time.time() if now is None else now + clock() - started

    path = state_dir / "watch.json"
    code, lines = OK, []
    states: dict[str, Any] = {}
    try:
        states = load(path)
        changing = writes_in_flight(Ledger(state_dir))
        order = targets(repo, states, changing)
        docker_reachable(context)
    except WriteError as error:
        monitor, message = transition(states.get(MONITOR), False, error.reason, wall())
        failure = _push(MONITOR, monitor, message, wall())
        states[MONITOR] = monitor  # every service keeps its state: nothing was observed
        lines.append({"target": MONITOR, "outcome": "unavailable", "reason": error.reason,
                      **({"alert": failure or "sent"} if message else {})})
        code = UNAVAILABLE
    else:
        declared = {f"svc/{service}" for service in order} | changing
        fresh: dict[str, Any] = {key: value for key, value in states.items() if key in declared}
        for target in sorted(changing):
            lines.append({"target": target, "outcome": "skipped", "reason": "a write is changing it"})
        unobserved = []
        for service in order:
            target = f"svc/{service}"
            if clock() - started >= PASS_BUDGET_SECONDS:
                unobserved.append(target)  # keeps its state; observed first next pass
                continue
            try:
                evidence = _bounded(lambda: deploy.observe(repo, service, context),
                                    OBSERVE_MAX_SECONDS)
                healthy, reason, revision = True, None, str(evidence.get("revision", ""))
            except WriteError as error:
                healthy, reason, revision = False, error.reason, None
            entry, message = transition(states.get(target), healthy, reason, wall())
            failure = _push(target, entry, message, wall())  # at once, not at the end of the pass
            entry["observed_at"] = wall()
            fresh[target] = entry
            row = {"target": target, "source": revision, "outcome": entry["status"],
                   "reason": reason}
            if message:
                row["alert"] = failure or "sent"
            lines.append(row)
            if not healthy:
                code = FAILED
        for target in unobserved:
            lines.append({"target": target, "outcome": "skipped", "reason": "pass budget used"})
        # A pass that can't observe everything in budget breaks the latency promise: that is a
        # monitor failure (two strikes → alert), not a silent gap.
        budget_reason = f"{len(unobserved)} service(s) not observed within the pass budget"
        monitor, message = transition(states.get(MONITOR), not unobserved,
                                      budget_reason if unobserved else None, wall())
        _push(MONITOR, monitor, message, wall())
        fresh[MONITOR] = monitor
        states = fresh
    # `/fail` pages at once on healthchecks.io, so it follows the same two-strike rule as the
    # monitor alert. Unwritable state can't count strikes (and won't heal itself): fail at once.
    monitor_down = states.get(MONITOR, {}).get("status") == "unhealthy"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        common.atomic_write_text(path, json.dumps(states, indent=2, sort_keys=True) + "\n")
    except OSError:
        lines.append({"target": MONITOR, "outcome": "unavailable", "reason": "watch state unwritable"})
        code, monitor_down = UNAVAILABLE, True
    ping_failure = alert.ping(not monitor_down)
    if ping_failure:
        lines.append({"target": "dead-man", "outcome": "unavailable", "reason": ping_failure})
    for row in lines:
        writepath.emit(row, json_output, stdout)
    return code
