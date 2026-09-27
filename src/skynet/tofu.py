"""`skynet tofu`: the one executor that turns a merged `tofu/<stack>/` into live infrastructure.

ADR 0008, OpenTofu half. One stack per actuator; the directory is the scope.

- **plan** (the PR author): plan the committed tree, print it and its normalized-change hash;
  `--approve` writes `tofu/<stack>/approved-plan.json`, which the PR carries. The merge approves it.
- **apply** (the executor, after merge): plan the merged revision from git objects, require the
  approved hash, refuse delete/replace/forget, excluded guests, and foreign resource types,
  snapshot every existing-guest update, apply that saved plan, and require a clean re-plan.
  A failure whose changes were all snapshotted guest updates rolls back; anything else has no
  automatic inverse and alerts.
- **record**: state is encrypted by OpenTofu at `/opt/skynet-ops/state/tofu/<stack>.tfstate` and
  mirrored with `<stack>/applied.json` to the `tofu-state` branch. The branch is the truth: a
  missing local file is rebuilt from it, and a local file the branch lacks is pushed first.
- **pending** (the 30 s deploy timer): apply each stack whose newest input commit on main is not
  the applied one. A refusal holds that revision and alerts once, until main moves.
- **drift** (the nightly): a read-only plan per stack.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from skynet import alert, common, deploy, pve, writepath
from skynet.common import CollectionError
from skynet.deploy import MAIN
from skynet.writepath import FAILED, OK, UNAVAILABLE, USAGE, Ledger, Operation, WriteError

STATE_BRANCH = "tofu-state"
STATE_REF = f"refs/remotes/origin/{STATE_BRANCH}"
SECRETS = Path("/opt/skynet-ops/secrets")
CERTS = Path("/opt/skynet-ops/certs")
APPROVED = "approved-plan.json"
PLAN_FILE = "skynet.tfplan"
GUEST_TYPES = {"proxmox_virtual_environment_container": "lxc", "proxmox_virtual_environment_vm": "qemu"}
REFUSED_ACTIONS = {"delete", "forget"}
HOLD_AFTER_FAILURES = 3
MISMATCH = "plan differs from the approved plan (drift or an unapproved change); re-plan in a new PR"
NO_APPROVAL = "plan has changes but the merged revision carries no approved-plan.json"


# --- stacks ----------------------------------------------------------------------------------

def _secrets() -> Path:
    return Path(os.environ.get("SKYNET_SECRETS_DIR", SECRETS))


def _values(name: str, allowed: tuple[str, ...], required: tuple[str, ...]) -> dict[str, str]:
    try:
        return common.read_assignments(_secrets() / name, allowed, required)
    except CollectionError:
        raise WriteError(f"{name} credentials unavailable", UNAVAILABLE) from None


def _proxmox_core_env() -> dict[str, str]:
    values = _values("proxmox-core.env", ("PVE_HOST", "PVE_TOKEN", "PVE_TOKEN_OPERATE", "PVE_CACERT"),
                     ("PVE_HOST", "PVE_TOKEN_OPERATE"))
    host = values["PVE_HOST"]
    if not common.valid_host(host):
        raise WriteError("proxmox-core.env credentials unavailable", UNAVAILABLE)
    # The node's certificate is self-signed: this stack trusts exactly its pinned CA.
    return {"TF_VAR_proxmox_endpoint": f"https://{host}:8006",
            "TF_VAR_proxmox_api_token": values["PVE_TOKEN_OPERATE"],
            "SSL_CERT_FILE": values.get("PVE_CACERT", str(CERTS / "proxmox-core.crt"))}


def _technitium_env() -> dict[str, str]:
    values = _values("technitium.env", ("TECH_HOST", "TECH_TOKEN", "TECH_CACERT"),
                     ("TECH_HOST", "TECH_TOKEN"))
    host = values["TECH_HOST"]
    if not common.valid_host(host):
        raise WriteError("technitium.env credentials unavailable", UNAVAILABLE)
    # The provider has no CA argument: this stack alone trusts exactly the pinned certificate.
    return {"TF_VAR_technitium_url": f"https://{host}:53443",
            "TF_VAR_technitium_api_token": values["TECH_TOKEN"],
            "SSL_CERT_FILE": values.get("TECH_CACERT", str(CERTS / "technitium.crt"))}


def _cloudflare_env() -> dict[str, str]:
    values = _values("cloudflare-dns.env", ("CF_DNS_TOKEN", "CF_ZONE", "TUNNEL_ID"),
                     ("CF_DNS_TOKEN", "TUNNEL_ID"))
    return {"TF_VAR_cloudflare_api_token": values["CF_DNS_TOKEN"],
            "TF_VAR_cloudflare_tunnel_id": values["TUNNEL_ID"]}


@dataclass(frozen=True)
class Stack:
    name: str
    types: frozenset[str]  # the only resource types this stack may change
    inputs: tuple[str, ...]  # repo paths whose change needs a new plan (tofu/<stack> is implied)
    credentials: Callable[[], dict[str, str]]
    node: str | None = None  # a Proxmox stack's one node

    @property
    def paths(self) -> tuple[str, ...]:
        return (f"tofu/{self.name}", *self.inputs)


STACKS = {stack.name: stack for stack in (
    Stack("proxmox-core", frozenset(GUEST_TYPES), (), _proxmox_core_env, "server-proxmox-core"),
    Stack("technitium-dns", frozenset({"technitium_record"}), ("compose/caddy-apps/Caddyfile",),
          _technitium_env),
    Stack("cloudflare-dns", frozenset({"cloudflare_dns_record"}), ("compose/cloudflared/config.yml",),
          _cloudflare_env),
)}


# --- the normalized change -------------------------------------------------------------------

def _mask(value: Any, sensitive: Any) -> Any:
    if sensitive is True:
        return "(sensitive)"
    if isinstance(value, dict) and isinstance(sensitive, dict):
        return {key: _mask(item, sensitive.get(key)) for key, item in value.items()}
    if isinstance(value, list) and isinstance(sensitive, list):
        return [_mask(item, sensitive[index] if index < len(sensitive) else None)
                for index, item in enumerate(value)]
    return value


def changes(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Every resource change that does something (moves and imports included), in address order.
    `before` is left out: it is refresh noise, not the effect."""
    found = []
    for entry in plan.get("resource_changes") or []:
        change = entry.get("change") or {}
        actions = list(change.get("actions") or [])
        moved, importing = entry.get("previous_address"), change.get("importing")
        if actions == ["no-op"] and not moved and not importing:
            continue
        found.append({
            "address": entry.get("address"), "previous_address": moved, "type": entry.get("type"),
            "actions": actions, "importing": bool(importing),
            "after": _mask(change.get("after"), change.get("after_sensitive")),
            "after_unknown": change.get("after_unknown"),
        })
    return sorted(found, key=lambda item: str(item["address"]))


def plan_hash(stack: str, found: list[dict[str, Any]]) -> str:
    canonical = json.dumps({"stack": stack, "changes": found}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def summary(found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"address": item["address"], "actions": item["actions"],
             **({"from": item["previous_address"]} if item["previous_address"] else {})}
            for item in found]


def _after(item: dict[str, Any]) -> dict[str, Any]:
    after = item.get("after")
    return after if isinstance(after, dict) else {}


def _vmid(item: dict[str, Any]) -> int | None:
    after = _after(item)
    # An imported guest's state holds its VMID in `id`, not `vm_id`.
    for value in (after.get("vm_id"), after.get("id")):
        if isinstance(value, int | str) and str(value).isdigit():
            return int(value)
    return None


def guests(stack: Stack, found: list[dict[str, Any]]) -> list[pve.Guest]:
    """The existing guests an update changes: the ones to snapshot. Templates cannot be."""
    result = []
    for item in found:
        after = _after(item)
        if item["type"] in GUEST_TYPES and item["actions"] == ["update"] and not after.get("template"):
            vmid = _vmid(item)
            assert vmid is not None and stack.node is not None  # refuse() proved both
            result.append(pve.Guest(stack.node, GUEST_TYPES[item["type"]], vmid))
    return result


def reversible(stack: Stack, found: list[dict[str, Any]]) -> bool:
    """True when every change is a snapshotted guest update or a state-only move."""
    snapshotted = {guest.vmid for guest in guests(stack, found)}
    for item in found:
        if item["actions"] == ["no-op"] and not item["importing"]:
            continue  # a move: state only
        if item["type"] in GUEST_TYPES and item["actions"] == ["update"] and _vmid(item) in snapshotted:
            continue
        return False
    return True


def refuse(stack: Stack, found: list[dict[str, Any]], excluded: set[int]) -> None:
    """The refusals no approval overrides: delete/replace/forget, excluded guests, foreign types."""
    for item in found:
        address = item["address"]
        if REFUSED_ACTIONS & set(item["actions"]):
            raise WriteError(f"{address}: delete/replace/forget is a hard checkpoint, never applied "
                             "by the executor", USAGE)
        if item["type"] not in stack.types:
            raise WriteError(f"{address}: resource type is outside the {stack.name} stack", USAGE)
        if item["type"] in GUEST_TYPES:
            after = _after(item)
            if after.get("node_name") != stack.node:
                raise WriteError(f"{address}: guest is not on {stack.node}", USAGE)
            vmid = _vmid(item)
            if vmid is None and "create" not in item["actions"]:
                raise WriteError(f"{address}: guest VMID unknown", USAGE)
            if vmid in excluded:
                raise WriteError(f"{address}: guest {vmid} is excluded; use its privileged path", USAGE)


def excluded_guests(root: Path) -> set[int]:
    try:
        data = json.loads((root / "invariants.json").read_text(encoding="utf-8"))
        return {int(guest["vmid"]) for guest in data["excluded_guests"]["guests"]}
    except (OSError, ValueError, KeyError, TypeError):
        raise WriteError("invariants.json unreadable at the merged revision", UNAVAILABLE) from None


# --- running tofu ----------------------------------------------------------------------------

def state_dir(ledger: Ledger) -> Path:
    return ledger.state_dir / "tofu"


def _env(stack: Stack, *, credentials: bool = True) -> dict[str, str]:
    try:
        passphrase = (_secrets() / "tofu-passphrase").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        raise WriteError("tofu state passphrase unavailable", UNAVAILABLE) from None
    if not passphrase:
        raise WriteError("tofu state passphrase unavailable", UNAVAILABLE)
    cache = Path(os.environ.get("HOME", "/tmp")) / ".cache/skynet/tofu-plugins"
    cache.mkdir(parents=True, exist_ok=True)
    env = {key: os.environ[key] for key in ("PATH", "HOME") if key in os.environ}
    env.update({"TF_IN_AUTOMATION": "1", "TF_INPUT": "0", "TF_PLUGIN_CACHE_DIR": str(cache),
                "TF_VAR_state_passphrase": passphrase})
    if credentials:
        env.update(stack.credentials())
    return env


def _tofu(workdir: Path, env: dict[str, str], *args: str,
          timeout: float) -> subprocess.CompletedProcess[bytes]:
    return deploy._run([os.environ.get("SKYNET_TOFU", "tofu"), f"-chdir={workdir}", *args],
                       env=env, timeout=timeout)


def _require(result: subprocess.CompletedProcess[bytes], reason: str, *ok: int) -> bytes:
    if result.returncode not in (ok or (0,)):
        raise WriteError(reason, UNAVAILABLE)
    return result.stdout


@dataclass
class Workspace:
    stack: Stack
    root: Path  # the extracted tree (tofu/, compose/, invariants.json)
    env: dict[str, str]

    @property
    def dir(self) -> Path:
        return self.root / "tofu" / self.stack.name

    def init(self, state: Path) -> None:
        _require(_tofu(self.dir, self.env, "init", "-no-color", "-input=false", "-lockfile=readonly",
                       f"-backend-config=path={state}", timeout=600),
                 "tofu init failed")

    def plan(self) -> tuple[list[dict[str, Any]], str]:
        """Save a plan in the workspace and return its changes and hash."""
        _require(_tofu(self.dir, self.env, "plan", "-no-color", "-input=false",
                       "-detailed-exitcode", f"-out={PLAN_FILE}", timeout=1800),
                 "tofu plan failed", 0, 2)
        raw = _require(_tofu(self.dir, self.env, "show", "-json", PLAN_FILE, timeout=300), "tofu show failed")
        try:
            found = changes(json.loads(raw))
        except (ValueError, AttributeError, TypeError):
            raise WriteError("tofu show returned an unreadable plan", UNAVAILABLE) from None
        return found, plan_hash(self.stack.name, found)

    def show(self) -> str:
        return _require(_tofu(self.dir, self.env, "show", "-no-color", PLAN_FILE, timeout=300), "tofu show failed").decode("utf-8", "replace")

    def apply(self) -> None:
        _require(_tofu(self.dir, self.env, "apply", "-no-color", "-input=false", PLAN_FILE,
                       timeout=3600), "tofu apply failed", 0)

    def clean(self) -> None:
        result = _tofu(self.dir, self.env, "plan", "-no-color", "-input=false", "-detailed-exitcode",
                       timeout=1800)
        if result.returncode == 2:
            raise WriteError("post-apply plan is not clean", FAILED)
        _require(result, "post-apply plan unavailable")

    def approved(self) -> dict[str, Any] | None:
        path = self.dir / APPROVED
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise WriteError("approved-plan.json unreadable", USAGE) from None
        return value if isinstance(value, dict) else None


@contextmanager
def workspace(repo: Path, stack: Stack, revision: str, *, credentials: bool = True) -> Iterator[Workspace]:
    env = _env(stack, credentials=credentials)
    with deploy.checkout(repo, revision, *stack.paths, "invariants.json") as root:
        yield Workspace(stack, root, env)


# --- the state branch ------------------------------------------------------------------------

def fetch_state(repo: Path) -> bool:
    """Refresh the remote-tracking state branch; False when it does not exist yet."""
    heads = deploy._git(repo, "ls-remote", "origin", f"refs/heads/{STATE_BRANCH}",
                        reason="git ls-remote of the state branch failed")
    if not heads:
        return False
    deploy._git(repo, "fetch", "--quiet", "origin", f"+refs/heads/{STATE_BRANCH}:{STATE_REF}",
                reason="git fetch of the state branch failed")
    return True


def _blob(repo: Path, path: str) -> bytes | None:
    result = deploy._run(["git", "-C", str(repo), "cat-file", "blob", f"{STATE_REF}:{path}"])
    return result.stdout if result.returncode == 0 else None


def branch_state(repo: Path, stack: str) -> bytes | None:
    return _blob(repo, f"{stack}/terraform.tfstate")


def applied(repo: Path, stack: str) -> dict[str, Any]:
    raw = _blob(repo, f"{stack}/applied.json")
    try:
        value = json.loads(raw) if raw else {}
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def record_state(repo: Path, stack: str, state: bytes, record: dict[str, Any] | None,
                 message: str) -> str:
    """Commit this stack's state (and its applied record) to the state branch; fast-forward only."""
    exists = fetch_state(repo)
    parent = deploy._git(repo, "rev-parse", STATE_REF, reason="state branch unreadable") if exists else None
    with tempfile.TemporaryDirectory(prefix="skynet-state-") as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}

        def git(*args: str, stdin: bytes | None = None) -> str:
            result = deploy._run(["git", "-C", str(repo), *args], stdin=stdin, env=env)
            if result.returncode != 0:
                raise WriteError("state branch commit failed", UNAVAILABLE)
            return result.stdout.decode().strip()

        git("read-tree", *([parent] if parent else ["--empty"]))
        files = {f"{stack}/terraform.tfstate": state}
        if record is not None:
            files[f"{stack}/applied.json"] = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode()
        for path, content in files.items():
            blob = git("hash-object", "-w", "--stdin", stdin=content)
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}")
        tree = git("write-tree")
        if parent and git("rev-parse", f"{parent}^{{tree}}") == tree:
            return parent
        commit = git("commit-tree", tree, *(["-p", parent] if parent else []), "-m", message)
    deploy._git(repo, "push", "--quiet", "origin", f"{commit}:refs/heads/{STATE_BRANCH}",
                reason="state branch push failed (not a fast-forward, or origin unreachable)")
    deploy._git(repo, "update-ref", STATE_REF, commit, reason="state branch unreadable")
    return commit


def local_state(ledger: Ledger, stack: str) -> Path:
    return state_dir(ledger) / f"{stack}.tfstate"


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError:
        raise WriteError("local tofu state unreadable", UNAVAILABLE) from None


def _write(path: Path, content: bytes | None) -> None:
    try:
        if content is None:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            handle.write(content)
        os.chmod(handle.name, 0o600)
        os.replace(handle.name, path)
    except OSError:
        raise WriteError("local tofu state unwritable", UNAVAILABLE) from None


def sync_state(repo: Path, ledger: Ledger, stack: str) -> bytes | None:
    """Make the local state equal the branch and return it. A missing local file is rebuilt from
    git; a local file the branch lacks (an unrecorded apply) is pushed before anything else."""
    fetch_state(repo)
    remote, local = branch_state(repo, stack), _read(local_state(ledger, stack))
    if local is None:
        _write(local_state(ledger, stack), remote)
        return remote
    if local != remote:
        record_state(repo, stack, local, None, f"tofu-state({stack}): record unpushed local state")
    return local


def _state_copy(repo: Path, ledger: Ledger, stack: str, into: Path) -> Path:
    """A read-only copy of the current state (local if present, else the branch)."""
    local = _read(local_state(ledger, stack))
    if local is None and fetch_state(repo):
        local = branch_state(repo, stack)
    path = into / f"{stack}.tfstate"
    if local is not None:
        path.write_bytes(local)
    return path


# --- apply -----------------------------------------------------------------------------------

def input_revision(repo: Path, stack: Stack, ref: str = MAIN) -> str | None:
    revision = deploy._git(repo, "log", "-1", "--format=%H", ref, "--", *stack.paths)
    return revision or None


@dataclass
class _Saved:
    found: list[dict[str, Any]] = field(default_factory=list)
    hash: str = ""
    before: bytes | None = None
    snapshot: str = ""
    taken: list[pve.Guest] = field(default_factory=list)


def _refused(ledger: Ledger, name: str, reason: str, code: int = USAGE, source: str = "") -> Operation:
    return writepath.refuse(Operation("tofu", f"tofu/{name}"[:200], source), ledger, reason, code)


def apply(repo: Path, name: str, *, revision: str | None = None, ledger: Ledger,
          refresh: bool = True) -> Operation:
    """Apply one stack at one merged revision through the write-path shape."""
    stack = STACKS.get(name)
    if stack is None:
        return _refused(ledger, name, "unknown stack")
    try:
        if refresh:
            deploy.fetch(repo)
        target = deploy.resolve(repo, revision) if revision else input_revision(repo, stack)
    except WriteError as error:
        return _refused(ledger, name, error.reason, error.code)
    if target is None:
        return _refused(ledger, name, "stack is not on origin/main")
    settle_interrupted(repo, ledger)
    operation = Operation("tofu", f"tofu/{name}", target)
    saved = _Saved(snapshot=f"skynet-{operation.id}")
    state = local_state(ledger, name)
    try:
        with workspace(repo, stack, target) as space:
            def preflight() -> None:
                if not deploy.merged(repo, target):
                    raise WriteError("revision is not merged to origin/main", USAGE)
                saved.before = sync_state(repo, ledger, name)
                space.init(state)
                saved.found, saved.hash = space.plan()
                operation.context = {"stack": name, "hash": saved.hash, "snapshot": saved.snapshot,
                                     "changes": summary(saved.found)}
                if not saved.found:
                    return
                approval = space.approved()
                if approval is None:
                    raise WriteError(NO_APPROVAL, USAGE)
                if approval.get("hash") != saved.hash:
                    raise WriteError(MISMATCH, USAGE)
                refuse(stack, saved.found, excluded_guests(space.root))

            def snapshot() -> _Saved:
                for guest in guests(stack, saved.found):
                    try:
                        pve.create(guest, saved.snapshot)
                    except WriteError:
                        _prune(saved, operation)
                        raise WriteError(f"could not snapshot {guest}; nothing applied", UNAVAILABLE) \
                            from None
                    saved.taken.append(guest)
                operation.context["guests"] = [str(guest) for guest in saved.taken]
                return saved

            def execute(state_: _Saved) -> None:
                if state_.found:
                    space.apply()

            def verify(state_: _Saved) -> dict[str, Any]:
                if state_.found:
                    space.clean()
                return {"changes": len(state_.found), "hash": state_.hash, "post_apply_plan": "clean"}

            def rollback(state_: _Saved, error: WriteError) -> str:
                if not reversible(stack, state_.found):
                    try:
                        _record(repo, ledger, name, None, f"tofu-state({name}): after failed "
                                f"{operation.id}")
                        operation.note("state", "ok", "the state tofu wrote is recorded")
                    except WriteError as record_error:
                        operation.note("state", "failed", record_error.reason)
                    raise WriteError("no automatic inverse for these changes; operator recovery "
                                     f"(snapshots {state_.snapshot} kept)")
                for guest in reversed(state_.taken):
                    pve.rollback(guest, state_.snapshot)
                _write(state, state_.before)
                _prune(state_, operation)
                return "rolled-back"

            def reconcile() -> dict[str, Any]:
                return {"state": "settled before this run"}

            def commit(state_: _Saved) -> None:
                _prune(state_, operation)
                _record(repo, ledger, name, {"revision": target, "hash": state_.hash,
                                             "operation": operation.id},
                        f"tofu-state({name}): {operation.id} applied {target[:12]}")

            return writepath.run(operation, ledger, preflight=preflight, snapshot=snapshot,
                                 execute=execute, verify=verify, rollback=rollback,
                                 reconcile=reconcile, commit=commit)
    except WriteError as error:  # the workspace itself (credentials, checkout) is unavailable
        return _refused(ledger, name, error.reason, error.code, target)


def _record(repo: Path, ledger: Ledger, stack: str, record: dict[str, Any] | None, message: str) -> None:
    state = _read(local_state(ledger, stack))
    if state is None:
        raise WriteError("no local tofu state to record", UNAVAILABLE)
    record_state(repo, stack, state, record, message)


def _prune(saved: _Saved, operation: Operation) -> None:
    for guest in saved.taken:
        try:
            pve.delete(guest, saved.snapshot)
        except WriteError as error:
            operation.note("prune", "failed", f"{guest}: {error.reason}")
    saved.taken = []


def settle_interrupted(repo: Path, ledger: Ledger) -> list[dict[str, Any]]:
    """An apply interrupted mid-write cannot be shown safe: record the state tofu wrote, keep the
    snapshots, and close it as rollback-failed so a human looks."""
    if ledger.busy():
        return []
    results = []
    for entry in ledger.unfinished("tofu"):
        context = entry.get("context") or {}
        stack = str(context.get("stack", ""))
        note = "state not recorded"
        if stack in STACKS:
            try:
                _record(repo, ledger, stack, None, f"tofu-state({stack}): after interrupted "
                        f"{entry.get('id')}")
                note = "state recorded as tofu wrote it"
            except WriteError as error:
                note = f"state not recorded: {error.reason}"
        operation = writepath.settle(ledger, entry, alarm=f"interrupted tofu apply; {note}; "
                                     f"snapshots {context.get('snapshot', '?')} kept; check by hand")
        results.append(writepath.report(operation))
    return results


# --- pending ---------------------------------------------------------------------------------

def _facts_path(ledger: Ledger) -> Path:
    return state_dir(ledger) / "pending.json"


def _facts(ledger: Ledger) -> dict[str, Any]:
    try:
        value = json.loads(_facts_path(ledger).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def pending(repo: Path, *, ledger: Ledger) -> list[dict[str, Any]]:
    """Apply each stack whose newest input commit on main is not the applied one (main is already
    fetched by the deploy pass). A refused revision, or one that could not be planned three passes
    running, is held and alerts once; it is retried only when main moves."""
    results = settle_interrupted(repo, ledger)
    fetch_state(repo)
    facts = _facts(ledger)
    before = json.dumps(facts, sort_keys=True)
    for name, stack in STACKS.items():
        target = input_revision(repo, stack)
        if target is None or applied(repo, name).get("revision") == target:
            continue
        known = facts.get(name)
        fact: dict[str, Any] = known if isinstance(known, dict) else {}
        if fact.get("revision") != target:
            fact = {"revision": target, "failures": 0, "held": False}
        if fact.get("held"):
            results.append({"target": f"tofu/{name}", "source": target, "outcome": "held",
                            "reason": "refused revision; awaiting a new merge"})
            continue
        result = writepath.report(apply(repo, name, revision=target, ledger=ledger, refresh=False))
        if result.get("outcome") == "refused" and result.get("code") != UNAVAILABLE:
            fact["held"] = True
        elif result.get("code") == UNAVAILABLE:
            fact["failures"] = int(fact.get("failures", 0)) + 1
            fact["held"] = fact["failures"] >= HOLD_AFTER_FAILURES
        if fact.get("held"):
            failure = alert.send(f"skynet: tofu/{name} held", writepath.line(result), priority=1)
            result.setdefault("steps", []).append(
                {"step": "alert", "outcome": "failed" if failure else "ok", **({"detail": failure}
                                                                              if failure else {})})
        facts[name] = fact
        results.append(result)
    if json.dumps(facts, sort_keys=True) == before:
        return results
    try:
        _facts_path(ledger).parent.mkdir(parents=True, exist_ok=True)
        common.atomic_write_text(_facts_path(ledger), json.dumps(facts, sort_keys=True) + "\n")
    except OSError:
        results.append({"target": "tofu", "outcome": "unrecorded", "code": UNAVAILABLE,
                        "reason": "tofu pending facts unwritable"})
    return results


# --- plan and drift (read-only) --------------------------------------------------------------

def _read_only_plan(repo: Path, ledger: Ledger, stack: Stack, revision: str,
                    ) -> tuple[list[dict[str, Any]], str, str]:
    with tempfile.TemporaryDirectory(prefix="skynet-tofu-") as tmp, \
            workspace(repo, stack, revision) as space:
        space.init(_state_copy(repo, ledger, stack.name, Path(tmp)))
        found, digest = space.plan()
        return found, digest, space.show()


def run_plan(repo: Path, name: str, *, ref: str, approve: bool, state_dir_: Path,
             stdout: TextIO) -> int:
    """The PR author's plan: print it and its hash; `--approve` writes approved-plan.json."""
    stack = STACKS.get(name)
    if stack is None:
        print(f"tofu plan: unknown stack (one of {', '.join(STACKS)})", file=stdout)
        return USAGE
    try:
        revision = deploy.resolve(repo, ref)
        found, digest, text = _read_only_plan(repo, Ledger(state_dir_), stack, revision)
    except WriteError as error:
        print(f"tofu/{name}: {error.reason}", file=stdout)
        return error.code
    print(text.rstrip(), file=stdout)
    print(f"\ntofu/{name}@{revision[:12]}: {len(found)} change(s), sha256:{digest}", file=stdout)
    if approve:
        if not found:
            print("nothing to approve: the plan is empty", file=stdout)
            return OK
        path = repo / "tofu" / name / APPROVED
        common.atomic_write_text(path, json.dumps(
            {"stack": name, "hash": digest, "changes": summary(found)}, indent=2) + "\n")
        print(f"wrote {path.relative_to(repo)}; commit it with the change", file=stdout)
    return OK


def run_drift(repo: Path, *, output: Path, state_dir_: Path, stdout: TextIO) -> int:
    """The nightly's read-only plan per stack at origin/main."""
    ledger, lines, code = Ledger(state_dir_), [], OK
    try:
        deploy.fetch(repo)
        head = deploy.resolve(repo, MAIN)
    except WriteError as error:
        print(f"tofu drift: {error.reason}", file=stdout)
        return error.code
    for name, stack in STACKS.items():
        try:
            found, digest, _ = _read_only_plan(repo, ledger, stack, head)
        except WriteError as error:
            lines.append(f"{name}: plan unavailable — {error.reason}")
            code = UNAVAILABLE
            continue
        lines.append(f"{name}: {'no changes' if not found else f'{len(found)} change(s), sha256:{digest}'}")
        lines += [f"  {item['address']}: {'/'.join(item['actions'])}" for item in found]
    text = f"# tofu drift at {head[:12]}\n" + "\n".join(lines) + "\n"
    try:
        common.atomic_write_text(output, text)
    except OSError:
        code = UNAVAILABLE
    print(text, end="", file=stdout)
    return code


def run_apply(repo: Path, name: str | None, *, revision: str | None, pending_all: bool,
              state_dir_: Path, json_output: bool, stdout: TextIO) -> int:
    ledger = Ledger(state_dir_)
    if pending_all:
        try:
            deploy.fetch(repo)
            results = pending(repo, ledger=ledger)
        except WriteError as error:
            results = [{"target": "tofu", "outcome": "unavailable", "reason": error.reason,
                        "code": error.code}]
        for result in results:
            writepath.emit(result, json_output, stdout)
        return max((int(result.get("code", 0)) for result in results), default=OK)
    assert name is not None
    result = writepath.report(apply(repo, name, revision=revision, ledger=ledger))
    writepath.emit(result, json_output, stdout)
    return int(result["code"])

