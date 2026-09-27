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
    return change(f'{kind}.g["{vmid}"]', kind, actions or ["update"], vm_id=vmid, node_name=node,
                  **extra)


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
        self.snapshot_fail: set[int] = set()
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
        def run(g: pve.Guest, name: str) -> None:
            host.calls.append((action, g.vmid))
            if action == "create" and g.vmid in host.snapshot_fail:
                raise WriteError("Proxmox snapshot task failed", UNAVAILABLE)
        return run

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
    monkeypatch.setattr(alert, "send", send)
    return host


def run(fake: Fake, tmp_path: Path, stack: str = "proxmox-core") -> Operation:
    return tofu.apply(tmp_path, stack, revision=REV, ledger=Ledger(tmp_path / "state"))


# --- the normalized change -------------------------------------------------------------------

def test_hash_ignores_refresh_noise_and_follows_the_effect() -> None:
    one = guest(cores=2)
    noisy = guest(cores=2)
    noisy["change"]["before"] = {"id": "10030", "uptime": 999}
    other = guest(cores=4)
    digest = lambda entry: tofu.plan_hash("s", tofu.changes({"resource_changes": [entry]}))  # noqa: E731
    assert digest(one) == digest(noisy)
    assert digest(one) != digest(other)
    assert tofu.plan_hash("s", []) != tofu.plan_hash("t", [])


def test_no_ops_drop_out_and_moves_and_imports_stay() -> None:
    noop = change("a.b", CT, ["no-op"])
    moved = {**change("a.c", CT, ["no-op"]), "previous_address": "a.old"}
    imported = change("a.d", CT, ["no-op"])
    imported["change"]["importing"] = {"id": "1"}
    found = tofu.changes({"resource_changes": [noop, moved, imported]})
    assert [item["address"] for item in found] == ["a.c", "a.d"]


def test_sensitive_values_are_masked() -> None:
    entry = change("a.b", VM, ["update"], password="hunter2", name="n")
    entry["change"]["after_sensitive"] = {"password": True}
    (found,) = tofu.changes({"resource_changes": [entry]})
    assert found["after"] == {"password": "(sensitive)", "name": "n"}


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
    assert ("rollback", 10030) in fake.calls and ("delete", 10030) in fake.calls
    assert state.read_bytes() == b"before"
    assert fake.alerts == [] and fake.recorded == []


def test_a_failed_create_has_no_inverse_records_true_state_and_alerts(fake: Fake, tmp_path: Path) -> None:
    fake.apply_error = True
    fake.plan = [guest(10030, cores=4), guest(10040, actions=["create"])]
    fake.approve()
    operation = run(fake, tmp_path)
    assert operation.outcome == "rollback-failed"
    assert fake.recorded == [None]  # the state tofu wrote, without an applied record
    assert ("rollback", 10030) not in fake.calls and ("delete", 10030) not in fake.calls  # kept
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


def test_an_unplannable_revision_is_retried_then_held(fake: Fake, tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = Ledger(tmp_path / "state")

    def broken(self: FakeSpace, state: Path) -> None:
        raise WriteError("tofu init failed", UNAVAILABLE)

    monkeypatch.setattr(FakeSpace, "init", broken)
    outcomes = [tofu.pending(tmp_path, ledger=ledger)[0]["outcome"] for _ in range(4)]
    assert outcomes == ["refused", "refused", "refused", "held"]
    assert fake.alerts == ["skynet: tofu/proxmox-core held"]


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


def test_an_unpushed_local_state_is_pushed_before_anything_else(clone: Path, tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "state")
    tofu.record_state(clone, "proxmox-core", b"v1", {"revision": REV}, "first")
    path = tofu.local_state(ledger, "proxmox-core")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"v2")
    assert tofu.sync_state(clone, ledger, "proxmox-core") == b"v2"
    assert tofu.branch_state(clone, "proxmox-core") == b"v2"
    assert tofu.applied(clone, "proxmox-core") == {"revision": REV}  # the record is kept


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
        pve.rollback(pve.Guest(CORE, "lxc", 10030), "skynet-x")


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
