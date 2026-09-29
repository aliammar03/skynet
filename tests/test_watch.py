"""`skynet watch`: an outage alerts once within two passes, a flap never alerts, recovery alerts
once, and a monitor that cannot observe says so instead of going quiet (F14)."""

import time
from pathlib import Path
from typing import Any

import pytest

from skynet import alert, deploy, watch, writepath
from skynet.writepath import Ledger, Operation, WriteError

REV = "1" * 40


class Lab:
    def __init__(self) -> None:
        self.health: dict[str, bool] = {"demo": True, "other": True}
        self.docker_down = False
        self.sent: list[tuple[str, str]] = []
        self.pings: list[bool] = []
        self.send_fails = False


@pytest.fixture
def lab(monkeypatch: pytest.MonkeyPatch) -> Lab:
    fake = Lab()

    def observe(repo: Path, service: str, context: str, revision: str | None = None) -> dict[str, Any]:
        if fake.docker_down:
            raise WriteError("Docker command unavailable", 3)
        if not fake.health[service]:
            raise WriteError("container is not healthy", 1)
        return {"revision": REV}

    def send(title: str, message: str, *, priority: int = 0, path: Any = None) -> str | None:
        if fake.send_fails:
            return "api.pushover.net unreachable or refused the request"
        fake.sent.append((title, message))
        return None

    monkeypatch.setattr(deploy, "fetch", lambda repo: None)
    monkeypatch.setattr(deploy, "services", lambda repo, ref="": sorted(fake.health))
    monkeypatch.setattr(deploy, "manual", lambda repo, service, ref: False)
    def reachable(context: str) -> None:
        if fake.docker_down:
            raise WriteError("Docker host unreachable", 3)

    monkeypatch.setattr(deploy, "observe", observe)
    monkeypatch.setattr(watch, "docker_reachable", reachable)
    monkeypatch.setattr(alert, "send", send)
    monkeypatch.setattr(alert, "ping", lambda ok=True, path=None: fake.pings.append(ok))
    return fake


class Out:
    def __init__(self) -> None:
        self.text = ""

    def write(self, value: str) -> None:
        self.text += value


def _pass(tmp_path: Path, minute: int) -> int:
    return watch.run(tmp_path, context="docker-dmz", state_dir=tmp_path / "state", json_output=False,
                     stdout=Out(), now=1_000_000.0 + minute * 300)  # type: ignore[arg-type]


def test_flapping_service_never_alerts(lab: Lab, tmp_path: Path) -> None:
    for minute, healthy in enumerate([False, True, False, True, False, True]):
        lab.health["demo"] = healthy
        _pass(tmp_path, minute)
    assert lab.sent == []


def test_sustained_outage_alerts_once_then_recovers_once(lab: Lab, tmp_path: Path) -> None:
    lab.health["demo"] = False
    codes = [_pass(tmp_path, minute) for minute in range(5)]
    assert codes == [1] * 5
    assert [title for title, _ in lab.sent] == ["skynet: svc/demo"]
    assert lab.sent[0][1].startswith("DOWN — container is not healthy")
    lab.health["demo"] = True
    assert _pass(tmp_path, 5) == 0
    assert lab.sent[-1][1].startswith("recovered") and len(lab.sent) == 2
    _pass(tmp_path, 6)
    assert len(lab.sent) == 2


def test_still_down_reminds_at_most_daily(lab: Lab, tmp_path: Path) -> None:
    lab.health["demo"] = False
    for minute in range(12 * 24 + 4):  # 24 h of 5-minute passes, plus a few
        _pass(tmp_path, minute)
    reminders = [message for _, message in lab.sent if message.startswith("still down")]
    assert len(reminders) == 1 and len(lab.sent) == 2


def test_an_unsent_alert_is_retried_next_pass(lab: Lab, tmp_path: Path) -> None:
    lab.health["demo"], lab.send_fails = False, True
    _pass(tmp_path, 0)
    _pass(tmp_path, 1)
    assert lab.sent == []
    lab.send_fails = False
    _pass(tmp_path, 2)
    assert [message[:4] for _, message in lab.sent] == ["DOWN"]


def test_monitor_that_cannot_observe_alerts_and_fails_the_ping(lab: Lab, tmp_path: Path) -> None:
    lab.docker_down = True
    assert [_pass(tmp_path, minute) for minute in range(3)] == [3, 3, 3]
    assert lab.pings == [True, False, False]  # /fail only once the monitor is down (2 strikes)
    assert [title for title, _ in lab.sent] == ["skynet: monitor"]
    assert not [title for title, _ in lab.sent if "svc/" in title]  # no storm per service
    lab.docker_down = False
    assert _pass(tmp_path, 3) == 0
    assert lab.sent[-1] == ("skynet: monitor", lab.sent[-1][1]) and "recovered" in lab.sent[-1][1]
    assert lab.pings[-1] is True


def test_a_long_write_skips_only_its_own_target(lab: Lab, tmp_path: Path) -> None:
    """A deploy of `demo` in flight never hides an outage of `other`."""
    lab.health["demo"] = lab.health["other"] = False
    ledger = Ledger(tmp_path / "state")
    ledger.append(Operation("deploy", "svc/demo", REV).record("started"))
    with ledger.lock():
        for minute in range(3):
            assert _pass(tmp_path, minute) == 1
    assert [title for title, _ in lab.sent] == ["skynet: svc/other"]
    assert lab.pings == [True, True, True]  # the monitor itself is working


def test_a_fenced_docker_host_is_a_planned_change_not_an_outage(lab: Lab, tmp_path: Path) -> None:
    """A guest update rebooting the host holds its fence: nothing alerts, nothing is lost."""
    ledger = Ledger(tmp_path / "state")
    lab.docker_down = True  # the host is rebooting
    with ledger.lock(writepath.fence("docker-dmz")):
        assert [_pass(tmp_path, minute) for minute in range(4)] == [0] * 4
    assert lab.sent == [] and lab.pings == [True] * 4
    lab.docker_down = False
    lab.health["demo"] = False  # the fence is gone: a real outage alerts as ever
    _pass(tmp_path, 4)
    _pass(tmp_path, 5)
    assert [title for title, _ in lab.sent] == ["skynet: svc/demo"]


def test_another_hosts_fence_hides_nothing(lab: Lab, tmp_path: Path) -> None:
    lab.health["demo"] = False
    with Ledger(tmp_path / "state").lock(writepath.fence("docker-other")):
        _pass(tmp_path, 0)
        _pass(tmp_path, 1)
    assert [title for title, _ in lab.sent] == ["skynet: svc/demo"]


def test_a_crashed_write_never_hides_a_service(lab: Lab, tmp_path: Path) -> None:
    """A `started` record with no lock held is a crash, not a write in progress."""
    lab.health["demo"] = False
    Ledger(tmp_path / "state").append(Operation("deploy", "svc/demo", REV).record("started"))
    _pass(tmp_path, 0)
    _pass(tmp_path, 1)
    assert [title for title, _ in lab.sent] == ["skynet: svc/demo"]


def test_a_service_removed_from_main_drops_out(lab: Lab, tmp_path: Path) -> None:
    lab.health["other"] = False
    _pass(tmp_path, 0)
    del lab.health["other"]
    _pass(tmp_path, 1)
    assert lab.sent == []
    assert "svc/other" not in (tmp_path / "state" / "watch.json").read_text()


def test_an_unsent_recovery_is_retried(lab: Lab, tmp_path: Path) -> None:
    lab.health["demo"] = False
    _pass(tmp_path, 0)
    _pass(tmp_path, 1)
    lab.health["demo"], lab.send_fails = True, True
    _pass(tmp_path, 2)
    _pass(tmp_path, 3)
    lab.send_fails = False
    _pass(tmp_path, 4)
    _pass(tmp_path, 5)
    assert [message.split(" ")[0] for _, message in lab.sent] == ["DOWN", "recovered"]


def test_one_failed_pass_neither_alerts_nor_fails_the_ping(lab: Lab, tmp_path: Path) -> None:
    """A single fetch blip must not page through healthchecks' /fail either."""
    lab.docker_down = True
    assert _pass(tmp_path, 0) == 3
    lab.docker_down = False
    assert _pass(tmp_path, 1) == 0
    assert lab.sent == [] and lab.pings == [True, True]


def test_a_blip_keeps_an_unsent_recovery_pending(lab: Lab, tmp_path: Path) -> None:
    lab.health["demo"] = False
    _pass(tmp_path, 0)
    _pass(tmp_path, 1)                                   # DOWN sent
    lab.health["demo"], lab.send_fails = True, True
    _pass(tmp_path, 2)                                   # recovery not sent
    lab.health["demo"], lab.send_fails = False, False
    _pass(tmp_path, 3)                                   # one blip, below the threshold
    lab.health["demo"] = True
    _pass(tmp_path, 4)
    assert [message.split(" ")[0] for _, message in lab.sent] == ["DOWN", "recovered"]


@pytest.mark.parametrize("entry, healthy, expected", [
    (None, False, None),
    ({"status": "healthy", "failures": 1}, False, "DOWN — x"),
    ({"status": "unhealthy", "failures": 3, "since": 0.0, "alerted": True, "reminded_at": 0.0},
     True, "recovered (down since 1970-01-01 00:00 UTC)"),
    ({"status": "unhealthy", "failures": 3, "since": 0.0, "alerted": False}, True, None),
])
def test_transition_table(entry: dict[str, Any] | None, healthy: bool, expected: str | None) -> None:
    assert watch.transition(entry, healthy, None if healthy else "x", 60.0)[1] == expected


def test_an_empty_declaration_is_not_healthy_and_keeps_state(lab: Lab, tmp_path: Path) -> None:
    lab.health["demo"] = False
    _pass(tmp_path, 0)                                   # demo: one strike recorded
    lab.health.clear()                                   # main suddenly declares nothing
    assert [_pass(tmp_path, m) for m in (1, 2)] == [3, 3]
    assert lab.pings == [True, True, False]              # /fail once the monitor is down
    assert [title for title, _ in lab.sent] == ["skynet: monitor"]
    assert '"svc/demo"' in (tmp_path / "state" / "watch.json").read_text()  # not discarded


class Clock:
    """A fake wall clock: observations and pushes take time; passes start on a schedule."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_a_pass_over_budget_rotates_and_alerts_as_a_coverage_gap(
        lab: Lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = Clock()
    lab.health = {"a": True, "b": True, "c": True}
    seen: list[str] = []

    def slow(repo: Path, service: str, context: str, revision: str | None = None) -> dict[str, Any]:
        seen.append(service)
        clock.t += 50.0
        return {"revision": REV}

    monkeypatch.setattr(deploy, "observe", slow)

    def run_at(start: float) -> int:
        clock.t = start
        return watch.run(tmp_path, context="c", state_dir=tmp_path / "state", json_output=False,
                         stdout=Out(), now=start, clock=clock)  # type: ignore[arg-type]

    run_at(0.0)
    run_at(181.0)
    assert seen == ["a", "b", "c", "a"]                  # 2 per pass; c first in pass two
    assert [title for title, _ in lab.sent] == ["skynet: monitor"]
    assert "not observed within the pass budget" in lab.sent[0][1]


def test_an_outage_alerts_within_ten_minutes_with_slow_probes(
        lab: Lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The latency budget, simulated: passes start 181 s apart (OnUnitActiveSec=3m plus
    AccuracySec), each observation takes 35 s, a push takes 15 s; the outage of the last-observed
    service starts at every 10 s offset across two intervals."""
    clock = Clock()
    lab.health = {"a": True, "b": True, "c": True}
    outage = {"at": 0.0}
    alerted: list[float] = []

    def slow(repo: Path, service: str, context: str, revision: str | None = None) -> dict[str, Any]:
        began = clock.t
        clock.t += 35.0
        if service == "c" and began >= outage["at"]:
            raise WriteError("container is not healthy", 1)
        return {"revision": REV}

    def send(title: str, message: str, *, priority: int = 0, path: Any = None) -> None:
        clock.t += 15.0
        if message.startswith("DOWN"):
            alerted.append(clock.t)

    monkeypatch.setattr(deploy, "observe", slow)
    monkeypatch.setattr(alert, "send", send)
    worst = 0.0
    for offset in range(0, 362, 10):
        state = tmp_path / f"state-{offset}"
        outage["at"], alerted[:] = 1000.0 + offset, []
        start = 0.0
        while not alerted:
            clock.t = start
            watch.run(tmp_path, context="c", state_dir=state, json_output=False,
                      stdout=Out(), now=start, clock=clock)  # type: ignore[arg-type]
            assert clock.t - start < 181.0               # a pass fits inside its interval
            start += 181.0
        worst = max(worst, alerted[0] - outage["at"])
    assert worst < 600.0


def test_an_observation_that_overruns_its_cap_fails_that_service() -> None:
    with pytest.raises(WriteError, match="observation exceeded"):
        watch._bounded(lambda: (time.sleep(2), {})[1], 0.1)


def test_a_down_alert_that_keeps_failing_to_send_escalates_via_the_dead_man(
        lab: Lab, tmp_path: Path) -> None:
    """Observation works, delivery doesn't: the independent channel must not say healthy."""
    lab.health["demo"], lab.send_fails = False, True
    for minute in range(5):
        _pass(tmp_path, minute)
    assert lab.sent == []
    assert lab.pings == [True, True, False, False, False]  # owed from pass 2; escalated from 3
    lab.send_fails = False
    _pass(tmp_path, 5)                                      # delivered at last
    assert [message[:4] for _, message in lab.sent] == ["DOWN"] and lab.pings[-1] is True


def test_an_undeliverable_recovery_escalates_too(lab: Lab, tmp_path: Path) -> None:
    lab.health["demo"] = False
    _pass(tmp_path, 0)
    _pass(tmp_path, 1)                                      # DOWN delivered
    lab.health["demo"], lab.send_fails = True, True
    for minute in range(2, 5):
        _pass(tmp_path, minute)
    assert lab.pings[-3:] == [True, False, False]


def test_healthy_services_and_a_broken_channel_stay_quiet(lab: Lab, tmp_path: Path) -> None:
    """Nothing owed, nothing to escalate: a broken credential alone isn't an outage."""
    lab.send_fails = True
    for minute in range(3):
        _pass(tmp_path, minute)
    assert lab.pings == [True, True, True]
