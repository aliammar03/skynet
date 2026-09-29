"""`skynet tofu`: approval by hash, refusals, config-restore rollback, the state branch, and pending."""

import json
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from skynet import alert, deploy, pve, tofu, writepath
from skynet.writepath import UNAVAILABLE, Ledger, Operation, WriteError

real_persist = tofu.persist_pending
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
        self.host.held_at_apply = dict(self.host.holds)
        if self.host.apply_error:
            raise WriteError("tofu apply failed", UNAVAILABLE)
        if self.host.apply_lost:
            raise WriteError(tofu.INDETERMINATE, UNAVAILABLE)

    def clean(self) -> list[dict[str, Any]]:
        self.host.calls.append("verify")
        if self.host.unverified:
            raise WriteError(tofu.UNVERIFIED, UNAVAILABLE)
        if self.host.dirty:  # the approved change did not land: the re-plan still wants it
            return tofu.changes({"resource_changes": self.host.plan})
        return tofu.changes({"resource_changes": self.host.drift})

    def approved(self) -> dict[str, Any] | None:
        return self.host.approved


class Fake:
    def __init__(self) -> None:
        self.stack = "proxmox-core"
        self.plan: list[dict[str, Any]] = []
        self.approved: dict[str, Any] | None = None
        self.apply_error = False
        self.dirty = False
        self.drift: list[dict[str, Any]] = []  # a post-apply plan dirty elsewhere
        self.left_pending: set[int] = set()  # a restore that leaves changes pending
        self.held_at_apply: dict[str, Any] = {}
        self.apply_lost = False
        self.unverified = False
        self.snapshot_fail: set[int] = set()
        self.restore_fail: set[int] = set()
        self.snapshots: set[int] = set()  # guests that really have this run's snapshot
        self.leftover: set[int] = set()  # a failed create that made one anyway
        self.stuck: set[int] = set()  # a snapshot that cannot be deleted
        self.rolled: set[int] = set()
        self.config_drift: set[int] = set()  # a rollback that does not bring the config back
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
        def run(g: pve.Guest, name: str, *, excluded: Any) -> None:
            assert g.vmid not in excluded
            host.calls.append((action, g.vmid))
            if action == "create" and g.vmid in host.snapshot_fail:
                host.snapshots |= host.leftover & {g.vmid}
                raise WriteError("Proxmox task failed", UNAVAILABLE)
            if action == "create":
                host.snapshots.add(g.vmid)
            if action == "delete":
                if g.vmid in host.stuck:
                    raise WriteError("Proxmox task failed", UNAVAILABLE)
                host.snapshots.discard(g.vmid)
        return run

    def restore(g: pve.Guest, saved: dict[str, Any], power: str, *, excluded: Any) -> None:
        assert g.vmid not in excluded
        host.calls.append(("restore", g.vmid, power))
        if g.vmid in host.restore_fail:
            raise WriteError(f"{g} did not return to {power}", UNAVAILABLE)
        host.rolled.add(g.vmid)

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
    for action in ("create", "delete"):
        monkeypatch.setattr(pve, action, snapshot(action))
    monkeypatch.setattr(pve, "restore", restore)
    monkeypatch.setattr(pve, "pending",
                        lambda g: ["cores"] if g.vmid in host.rolled & host.left_pending else [])
    monkeypatch.setattr(tofu, "main_excluded", lambda repo: frozenset({5001, 635, 837, 2020}))
    monkeypatch.setattr(pve, "status", lambda g: host.power.get(g.vmid, "running"))
    monkeypatch.setattr(pve, "exists", lambda g, name: g.vmid in host.snapshots)
    monkeypatch.setattr(tofu, "persist_pending", lambda repo, ledger: [])  # own tests below

    def config(g: pve.Guest) -> dict[str, Any]:
        drifted = g.vmid in host.rolled and g.vmid in host.config_drift
        return {"memory": 1024, "cores": 4 if drifted else 2, "pool": "outside-the-snapshot"}

    monkeypatch.setattr(pve, "config", config)
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


def test_a_fully_known_nested_block_is_not_a_change_but_a_nested_unknown_is() -> None:
    entry = _update({"cores": 2, "disk": [{"size": 8}]}, {"cores": 4, "disk": [{"size": 8}]})
    entry["change"]["after_unknown"] = {"disk": [{}], "network_interface": [{}, {}], "mount_point": []}
    (found,) = tofu.changes({"resource_changes": [entry]})
    assert set(found["delta"]) == {"cores"}  # rollback-covered, so reversible
    entry["change"]["after_unknown"]["disk"] = [{"path": True}]
    (found,) = tofu.changes({"resource_changes": [entry]})
    assert found["delta"]["disk"] == {"after": tofu.UNKNOWN}


def _agent(ips: list[str], after_ips: list[str] | None = None) -> dict[str, Any]:
    """docker-dmz: the guest agent's IP/MAC lists churn as Docker adds and removes networks."""
    base = {"tags": ["a"], "ipv4_addresses": [ips], "mac_addresses": [f"mac-{ip}" for ip in ips]}
    after = {**base, "tags": ["a", "b"]}
    if after_ips is not None:
        after |= {"ipv4_addresses": [after_ips]}
    return _update(base, after)


def test_volatile_refresh_values_stay_out_of_the_hash() -> None:
    at_approval = _agent(["10.10.100.15", "172.17.0.1"])
    at_merge = _agent(["10.10.100.15", "172.17.0.1", "172.30.0.1"])  # a new compose network
    assert _digest(at_approval) == _digest(at_merge)
    (found,) = tofu.changes({"resource_changes": [at_merge]})
    assert set(found["delta"]) == {"tags"}
    # A computed attribute the plan cannot know is bound by name, never by its refreshed value.
    unknown = [_agent(ips) for ips in (["1"], ["2"])]
    for entry in unknown:
        entry["change"]["after_unknown"] = {"ipv4_addresses": True}
    assert _digest(unknown[0]) == _digest(unknown[1])
    assert _digest(unknown[0]) != _digest(at_approval)


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
    assert ("restore", 10030, "running") in fake.calls and ("delete", 10030) in fake.calls
    assert state.read_bytes() == b"before"
    assert fake.alerts == [] and fake.recorded == []


def test_rollback_restores_each_guests_prior_power_state(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.power = {10030: "running", 10031: "stopped"}
    fake.plan = [guest(10030, cores=4), guest(10031, cores=4)]
    fake.approve()
    assert run(fake, tmp_path).outcome == "rolled-back"
    assert ("restore", 10030, "running") in fake.calls and ("restore", 10031, "stopped") in fake.calls


def test_a_rollback_whose_config_does_not_come_back_is_not_trusted(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.config_drift = {10030}  # RESTORE_COVERS was wrong about something this change touched
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed"
    import re
    # Key names only, never values: exactly "cores", then the kept-snapshot note.
    assert re.search(r"config differs after rollback: cores \(snapshots skynet-[0-9a-f]+ kept\)$",
                     str(operation.reason))
    assert not any(c[0] == "delete" for c in fake.calls if isinstance(c, tuple))  # snapshot kept
    assert fake.holds["proxmox-core"]["revision"] == REV


def test_config_comparison_ignores_only_what_a_snapshot_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = {"memory": 1024, "digest": "abc", "parent": "skynet-x", "lock": "snapshot"}
    monkeypatch.setattr(pve, "_call", lambda node, method, path, fields=None: dict(raw))
    assert pve.config(pve.Guest(CORE, "lxc", 10030)) == {"memory": 1024}
    assert tofu._config_diff({"memory": 1024}, {"memory": 2048, "swap": 512}) == ["memory", "swap"]


def test_one_failed_guest_rollback_still_rolls_back_the_rest(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.restore_fail = {10031}
    fake.plan = [guest(10030, cores=4), guest(10031, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed" and "10031" in str(operation.reason)
    assert ("restore", 10030, "running") in fake.calls  # tried after 10031 failed
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
    assert not any(c[0] == "restore" for c in fake.calls if isinstance(c, tuple))
    assert tofu.reversible(tofu.STACKS["proxmox-core"],
                           tofu.changes({"resource_changes": [guest(240, cores=4)]}))


def test_a_dirty_re_plan_outside_the_approved_change_is_held_not_rolled_back(fake: Fake,
                                                                            tmp_path: Path) -> None:
    fake.plan = [guest(10030, cores=4)]
    fake.drift = [guest(10031, memory=4096)]  # unrelated drift, or a provider's perpetual diff
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed" and "dirty elsewhere" in str(operation.reason)
    assert not any(c[0] in ("restore", "delete") for c in fake.calls if isinstance(c, tuple))
    assert fake.recorded == [None] and fake.holds["proxmox-core"]["revision"] == REV
    assert fake.alerts == ["skynet: tofu/proxmox-core rollback-failed"]


@pytest.mark.parametrize("remaining,landed", [
    ([guest(10030, cores=4)], False),                  # the same attribute: it did not land
    ([guest(10030, memory=4096)], True),               # another attribute of the same guest
    ([guest(10031, cores=4)], True),                   # another guest
    ([guest(10030, actions=["create"])], False),       # the whole resource again
])
def test_overlap_is_by_address_and_attribute(remaining: list[dict[str, Any]], landed: bool) -> None:
    approved = tofu.changes({"resource_changes": [guest(10030, cores=4)]})
    assert tofu.overlaps(approved, tofu.changes({"resource_changes": remaining})) is not landed


def test_a_restore_that_leaves_changes_pending_is_not_trusted(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.left_pending = {10030}
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed" and "still pending after rollback: cores" in str(
        operation.reason)
    assert not any(c[0] == "delete" for c in fake.calls if isinstance(c, tuple))  # snapshot kept


def test_a_guest_with_pending_changes_before_the_apply_is_refused(
        fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pve, "pending", lambda g: ["memory"] if g.vmid == 10031 else [])
    fake.plan = [guest(10030, cores=4), guest(10031, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "refused" and "pending config changes" in str(operation.reason)
    assert operation.code == writepath.USAGE and "apply" not in fake.calls
    assert ("delete", 10030) in fake.calls  # the first guest's snapshot is pruned


def test_an_unverifiable_apply_is_not_rolled_back(fake: Fake, tmp_path: Path) -> None:
    fake.unverified = True
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed" and "unverified" in str(operation.reason)
    assert not any(c[0] in ("restore", "delete") for c in fake.calls if isinstance(c, tuple))
    assert fake.recorded == [None] and fake.holds["proxmox-core"]["revision"] == REV


def test_a_verification_that_cannot_run_is_unverified_not_rolled_back(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def timed_out(workdir: Path, env: dict[str, str], *args: str, timeout: float) -> Any:
        raise WriteError("tofu timed out", UNAVAILABLE)  # what deploy._run raises on a timeout

    monkeypatch.setattr(tofu, "_tofu", timed_out)
    space = tofu.Workspace(tofu.STACKS["proxmox-core"], tmp_path, {})
    with pytest.raises(WriteError) as raised:
        space.clean()
    assert raised.value.reason == tofu.UNVERIFIED


def test_the_revision_is_held_before_it_executes(fake: Fake, tmp_path: Path) -> None:
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    assert run(fake, tmp_path).outcome == "success"
    assert fake.held_at_apply["proxmox-core"]["revision"] == REV


def test_a_crash_after_the_final_record_cannot_retry_the_revision(
        fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.apply_error = True
    fake.plan = [guest(10030, cores=4)]
    fake.approve()

    def crash(*args: Any, **kwargs: Any) -> None:
        raise SystemExit("killed between the final record and the hold")

    real_hold = tofu._hold
    monkeypatch.setattr(tofu, "_hold", crash)
    with pytest.raises(SystemExit):
        tofu.pending(tmp_path, ledger=ledger)
    monkeypatch.setattr(tofu, "_hold", real_hold)  # the restarted process
    fake.calls.clear()
    assert tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] == "held"  # the pre-apply hold
    assert "apply" not in fake.calls


def test_a_failed_snapshot_cleanup_after_success_is_queued_retried_and_alerted(
        fake: Fake, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.stuck = {10030}
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "success"
    assert fake.alerts == ["skynet: tofu/proxmox-core snapshot cleanup failed"]
    assert tofu._facts(ledger)["_cleanup"][0]["vmid"] == 10030
    fake.stuck.clear()
    fake.applied["proxmox-core"] = REV  # nothing left to apply: the queue alone is retried
    results = tofu.pending(tmp_path, ledger=ledger)
    assert results[0]["target"].startswith("cleanup/") and fake.snapshots == set()
    assert tofu._facts(ledger)["_cleanup"] == [] and len(fake.alerts) == 1


def test_a_failed_snapshot_cleanup_after_rollback_is_queued(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.stuck = {10030}
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    assert run(fake, tmp_path).outcome == "rolled-back"
    assert tofu._facts(Ledger(tmp_path / "state"))["_cleanup"][0]["vmid"] == 10030


@pytest.mark.parametrize("where", ["main", "state"])
def test_a_pass_that_cannot_reach_git_alerts_after_three(
        fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, where: str) -> None:
    import io

    def broken(repo: Path) -> Any:
        raise WriteError(f"git fetch of {where} failed", UNAVAILABLE)

    monkeypatch.setattr(deploy if where == "main" else tofu,
                        "fetch" if where == "main" else "fetch_state", broken)
    codes = [tofu.run_apply(tmp_path, None, revision=None, pending_all=True,
                            state_dir_=tmp_path / "state", json_output=False, stdout=io.StringIO())
             for _ in range(5)]
    assert codes == [0] * 5
    assert fake.alerts == ["skynet: tofu passes failing (3 in a row)"]


def test_an_apply_that_times_out_is_indeterminate_not_rolled_back(fake: Fake, tmp_path: Path) -> None:
    fake.apply_lost = True
    fake.plan = [guest(10030, cores=4)]  # reversible, if the apply had finished
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed" and "did not finish" in str(operation.reason)
    assert not any(c[0] in ("restore", "delete") for c in fake.calls if isinstance(c, tuple))
    assert fake.holds["proxmox-core"]["revision"] == REV


def test_workspace_apply_timeout_is_indeterminate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def timed_out(workdir: Path, env: dict[str, str], *args: str, timeout: float) -> Any:
        raise WriteError("tofu timed out", UNAVAILABLE)

    monkeypatch.setattr(tofu, "_tofu", timed_out)
    with pytest.raises(WriteError) as raised:
        tofu.Workspace(tofu.STACKS["proxmox-core"], tmp_path, {}).apply()
    assert raised.value.reason == tofu.INDETERMINATE


def test_a_timeout_kills_the_whole_tofu_process_tree(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import os
    import time
    marker = tmp_path / "late-write"
    script = tmp_path / "fake-tofu"
    # A "provider" child that would write late, under a parent that hangs.
    script.write_text(f"#!/bin/sh\n(sleep 1; touch {marker}) &\nsleep 30\n")
    script.chmod(0o755)
    monkeypatch.setenv("SKYNET_TOFU", str(script))
    with pytest.raises(WriteError, match="timed out"):
        tofu._tofu(tmp_path, {"PATH": os.environ["PATH"]}, "apply", timeout=0.3)
    time.sleep(1.5)
    assert not marker.exists()  # the child died with its group


def test_a_failed_create_has_no_inverse_records_true_state_and_alerts(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.plan = [guest(10030, cores=4), guest(10040, actions=["create"])]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed"
    assert fake.recorded == [None]  # the state tofu wrote, without an applied record
    assert not any(c[0] in ("restore", "delete") for c in fake.calls if isinstance(c, tuple))  # kept
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
    # Settlement held REV, so the same revision is refused under the lock...
    assert (operation.outcome, operation.reason) == ("refused", tofu.HELD)
    # ...unless a supervised recovery says so explicitly.
    supervised = tofu.apply(tmp_path, "proxmox-core", revision=REV, ledger=ledger, ignore_hold=True)
    assert supervised.outcome == "success"
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


def test_a_success_clears_only_its_own_revisions_hold(clone: Path) -> None:
    tofu.set_hold(clone, "s", REV, "failed", "op1")
    assert tofu.is_held(clone, "s", REV)
    tofu.record_state(clone, "s", b"v2", {"revision": NEW}, "manual apply of another revision")
    assert tofu.held(clone, "s")["revision"] == REV  # the pending revision stays held
    tofu.record_state(clone, "s", b"v3", {"revision": REV}, "applied")
    assert tofu.held(clone, "s") == {}


def test_settlement_waits_for_a_running_write(fake: Fake, tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    monkeypatch.setattr(Ledger, "wait", 0.05)
    running = Operation("tofu", "tofu/proxmox-core", REV, context={"stack": "proxmox-core"})
    ledger.append(running.record("started"))
    with ledger.lock(tofu.LOCK):  # the apply is still running
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


def test_a_pre_apply_hold_git_refuses_applies_nothing_and_retries(
        fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")

    def rejected(repo: Path, stack: str, revision: str, reason: str, operation: str) -> None:
        raise WriteError("state branch push failed (not a fast-forward, or origin unreachable)",
                         UNAVAILABLE)

    monkeypatch.setattr(tofu, "set_hold", rejected)
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    first = tofu.pending(tmp_path, ledger=ledger)[0]
    assert first["outcome"] == "refused" and "pre-apply hold" in first["reason"]
    assert "apply" not in fake.calls and ("delete", 10030) in fake.calls  # snapshot pruned
    assert not tofu.is_held(tmp_path, "proxmox-core", REV, ledger)  # retried next pass


def test_a_failed_hold_update_after_the_pre_apply_hold_still_holds(
        fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    writes: list[str] = []

    def once(repo: Path, stack: str, revision: str, reason: str, operation: str) -> None:
        writes.append(reason)
        if len(writes) > 1:  # the post-failure update is rejected
            raise WriteError("state branch push failed (not a fast-forward, or origin unreachable)",
                             UNAVAILABLE)
        fake.holds[stack] = {"revision": revision, "reason": reason}

    monkeypatch.setattr(tofu, "set_hold", once)
    fake.apply_error = True
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    assert tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] == "rolled-back"
    assert fake.alerts == ["skynet: tofu/proxmox-core held"]  # no "not recorded" alarm: it is
    fake.calls.clear()
    assert tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] == "held"
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


def test_the_tofu_timer_is_not_enabled_before_its_drills() -> None:
    """Flipping this is the P15 promotion: it lands with the recorded LXC and VM rollback drills."""
    nix = (Path(__file__).resolve().parents[1] / "nix/modules/timers.nix").read_text()
    timer = nix[nix.index("systemd.timers.skynet-tofu"):]
    timer = timer[:timer.index("};\n  };") if "};\n  };" in timer else len(timer)]
    assert "wantedBy = [ ];" in timer and '"timers.target"' not in timer


def test_a_held_revision_is_refused_under_the_lock(fake: Fake, tmp_path: Path) -> None:
    fake.holds["proxmox-core"] = {"revision": REV}
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    operation = run(fake, tmp_path)  # a direct apply, not through pending
    assert (operation.outcome, operation.reason) == ("refused", tofu.HELD)
    assert fake.calls == []


def test_overlapping_pending_passes_apply_a_revision_once(fake: Fake, tmp_path: Path,
                                                           monkeypatch: pytest.MonkeyPatch) -> None:
    import threading
    ledger = Ledger(tmp_path / "state")
    fake.apply_error = True
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    real = tofu.is_held
    outside = threading.Barrier(2)
    seen = {"n": 0}
    lock = threading.Lock()

    def both_see_no_hold(repo: Path, name: str, revision: str, ledger_: Any = None) -> bool:
        with lock:
            seen["n"] += 1
            first_two = seen["n"] <= 2
        if first_two:  # pending's unlocked checks: both callers pass before either applies
            outside.wait(timeout=5)
            return False
        return real(repo, name, revision, ledger_)

    monkeypatch.setattr(tofu, "is_held", both_see_no_hold)
    outcomes: list[str] = []
    threads = [threading.Thread(target=lambda: outcomes.append(
        tofu.pending(tmp_path, ledger=ledger)[0]["outcome"])) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert fake.calls.count("apply") == 1
    assert sorted(outcomes) == ["refused", "rolled-back"]


def test_state_is_persisted_after_git_recovers_without_rerunning_the_apply(
        fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.record_error = True  # git is down when the verified apply tries to record
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    assert run(fake, tmp_path).outcome == "unrecorded"
    fake.record_error = False  # git is back
    monkeypatch.setattr(tofu, "persist_pending", real_persist)
    fake.calls.clear()
    results = tofu.pending(tmp_path, ledger=ledger)
    assert results[0]["reason"] == "unpushed state persisted to tofu-state"
    assert fake.recorded[-1] == {"revision": REV, "hash": fake.approved and fake.approved["hash"],
                                 "operation": fake.recorded[-1]["operation"]}  # type: ignore[index]
    assert "apply" not in fake.calls  # infrastructure is never rerun to retry a push
    assert tofu._facts(ledger).get("_unrecorded") == {}


def test_partial_failure_state_is_persisted_while_the_revision_stays_held(
        fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.apply_error = fake.record_error = True
    fake.plan = [guest(10030, cores=4), guest(10040, actions=["create"])]
    fake.approve()
    path = tofu.local_state(ledger, "proxmox-core")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"what the partial apply wrote")  # no base: a first, unpushed state
    assert run(fake, tmp_path).outcome == "rollback-failed"
    fake.record_error = False
    monkeypatch.setattr(tofu, "persist_pending", real_persist)
    fake.calls.clear()
    results = tofu.pending(tmp_path, ledger=ledger)
    assert [r["outcome"] for r in results] == ["success", "held"]
    assert fake.recorded[-1] is None and "apply" not in fake.calls


def test_a_crash_after_a_remote_snapshot_leaves_an_intent_the_next_pass_cleans(
        fake: Fake, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    real_create = pve.create

    def crash(g: pve.Guest, name: str, *, excluded: Any) -> None:
        fake.snapshots.add(g.vmid)  # Proxmox made it...
        raise SystemExit("...and the process died before any record")

    monkeypatch.setattr(pve, "create", crash)
    with pytest.raises(SystemExit):
        tofu.pending(tmp_path, ledger=ledger)
    assert ledger.unfinished("tofu") == [] and fake.holds == {}
    assert [i.get("intent") for i in tofu._facts(ledger)["_cleanup"]] != []
    monkeypatch.setattr(pve, "create", real_create)
    results = tofu.retry_cleanup(tmp_path, ledger)
    assert results and results[0]["outcome"] == "success" and 10030 not in fake.snapshots
    assert tofu._facts(ledger)["_cleanup"] == []


def test_an_intent_whose_operation_was_recorded_is_left_to_its_record(fake: Fake, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.apply_lost = True  # snapshots kept for the operator
    fake.plan = [guest(10030, cores=4)]
    fake.approve()
    run(fake, tmp_path)
    assert tofu.retry_cleanup(tmp_path, ledger) == [] and 10030 in fake.snapshots  # kept, not "cleaned"


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
        with ledger.lock(tofu.LOCK):  # a manual apply holds the tofu lock
            result = tofu.pending(tmp_path, ledger=ledger)[0]
        assert result["reason"] == writepath.LOCK_BUSY
    assert fake.alerts == [] and fake.holds == {}
    fake.plan = []
    assert tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] == "success"  # applied once free


def test_tofu_and_the_service_write_paths_never_wait_on_each_other(fake: Fake, tmp_path: Path,
                                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    monkeypatch.setattr(Ledger, "wait", 0.01)
    with ledger.lock():  # a deploy (or the revert auto-merge) is running
        assert tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] == "success"
    with ledger.lock(tofu.LOCK):  # an hours-long apply is running
        assert not ledger.busy()  # watch and automerge see no service write
        with ledger.lock():
            pass  # a deploy takes its lock at once


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


def test_an_unreadable_hold_alerts_once_and_a_supervised_success_clears_it(
        fake: Fake, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.holds["proxmox-core"] = {"revision": "*", "reason": "unreadable hold"}
    for _ in range(3):
        result = tofu.pending(tmp_path, ledger=ledger)[0]
        assert result["outcome"] == "held" and "unreadable" in result["reason"]
    assert fake.alerts == ["skynet: tofu/proxmox-core held"]


def test_a_success_clears_an_unreadable_hold(clone: Path) -> None:
    tofu.write_branch(clone, {"s/held.json": b"{not json"}, "corrupt")
    tofu.record_state(clone, "s", b"v1", {"revision": REV}, "supervised --ignore-hold success")
    assert tofu.held(clone, "s") == {}


def test_a_pre_apply_hold_a_crash_left_before_any_record_alerts_once(
        fake: Fake, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    fake.holds["proxmox-core"] = {"revision": REV, "reason": tofu.PREHOLD, "operation": "0badc0ffee00"}
    first = tofu.pending(tmp_path, ledger=ledger)[0]
    assert first["outcome"] == "held" and "no operation record" in first["reason"]
    tofu.pending(tmp_path, ledger=ledger)
    assert fake.alerts == ["skynet: tofu/proxmox-core held"] and "apply" not in fake.calls


def test_a_queued_cleanup_naming_an_excluded_guest_never_reaches_proxmox(
        fake: Fake, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    tofu._save_facts(ledger, {"_cleanup": [
        {"node": CORE, "kind": "qemu", "vmid": 2020, "snapshot": "skynet-x"},
        {"node": CORE, "kind": "lxc", "vmid": 10030, "snapshot": "skynet-x"}]})
    fake.snapshots = {2020, 10030}
    results = tofu.retry_cleanup(tmp_path, ledger)
    assert [r["outcome"] for r in results] == ["refused", "success"]
    assert fake.calls == [("delete", 10030)] and 2020 in fake.snapshots
    assert tofu._facts(ledger)["_cleanup"] == []  # dropped, not retried forever
    assert fake.alerts == ["skynet: tofu cleanup refused for excluded qemu/2020@server-proxmox-core"]


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


def test_a_state_commit_is_a_compare_and_swap(clone: Path, tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    tofu.record_state(clone, "proxmox-core", b"v1", {"revision": REV}, "first")
    tofu.sync_state(clone, ledger, "proxmox-core")
    tofu.local_state(ledger, "proxmox-core").write_bytes(b"v2")  # pending on top of v1
    real = tofu.classify

    def race(ledger_: Ledger, stack: str, remote: bytes | None) -> str:
        kind = real(ledger_, stack, remote)  # passes: v2 on top of v1 ...
        tofu.record_state(clone, stack, b"v3", {"revision": NEW}, "... then elsewhere publishes v3")
        return kind

    monkeypatch.setattr(tofu, "classify", race)
    with pytest.raises(WriteError, match="moved since it was checked"):
        tofu._record(clone, ledger, "proxmox-core", None, "stale parent")
    assert tofu.branch_state(clone, "proxmox-core") == b"v3"
    assert tofu.applied(clone, "proxmox-core") == {"revision": NEW}


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


def test_a_quiet_pass_fetches_the_state_branch_once(clone: Path, tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    for name in tofu.STACKS:
        tofu.record_state(clone, name, b"v1", {"revision": REV}, "applied")
        tofu.sync_state(clone, ledger, name)
    remote: list[str] = []
    real = deploy._git

    def counted(repo: Path, *args: str, reason: str = "") -> str:
        if args[0] in ("ls-remote", "fetch", "push"):
            remote.append(args[0])
        return real(repo, *args, reason=reason)

    monkeypatch.setattr(deploy, "_git", counted)
    tofu.pending(clone, ledger=ledger)  # no tofu/ on main: nothing to apply
    assert remote == ["ls-remote", "fetch"]


def test_a_record_fetches_once_and_still_refuses_a_moved_branch(clone: Path, tmp_path: Path,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")
    tofu.record_state(clone, "proxmox-core", b"v1", None, "first")
    tofu.sync_state(clone, ledger, "proxmox-core")
    tofu.local_state(ledger, "proxmox-core").write_bytes(b"v2")
    remote: list[str] = []
    real = deploy._git

    def counted(repo: Path, *args: str, reason: str = "") -> str:
        if args[0] in ("ls-remote", "fetch"):
            remote.append(args[0])
        return real(repo, *args, reason=reason)

    monkeypatch.setattr(deploy, "_git", counted)
    tofu._record(clone, ledger, "proxmox-core", None, "pending")
    assert remote == ["ls-remote", "fetch"] and tofu.branch_state(clone, "proxmox-core") == b"v2"


# --- snapshots -------------------------------------------------------------------------------

class FakeProxmox:
    """A Proxmox API for pve's own tests: one guest's config, pending list, and power state."""

    def __init__(self, config: dict[str, Any], power: str = "running",
                 pending_after_put: bool = False) -> None:
        self.config, self.power, self.pending_after_put = dict(config), power, pending_after_put
        self.pending: list[dict[str, Any]] = []
        self.calls: list[tuple[str, str, Any]] = []
        self.exitstatus = "OK"

    def __call__(self, node: str, method: str, path: str, fields: dict[str, str] | None = None) -> Any:
        self.calls.append((method, path.split("/10030/")[-1] if "/10030/" in path else path, fields))
        if "/tasks/" in path:
            return {"status": "stopped", "exitstatus": self.exitstatus}
        if path.endswith("/config") and method == "GET":
            return {**self.config, "digest": "d1"}
        if path.endswith("/config") and method == "PUT":
            assert fields is not None
            for key in fields.get("delete", "").split(",") if fields.get("delete") else []:
                self.config.pop(key)
            self.config.update({k: v for k, v in fields.items() if k not in ("delete", "digest")})
            if self.pending_after_put:
                self.pending = [{"key": "cores", "value": 4, "pending": 2}]
            return None
        if path.endswith("/pending"):
            return self.pending
        if path.endswith("/status/current"):
            return {"status": self.power}
        if path.endswith("/status/reboot"):
            self.pending = []
            return "UPID:node:1"
        if path.endswith("/status/start"):
            self.power = "running"
        if path.endswith("/status/shutdown"):
            self.power = "stopped"
        return "UPID:node:1"


LXC = pve.Guest(CORE, "lxc", 10030)


def test_a_snapshot_is_disk_only_and_a_failed_task_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeProxmox({})
    monkeypatch.setattr(pve, "_call", api)
    pve.create(pve.Guest(CORE, "qemu", 10030), "skynet-x", excluded=())
    assert api.calls[0][2] is not None and "vmstate" not in api.calls[0][2]  # no RAM dump
    api.exitstatus = "snapshot failed"
    with pytest.raises(WriteError, match="task failed"):
        pve.delete(LXC, "skynet-x", excluded=())


def test_restore_sets_back_only_what_differs_deletes_what_was_added_and_uses_the_digest(
        monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeProxmox({"cores": 4, "memory": 1024, "swap": 512})  # the apply set cores, added swap
    monkeypatch.setattr(pve, "_call", api)
    pve.restore(LXC, {"cores": 2, "memory": 1024}, "running", excluded=())
    (put,) = [c for c in api.calls if c[0] == "PUT"]
    assert put[2] == {"cores": "2", "delete": "swap", "digest": "d1"}
    assert api.config == {"cores": "2", "memory": 1024}
    assert not any(c[1] == "status/reboot" for c in api.calls)  # nothing pending: no reboot


def test_restore_of_an_unchanged_guest_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeProxmox({"cores": 2})  # the apply failed before touching the guest
    monkeypatch.setattr(pve, "_call", api)
    pve.restore(LXC, {"cores": 2}, "running", excluded=())
    assert [c[0] for c in api.calls if c[0] != "GET"] == []


def test_restore_reboots_a_running_guest_only_when_changes_are_pending(
        monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeProxmox({"cores": 4}, pending_after_put=True)
    monkeypatch.setattr(pve, "_call", api)
    pve.restore(pve.Guest(CORE, "qemu", 10030), {"cores": 2}, "running", excluded=())
    assert [c[1] for c in api.calls if c[0] == "POST"] == ["status/reboot"] and api.pending == []


def test_restore_stops_a_guest_first_so_its_config_applies_at_once(
        monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeProxmox({"cores": 4}, power="running")  # the apply also started it
    monkeypatch.setattr(pve, "_call", api)
    pve.restore(LXC, {"cores": 2}, "stopped", excluded=())
    order = [c[1] for c in api.calls if c[0] in ("POST", "PUT")]
    assert order == ["status/shutdown", "config"] and api.power == "stopped"


def test_restore_starts_a_guest_that_should_be_running(monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeProxmox({"cores": 2}, power="stopped")
    monkeypatch.setattr(pve, "_call", api)
    monkeypatch.setattr(pve, "POLL_SECONDS", 0)
    pve.restore(LXC, {"cores": 2}, "running", excluded=())
    assert [c[1] for c in api.calls if c[0] == "POST"] == ["status/start"] and api.power == "running"


def test_a_guest_that_does_not_come_back_fails_the_restore(monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeProxmox({"cores": 2}, power="stopped")
    monkeypatch.setattr(api, "__call__", api.__call__)
    real = api.__call__

    def stuck(node: str, method: str, path: str, fields: dict[str, str] | None = None) -> Any:
        result = real(node, method, path, fields)
        api.power = "stopped"  # the start task succeeds, the guest never runs
        return result

    monkeypatch.setattr(pve, "_call", stuck)
    monkeypatch.setattr(pve, "POLL_SECONDS", 0)
    monkeypatch.setattr(pve, "TASK_SECONDS", 0)
    with pytest.raises(WriteError, match="did not return to running"):
        pve.restore(LXC, {"cores": 2}, "running", excluded=())


@pytest.mark.parametrize("write", [
    lambda g: pve.create(g, "skynet-x", excluded={2020}),
    lambda g: pve.delete(g, "skynet-x", excluded={2020}),
    lambda g: pve.restore(g, {}, "running", excluded={2020}),
])
def test_every_proxmox_write_refuses_an_excluded_guest_itself(
        monkeypatch: pytest.MonkeyPatch, write: Any) -> None:
    api = FakeProxmox({})
    monkeypatch.setattr(pve, "_call", api)
    with pytest.raises(WriteError, match="excluded") as raised:
        write(pve.Guest(CORE, "qemu", 2020))
    assert raised.value.code == writepath.USAGE and api.calls == []


def test_pending_lists_only_keys_with_a_waiting_change(monkeypatch: pytest.MonkeyPatch) -> None:
    listed = [{"key": "cores", "value": 2}, {"key": "memory", "value": 1, "pending": 2},
              {"key": "swap", "delete": 1}]
    monkeypatch.setattr(pve, "_call", lambda node, method, path, fields=None: listed)
    assert pve.pending(LXC) == ["memory", "swap"]


def test_missing_operate_credentials_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SKYNET_SECRETS_DIR", str(tmp_path))
    with pytest.raises(WriteError, match="operate credentials unavailable"):
        pve.create(pve.Guest(CORE, "lxc", 10030), "skynet-x", excluded=())


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
    (tmp_path / "tofu-passphrase").write_text("p")
    assert tofu.STACKS[stack].credentials()["SSL_CERT_FILE"] == pinned
    seen: list[dict[str, str]] = []
    monkeypatch.setattr(deploy, "checkout", _fake_checkout(tmp_path))
    monkeypatch.setattr(tofu, "_tofu", lambda workdir, env, *args, timeout: (
        seen.append(dict(env)), subprocess.CompletedProcess(args, 0, b"", b""))[1])
    with tofu.workspace(tmp_path, tofu.STACKS[stack], REV) as space:
        # Go also loads SSL_CERT_DIR: an empty one leaves the pinned CA the only trust.
        cert_dir = Path(space.env["SSL_CERT_DIR"])
        assert cert_dir.is_dir() and list(cert_dir.iterdir()) == []
        space.init(tmp_path / "state.tfstate")
    (init_env,) = seen  # provider install uses public trust, and no API credentials
    assert not any(key.startswith("SSL_CERT_") for key in init_env)
    assert [key for key in init_env if key.startswith("TF_VAR_")] == ["TF_VAR_state_passphrase"]


def _fake_checkout(tmp_path: Path) -> Any:
    @contextmanager
    def checkout(repo: Path, revision: str, *paths: str) -> Iterator[Path]:
        root = tmp_path / "checkout"
        root.mkdir(exist_ok=True)
        yield root
    return checkout


def test_the_public_ca_stack_keeps_system_trust(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SKYNET_SECRETS_DIR", str(tmp_path))
    (tmp_path / "cloudflare-dns.env").write_text("CF_DNS_TOKEN=t\nTUNNEL_ID=u\n")
    (tmp_path / "tofu-passphrase").write_text("p")
    monkeypatch.setattr(deploy, "checkout", _fake_checkout(tmp_path))
    with tofu.workspace(tmp_path, tofu.STACKS["cloudflare-dns"], REV) as space:
        assert not any(key.startswith("SSL_CERT_") for key in space.env)


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
