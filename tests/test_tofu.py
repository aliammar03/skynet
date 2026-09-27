"""`skynet tofu`: approval by hash, refusals, snapshot rollback, the state branch, and pending."""

import json
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from skynet import alert, deploy, pve, tofu, writepath
from skynet.writepath import UNAVAILABLE, Ledger, Operation, WriteError

REV = "a" * 40
NEW = "b" * 40
CT = "proxmox_virtual_environment_container"
VM = "proxmox_virtual_environment_vm"
CORE = "server-proxmox-core"


def change(address: str, kind: str, actions: list[str], **after: Any) -> dict[str, Any]:
    return {"address": address, "type": kind,
            "change": {"actions": actions, "before": {"id": "x", "noise": 1}, "after": after,
                       "after_unknown": {}, "after_sensitive": {}}}


def guest(vmid: int = 10030, *, kind: str = CT, actions: list[str] | None = None,
          node: str = CORE, **extra: Any) -> dict[str, Any]:
    """A guest change shaped like bpg's: `before` equals `after` except for the attributes the
    test changes (`cores` goes in the `cpu` block, as in the provider)."""
    if "cores" in extra:
        extra["cpu"] = [{"cores": extra.pop("cores")}]
    after = {"vm_id": vmid, "id": str(vmid), "node_name": node, **extra}
    entry = change(f'{kind}.g["{vmid}"]', kind, actions or ["update"], **after)
    entry["change"]["before"] = (None if "create" in (actions or [])
                                 else {**after, **{key: "old" for key in extra}})
    return entry


class FakeSpace:
    def __init__(self, host: "Fake") -> None:
        self.host = host
        self.root = Path("/nonexistent")

    def init(self, state: Path) -> None:
        self.host.calls.append("init")

    def plan(self) -> tuple[list[dict[str, Any]], str]:
        found = tofu.changes({"resource_changes": self.host.plan})
        return found, tofu.plan_hash(self.host.stack, found)

    def apply(self) -> None:
        self.host.calls.append("apply")
        if self.host.apply_error:
            raise WriteError("tofu apply failed", UNAVAILABLE)

    def clean(self) -> None:
        self.host.calls.append("verify")
        if self.host.unverified:
            raise WriteError(tofu.UNVERIFIED, UNAVAILABLE)
        if self.host.dirty:
            raise WriteError("post-apply plan is not clean")

    def approved(self) -> dict[str, Any] | None:
        return self.host.approved


class Fake:
    def __init__(self) -> None:
        self.stack = "proxmox-core"
        self.plan: list[dict[str, Any]] = []
        self.approved: dict[str, Any] | None = None
        self.apply_error = False
        self.dirty = False
        self.unverified = False
        self.snapshot_fail: set[int] = set()
        self.rollback_fail: set[int] = set()
        self.snapshots: set[int] = set()  # guests that really have this run's snapshot
        self.leftover: set[int] = set()  # a failed create that made one anyway
        self.stuck: set[int] = set()  # a snapshot that cannot be deleted
        self.power: dict[int, str] = {}
        self.holds: dict[str, dict[str, Any]] = {}
        self.record_error = False
        self.calls: list[Any] = []
        self.alerts: list[str] = []
        self.recorded: list[dict[str, Any] | None] = []
        self.applied: dict[str, str] = {}
        self.inputs: dict[str, str] = {"proxmox-core": REV}

    def approve(self) -> None:
        found = tofu.changes({"resource_changes": self.plan})
        self.approved = {"stack": self.stack, "hash": tofu.plan_hash(self.stack, found), "changes": []}


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Fake:
    host = Fake()

    @contextmanager
    def workspace(repo: Path, stack: tofu.Stack, revision: str, *, credentials: bool = True
                  ) -> Iterator[FakeSpace]:
        yield FakeSpace(host)

    def snapshot(action: str) -> Any:
        def run(g: pve.Guest, name: str, *power: str) -> None:
            host.calls.append((action, g.vmid, *power))
            if action == "create" and g.vmid in host.snapshot_fail:
                host.snapshots |= host.leftover & {g.vmid}
                raise WriteError("Proxmox snapshot task failed", UNAVAILABLE)
            if action == "create":
                host.snapshots.add(g.vmid)
            if action == "delete":
                if g.vmid in host.stuck:
                    raise WriteError("Proxmox snapshot task failed", UNAVAILABLE)
                host.snapshots.discard(g.vmid)
            if action == "rollback" and g.vmid in host.rollback_fail:
                raise WriteError(f"{g} did not return to running after rollback", UNAVAILABLE)
        return run

    def set_hold(repo: Path, stack: str, revision: str, reason: str, operation: str) -> None:
        host.holds[stack] = {"revision": revision, "reason": reason}

    def record(repo: Path, ledger: Ledger, stack: str, record: dict[str, Any] | None, message: str) -> None:
        if host.record_error:
            raise WriteError("state branch push failed", UNAVAILABLE)
        host.recorded.append(record)
        if record:
            host.applied[stack] = record["revision"]

    def send(title: str, message: str, priority: int = 0) -> str | None:
        host.alerts.append(title)
        return None

    monkeypatch.setattr(deploy, "fetch", lambda repo: None)
    monkeypatch.setattr(deploy, "resolve", lambda repo, ref: ref)
    monkeypatch.setattr(deploy, "merged", lambda repo, revision: True)
    monkeypatch.setattr(tofu, "workspace", workspace)
    monkeypatch.setattr(tofu, "sync_state", lambda repo, ledger, stack: b"before")
    monkeypatch.setattr(tofu, "excluded_guests", lambda root: {5001, 635, 837, 2020})
    monkeypatch.setattr(tofu, "_record", record)
    monkeypatch.setattr(tofu, "fetch_state", lambda repo: True)
    monkeypatch.setattr(tofu, "applied", lambda repo, stack: {"revision": host.applied.get(stack)})
    monkeypatch.setattr(tofu, "input_revision",
                        lambda repo, stack, ref="": host.inputs.get(stack.name))
    for action in ("create", "rollback", "delete"):
        monkeypatch.setattr(pve, action, snapshot(action))
    monkeypatch.setattr(pve, "status", lambda g: host.power.get(g.vmid, "running"))
    monkeypatch.setattr(pve, "exists", lambda g, name: g.vmid in host.snapshots)
    monkeypatch.setattr(tofu, "set_hold", set_hold)
    monkeypatch.setattr(tofu, "held", lambda repo, stack: host.holds.get(stack, {}))
    monkeypatch.setattr(alert, "send", send)
    return host


def run(fake: Fake, tmp_path: Path, stack: str = "proxmox-core") -> Operation:
    return tofu.apply(tmp_path, stack, revision=REV, ledger=Ledger(tmp_path / "state"))


# --- the normalized change -------------------------------------------------------------------

def _update(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {"address": 'ct.g["731"]', "type": CT,
            "change": {"actions": ["update"], "before": before, "after": after, "after_unknown": {}}}


def _digest(*entries: dict[str, Any]) -> str:
    return tofu.plan_hash("s", tofu.changes({"resource_changes": list(entries)}))


def test_hash_is_stable_and_follows_the_effect() -> None:
    approved = _update({"memory": 1024, "cores": 2}, {"memory": 2048, "cores": 2})
    assert _digest(approved) == _digest(_update({"memory": 1024, "cores": 2}, {"memory": 2048, "cores": 2}))
    assert _digest(approved) != _digest(_update({"memory": 1024, "cores": 2}, {"memory": 4096, "cores": 2}))
    assert tofu.plan_hash("s", []) != tofu.plan_hash("t", [])


def test_a_hand_edit_to_an_unapproved_attribute_changes_the_hash() -> None:
    approved = _update({"memory": 1024, "cores": 2}, {"memory": 2048, "cores": 2})
    # Someone sets cores=6 by hand; the same config would now also put cores back to 2.
    drifted = _update({"memory": 1024, "cores": 6}, {"memory": 2048, "cores": 2})
    assert _digest(approved) != _digest(drifted)
    (found,) = tofu.changes({"resource_changes": [drifted]})
    assert set(found["delta"]) == {"memory", "cores"}


def test_no_ops_drop_out_and_moves_and_imports_stay() -> None:
    noop = change("a.b", CT, ["no-op"])
    moved = {**change("a.c", CT, ["no-op"]), "previous_address": "a.old"}
    imported = change("a.d", CT, ["no-op"])
    imported["change"]["importing"] = {"id": "1"}
    found = tofu.changes({"resource_changes": [noop, moved, imported]})
    assert [item["address"] for item in found] == ["a.c", "a.d"]


def _secret_plan(password: str) -> dict[str, Any]:
    entry = change("a.b", VM, ["update"], password=password, name="n")
    entry["change"]["after_sensitive"] = {"password": True}
    return {"resource_changes": [entry]}


def test_sensitive_values_are_hidden_but_bound_into_the_hash() -> None:
    key = b"state-passphrase"
    digest = lambda password: tofu.plan_hash("s", tofu.changes(_secret_plan(password), key))  # noqa: E731
    (found,) = tofu.changes(_secret_plan("hunter2"), key)
    assert "hunter2" not in json.dumps(found) and found["after"]["name"] == "n"
    assert digest("hunter2") == digest("hunter2")
    assert digest("hunter2") != digest("hunter3")  # a changed secret is a changed effect


def test_sensitive_values_without_a_key_are_refused() -> None:
    with pytest.raises(WriteError, match="cannot compare safely"):
        tofu.changes(_secret_plan("hunter2"))


# --- apply -----------------------------------------------------------------------------------

def test_approved_guest_update_is_snapshotted_applied_verified_and_recorded(fake: Fake,
                                                                             tmp_path: Path) -> None:
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "success", operation.reason
    assert fake.calls == ["init", ("create", 10030), "apply", "verify", ("delete", 10030)]
    assert fake.recorded[-1] == {"revision": REV, "hash": fake.approved and fake.approved["hash"],
                                 "operation": operation.id}


def test_mismatched_hash_is_refused_before_any_change(fake: Fake, tmp_path: Path) -> None:
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    fake.plan = [guest(10030, cores=8)]  # drift, or a later change than the PR's
    operation = run(fake, tmp_path)
    assert (operation.outcome, operation.reason) == ("refused", tofu.MISMATCH)
    assert fake.calls == ["init"]


def test_changes_without_an_approved_plan_are_refused(fake: Fake, tmp_path: Path) -> None:
    fake.plan = [guest(10030, cores=4)]
    operation = run(fake, tmp_path)
    assert (operation.outcome, operation.reason) == ("refused", tofu.NO_APPROVAL)


@pytest.mark.parametrize("actions", [["delete"], ["delete", "create"], ["create", "delete"], ["forget"]])
def test_delete_replace_and_forget_are_refused_even_when_approved(fake: Fake, tmp_path: Path,
                                                                  actions: list[str]) -> None:
    fake.plan = [guest(10030, actions=actions)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "refused" and "hard checkpoint" in str(operation.reason)
    assert "apply" not in fake.calls


@pytest.mark.parametrize("entry,reason", [
    (guest(2020, kind=VM), "excluded"),
    (change("technitium_record.x", "technitium_record", ["create"]), "outside the proxmox-core"),
    (guest(10030, node="server-proxmox-network"), "not on server-proxmox-core"),
])
def test_unsafe_targets_are_refused_even_when_approved(fake: Fake, tmp_path: Path,
                                                       entry: dict[str, Any], reason: str) -> None:
    fake.plan = [entry]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "refused" and reason in str(operation.reason)
    assert "apply" not in fake.calls


def test_a_failed_snapshot_applies_nothing_and_prunes_what_it_took(fake: Fake, tmp_path: Path) -> None:
    fake.plan = [guest(10030, cores=4), guest(10031, cores=4)]
    fake.snapshot_fail = {10031}
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "refused" and operation.code == UNAVAILABLE
    assert ("delete", 10030) in fake.calls and "apply" not in fake.calls


@pytest.mark.parametrize("failure", ["apply_error", "dirty"])
def test_a_failed_guest_update_rolls_back_snapshots_and_state(fake: Fake, tmp_path: Path,
                                                              failure: str) -> None:
    setattr(fake, failure, True)
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    state = tofu.local_state(Ledger(tmp_path / "state"), "proxmox-core")
    state.parent.mkdir(parents=True)
    state.write_bytes(b"what apply wrote")
    operation = run(fake, tmp_path)
    assert (operation.outcome, operation.recovery) == ("rolled-back", "rolled-back")
    assert ("rollback", 10030, "running") in fake.calls and ("delete", 10030) in fake.calls
    assert state.read_bytes() == b"before"
    assert fake.alerts == [] and fake.recorded == []


def test_rollback_restores_each_guests_prior_power_state(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.power = {10030: "running", 10031: "stopped"}
    fake.plan = [guest(10030, cores=4), guest(10031, cores=4)]
    fake.approve()
    assert run(fake, tmp_path).outcome == "rolled-back"
    assert ("rollback", 10030, "running") in fake.calls and ("rollback", 10031, "stopped") in fake.calls


def test_one_failed_guest_rollback_still_rolls_back_the_rest(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.rollback_fail = {10031}
    fake.plan = [guest(10030, cores=4), guest(10031, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed" and "10031" in str(operation.reason)
    assert ("rollback", 10030, "running") in fake.calls  # tried after 10031 failed
    assert fake.recorded == [None]  # the partial state is recorded to git
    assert not any(c[0] == "delete" for c in fake.calls if isinstance(c, tuple))  # snapshots kept
    assert fake.holds["proxmox-core"]["revision"] == REV


def test_a_snapshot_a_failed_create_left_behind_is_cleaned_up(fake: Fake, tmp_path: Path) -> None:
    fake.snapshot_fail = fake.leftover = {10030}  # timed out, but Proxmox made it anyway
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "refused" and operation.code == UNAVAILABLE  # a clean retry
    assert ("delete", 10030) in fake.calls and fake.snapshots == set()


def test_a_snapshot_that_cannot_be_cleaned_up_holds_instead_of_piling_up(fake: Fake,
                                                                        tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.snapshot_fail = fake.leftover = fake.stuck = {10030}
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    first = tofu.pending(tmp_path, ledger=ledger)[0]
    assert first["outcome"] == "refused" and "could not be cleaned up" in first["reason"]
    assert fake.holds["proxmox-core"]["revision"] == REV
    fake.calls.clear()
    assert tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] == "held"
    assert not any(c[0] == "create" for c in fake.calls if isinstance(c, tuple))


def test_a_change_outside_the_snapshot_is_not_rolled_back(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.plan = [guest(240, pool_id="elsewhere")]  # pool membership is not in a snapshot
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed" and "no automatic inverse" in str(operation.reason)
    assert not any(c[0] == "rollback" for c in fake.calls if isinstance(c, tuple))
    assert tofu.reversible(tofu.STACKS["proxmox-core"],
                           tofu.changes({"resource_changes": [guest(240, cores=4)]}))


def test_an_unverifiable_apply_is_not_rolled_back(fake: Fake, tmp_path: Path) -> None:
    fake.unverified = True
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed" and "unverified" in str(operation.reason)
    assert not any(c[0] in ("rollback", "delete") for c in fake.calls if isinstance(c, tuple))
    assert fake.recorded == [None] and fake.holds["proxmox-core"]["revision"] == REV


def test_a_failed_create_has_no_inverse_records_true_state_and_alerts(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.plan = [guest(10030, cores=4), guest(10040, actions=["create"])]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed"
    assert fake.recorded == [None]  # the state tofu wrote, without an applied record
    assert not any(c[0] in ("rollback", "delete") for c in fake.calls if isinstance(c, tuple))  # kept
    assert fake.alerts == ["skynet: tofu/proxmox-core rollback-failed"]


def test_an_unrecorded_state_alerts(fake: Fake, tmp_path: Path) -> None:
    fake.record_error = True
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "unrecorded"
    assert fake.alerts == ["skynet: tofu/proxmox-core unrecorded"]


def test_an_empty_plan_needs_no_approval_and_records_the_revision(fake: Fake, tmp_path: Path) -> None:
    operation = run(fake, tmp_path)
    assert operation.outcome == "success"
    assert fake.calls == ["init"] and fake.recorded[-1]["revision"] == REV  # type: ignore[index]


def test_a_move_alone_is_reversible_without_a_snapshot() -> None:
    stack = tofu.STACKS["proxmox-core"]
    moved = tofu.changes({"resource_changes": [{**change("a.c", CT, ["no-op"]),
                                                "previous_address": "a.o"}]})
    assert tofu.reversible(stack, moved) and tofu.guests(stack, moved) == []


def test_a_template_update_is_not_snapshotted_and_not_reversible() -> None:
    stack = tofu.STACKS["proxmox-core"]
    found = tofu.changes({"resource_changes": [guest(9000, kind=VM, template=True)]})
    assert tofu.guests(stack, found) == [] and not tofu.reversible(stack, found)


def test_an_interrupted_apply_is_settled_with_an_alarm(fake: Fake, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    interrupted = Operation("tofu", "tofu/proxmox-core", REV,
                            context={"stack": "proxmox-core", "snapshot": "skynet-x"})
    ledger.append(interrupted.record("started"))
    fake.plan = []
    operation = run(fake, tmp_path)
    assert operation.outcome == "success"
    finals = [e for e in ledger.entries() if e.get("id") == interrupted.id and e["phase"] == "final"]
    assert finals and finals[0]["outcome"] == "rollback-failed"
    assert fake.recorded[0] is None and "skynet: tofu/proxmox-core rollback-failed" in fake.alerts


# --- pending ---------------------------------------------------------------------------------

def test_pending_skips_applied_stacks(fake: Fake, tmp_path: Path) -> None:
    fake.applied["proxmox-core"] = REV
    assert tofu.pending(tmp_path, ledger=Ledger(tmp_path / "state")) == []
    assert fake.calls == []


def test_a_refused_revision_is_held_and_alerts_once_until_main_moves(fake: Fake, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.plan = [guest(10030, cores=4)]  # no approval
    first = tofu.pending(tmp_path, ledger=ledger)
    assert first[0]["outcome"] == "refused" and fake.alerts == ["skynet: tofu/proxmox-core held"]
    fake.calls.clear()
    again = tofu.pending(tmp_path, ledger=ledger)
    assert again[0]["outcome"] == "held" and fake.calls == [] and len(fake.alerts) == 1
    fake.inputs["proxmox-core"] = NEW
    fake.approve()
    moved = tofu.pending(tmp_path, ledger=ledger)
    assert moved[0]["outcome"] == "success" and fake.applied["proxmox-core"] == NEW


@pytest.mark.parametrize("plan,outcome", [
    ([guest(10030, cores=4)], "rolled-back"),
    ([guest(10030, cores=4), guest(10040, actions=["create"])], "rollback-failed"),
])
def test_a_failed_apply_is_held_not_retried(fake: Fake, tmp_path: Path,
                                            plan: list[dict[str, Any]], outcome: str) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.apply_error = True
    fake.plan = plan
    fake.approve()
    first = tofu.pending(tmp_path, ledger=ledger)
    assert first[0]["outcome"] == outcome
    fake.calls.clear()
    for _ in range(3):
        again = tofu.pending(tmp_path, ledger=ledger)
        assert again[0]["outcome"] == "held"
    assert "apply" not in fake.calls and ("create", 10030) not in fake.calls
    # One alert: the rollback-failed alarm itself, or the hold for a rollback.
    assert len(fake.alerts) == 1


def test_an_interrupted_apply_holds_its_revision(fake: Fake, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    ledger.append(Operation("tofu", "tofu/proxmox-core", REV,
                            context={"stack": "proxmox-core", "snapshot": "skynet-x"}).record("started"))
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    results = tofu.pending(tmp_path, ledger=ledger)
    assert [r["outcome"] for r in results] == ["rollback-failed", "held"]
    assert "apply" not in fake.calls


def test_a_hold_survives_losing_local_state(fake: Fake, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.apply_error = True
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    tofu.pending(tmp_path, ledger=ledger)
    import shutil
    shutil.rmtree(tmp_path / "state")  # an ops VM rebuilt from git
    fake.calls.clear()
    assert tofu.pending(tmp_path, ledger=Ledger(tmp_path / "state"))[0]["outcome"] == "held"
    assert "apply" not in fake.calls


def test_an_unreadable_hold_holds_everything(clone: Path) -> None:
    tofu.write_branch(clone, {"proxmox-core/held.json": b"{not json"}, "corrupt")
    assert tofu.is_held(clone, "proxmox-core", REV) and tofu.is_held(clone, "proxmox-core", NEW)


def test_a_success_clears_the_hold(clone: Path) -> None:
    tofu.set_hold(clone, "s", REV, "failed", "op1")
    assert tofu.is_held(clone, "s", REV)
    tofu.record_state(clone, "s", b"v2", {"revision": NEW}, "applied")
    assert tofu.held(clone, "s") == {}


def test_settlement_waits_for_a_running_write(fake: Fake, tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    monkeypatch.setattr(Ledger, "wait", 0.05)
    running = Operation("tofu", "tofu/proxmox-core", REV, context={"stack": "proxmox-core"})
    ledger.append(running.record("started"))
    with ledger.lock():  # the apply is still running
        assert tofu.settle_interrupted(tmp_path, ledger) == []
    assert [e["id"] for e in ledger.unfinished("tofu")] == [running.id]
    assert fake.recorded == [] and fake.alerts == []


def test_a_refused_manual_run_cannot_replace_the_pending_hold(fake: Fake, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.apply_error = True
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    assert tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] == "rolled-back"
    assert fake.holds["proxmox-core"]["revision"] == REV
    other = tofu.apply(tmp_path, "proxmox-core", revision=NEW, ledger=ledger)  # manual, not main's
    assert other.outcome in ("refused", "rolled-back")
    assert fake.holds["proxmox-core"]["revision"] == REV  # the real hold stands
    fake.calls.clear()
    assert tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] == "held"
    assert "apply" not in fake.calls


def test_a_hold_git_refuses_is_kept_locally_and_alerts(fake: Fake, tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")

    def rejected(repo: Path, stack: str, revision: str, reason: str, operation: str) -> None:
        raise WriteError("state branch push failed (not a fast-forward, or origin unreachable)",
                         UNAVAILABLE)

    monkeypatch.setattr(tofu, "set_hold", rejected)
    fake.apply_error = True
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    first = tofu.pending(tmp_path, ledger=ledger)
    assert first[0]["outcome"] == "rolled-back"
    assert fake.alerts == ["skynet: tofu/proxmox-core hold not recorded in git"]
    fake.calls.clear()
    assert tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] == "held"  # the local fallback
    assert "apply" not in fake.calls


def test_a_run_meeting_an_unsettled_interruption_refuses_rather_than_closing_it(
        fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    interrupted = Operation("tofu", "tofu/proxmox-core", REV, context={"stack": "proxmox-core"})
    ledger.append(interrupted.record("started"))
    monkeypatch.setattr(tofu, "settle_interrupted", lambda repo, ledger: [])  # the lock was busy
    operation = run(fake, tmp_path)
    assert operation.outcome == "refused" and "not settled yet" in str(operation.reason)
    assert [e["id"] for e in ledger.unfinished("tofu")] == [interrupted.id]  # still open


def test_a_stack_starts_only_if_its_worst_case_fits_the_pass(fake: Fake, tmp_path: Path) -> None:
    import time
    results = tofu.pending(tmp_path, ledger=Ledger(tmp_path / "state"),
                           deadline=time.monotonic() + tofu.STACK_BUDGET - 1)
    assert results[0]["outcome"] == "deferred" and fake.calls == []


def test_too_many_guests_in_one_apply_are_refused(fake: Fake, tmp_path: Path) -> None:
    fake.plan = [guest(10030 + n, cores=4) for n in range(tofu.MAX_GUESTS + 1)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "refused" and "split it" in str(operation.reason)
    assert "apply" not in fake.calls


def test_the_unit_timeout_covers_a_full_pass_budget() -> None:
    import re
    nix = (Path(__file__).resolve().parents[1] / "nix/modules/timers.nix").read_text()
    unit = nix[nix.index("systemd.services.skynet-tofu"):nix.index("systemd.timers.skynet-tofu")]
    hours = int(re.search(r'TimeoutStartSec = "(\d+)h";', unit)[1])  # type: ignore[index]
    assert hours * 3600 == tofu.PASS_SECONDS
    assert 'skynet tofu apply --pending' in unit
    # One stack's full worst case fits in a pass, with the margin left for reporting.
    assert tofu.STACK_BUDGET <= tofu.PASS_SECONDS - tofu.PASS_MARGIN
    # Every wait is in it: all tofu commands, and per guest every task's HTTP call and last poll.
    assert tofu.GUEST_SECONDS >= 4 * (pve.TASK_SECONDS + pve.TIMEOUT) + pve.TIMEOUT
    assert tofu.STACK_BUDGET > sum(tofu.TOFU_SECONDS.values()) + tofu.MAX_GUESTS * tofu.GUEST_SECONDS


def test_an_unplannable_revision_is_retried_and_alerts_once_never_held(
        fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")

    def broken(self: FakeSpace, state: Path) -> None:
        raise WriteError("tofu init failed", UNAVAILABLE)

    monkeypatch.setattr(FakeSpace, "init", broken)
    outcomes = [tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] for _ in range(5)]
    assert outcomes == ["refused"] * 5  # every pass retries: nothing live changed
    assert fake.alerts == ["skynet: tofu/proxmox-core unavailable 3 passes running"]
    assert fake.holds == {}
    monkeypatch.undo()


def test_waiting_on_another_write_is_not_a_failure(fake: Fake, tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    monkeypatch.setattr(Ledger, "wait", 0.01)
    for _ in range(4):
        with ledger.lock():  # a manual apply or a long deploy holds the lock
            result = tofu.pending(tmp_path, ledger=ledger)[0]
        assert result["reason"] == writepath.LOCK_BUSY
    assert fake.alerts == [] and fake.holds == {}
    fake.plan = []
    assert tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] == "success"  # applied once free


def test_only_consecutive_failures_count(fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    broken = [True, True, False, True, True]

    def flaky(self: FakeSpace, state: Path) -> None:
        if broken.pop(0):
            raise WriteError("tofu init failed", UNAVAILABLE)

    monkeypatch.setattr(FakeSpace, "init", flaky)
    fake.plan = [guest(10030, cores=4)]  # no approval: the good pass is a (held) refusal
    fake.inputs["proxmox-core"] = REV
    for _ in range(2):
        tofu.pending(tmp_path, ledger=ledger)
    assert tofu._failures(ledger, "proxmox-core", REV) == 2
    tofu.pending(tmp_path, ledger=ledger)  # a real outcome resets the count
    assert tofu._failures(ledger, "proxmox-core", REV) == 0


# --- the state branch ------------------------------------------------------------------------

def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                          text=True).stdout.strip()


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True, capture_output=True)
    for key, value in (("user.name", "t"), ("user.email", "t@example.invalid")):
        _git(work, "config", key, value)
    _git(work, "commit", "-q", "--allow-empty", "-m", "init")
    _git(work, "push", "-q", "origin", "HEAD:main")
    return work


def test_state_round_trips_through_the_branch_and_rebuilds_a_lost_local_file(clone: Path,
                                                                            tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    assert not tofu.fetch_state(clone)
    tofu.record_state(clone, "proxmox-core", b"v1", {"revision": REV}, "first")
    assert tofu.branch_state(clone, "proxmox-core") == b"v1"
    assert tofu.applied(clone, "proxmox-core") == {"revision": REV}
    assert _git(clone, "status", "--porcelain") == ""  # the working tree is never touched
    assert tofu.sync_state(clone, ledger, "proxmox-core") == b"v1"  # rebuilt from git
    assert tofu.local_state(ledger, "proxmox-core").read_bytes() == b"v1"


def test_pending_local_writes_are_pushed_before_anything_else(clone: Path, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    tofu.record_state(clone, "proxmox-core", b"v1", {"revision": REV}, "first")
    assert tofu.sync_state(clone, ledger, "proxmox-core") == b"v1"  # the cache's base is v1
    tofu.local_state(ledger, "proxmox-core").write_bytes(b"v2")  # an apply that was not recorded
    assert tofu.sync_state(clone, ledger, "proxmox-core") == b"v2"
    assert tofu.branch_state(clone, "proxmox-core") == b"v2"
    assert tofu.applied(clone, "proxmox-core") == {"revision": REV}  # the record is kept


def test_a_stale_cache_never_overwrites_newer_branch_state(clone: Path, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    tofu.record_state(clone, "proxmox-core", b"v1", {"revision": REV}, "first")
    tofu.sync_state(clone, ledger, "proxmox-core")
    tofu.record_state(clone, "proxmox-core", b"v2", {"revision": NEW}, "applied elsewhere")
    assert tofu.sync_state(clone, ledger, "proxmox-core") == b"v2"  # the cache is refreshed
    assert tofu.branch_state(clone, "proxmox-core") == b"v2"
    assert tofu.local_state(ledger, "proxmox-core").read_bytes() == b"v2"


def test_a_diverged_cache_is_refused(clone: Path, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    tofu.record_state(clone, "proxmox-core", b"v1", None, "first")
    tofu.sync_state(clone, ledger, "proxmox-core")
    tofu.local_state(ledger, "proxmox-core").write_bytes(b"local")
    tofu.record_state(clone, "proxmox-core", b"remote", None, "elsewhere")
    with pytest.raises(WriteError, match="both changed"):
        tofu.sync_state(clone, ledger, "proxmox-core")
    assert tofu.branch_state(clone, "proxmox-core") == b"remote"


def test_a_first_local_state_bootstraps_the_branch(clone: Path, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    path = tofu.local_state(ledger, "proxmox-core")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"split")
    assert tofu.sync_state(clone, ledger, "proxmox-core") == b"split"
    assert tofu.branch_state(clone, "proxmox-core") == b"split"


def test_a_local_file_without_a_base_beside_branch_state_is_refused(clone: Path, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    tofu.record_state(clone, "proxmox-core", b"v1", None, "first")
    path = tofu.local_state(ledger, "proxmox-core")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"unknown provenance")
    with pytest.raises(WriteError, match="both changed"):
        tofu.sync_state(clone, ledger, "proxmox-core")


def test_settlement_never_pushes_a_stale_cache(clone: Path, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    tofu.record_state(clone, "proxmox-core", b"v1", {"revision": REV}, "first")
    tofu.sync_state(clone, ledger, "proxmox-core")
    tofu.record_state(clone, "proxmox-core", b"v2", {"revision": NEW}, "newer")
    with pytest.raises(WriteError, match="older than the branch"):
        tofu._record(clone, ledger, "proxmox-core", None, "interrupted")
    assert tofu.branch_state(clone, "proxmox-core") == b"v2"
    assert tofu.applied(clone, "proxmox-core") == {"revision": NEW}


def test_a_git_read_error_is_not_a_missing_file(clone: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tofu.record_state(clone, "s", b"v1", None, "first")
    assert tofu._blob(clone, "s/absent.json") is None  # truly missing
    real = deploy._run

    def failing(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if "ls-tree" in args:
            return subprocess.CompletedProcess(args, 128, b"", b"fatal")
        return real(args, **kwargs)

    monkeypatch.setattr(deploy, "_run", failing)
    with pytest.raises(WriteError, match="unreadable"):
        tofu.branch_state(clone, "s")


def test_a_branch_that_lost_its_state_is_refused_not_trusted(clone: Path, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    tofu.record_state(clone, "proxmox-core", b"v1", None, "first")
    tofu.sync_state(clone, ledger, "proxmox-core")
    tofu.write_branch(clone, {"proxmox-core/terraform.tfstate": None}, "someone removed it")
    with pytest.raises(WriteError, match="both changed"):
        tofu.sync_state(clone, ledger, "proxmox-core")
    assert tofu.local_state(ledger, "proxmox-core").read_bytes() == b"v1"  # never deleted


def test_an_unchanged_record_makes_no_commit(clone: Path) -> None:
    first = tofu.record_state(clone, "s", b"v1", {"revision": REV}, "first")
    assert tofu.record_state(clone, "s", b"v1", {"revision": REV}, "again") == first


def test_the_state_push_is_fast_forward_only(clone: Path, tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    tofu.record_state(clone, "s", b"v1", None, "first")
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", "-b", "tofu-state", str(tmp_path / "origin.git"), str(other)],
                   check=True, capture_output=True)
    for key, value in (("user.name", "t"), ("user.email", "t@example.invalid")):
        _git(other, "config", key, value)
    _git(other, "commit", "-q", "--allow-empty", "-m", "elsewhere")
    _git(other, "push", "-q", "origin", "tofu-state")
    monkeypatch.setattr(tofu, "fetch_state", lambda repo: True)  # keep the stale parent
    with pytest.raises(WriteError, match="not a fast-forward"):
        tofu.record_state(clone, "s", b"v2", None, "stale")


# --- snapshots -------------------------------------------------------------------------------

def test_a_vm_snapshot_keeps_ram_and_a_failed_task_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, Any]] = []
    status = {"status": "stopped", "exitstatus": "OK"}

    def call(node: str, method: str, path: str, fields: dict[str, str] | None = None) -> Any:
        calls.append((method, path, fields))
        return status if path.endswith("/status") else "UPID:node:1"

    monkeypatch.setattr(pve, "_call", call)
    pve.create(pve.Guest(CORE, "qemu", 10015), "skynet-x")
    assert calls[0][2] and calls[0][2]["vmstate"] == "1"
    status["exitstatus"] = "snapshot failed"
    with pytest.raises(WriteError, match="task failed"):
        pve.rollback(pve.Guest(CORE, "lxc", 10030), "skynet-x", "stopped")


def test_a_running_container_is_restarted_and_observed_running(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, Any]] = []
    states = iter(["stopped", "running"])  # still starting on the first look

    def call(node: str, method: str, path: str, fields: dict[str, str] | None = None) -> Any:
        calls.append((method, path, fields))
        if path.endswith("/tasks/UPID%3Anode%3A1/status"):
            return {"status": "stopped", "exitstatus": "OK"}
        if path.endswith("/status/current"):
            return {"status": next(states)}
        return "UPID:node:1"

    monkeypatch.setattr(pve, "_call", call)
    monkeypatch.setattr(pve, "POLL_SECONDS", 0)
    pve.rollback(pve.Guest(CORE, "lxc", 10030), "skynet-x", "running")
    assert calls[0][1].endswith("/snapshot/skynet-x/rollback") and calls[0][2] == {"start": "1"}
    assert [c for c in calls if c[1].endswith("/status/current")] and next(states, None) is None


def test_a_container_that_does_not_come_back_fails_the_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    def call(node: str, method: str, path: str, fields: dict[str, str] | None = None) -> Any:
        if "/tasks/" in path:
            return {"status": "stopped", "exitstatus": "OK"}
        if path.endswith("/status/current"):
            return {"status": "stopped"}
        return "UPID:node:1"

    monkeypatch.setattr(pve, "_call", call)
    monkeypatch.setattr(pve, "POLL_SECONDS", 0)
    monkeypatch.setattr(pve, "TASK_SECONDS", 0)
    with pytest.raises(WriteError, match="did not return to running"):
        pve.rollback(pve.Guest(CORE, "lxc", 10030), "skynet-x", "running")


def test_missing_operate_credentials_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SKYNET_SECRETS_DIR", str(tmp_path))
    with pytest.raises(WriteError, match="operate credentials unavailable"):
        pve.create(pve.Guest(CORE, "lxc", 10030), "skynet-x")


@pytest.mark.parametrize("stack,file,body,pinned", [
    ("proxmox-core", "proxmox-core.env",
     "PVE_HOST=10.10.50.11\nPVE_TOKEN_OPERATE=t\nPVE_CACERT=/pin/core.crt\n", "/pin/core.crt"),
    ("technitium-dns", "technitium.env",
     "TECH_HOST=10.10.70.50\nTECH_TOKEN=t\nTECH_CACERT=/pin/tech.crt\n", "/pin/tech.crt"),
])
def test_self_signed_stacks_trust_exactly_their_pinned_ca(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                                                         stack: str, file: str, body: str,
                                                         pinned: str) -> None:
    monkeypatch.setenv("SKYNET_SECRETS_DIR", str(tmp_path))
    (tmp_path / file).write_text(body)
    assert tofu.STACKS[stack].credentials()["SSL_CERT_FILE"] == pinned


def test_unknown_stack_is_refused_and_recorded(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    operation = tofu.apply(tmp_path, "proxmox-network", ledger=ledger)
    assert (operation.outcome, operation.reason) == ("refused", "unknown stack")
    assert ledger.entries()[-1]["outcome"] == "refused"


def test_registry_matches_the_committed_stacks() -> None:
    root = Path(__file__).resolve().parents[1] / "tofu"
    assert {p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")} == set(tofu.STACKS)
    assert json.dumps(sorted(tofu.STACKS))  # every stack is addressable by name


def test_writepath_line_names_the_stack() -> None:
    assert writepath.line({"target": "tofu/proxmox-core", "source": REV, "outcome": "held"}).startswith(
        "tofu/proxmox-core@aaaaaaaaaaaa: held")
