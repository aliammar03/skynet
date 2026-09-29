"""`skynet tofu`: the one executor that turns a merged `tofu/<stack>/` into live infrastructure.

ADR 0008, OpenTofu half. One stack per actuator; the directory is the scope.

- **plan** (the PR author): plan the committed tree, print it and its normalized-change hash;
  `--approve` writes `tofu/<stack>/approved-plan.json` (the hash, bound to a digest of the stack's
  inputs), which the PR carries. The merge approves it.
- **apply** (the executor, after merge): validate and plan the merged revision from git objects,
  require the approved hash and inputs, refuse excluded guests and foreign resource types, apply a
  bounded number of deletes only of a stack's derived DNS records, and defer (exclude from the plan,
  alert once) a guest's delete/replace/forget, a hard checkpoint that must never block the rest.
  Save each updated guest's config (and a disk-only fallback snapshot, unless a bind mount stops
  Proxmox from taking one); fence any Docker host among those guests against deploys; apply that
  saved plan; require a clean re-plan and every fenced Docker host answering. A failed apply, a
  re-plan that still wants the approved change, or a fenced host that never answers, whose changes
  were all restorable guest updates, writes the saved configs back; anything else (including a
  re-plan dirty only elsewhere) has no automatic inverse, is held, and alerts.
- **record**: state is encrypted by OpenTofu at `/opt/skynet-ops/state/tofu/<stack>.tfstate` and
  mirrored with `<stack>/applied.json` to the `tofu-state` branch. The branch is the truth: every
  pass rebuilds a missing or stale local file from it, and pushes local writes on top of it. A
  first local state (no branch, no base) is pushed only by an apply at its stack that used it.
- **pending** (the skynet-tofu timer, under its own `tofu` lock): apply each stack whose newest
  input commit on main is not the applied one. A refusal holds that revision and alerts once,
  until main moves; every hold alerts once, however it was set. An unavailable stack backs off
  (1 min doubling to 1 h), alerts on the third failure, and reminds daily.
- **drift** (the nightly): a read-only plan per stack.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import signal
import subprocess
import tempfile
import time
from collections.abc import Callable, Collection, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO, TypeVar

from skynet import alert, common, deploy, dns, proxmox, publish, pve, watch, writepath
from skynet.common import CollectionError
from skynet.deploy import MAIN
from skynet.writepath import FAILED, OK, UNAVAILABLE, USAGE, Ledger, Operation, WriteError

STATE_BRANCH = "tofu-state"
STATE_REF = f"refs/remotes/origin/{STATE_BRANCH}"
SECRETS = Path("/opt/skynet-ops/secrets")
APPROVED = "approved-plan.json"
PLAN_FILE = "skynet.tfplan"
VERIFY_FILE = "skynet-verify.tfplan"
GUEST_TYPES = {"proxmox_virtual_environment_container": "lxc", "proxmox_virtual_environment_vm": "qemu"}
REFUSED_ACTIONS = {"delete", "forget"}
MAX_DELETES = 3  # derived-record deletes per apply: a parse regression never wipes a zone
ALERT_AFTER_FAILURES = 3
BACKOFF_SECONDS, BACKOFF_MAX = 60, 3600  # an unavailable stack's retry: 1 min doubling to 1 h
REMIND_SECONDS = 86400  # a stack still unavailable re-alerts daily after its first alert
HOST_SETTLE_SECONDS = 600  # a fenced Docker host must answer this soon after an apply or restore
HOST_DOWN = "a fenced Docker host did not answer after the apply"
INVALID = "merged source does not validate (tofu validate); fix it in a new PR"
STALE_APPROVAL = ("approved-plan.json was made for other inputs; re-run `skynet tofu plan "
                  "--approve` on this tree in a new PR")
UNVERIFIED = "post-apply plan could not run"
DRIFTED = "post-apply plan is dirty outside the approved change (drift or a provider diff)"
INDETERMINATE = "tofu apply did not finish (timed out or lost); remote work may still be running"
HELD = "revision is held; awaiting a new merge (or a supervised --ignore-hold)"
# Outcomes that mean "we do not know what is live": never roll back over them.
UNSETTLED = frozenset({UNVERIFIED, INDETERMINATE, DRIFTED})
NOT_LANDED = "post-apply plan still wants the approved change"
LOCK = "tofu"  # OpenTofu's own write lock (writepath.Ledger.lock)
NOT_SETTLED = "an interrupted tofu apply is not settled yet; retrying next pass"
CONTENDED = frozenset({writepath.LOCK_BUSY, NOT_SETTLED, HELD})
# The time budget. The skynet-tofu unit's TimeoutStartSec is PASS_SECONDS (nix/modules/timers.nix;
# a test pins them together). A stack starts only if its worst case still fits before the deadline,
# so systemd never kills a rollback half-way. The worst case counts every wait: each tofu command's
# timeout; per guest, every Proxmox task (the POST, the task wait, and a last poll that may start at
# the deadline) plus the reads; and an allowance for each git call and alert.
TOFU_SECONDS = {"init": 300, "validate": 120, "schema": 120, "plan": 900, "show": 120,
                "replan": 900, "replan_show": 120, "apply": 1800, "verify": 900, "verify_show": 120}
MAX_GUESTS = 5  # updated guests per apply; bounds the rollback time
_TASK = 2 * pve.TIMEOUT + pve.TASK_SECONDS + pve.POLL_SECONDS  # POST, wait, a last in-flight poll
GUEST_SECONDS = (3 * pve.TIMEOUT      # before: status, config, pending
                 + 4 * pve.TIMEOUT    # restore: config, PUT, pending, status
                 + 2 * pve.TIMEOUT    # proof: config, pending
                 + 3 * _TASK          # snapshot, prune, and one power task (reboot, start, or stop)
                 + pve.TASK_SECONDS + pve.TIMEOUT + pve.POLL_SECONDS)  # wait to see the power state
GIT_CALLS, GIT_SECONDS, ALERTS = 60, 60, 4  # per stack: sync, record, hold, checkout; alerts
# Every fenced host shares one settle deadline after the apply and one after a restore.
STACK_BUDGET = (sum(TOFU_SECONDS.values()) + MAX_GUESTS * GUEST_SECONDS + GIT_CALLS * GIT_SECONDS
                + 2 * HOST_SETTLE_SECONDS
                + 120 + ALERTS * int(alert.TIMEOUT))  # 120: the source archive
PASS_SECONDS = 6 * 3600
PASS_MARGIN = 300  # reporting, the exit, and systemd's own stop
# Outcomes after a write ran: retrying could disrupt guests again or repeat a partial create.
HELD_OUTCOMES = frozenset({"failed", "rolled-back", "rollback-failed"})
MISMATCH = "plan differs from the approved plan (drift or an unapproved change); re-plan in a new PR"
NO_APPROVAL = "plan has changes but the merged revision carries no approved-plan.json"


# --- stacks ----------------------------------------------------------------------------------

def _secrets() -> Path:
    return Path(os.environ.get("SKYNET_SECRETS_DIR", SECRETS))


def _values(name: str, parse: Callable[[Path], dict[str, str]]) -> dict[str, str]:
    """A credential file read by the same parser its actuator's API client uses, so a file the
    snapshot or restore step would reject never passes the plan."""
    try:
        return parse(_secrets() / name)
    except (CollectionError, WriteError):
        raise WriteError(f"{name} credentials unavailable", UNAVAILABLE) from None


def _proxmox_core_env() -> dict[str, str]:
    values = _values("proxmox-core.env", lambda path: proxmox.assignments(path, "PVE_TOKEN_OPERATE"))
    # The node's certificate is self-signed: this stack trusts exactly its pinned CA.
    return {"TF_VAR_proxmox_endpoint": f"https://{values['PVE_HOST']}:8006",
            "TF_VAR_proxmox_api_token": values["PVE_TOKEN_OPERATE"],
            "SSL_CERT_FILE": values["PVE_CACERT"]}


def _technitium_env() -> dict[str, str]:
    values = _values("technitium.env", dns.assignments)
    # The provider has no CA argument: this stack alone trusts exactly the pinned certificate.
    return {"TF_VAR_technitium_url": f"https://{values['TECH_HOST']}:53443",
            "TF_VAR_technitium_api_token": values["TECH_TOKEN"],
            "SSL_CERT_FILE": values["TECH_CACERT"]}


def _cloudflare_env() -> dict[str, str]:
    values = _values("cloudflare-dns.env", publish.cloudflare_credentials)
    if not common.printable(values.get("TUNNEL_ID", "")):
        raise WriteError("cloudflare-dns.env credentials unavailable", UNAVAILABLE)
    return {"TF_VAR_cloudflare_api_token": values["CF_DNS_TOKEN"],
            "TF_VAR_cloudflare_tunnel_id": values["TUNNEL_ID"]}


@dataclass(frozen=True)
class Stack:
    name: str
    types: frozenset[str]  # the only resource types this stack may change
    inputs: tuple[str, ...]  # repo paths whose change needs a new plan (tofu/<stack> is implied)
    credentials: Callable[[], dict[str, str]]
    node: str | None = None  # a Proxmox stack's one node
    # Types whose approved delete the executor applies: records derived from git, holding no
    # payload, that the revert of their PR recreates. Every other delete is deferred.
    deletable: frozenset[str] = frozenset()

    @property
    def paths(self) -> tuple[str, ...]:
        return (f"tofu/{self.name}", *self.inputs)


STACKS = {stack.name: stack for stack in (
    Stack("proxmox-core", frozenset(GUEST_TYPES), (), _proxmox_core_env, "server-proxmox-core"),
    Stack("technitium-dns", frozenset({"technitium_record"}), ("compose/caddy-apps/Caddyfile",),
          _technitium_env, deletable=frozenset({"technitium_record"})),
    Stack("cloudflare-dns", frozenset({"cloudflare_dns_record"}), ("compose/cloudflared/config.yml",),
          _cloudflare_env, deletable=frozenset({"cloudflare_dns_record"})),
)}


# --- the normalized change -------------------------------------------------------------------

def _commit(value: Any, secret: bytes) -> str:
    """A keyed commitment to a sensitive value: it changes when the value changes, and without the
    key it cannot be brute-forced back to the value."""
    if not secret:
        raise WriteError("plan has sensitive values but no commitment key; cannot compare safely",
                         UNAVAILABLE)
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "(sensitive:" + hmac.new(secret, canonical, hashlib.sha256).hexdigest() + ")"


def _mask(value: Any, sensitive: Any, secret: bytes) -> Any:
    if sensitive is True:
        return _commit(value, secret)
    if isinstance(value, dict) and isinstance(sensitive, dict):
        return {key: _mask(item, sensitive.get(key), secret) for key, item in value.items()}
    if isinstance(value, list) and isinstance(sensitive, list):
        return [_mask(item, sensitive[index] if index < len(sensitive) else None, secret)
                for index, item in enumerate(value)]
    return value


UNKNOWN = "(known after apply)"


def _has_unknown(value: Any) -> bool:
    """True only for a `true` leaf: tofu writes a fully known nested block as `[{}]`."""
    if value is True:
        return True
    if isinstance(value, dict):
        return any(_has_unknown(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_unknown(item) for item in value)
    return False


def _delta(before: Any, after: Any, unknown: Any) -> dict[str, Any]:
    """The top-level attributes this change actually moves, as before → after. A hand edit to an
    attribute the PR did not touch makes it appear here, so the hash no longer matches. An
    attribute known only after apply is recorded as such, without its refreshed `before`."""
    before = before if isinstance(before, dict) else {}
    after = after if isinstance(after, dict) else {}
    unknown = unknown if isinstance(unknown, dict) else {}
    pending = {key for key, value in unknown.items() if _has_unknown(value)}
    keys = {key for key in before.keys() | after.keys() if before.get(key) != after.get(key)}
    return {key: ({"after": UNKNOWN} if key in pending
                  else {"before": before.get(key), "after": after.get(key)})
            for key in sorted(keys | pending)}


def changes(plan: dict[str, Any], secret: bytes = b"") -> list[dict[str, Any]]:
    """Every resource change that does something (moves and imports included), in address order.
    Each carries its full `after` (read for the VMID, node, and template checks) and its `delta`;
    only the delta is hashed, so untouched attributes' refresh values (a guest agent's IP and MAC
    lists) stay out. Sensitive values become keyed commitments (`secret`), so the hash follows them
    without the plan revealing them. A data source's read changes nothing: it is not a change
    (which providers may run at all is the lock file's decision)."""
    found = []
    for entry in plan.get("resource_changes") or []:
        if entry.get("mode") == "data":
            continue
        change = entry.get("change") or {}
        actions = list(change.get("actions") or [])
        moved, importing = entry.get("previous_address"), change.get("importing")
        if actions == ["no-op"] and not moved and not importing:
            continue
        found.append({
            "address": entry.get("address"), "previous_address": moved, "type": entry.get("type"),
            "actions": actions, "importing": bool(importing),
            "after": _mask(change.get("after"), change.get("after_sensitive"), secret),
            "after_unknown": change.get("after_unknown"),
            "delta": _delta(_mask(change.get("before"), change.get("before_sensitive"), secret),
                            _mask(change.get("after"), change.get("after_sensitive"), secret),
                            change.get("after_unknown")),
        })
    return sorted(found, key=lambda item: str(item["address"]))


HASHED = ("address", "previous_address", "type", "actions", "importing", "delta")


def plan_hash(stack: str, found: list[dict[str, Any]], deferred: Collection[str] = ()) -> str:
    """The change set's identity. What a plan defers is part of it: approving a plan approves
    leaving exactly those addresses for their hard checkpoint."""
    effect = [{key: item.get(key) for key in HASHED} for item in found]
    value: dict[str, Any] = {"stack": stack, "changes": effect}
    if deferred:
        value["deferred"] = sorted(deferred)
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
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
    """The existing guests an update changes: the ones whose config is saved. Templates are not."""
    result = []
    for item in found:
        after = _after(item)
        if item["type"] in GUEST_TYPES and item["actions"] == ["update"] and not after.get("template"):
            vmid = _vmid(item)
            assert vmid is not None and stack.node is not None  # refuse() proved both
            result.append(pve.Guest(stack.node, GUEST_TYPES[item["type"]], vmid))
    return result


# The top-level attributes a config restore (pve.restore) sets back: plain guest config keys, plus
# power state. Anything else, such as pool membership, a disk resize (disks cannot shrink), or a
# template conversion, has no automatic inverse. This list is trusted only to choose the path:
# every rollback is then proved by comparing the guest's whole config with its pre-apply copy.
RESTORE_COVERS = {
    "proxmox_virtual_environment_container": frozenset({
        "console", "cpu", "description", "features", "initialization", "memory",
        "network_interface", "operating_system", "started", "startup", "tags"}),
    "proxmox_virtual_environment_vm": frozenset({
        "agent", "bios", "boot_order", "cpu", "description", "machine", "memory", "name",
        "network_device", "on_boot", "operating_system", "serial_device", "started", "startup",
        "tablet_device", "tags", "vga"}),
}


def _config_diff(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """The config keys (names only, never values) that differ."""
    return sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))


WHOLE, MOVED, IMPORTED, DELETED = "*", "@moved", "@import", "@delete"


def _touched(found: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """(address, marker) pairs a change set moves: a create touches the whole resource (`*`), an
    update its attributes, and a move, an import, or a delete only that event."""
    pairs: set[tuple[str, str]] = set()
    for item in found:
        address, actions = str(item.get("address")), item.get("actions", [])
        if "create" in actions:
            pairs.add((address, WHOLE))
            continue
        if REFUSED_ACTIONS & set(actions):
            pairs.add((address, DELETED))
        if item.get("previous_address"):
            pairs.add((address, MOVED))
        if item.get("importing"):
            pairs.add((address, IMPORTED))
        if "update" in actions:
            pairs |= {(address, key) for key in item.get("delta") or {}} or {(address, WHOLE)}
    return pairs


def overlaps(approved: list[dict[str, Any]], remaining: list[dict[str, Any]]) -> bool:
    """Whether a post-apply plan still wants something the approved change moved: the change did
    not land. A create not landed shows up as anything at its address, and anything the change
    touched wanted whole again (created anew) did not land either; a move, an import, or a delete
    shows up only as that same event again. A re-plan dirty only elsewhere (including other
    attributes of a moved or imported address) is drift or a provider diff, not this change."""
    done, left = _touched(approved), _touched(remaining)
    created = {address for address, key in done if key == WHOLE}
    addresses = {address for address, _ in done}
    return bool(done & left) or any(address in created or (key == WHOLE and address in addresses)
                                    for address, key in left)


def _covered(item: dict[str, Any], readonly: Collection[str] = ()) -> bool:
    """Every attribute the update moves is one a config restore sets back. A computed-only
    attribute (the provider's output, never configuration: a guest agent's address lists) is
    re-read, not restored, so it never makes an update irreversible."""
    covers = RESTORE_COVERS.get(str(item["type"]), frozenset())
    return all(key in covers or key in readonly or key.startswith("timeout_")
               for key in item.get("delta", {}))


def reversible(stack: Stack, found: list[dict[str, Any]],
               readonly: dict[str, frozenset[str]] | None = None) -> bool:
    """True when every change is a state-only move, or an updated guest's change to attributes a
    config restore sets back (`readonly`: each type's computed-only attributes, from the
    provider schema)."""
    snapshotted = {guest.vmid for guest in guests(stack, found)}
    for item in found:
        if item["actions"] == ["no-op"] and not item["importing"]:
            continue  # a move: state only
        if (item["type"] in GUEST_TYPES and item["actions"] == ["update"]
                and _vmid(item) in snapshotted
                and _covered(item, (readonly or {}).get(str(item["type"]), frozenset()))):
            continue
        return False
    return True


def deferrable(stack: Stack, item: dict[str, Any]) -> bool:
    """A delete, replace, or forget the executor never applies (anything but a derived record of
    this stack): excluded from the plan so it waits for its hard checkpoint without blocking the
    rest of the stack."""
    return bool(REFUSED_ACTIONS & set(item["actions"])) and item["type"] not in stack.deletable


def refuse(stack: Stack, found: list[dict[str, Any]], excluded: Collection[int]) -> None:
    """The refusals no approval overrides: an undeferred delete/replace/forget of anything but a
    derived record, excluded guests, foreign types."""
    for item in found:
        address = item["address"]
        if deferrable(stack, item):
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


def check(stack: Stack, found: list[dict[str, Any]], excluded: Collection[int]) -> None:
    """Everything the executor refuses whatever the approval: run at `plan --approve` too, so a PR
    never carries an approval the executor would only refuse and hold."""
    refuse(stack, found, excluded)
    if len(guests(stack, found)) > MAX_GUESTS:
        raise WriteError(f"plan updates more than {MAX_GUESTS} existing guests; split it "
                         "so its rollback fits the time budget", USAGE)
    if sum("delete" in item["actions"] for item in found) > MAX_DELETES:
        raise WriteError(f"plan deletes more than {MAX_DELETES} records (a parse regression?); "
                         "split it", USAGE)


def excluded_guests(root: Path) -> set[int]:
    try:
        data = json.loads((root / "invariants.json").read_text(encoding="utf-8"))
        return {int(guest["vmid"]) for guest in data["excluded_guests"]["guests"]}
    except (OSError, ValueError, KeyError, TypeError):
        raise WriteError("invariants.json unreadable at the merged revision", UNAVAILABLE) from None


def main_excluded(repo: Path) -> frozenset[int]:
    """The excluded guests on origin/main: what a queue entry (local, unreviewed) is checked against."""
    with deploy.checkout(repo, MAIN, "invariants.json") as root:
        return frozenset(excluded_guests(root))


def all_excluded(repo: Path, root: Path) -> frozenset[int]:
    """The excluded guests at a checked-out revision and on origin/main together: an older or
    unmerged revision can add an exclusion but never lift one main has."""
    return frozenset(excluded_guests(root)) | main_excluded(repo)


# --- running tofu ----------------------------------------------------------------------------

def state_dir(ledger: Ledger) -> Path:
    return ledger.state_dir / "tofu"


def _env(stack: Stack, ledger: Ledger, *, credentials: bool = True) -> dict[str, str]:
    try:
        passphrase = (_secrets() / "tofu-passphrase").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        raise WriteError("tofu state passphrase unavailable", UNAVAILABLE) from None
    if not passphrase:
        raise WriteError("tofu state passphrase unavailable", UNAVAILABLE)
    # Beside the state it serves: persisted, and owned by the account that runs every pass.
    cache = state_dir(ledger) / "plugins"
    try:
        cache.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise WriteError("tofu plugin cache unwritable", UNAVAILABLE) from None
    env = {key: os.environ[key] for key in ("PATH", "HOME") if key in os.environ}
    env.update({"TF_IN_AUTOMATION": "1", "TF_INPUT": "0", "TF_PLUGIN_CACHE_DIR": str(cache),
                "TF_VAR_state_passphrase": passphrase})
    if credentials:
        env.update(stack.credentials())
    return env


def _tofu(workdir: Path, env: dict[str, str], *args: str,
          timeout: float) -> subprocess.CompletedProcess[bytes]:
    """Run tofu in its own process group. On a timeout the whole group (tofu and its provider
    plugins) is killed, so nothing local keeps writing; remote work may still be running, which
    callers treat as indeterminate, never as a clean failure."""
    command = [os.environ.get("SKYNET_TOFU", "tofu"), f"-chdir={workdir}", *args]
    try:
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
    except OSError:
        raise WriteError("tofu unavailable", UNAVAILABLE) from None
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                break
            try:
                process.communicate(timeout=10)
                break
            except subprocess.TimeoutExpired:
                continue
        raise WriteError("tofu timed out", UNAVAILABLE) from None
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


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
        # Provider install talks to the public registry: no pin, no API credentials.
        registry = {key: value for key, value in self.env.items()
                    if not key.startswith("SSL_CERT_")
                    and (not key.startswith("TF_VAR_") or key == "TF_VAR_state_passphrase")}
        _require(_tofu(self.dir, registry, "init", "-no-color", "-input=false", "-lockfile=readonly",
                       f"-backend-config=path={state}", timeout=TOFU_SECONDS["init"]),
                 "tofu init failed")

    def validate(self) -> None:
        """Static errors are the revision's own: USAGE, so the revision is held rather than
        re-planned every pass. A validate that cannot run is UNAVAILABLE."""
        result = _tofu(self.dir, self.env, "validate", "-json", "-no-color",
                       timeout=TOFU_SECONDS["validate"])
        if result.returncode == 0:
            return
        try:
            valid = json.loads(result.stdout).get("valid")
        except (ValueError, AttributeError):
            valid = None
        if valid is False:
            raise WriteError(INVALID, USAGE)
        raise WriteError("tofu validate failed", UNAVAILABLE)

    def readonly(self) -> dict[str, frozenset[str]]:
        """Each resource type's computed-only attributes (provider output, never configuration),
        from the provider schema. No credentials: the providers are not configured."""
        raw = _require(_tofu(self.dir, self.env, "providers", "schema", "-json",
                             timeout=TOFU_SECONDS["schema"]), "tofu providers schema failed")
        try:
            result = {}
            for provider in json.loads(raw)["provider_schemas"].values():
                for kind, schema in (provider.get("resource_schemas") or {}).items():
                    attributes = (schema.get("block") or {}).get("attributes") or {}
                    result[kind] = frozenset(
                        name for name, spec in attributes.items()
                        if spec.get("computed") and not spec.get("optional")
                        and not spec.get("required"))
            return result
        except (ValueError, KeyError, TypeError, AttributeError):
            raise WriteError("tofu providers schema unreadable", UNAVAILABLE) from None

    def plan(self, exclude: Collection[str] = ()) -> list[dict[str, Any]]:
        """Save a plan in the workspace (leaving out `exclude` and what depends on it) and return
        its changes."""
        _require(_tofu(self.dir, self.env, "plan", "-no-color", "-input=false",
                       "-detailed-exitcode", f"-out={PLAN_FILE}",
                       *(f"-exclude={address}" for address in exclude),
                       timeout=TOFU_SECONDS["replan" if exclude else "plan"]),
                 "tofu plan failed", 0, 2)
        raw = _require(_tofu(self.dir, self.env, "show", "-json", PLAN_FILE,
                             timeout=TOFU_SECONDS["replan_show" if exclude else "show"]),
                       "tofu show failed")
        try:
            return changes(json.loads(raw), self.env["TF_VAR_state_passphrase"].encode())
        except (ValueError, AttributeError, TypeError):
            raise WriteError("tofu show returned an unreadable plan", UNAVAILABLE) from None

    def show(self) -> str:
        return _require(_tofu(self.dir, self.env, "show", "-no-color", PLAN_FILE, timeout=TOFU_SECONDS["show"]), "tofu show failed").decode("utf-8", "replace")

    def apply(self) -> None:
        try:
            result = _tofu(self.dir, self.env, "apply", "-no-color", "-input=false", PLAN_FILE,
                           timeout=TOFU_SECONDS["apply"])
        except WriteError:  # timed out or lost: remote work may still be landing
            raise WriteError(INDETERMINATE, UNAVAILABLE) from None
        _require(result, "tofu apply failed", 0)

    def clean(self) -> list[dict[str, Any]]:
        """The post-apply plan's changes ([] when clean). Any failure to read it is UNVERIFIED:
        nothing then says the apply was wrong."""
        try:
            result = _tofu(self.dir, self.env, "plan", "-no-color", "-input=false",
                           "-detailed-exitcode", f"-out={VERIFY_FILE}", timeout=TOFU_SECONDS["verify"])
            if result.returncode == 0:
                return []
            if result.returncode != 2:
                raise WriteError(UNVERIFIED, UNAVAILABLE)
            raw = _require(_tofu(self.dir, self.env, "show", "-json", VERIFY_FILE,
                                 timeout=TOFU_SECONDS["verify_show"]), UNVERIFIED)
            found = changes(json.loads(raw), self.env["TF_VAR_state_passphrase"].encode())
        except (WriteError, ValueError, AttributeError, TypeError, KeyError):
            raise WriteError(UNVERIFIED, UNAVAILABLE) from None
        return found or [{"address": "(unreadable)", "delta": {}}]  # exit 2 is never "clean"

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
def workspace(repo: Path, stack: Stack, revision: str, *, ledger: Ledger,
              credentials: bool = True) -> Iterator[Workspace]:
    env = _env(stack, ledger, credentials=credentials)
    with ExitStack() as scope:
        try:  # only the setup: an error inside the caller's body is the caller's to judge
            root = scope.enter_context(deploy.checkout(repo, revision, *stack.paths,
                                                       "invariants.json", "lab.json"))
            if "SSL_CERT_FILE" in env:
                # Go also loads every CA in SSL_CERT_DIR (default /etc/ssl/certs): an empty one
                # makes the pinned certificate the only trust.
                (root / ".no-system-ca").mkdir()
                env["SSL_CERT_DIR"] = str(root / ".no-system-ca")
        except OSError:
            raise WriteError("tofu workspace unavailable", UNAVAILABLE) from None
        yield Workspace(stack, root, env)


def planned(space: Workspace, stack: Stack) -> tuple[list[dict[str, Any]], str, list[str]]:
    """The plan an approval and the executor both judge: every change except the deletes the
    executor never applies, which (with anything depending on them) are excluded and returned as
    deferred, so a pending hard checkpoint never blocks the rest of its stack. The hash covers
    both."""
    found = space.plan()
    deferred = [str(item["address"]) for item in found if deferrable(stack, item)]
    if not deferred:
        return found, plan_hash(stack.name, found), []
    kept = space.plan(exclude=deferred)
    left = {str(item["address"]) for item in kept}
    deferred = sorted({str(item["address"]) for item in found} - left)
    return kept, plan_hash(stack.name, kept, deferred), deferred


def inputs_digest(repo: Path, revision: str, stack: Stack) -> str:
    """The identity of what a stack plans from at `revision`: every input blob but the approval
    itself, so an approval binds to exactly the tree it was made on."""
    listing = deploy._git(repo, "ls-tree", "-r", "--full-tree", revision, "--", *stack.paths,
                          reason="git ls-tree of the stack inputs failed")
    approval = f"tofu/{stack.name}/{APPROVED}"
    kept = [line for line in listing.splitlines() if line.partition("\t")[2] != approval]
    return hashlib.sha256("\n".join(kept).encode()).hexdigest()


# --- host fences -----------------------------------------------------------------------------

def docker_hosts(root: Path) -> dict[int, str]:
    """lab.json's Docker hosts: guest VMID → Docker context (the host label)."""
    try:
        data = json.loads((root / "lab.json").read_text(encoding="utf-8"))
        return {int(host["vmid"]): str(host["label"]) for host in data["docker_hosts"]["hosts"]}
    except (OSError, ValueError, KeyError, TypeError):
        raise WriteError("lab.json unreadable", UNAVAILABLE) from None


def all_docker_hosts(repo: Path, root: Path) -> dict[int, str]:
    """The revision's Docker hosts and main's together: a fence is never lifted by an older tree."""
    with deploy.checkout(repo, MAIN, "lab.json") as main_root:
        return {**docker_hosts(root), **docker_hosts(main_root)}


def fences(stack: Stack, found: list[dict[str, Any]], hosts: dict[int, str]) -> list[str]:
    """The Docker contexts whose host guest this change updates: a deploy there must wait."""
    return sorted({hosts[guest.vmid] for guest in guests(stack, found) if guest.vmid in hosts})


def _answers(context: str) -> bool:
    try:
        watch.docker_reachable(context)
    except WriteError:
        return False
    return True


HOST_POLL_SECONDS = 10


def settle_hosts(contexts: Collection[str]) -> list[str]:
    """The fenced Docker hosts that did not answer within HOST_SETTLE_SECONDS (one shared
    deadline): a guest change that broke its host is a failed change."""
    deadline = time.monotonic() + HOST_SETTLE_SECONDS
    waiting = sorted(contexts)
    while True:
        waiting = [context for context in waiting if not _answers(context)]
        if not waiting or time.monotonic() >= deadline:
            return waiting
        time.sleep(HOST_POLL_SECONDS)


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
    """The file at `path` on the fetched state branch; None only when the branch or the path does
    not exist. Any other git failure raises: a read error must never look like a missing file."""
    if deploy._run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet",
                    f"{STATE_REF}^{{commit}}"]).returncode != 0:
        return None  # no state branch yet
    listed = deploy._run(["git", "-C", str(repo), "ls-tree", "--name-only", STATE_REF, "--", path])
    if listed.returncode != 0:
        raise WriteError("state branch unreadable", UNAVAILABLE)
    if not listed.stdout.strip():
        return None
    result = deploy._run(["git", "-C", str(repo), "cat-file", "blob", f"{STATE_REF}:{path}"])
    if result.returncode != 0:
        raise WriteError("state branch unreadable", UNAVAILABLE)
    return result.stdout


def branch_state(repo: Path, stack: str) -> bytes | None:
    return _blob(repo, f"{stack}/terraform.tfstate")


def applied(repo: Path, stack: str) -> dict[str, Any]:
    raw = _blob(repo, f"{stack}/applied.json")
    try:
        value = json.loads(raw) if raw else {}
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def state_head(repo: Path) -> str:
    """The fetched state branch commit, or "" when the branch does not exist yet."""
    if not fetch_state(repo):
        return ""
    return deploy._git(repo, "rev-parse", STATE_REF, reason="state branch unreadable")


STATE_MOVED = ("the tofu-state branch moved since it was checked, or origin is unreachable; "
               "not recorded (retried next pass)")


def write_branch(repo: Path, files: dict[str, bytes | None], message: str,
                 expect: str | None = None) -> str:
    """Commit `files` (None removes one) to the state branch; fast-forward only, never the
    working tree. With `expect` (a commit, or "" for no branch) it is a compare-and-swap: a branch
    that moved since the caller checked it is refused, never silently rebased onto."""
    # With `expect` the caller has just fetched: it is the parent, and the fast-forward-only push
    # refuses the commit if the branch has moved since.
    parent = (state_head(repo) if expect is None else expect) or None
    with tempfile.TemporaryDirectory(prefix="skynet-state-") as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}

        def git(*args: str, stdin: bytes | None = None) -> str:
            result = deploy._run(["git", "-C", str(repo), *args], stdin=stdin, env=env)
            if result.returncode != 0:
                raise WriteError("state branch commit failed", UNAVAILABLE)
            return result.stdout.decode().strip()

        git("read-tree", *([parent] if parent else ["--empty"]))
        for path, content in files.items():
            if content is None:
                git("update-index", "--force-remove", path)
                continue
            blob = git("hash-object", "-w", "--stdin", stdin=content)
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}")
        tree = git("write-tree")
        if parent and git("rev-parse", f"{parent}^{{tree}}") == tree:
            return parent
        commit = git("commit-tree", tree, *(["-p", parent] if parent else []), "-m", message)
    deploy._git(repo, "push", "--quiet", "origin", f"{commit}:refs/heads/{STATE_BRANCH}",
                reason=STATE_MOVED if expect is not None else
                "state branch push failed (not a fast-forward, or origin unreachable)")
    deploy._git(repo, "update-ref", STATE_REF, commit, reason="state branch unreadable")
    return commit


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def record_state(repo: Path, stack: str, state: bytes | None, record: dict[str, Any] | None,
                 message: str, expect: str | None = None) -> str:
    """Commit this stack's state (and, after a success, its applied record, which also clears a
    hold on that same revision, and only that one, or an unreadable hold, which only a supervised
    `--ignore-hold` success can reach) in one commit."""
    files: dict[str, bytes | None] = {}
    if state is not None:  # None: a stack that holds nothing yet records only its revision
        files[f"{stack}/terraform.tfstate"] = state
    if record is not None:
        files[f"{stack}/applied.json"] = _json_bytes(record)
        if held(repo, stack).get("revision") in (record.get("revision"), "*"):
            files[f"{stack}/held.json"] = None
    return write_branch(repo, files, message, expect)


def held(repo: Path, stack: str) -> dict[str, Any]:
    """The hold on the state branch: a revision the executor must not retry until main moves.
    It lives in git, so it survives an ops VM rebuild."""
    raw = _blob(repo, f"{stack}/held.json")
    if raw is None:
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        return {"revision": "*", "reason": "unreadable hold"}  # fail closed: hold everything
    return value if isinstance(value, dict) else {"revision": "*", "reason": "unreadable hold"}


PREHOLD = "apply in progress; a recorded success clears this"


def set_hold(repo: Path, stack: str, revision: str, reason: str, operation: str) -> None:
    write_branch(repo, {f"{stack}/held.json": _json_bytes(
        {"revision": revision, "reason": reason, "operation": operation})},
        f"tofu-state({stack}): hold {revision[:12]} ({operation})")


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


def _digest(content: bytes | None) -> str:
    return hashlib.sha256(content).hexdigest() if content is not None else "absent"


def _base_path(ledger: Ledger, stack: str) -> Path:
    """The digest of the branch state the local file was last synced to or pushed as."""
    return state_dir(ledger) / f"{stack}.base"


def _base(ledger: Ledger, stack: str) -> str | None:
    try:
        return _base_path(ledger, stack).read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None
    except OSError:
        raise WriteError("local tofu state base unreadable", UNAVAILABLE) from None


def _set_base(ledger: Ledger, stack: str, content: bytes | None) -> None:
    try:
        _base_path(ledger, stack).parent.mkdir(parents=True, exist_ok=True)
        common.atomic_write_text(_base_path(ledger, stack), _digest(content) + "\n")
    except OSError:
        raise WriteError("local tofu state base unwritable", UNAVAILABLE) from None


def classify(ledger: Ledger, stack: str, remote: bytes | None) -> str:
    """How the local cache relates to the branch: `missing`, `same`, `pending` (local writes on top
    of the current branch), `stale` (the branch moved, local did not), `diverged` (both moved), or
    `bootstrap` (no branch and no base: a first state of unproven provenance, pushed only by an
    apply at this stack that used it)."""
    local = _read(local_state(ledger, stack))
    if local is None:
        return "missing"
    if local == remote:
        return "same"
    base = _base(ledger, stack)
    if remote is None and base is None:
        return "bootstrap"
    if remote is None and base != "absent":
        return "diverged"  # the branch lost a state it had: never treat that as a stale cache
    if base == _digest(remote):
        return "pending"
    if base == _digest(local):
        return "stale"
    return "diverged"


DIVERGED = "local tofu state and the tofu-state branch both changed; reconcile by hand"
UNADOPTED_DELETES = ("local tofu state has no branch and no base, and its plan deletes; not "
                     "adopted (a stray copy of another stack's state?)")
UNADOPTED = ("local tofu state has no branch and no base; recorded only after an apply at its "
             "stack accepts it")


def adopt(ledger: Ledger, stack: str) -> None:
    """Make a bootstrap state this stack's (base `absent`: pending writes on no branch) once an
    apply's plan has accepted it. sync_state has already refused every other base-less case."""
    if _read(local_state(ledger, stack)) is not None and _base(ledger, stack) is None:
        _set_base(ledger, stack, None)


def sync_state(repo: Path, ledger: Ledger, stack: str) -> bytes | None:
    """Make the local state equal the branch and return it. A missing or stale local file is
    rebuilt from git; pending local writes (an unrecorded apply) are pushed before anything else;
    a divergence is refused. A bootstrap state is returned unpushed: this apply's plan must accept
    it (a stray copy of another root plans deletes, which are refused) before `adopt` makes it
    recordable."""
    fetch_state(repo)
    remote = branch_state(repo, stack)
    kind = classify(ledger, stack, remote)
    path = local_state(ledger, stack)
    if kind in ("missing", "stale"):
        _hydrate(ledger, stack, remote)
        return remote
    if kind == "diverged":
        raise WriteError(DIVERGED, UNAVAILABLE)
    if kind == "bootstrap":
        return _read(path)
    if kind == "pending":
        _record(repo, ledger, stack, None, f"tofu-state({stack}): record unpushed local state")
    else:
        _set_base(ledger, stack, remote)
    return _read(path)


def _hydrate(ledger: Ledger, stack: str, remote: bytes | None) -> None:
    """Make a missing or stale local cache the branch's state (the branch is the truth)."""
    _write(local_state(ledger, stack), remote)
    _set_base(ledger, stack, remote)


def _state_copy(repo: Path, ledger: Ledger, stack: str, into: Path) -> Path:
    """A read-only copy of the current state: pending local writes if any, else the branch. A
    missing or stale local cache is rebuilt on the way, when no write holds the tofu lock."""
    remote = branch_state(repo, stack) if fetch_state(repo) else None
    kind = classify(ledger, stack, remote)
    if kind in ("missing", "stale") and remote is not None:
        try:
            with ledger.lock(LOCK):
                if classify(ledger, stack, remote) in ("missing", "stale"):
                    _hydrate(ledger, stack, remote)
        except WriteError:
            pass  # a write holds the lock (or the cache is unwritable): the copy still serves
    if kind == "diverged":
        raise WriteError(DIVERGED, UNAVAILABLE)
    content = _read(local_state(ledger, stack)) if kind in ("pending", "bootstrap") else remote
    path = into / f"{stack}.tfstate"
    if content is not None:
        path.write_bytes(content)
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
    restorable: list[pve.Guest] = field(default_factory=list)  # config saved: restored on rollback
    taken: list[pve.Guest] = field(default_factory=list)  # snapshot requested: pruned
    power: dict[pve.Guest, str] = field(default_factory=dict)
    config: dict[pve.Guest, dict[str, Any]] = field(default_factory=dict)
    excluded: frozenset[int] = frozenset()
    deferred: list[str] = field(default_factory=list)  # hard checkpoints left out of the plan
    readonly: dict[str, frozenset[str]] = field(default_factory=dict)  # computed-only attributes
    fences: list[str] = field(default_factory=list)  # Docker contexts whose host is updated


def _refused(ledger: Ledger, name: str, reason: str, code: int = USAGE, source: str = "") -> Operation:
    return writepath.refuse(Operation("tofu", f"tofu/{name}"[:200], source), ledger, reason, code)


def apply(repo: Path, name: str, *, revision: str | None = None, ledger: Ledger,
          refresh: bool = True, settle: bool = True, ignore_hold: bool = False) -> Operation:
    """Apply one stack at one merged revision through the write-path shape. A held revision is
    refused under the write lock unless a supervised run passes `ignore_hold`. `pending` settles
    interrupted applies once per pass and passes `settle=False`."""
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
    if settle:
        settle_interrupted(repo, ledger)
    operation = Operation("tofu", f"tofu/{name}", target)
    saved = _Saved(snapshot=f"skynet-{operation.id}")
    state = local_state(ledger, name)
    fence = ExitStack()  # the deploy lock and host fences, held until the write is recorded
    try:
        with workspace(repo, stack, target, ledger=ledger) as space, fence:
            def preflight() -> None:
                if not deploy.merged(repo, target):
                    raise WriteError("revision is not merged to origin/main", USAGE)
                saved.before = sync_state(repo, ledger, name)
                if not ignore_hold and is_held(repo, name, target, ledger):  # re-checked in the lock
                    raise WriteError(HELD, UNAVAILABLE)
                first = classify(ledger, name, branch_state(repo, name)) == "bootstrap"
                space.init(state)
                space.validate()
                saved.found, saved.hash, saved.deferred = planned(space, stack)
                operation.context = {"stack": name, "hash": saved.hash, "snapshot": saved.snapshot,
                                     "changes": summary(saved.found),
                                     **({"deferred": saved.deferred} if saved.deferred else {})}
                if first and (saved.deferred or any(
                        REFUSED_ACTIONS & set(item["actions"]) for item in saved.found)):
                    # A first state of unproven provenance (a stray copy of another root plans
                    # deletes) is never adopted, and nothing it would delete is applied.
                    raise WriteError(UNADOPTED_DELETES, USAGE)
                if not saved.found:
                    return
                approval = space.approved()
                if approval is None:
                    raise WriteError(NO_APPROVAL, USAGE)
                if approval.get("inputs") != inputs_digest(repo, target, stack):
                    raise WriteError(STALE_APPROVAL, USAGE)
                if approval.get("hash") != saved.hash:
                    raise WriteError(MISMATCH, USAGE)
                saved.excluded = all_excluded(repo, space.root)
                check(stack, saved.found, saved.excluded)
                if guests(stack, saved.found):
                    saved.readonly = space.readonly()
                    saved.fences = fences(stack, saved.found, all_docker_hosts(repo, space.root))

            def snapshot() -> _Saved:
                if saved.fences:
                    # Before anything changes: a deploy on this host (whose verification the guest
                    # change would fail, rolling back and opening a revert PR) waits for this write,
                    # and watch sees the fence rather than an outage. Busy: retried next pass.
                    fence.enter_context(ledger.lock())
                    for context in saved.fences:
                        fence.enter_context(ledger.lock(writepath.fence(context)))
                    operation.context["fences"] = saved.fences
                adopt(ledger, name)  # the approved (or empty) plan accepted this state
                for guest in guests(stack, saved.found):
                    try:
                        saved.power[guest] = pve.status(guest)
                        saved.config[guest] = pve.config(guest)
                        if pve.pending(guest):  # a restore could not prove it came back
                            raise WriteError(f"{guest} has pending config changes; apply or "
                                             "revert them first", USAGE)
                        saved.restorable.append(guest)
                        if not pve.snapshottable(saved.config[guest]):
                            # The rollback restores the saved config, never the snapshot.
                            operation.note("snapshot", "skipped",
                                           f"{guest}: bind mount; no fallback snapshot")
                            continue
                        saved.taken.append(guest)  # before the request: a failed create may leave one
                        # Durable before the request: a crash here (before the `started` record)
                        # leaves an intent the next pass cleans up.
                        _intend(ledger, guest, saved.snapshot, operation.id)
                        pve.create(guest, saved.snapshot, excluded=saved.excluded)
                    except WriteError as error:
                        if error.code == USAGE:  # held; a snapshot left behind is queued
                            _prune(saved, operation, ledger)
                            raise
                        if _prune(saved, operation, ledger):
                            raise WriteError(f"could not snapshot {guest}; nothing applied",
                                             UNAVAILABLE) from None
                        # A snapshot may remain: hold rather than add another one every minute.
                        raise WriteError(f"could not snapshot {guest}; nothing applied, but "
                                         f"{saved.snapshot} could not be cleaned up") from None
                operation.context["guests"] = [str(guest) for guest in saved.restorable]
                if saved.found and not _prehold(repo, ledger, name, target, operation):
                    _prune(saved, operation, ledger)
                    raise WriteError("could not record the pre-apply hold; nothing applied",
                                     UNAVAILABLE)
                return saved

            def execute(state_: _Saved) -> None:
                if state_.found:
                    space.apply()

            def verify(state_: _Saved) -> dict[str, Any]:
                if state_.found:
                    remaining = space.clean()
                    if remaining:
                        operation.note("post-apply-plan", "dirty", ", ".join(
                            sorted(str(item["address"]) for item in remaining))[:500])
                        if overlaps(state_.found, remaining):
                            raise WriteError(NOT_LANDED, FAILED)
                        raise WriteError(DRIFTED, UNAVAILABLE)
                if state_.fences:
                    down = settle_hosts(state_.fences)
                    if down:
                        operation.note("hosts", "down", ", ".join(down))
                        raise WriteError(HOST_DOWN, FAILED)
                    operation.note("hosts", "ok", ", ".join(state_.fences))
                return {"changes": len(state_.found), "hash": state_.hash, "post_apply_plan": "clean"}

            def rollback(state_: _Saved, error: WriteError) -> str:
                if error.reason in UNSETTLED or not reversible(stack, state_.found, state_.readonly):
                    try:
                        _record(repo, ledger, name, None, f"tofu-state({name}): after failed "
                                f"{operation.id}")
                        operation.note("state", "ok", "the state tofu wrote is recorded")
                    except WriteError as record_error:
                        operation.note("state", "failed", record_error.reason)
                    if error.reason == UNVERIFIED:
                        raise WriteError("applied but unverified; not rolled back, operator check "
                                         f"(snapshots {state_.snapshot} kept)")
                    if error.reason == INDETERMINATE:
                        raise WriteError("apply did not finish; not rolled back while remote work "
                                         f"may still land, operator check (snapshots "
                                         f"{state_.snapshot} kept)")
                    if error.reason == DRIFTED:
                        raise WriteError("applied, but the re-plan is dirty elsewhere; not rolled "
                                         f"back, operator check (snapshots {state_.snapshot} kept)")
                    raise WriteError("no automatic inverse for these changes; operator recovery "
                                     f"(snapshots {state_.snapshot} kept)")
                failures = []
                for guest in reversed(state_.restorable):  # every guest, even after one fails
                    try:
                        pve.restore(guest, state_.config[guest], state_.power[guest],
                                    excluded=state_.excluded)
                        # Prove the restore rather than trust RESTORE_COVERS: the whole config
                        # must be what it was before the apply, with nothing left pending.
                        differs = _config_diff(state_.config[guest], pve.config(guest))
                        if differs:
                            raise WriteError("config differs after rollback: " + ", ".join(differs))
                        waiting = pve.pending(guest)
                        if waiting:
                            raise WriteError("changes still pending after rollback: "
                                             + ", ".join(waiting))
                    except WriteError as rollback_error:
                        failures.append(f"{guest}: {rollback_error.reason}")
                if state_.fences and not failures:
                    failures += [f"{context}: Docker host did not answer after the restore"
                                 for context in settle_hosts(state_.fences)]
                if failures:
                    try:
                        _record(repo, ledger, name, None, f"tofu-state({name}): after failed "
                                f"rollback {operation.id}")
                        operation.note("state", "ok", "the state tofu wrote is recorded")
                    except WriteError as record_error:
                        operation.note("state", "failed", record_error.reason)
                    raise WriteError("guest rollback failed: " + "; ".join(failures)
                                     + f" (snapshots {state_.snapshot} kept)")
                _write(state, state_.before)
                _prune(state_, operation, ledger)
                return "rolled-back"

            def reconcile() -> dict[str, Any]:
                # An interrupted apply is settled only by settle_interrupted (alarm, hold, kept
                # snapshots); if it could not run yet, wait for it rather than paper over it.
                raise WriteError(NOT_SETTLED, UNAVAILABLE)

            def commit(state_: _Saved) -> None:
                _prune(state_, operation, ledger)
                record = {"revision": target, "hash": state_.hash, "operation": operation.id,
                          **({"deferred": state_.deferred} if state_.deferred else {})}
                try:
                    _record(repo, ledger, name, record,
                            f"tofu-state({name}): {operation.id} applied {target[:12]}")
                except WriteError:
                    _unrecorded(ledger, name, record)  # the persistence step pushes it later
                    raise
                _clear_local_hold(ledger, name, target)

            result = writepath.run(operation, ledger, preflight=preflight, snapshot=snapshot,
                                   execute=execute, verify=verify, rollback=rollback,
                                   reconcile=reconcile, commit=commit, lock=LOCK)
    except WriteError as error:  # the workspace itself (credentials, checkout) is unavailable
        return _refused(ledger, name, error.reason, error.code, target)
    finally:
        _drop_intents(ledger, operation.id)  # resolved: a record now carries this operation
    if result.outcome in HELD_OUTCOMES or (result.outcome == "refused" and result.code != UNAVAILABLE):
        _hold(repo, ledger, name, target, str(result.reason), result)
    if saved.deferred:
        _announce_deferred(ledger, name, saved.deferred, result)
    return result


def _announce_deferred(ledger: Ledger, name: str, deferred: list[str], operation: Operation) -> None:
    """A deferred hard checkpoint alerts once per address: it waits for a human, never silently."""
    new = [address for address in deferred if not _announced(ledger, f"{name}:deferred:{address}")]
    if not new:
        return
    failure = alert.send(f"skynet: tofu/{name} deferred {len(new)} hard-checkpoint change(s)",
                         "not applied (delete/replace/forget; a supervised path): "
                         + ", ".join(new)[:800], priority=1)
    operation.note("deferred", "announced", ", ".join(new)[:500])
    operation.note("alert", "failed" if failure else "ok", failure)


def _record(repo: Path, ledger: Ledger, stack: str, record: dict[str, Any] | None, message: str) -> None:
    """Push the local state only when it is pending writes on top of the current branch (or equal
    to it): a stale or diverged cache must never regress newer state, and a first state no apply
    at this stack adopted is never pushed."""
    state = _read(local_state(ledger, stack))
    parent = state_head(repo)
    remote = branch_state(repo, stack) if parent else None
    if state is None:
        # A stack that has never held a resource: an empty plan's success records its revision
        # alone. With state on the branch, a missing local file is a cache to rebuild, not this.
        if remote is not None or record is None:
            raise WriteError("no local tofu state to record", UNAVAILABLE)
        record_state(repo, stack, None, record, message, expect=parent)
        return
    kind = classify(ledger, stack, remote)
    if kind == "diverged":
        raise WriteError(DIVERGED, UNAVAILABLE)
    if kind == "bootstrap":
        raise WriteError(UNADOPTED, UNAVAILABLE)
    if kind == "stale":
        raise WriteError("local tofu state is older than the branch; not recorded", UNAVAILABLE)
    record_state(repo, stack, state, record, message, expect=parent)  # only onto what was checked
    _set_base(ledger, stack, state)


def _prune(saved: _Saved, operation: Operation, ledger: Ledger | None = None) -> bool:
    """Delete this run's snapshot wherever it exists; True when none is left behind. A snapshot
    that could not be deleted goes on the cleanup queue (retried every pass) and alerts once."""
    left = []
    for guest in saved.taken:
        try:
            if pve.exists(guest, saved.snapshot):
                pve.delete(guest, saved.snapshot, excluded=saved.excluded)
        except WriteError as error:
            operation.note("prune", "failed", f"{guest}: {error.reason}")
            left.append(guest)
    saved.taken = []
    if left and ledger is not None:
        _queue_cleanup(ledger, left, saved.snapshot, operation)
    return not left


def _queue_cleanup(ledger: Ledger, guests_: list[pve.Guest], snapshot: str,
                   operation: Operation) -> None:
    entries = [{"node": g.node, "kind": g.kind, "vmid": g.vmid, "snapshot": snapshot} for g in guests_]
    try:
        _update_facts(ledger, lambda facts: _queue(facts).extend(entries))
    except WriteError:
        operation.note("cleanup-queue", "failed", "cleanup queue unwritable")
    failure = alert.send(f"skynet: {operation.target} snapshot cleanup failed",
                         f"{snapshot} left on {', '.join(str(g) for g in guests_)}; retried each pass",
                         priority=1)
    operation.note("alert", "failed" if failure else "ok", failure)


def _intend(ledger: Ledger, guest: pve.Guest, snapshot: str, operation: str) -> None:
    """Record a snapshot about to be requested, before the request (raises if it cannot)."""
    entry = {"node": guest.node, "kind": guest.kind, "vmid": guest.vmid, "snapshot": snapshot,
             "intent": operation}
    _update_facts(ledger, lambda facts: _queue(facts).append(entry))


def _recorded(ledger: Ledger, operation: str) -> bool:
    try:
        return any(entry.get("id") == operation for entry in ledger.entries())
    except WriteError:
        return True  # unknown: keep the snapshot rather than guess it is an orphan


def _drop_intents(ledger: Ledger, operation: str) -> None:
    """Once a record carries the operation, its snapshots are owned by that record (pruned, kept
    for an operator, or settled); the intents are no longer needed."""
    if not _recorded(ledger, operation):
        return  # a crash before any record: leave them for retry_cleanup

    def drop(facts: dict[str, Any]) -> None:
        if "_cleanup" in facts:
            facts["_cleanup"] = [item for item in _queue(facts)
                                 if not (isinstance(item, dict) and item.get("intent") == operation)]
    try:
        _update_facts(ledger, drop)
    except WriteError:
        pass


def _unrecorded(ledger: Ledger, name: str, record: dict[str, Any]) -> None:
    try:
        _update_facts(ledger, lambda facts: _store(facts).update({name: record}))
    except WriteError:
        pass  # the state is still pushed (pending local writes); the record needs a human


def _clear_local_hold(ledger: Ledger, name: str, revision: str) -> None:
    def clear(facts: dict[str, Any]) -> None:
        fact = facts.get(name)
        if isinstance(fact, dict) and fact.get("held") == revision:
            fact.pop("held")
    try:
        _update_facts(ledger, clear)
    except WriteError:
        pass


def persist_pending(repo: Path, ledger: Ledger) -> list[dict[str, Any]]:
    """Make every stack's local state agree with the branch, under the tofu lock, before any hold
    is consulted: rebuild a missing or stale cache from the branch (so a rebuilt ops VM heals on
    its first pass), and push local state the branch lacks (and an applied record whose push
    failed). It never runs infrastructure: a held revision stays held, but its state still reaches
    git. The state branch is already fetched (`pending`)."""
    try:
        with ledger.lock(LOCK):
            results: list[dict[str, Any]] = []
            done: list[str] = []
            store = _store(_facts(ledger))
            for name in STACKS:
                record = store.get(name) if isinstance(store.get(name), dict) else None
                try:
                    remote = branch_state(repo, name)
                    kind = classify(ledger, name, remote)
                    if kind in ("missing", "stale") and remote is not None:
                        _hydrate(ledger, name, remote)
                        results.append({"target": f"tofu/{name}", "outcome": "success",
                                        "reason": "local state rebuilt from tofu-state"})
                        kind = "same"
                    if kind != "pending" and record is None:
                        continue
                    _record(repo, ledger, name, record,
                            f"tofu-state({name}): persist unpushed local state")
                except WriteError as error:
                    results.append({"target": f"tofu/{name}", "outcome": "unavailable",
                                    "code": UNAVAILABLE, "reason": f"state not persisted: {error.reason}"})
                    continue
                done.append(name)
                if record:
                    _clear_local_hold(ledger, name, str(record.get("revision")))
                results.append({"target": f"tofu/{name}", "outcome": "success",
                                "reason": "unpushed state persisted to tofu-state"})
            def forget(facts: dict[str, Any]) -> None:
                for name in done:
                    _store(facts).pop(name, None)
            if done:
                _update_facts(ledger, forget)
            return results
    except WriteError as error:
        if error.reason == writepath.LOCK_BUSY:
            return []
        raise


def retry_cleanup(repo: Path, ledger: Ledger) -> list[dict[str, Any]]:
    """Retry queued snapshot deletions under the tofu lock; an item leaves the queue only when
    its snapshot is gone. An entry naming an excluded guest never reaches Proxmox: it is dropped
    and alerts."""
    try:
        with ledger.lock(LOCK):
            queue = list(_queue(_facts(ledger)))
            if not queue:
                return []
            excluded = main_excluded(repo)
            done, results = [], []
            for item in queue:
                if isinstance(item, dict) and item.get("intent"):
                    if _recorded(ledger, str(item["intent"])):
                        done.append(item)
                        continue  # its record owns the snapshot now
                    # No record at all: a crash in the snapshot stage; nothing was applied.
                try:
                    guest = pve.Guest(str(item["node"]), str(item["kind"]), int(item["vmid"]))
                    if guest.vmid in excluded:
                        result = {"target": f"cleanup/{guest}", "outcome": "refused",
                                  "code": USAGE, "reason": "queued cleanup names an excluded guest; "
                                  "dropped, never sent to Proxmox"}
                        _alert(result, f"skynet: tofu cleanup refused for excluded {guest}")
                        results.append(result)
                        done.append(item)
                        continue
                    if pve.exists(guest, str(item["snapshot"])):
                        pve.delete(guest, str(item["snapshot"]), excluded=excluded)
                    results.append({"target": f"cleanup/{guest}", "outcome": "success",
                                    "reason": f"{item['snapshot']} removed"})
                    done.append(item)
                except (WriteError, KeyError, TypeError, ValueError):
                    pass  # kept: retried next pass

            def forget(facts: dict[str, Any]) -> None:
                facts["_cleanup"] = [item for item in _queue(facts) if item not in done]
            _update_facts(ledger, forget)  # entries queued meanwhile are kept
            return results
    except WriteError:  # a write holds the lock: retry next pass
        return []


def settle_interrupted(repo: Path, ledger: Ledger) -> list[dict[str, Any]]:
    """An apply interrupted mid-write cannot be shown safe: record the state tofu wrote (only if it
    is newer than the branch), keep the snapshots, hold the revision, and close the operation as
    rollback-failed so a human looks. Runs under the write lock, so a live apply is never settled."""
    try:
        with ledger.lock(LOCK):
            return [_settle(repo, ledger, entry) for entry in ledger.unfinished("tofu")]
    except WriteError:  # a write holds the lock (or the record is unavailable): settle next pass
        return []


def _settle(repo: Path, ledger: Ledger, entry: dict[str, Any]) -> dict[str, Any]:
    context = entry.get("context") or {}
    stack = str(context.get("stack", ""))
    note = "state not recorded"
    if stack in STACKS:
        try:
            _record(repo, ledger, stack, None, f"tofu-state({stack}): after interrupted {entry.get('id')}")
            note = "state recorded as tofu wrote it"
        except WriteError as error:
            note = f"state not recorded: {error.reason}"
    operation = writepath.settle(ledger, entry, alarm=f"interrupted tofu apply; {note}; "
                                 f"snapshots {context.get('snapshot', '?')} kept; check by hand")
    if stack in STACKS and entry.get("source"):
        _hold(repo, ledger, stack, str(entry["source"]), "interrupted apply", operation)
    return writepath.report(operation)


# --- pending ---------------------------------------------------------------------------------

def _facts_path(ledger: Ledger) -> Path:
    return state_dir(ledger) / "pending.json"


def _facts(ledger: Ledger) -> dict[str, Any]:
    try:
        value = json.loads(_facts_path(ledger).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _save_facts(ledger: Ledger, facts: dict[str, Any]) -> None:
    try:
        _facts_path(ledger).parent.mkdir(parents=True, exist_ok=True)
        common.atomic_write_text(_facts_path(ledger), json.dumps(facts, sort_keys=True) + "\n")
    except OSError:
        raise WriteError("tofu facts unwritable", UNAVAILABLE) from None


FACTS_LOCK = "tofu-facts"  # pending.json's own lock, held only for one read-modify-write
_T = TypeVar("_T")


def _update_facts(ledger: Ledger, change: Callable[[dict[str, Any]], _T]) -> _T:
    """Apply `change` to pending.json under its own lock, so the timer's counters and a live
    apply's cleanup intents never overwrite each other. Written only when something changed;
    raises WriteError when it cannot be. `change` must not update the facts itself."""
    with ledger.lock(FACTS_LOCK):
        facts = _facts(ledger)
        before = json.dumps(facts, sort_keys=True)
        result = change(facts)
        if json.dumps(facts, sort_keys=True) != before:
            _save_facts(ledger, facts)
        return result


def _queue(facts: dict[str, Any]) -> list[Any]:
    """The snapshot cleanup queue in `facts`, created if absent."""
    if not isinstance(facts.get("_cleanup"), list):
        facts["_cleanup"] = []
    queue: list[Any] = facts["_cleanup"]
    return queue


def _store(facts: dict[str, Any]) -> dict[str, Any]:
    """The applied records whose push failed, by stack, created if absent."""
    if not isinstance(facts.get("_unrecorded"), dict):
        facts["_unrecorded"] = {}
    store: dict[str, Any] = facts["_unrecorded"]
    return store


def _now() -> float:
    return time.time()


def _set_failures(ledger: Ledger, name: str, revision: str, count: int) -> None:
    """Reset this revision's count of consecutive `unavailable` passes (and with it the backoff
    and the reminder clock). Merged into the stack's fact so it never erases a local hold."""
    def count_(facts: dict[str, Any]) -> None:
        known = facts.get(name)
        fact: dict[str, Any] = known if isinstance(known, dict) else {}
        kept = {key: value for key, value in fact.items() if key == "held"}
        facts[name] = {**kept, "revision": revision, "failures": count}
    try:
        _update_facts(ledger, count_)
    except WriteError:
        pass


def _bump(ledger: Ledger, name: str, revision: str) -> tuple[int, bool]:
    """One more `unavailable` pass: (the count, whether to alert now). The stack is next tried
    after a doubling backoff; the third failure alerts, and a failure persisting a day past its
    last alert alerts again (local facts: losing them only delays an alert)."""
    now = _now()

    def bump(facts: dict[str, Any]) -> tuple[int, bool]:
        known = facts.get(name)
        fact: dict[str, Any] = known if isinstance(known, dict) else {}
        if fact.get("revision") != revision:
            fact = {key: value for key, value in fact.items() if key == "held"}
        count = int(fact.get("failures", 0)) + 1
        alerted = float(fact.get("alerted", 0))
        due = count == ALERT_AFTER_FAILURES or (count > ALERT_AFTER_FAILURES
                                                and now - alerted >= REMIND_SECONDS)
        facts[name] = {**fact, "revision": revision, "failures": count,
                       "due": now + min(BACKOFF_SECONDS * 2 ** (count - 1), BACKOFF_MAX),
                       **({"alerted": now} if due else {})}
        return count, due
    try:
        return _update_facts(ledger, bump)
    except WriteError:
        return 0, False


def _backoff(ledger: Ledger, name: str, revision: str) -> float | None:
    """When an unavailable revision is next due, if that is still ahead."""
    known = _facts(ledger).get(name)
    if isinstance(known, dict) and known.get("revision") == revision:
        due = known.get("due")
        if isinstance(due, int | float) and due > _now():
            return float(due)
    return None


def _failures(ledger: Ledger, name: str, revision: str) -> int:
    known = _facts(ledger).get(name)
    if isinstance(known, dict) and known.get("revision") == revision:
        return int(known.get("failures", 0))
    return 0


def _hold(repo: Path, ledger: Ledger, name: str, revision: str, reason: str,
          operation: Operation) -> None:
    """Hold `revision` so the timer never retries it, but only when it is the revision the timer
    would pick (the newest input commit on main): a manual run of another revision must not
    replace that hold. The hold goes to git (surviving a rebuild) and to a local fallback; a hold
    git did not take alerts, so a retry loop can never run silently."""
    try:
        current = input_revision(repo, STACKS[name])
    except WriteError:
        current = None
    if current is not None and current != revision:
        operation.note("hold", "skipped", "not the revision main would apply")
        return
    _local_hold(ledger, name, revision)
    try:
        set_hold(repo, name, revision, reason, operation.id)
    except WriteError as error:
        try:
            already = held(repo, name).get("revision") == revision  # the pre-apply hold
        except WriteError:
            already = False
        if already:
            operation.note("hold", "ok", f"pre-apply hold stands (reason not updated: {error.reason})")
            return
        operation.note("hold", "failed", f"{error.reason}; held locally only")
        failure = alert.send(f"skynet: tofu/{name} hold not recorded in git",
                             f"{writepath.line(writepath.report(operation))} — held on this VM only",
                             priority=1)
        operation.note("alert", "failed" if failure else "ok", failure)
        return
    operation.note("hold", "ok", "not retried until main moves")


def _prehold(repo: Path, ledger: Ledger, name: str, revision: str, operation: Operation) -> bool:
    """Hold the revision *before* it executes: a crash anywhere after this leaves it held, never
    retried. The success commit clears it (same revision, same commit as the state). A revision
    the timer would not pick needs no hold. False when the hold could not be recorded in git."""
    try:
        if input_revision(repo, STACKS[name]) != revision:
            return True
        set_hold(repo, name, revision, PREHOLD, operation.id)
    except WriteError as error:
        operation.note("prehold", "failed", error.reason)
        return False
    _local_hold(ledger, name, revision)
    operation.note("prehold", "ok", "held until a recorded success")
    return True


def _local_hold(ledger: Ledger, name: str, revision: str) -> None:
    def hold(facts: dict[str, Any]) -> None:
        known = facts.get(name)
        facts[name] = {**(known if isinstance(known, dict) else {}), "held": revision}
    try:
        _update_facts(ledger, hold)
    except WriteError:
        pass  # the git hold is the durable one; this is only its fallback


def is_held(repo: Path, name: str, revision: str, ledger: Ledger | None = None) -> bool:
    local = _facts(ledger).get(name) if ledger is not None else None
    if isinstance(local, dict) and local.get("held") == revision:
        return True
    return held(repo, name).get("revision") in (revision, "*")


def _alert(result: dict[str, Any], title: str) -> None:
    failure = alert.send(title, writepath.line(result), priority=1)
    result.setdefault("steps", []).append(
        {"step": "alert", "outcome": "failed" if failure else "ok", **({"detail": failure}
                                                                      if failure else {})})


def _count(ledger: Ledger, name: str, target: str, result: dict[str, Any]) -> None:
    """Unavailability changes nothing live, so it is retried (with a backoff), never held. Waiting
    on another write (the lock, an unsettled interruption) is not a failure at all. Any other
    outcome resets the count; the third `unavailable` pass in a row alerts, then daily."""
    if result.get("code") != UNAVAILABLE or result.get("outcome") not in ("refused", "unavailable"):
        _set_failures(ledger, name, target, 0)
        return
    if result.get("reason") in CONTENDED:
        return
    count, due = _bump(ledger, name, target)
    if due:
        _alert(result, f"skynet: tofu/{name} unavailable {count} passes running")


def pending(repo: Path, *, ledger: Ledger, deadline: float | None = None) -> list[dict[str, Any]]:
    """Apply each stack whose newest input commit on main is not the applied one (main is already
    fetched). A revision that was refused, failed, rolled back, or interrupted is held on the state
    branch and retried only when main moves; a hold alerts once, unless the outcome already
    alerted. An unavailable pass is retried (see `_count`)."""
    fetch_state(repo)  # once per pass; a write fetches again under the lock
    results = settle_interrupted(repo, ledger)
    results += persist_pending(repo, ledger)
    results += retry_cleanup(repo, ledger)
    for name, stack in STACKS.items():
        target = input_revision(repo, stack)
        if target is None or applied(repo, name).get("revision") == target:
            continue
        try:
            results.append(_pending_stack(repo, ledger, name, target, deadline))
        except OSError:  # one stack's local failure must never stop the others
            result: dict[str, Any] = {"target": f"tofu/{name}", "source": target,
                                      "outcome": "unavailable", "code": UNAVAILABLE,
                                      "reason": "local tofu files unavailable"}
            _count(ledger, name, target, result)
            results.append(result)
    return results


def _pending_stack(repo: Path, ledger: Ledger, name: str, target: str,
                   deadline: float | None) -> dict[str, Any]:
    if deadline is not None and time.monotonic() + STACK_BUDGET > deadline:
        return {"target": f"tofu/{name}", "source": target, "outcome": "deferred",
                "reason": "not enough of this pass left for a full apply and rollback"}
    if is_held(repo, name, target, ledger):
        return _held(repo, ledger, name, target)
    due = _backoff(ledger, name, target)
    if due is not None:
        return {"target": f"tofu/{name}", "source": target, "outcome": "backoff",
                "reason": f"unavailable; retried in {int(due - _now())} s"}
    result = writepath.report(apply(repo, name, revision=target, ledger=ledger, refresh=False,
                                    settle=False))
    _count(ledger, name, target, result)
    holds = {step.get("outcome") for step in result.get("steps", []) if step.get("step") == "hold"}
    # A hold git refused already alerted in _hold; a durable hold alerts once here.
    if "ok" in holds and result.get("outcome") not in writepath.ALARMS:
        _alert(result, f"skynet: tofu/{name} held")
    # Announced only when this result alerted: its hold step, or its own alarm. A hold it did
    # not announce (a pre-apply hold a run left as `unavailable`) alerts through _held next pass.
    if holds & {"ok", "failed"} or result.get("outcome") in writepath.ALARMS:
        if is_held(repo, name, target, ledger):
            _announced(ledger, _hold_key(repo, name, target))
    return result


def _hold_key(repo: Path, name: str, target: str) -> str:
    hold = held(repo, name)
    if hold.get("revision") in (target, "*"):
        return f"{name}:{hold.get('revision')}:{hold.get('operation', '')}"
    return f"{name}:{target}:local"


def _announced(ledger: Ledger, key: str) -> bool:
    """Mark a hold as alerted; True when it already was. Local: a rebuilt VM re-alerts once."""
    def mark(facts: dict[str, Any]) -> bool:
        known = facts.get("_hold_alerts")
        keys: list[Any] = known if isinstance(known, list) else []
        if key in keys:
            return True
        facts["_hold_alerts"] = [*keys, key][-50:]
        return False
    try:
        return _update_facts(ledger, mark)
    except WriteError:
        return False  # alert again rather than risk a silent hold


def _held(repo: Path, ledger: Ledger, name: str, target: str) -> dict[str, Any]:
    """A held revision's result. Every hold alerts once, however it was set: a hold nobody
    announced (an unreadable held.json, a pre-apply hold a crash left before any record, a
    manual run's refusal) must never stop a stack silently."""
    hold = held(repo, name)
    reason = "revision refused or failed; awaiting a new merge"
    if hold.get("revision") == "*":
        reason = ("held.json unreadable; every revision held until a supervised "
                  f"`skynet tofu apply {name} --ignore-hold` succeeds")
    elif hold.get("reason") == PREHOLD and not _recorded(ledger, str(hold.get("operation"))):
        reason = ("pre-apply hold with no operation record: nothing executed; check, then "
                  f"`skynet tofu apply {name} --ignore-hold`")
    result = {"target": f"tofu/{name}", "source": target, "outcome": "held", "reason": reason}
    if not _announced(ledger, _hold_key(repo, name, target)):
        _alert(result, f"skynet: tofu/{name} held")
    return result


# --- plan and drift (read-only) --------------------------------------------------------------

@dataclass
class ReadOnlyPlan:
    found: list[dict[str, Any]]
    hash: str
    text: str
    excluded: frozenset[int]
    deferred: list[str]


def _read_only_plan(repo: Path, ledger: Ledger, stack: Stack, revision: str, *,
                    approve: bool = False) -> ReadOnlyPlan:
    """A plan against a copy of the state; with `approve`, also the excluded guests to check it
    against (the revision's and main's)."""
    with tempfile.TemporaryDirectory(prefix="skynet-tofu-") as tmp, \
            workspace(repo, stack, revision, ledger=ledger) as space:
        space.init(_state_copy(repo, ledger, stack.name, Path(tmp)))
        space.validate()
        found, digest, deferred = planned(space, stack)
        excluded = all_excluded(repo, space.root) if approve and found else frozenset()
        return ReadOnlyPlan(found, digest, space.show(), excluded, deferred)


def _approval(repo: Path, name: str) -> dict[str, Any] | None:
    """The working tree's approved-plan.json, if readable."""
    try:
        value = json.loads((repo / "tofu" / name / APPROVED).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def changed_stacks(repo: Path, revision: str) -> list[str]:
    """Stacks that need a (re-)approval at `revision`: inputs that differ from origin/main, or an
    approval made for other inputs."""
    main = deploy.resolve(repo, MAIN)
    result = []
    for name, stack in STACKS.items():
        digest = inputs_digest(repo, revision, stack)
        approval = _approval(repo, name)
        if approval is not None and approval.get("inputs") == digest:
            continue
        if approval is not None or digest != inputs_digest(repo, main, stack):
            result.append(name)
    return result


def run_plan(repo: Path, name: str | None, *, ref: str, approve: bool, state_dir_: Path,
             stdout: TextIO, changed: bool = False) -> int:
    """The PR author's plan: print it and its hash; `--approve` writes approved-plan.json, bound
    to the stack's inputs at the planned revision (an empty plan too, so the approval stays
    current). `--changed` plans every stack whose approval is missing or stale."""
    if changed:
        try:
            names = changed_stacks(repo, deploy.resolve(repo, ref))
        except WriteError as error:
            print(f"tofu plan: {error.reason}", file=stdout)
            return error.code
        if not names:
            print("tofu plan: every stack's approval matches its inputs", file=stdout)
        return max((run_plan(repo, each, ref=ref, approve=approve, state_dir_=state_dir_,
                             stdout=stdout) for each in names), default=OK)
    stack = STACKS.get(name or "")
    if stack is None:
        print(f"tofu plan: unknown stack (one of {', '.join(STACKS)})", file=stdout)
        return USAGE
    try:
        revision = deploy.resolve(repo, ref)
        planned_ = _read_only_plan(repo, Ledger(state_dir_), stack, revision, approve=approve)
    except WriteError as error:
        print(f"tofu/{name}: {error.reason}", file=stdout)
        return error.code
    found = planned_.found
    print(planned_.text.rstrip(), file=stdout)
    print(f"\ntofu/{name}@{revision[:12]}: {len(found)} change(s), sha256:{planned_.hash}",
          file=stdout)
    for address in planned_.deferred:
        print(f"  deferred (hard checkpoint, not applied): {address}", file=stdout)
    if approve:
        try:  # never approve what the executor would only refuse and hold
            check(stack, found, planned_.excluded)
            inputs = inputs_digest(repo, revision, stack)
        except WriteError as error:
            print(f"not approved: {error.reason}", file=stdout)
            return error.code
        path = repo / "tofu" / stack.name / APPROVED
        common.atomic_write_text(path, json.dumps(
            {"stack": stack.name, "hash": planned_.hash, "inputs": inputs,
             "changes": summary(found), "deferred": planned_.deferred}, indent=2) + "\n")
        print(f"wrote {path.relative_to(repo)}; commit it with the change", file=stdout)
    return OK


def run_drift(repo: Path, *, output: Path, state_dir_: Path, stdout: TextIO) -> int:
    """The nightly's read-only plan per stack at origin/main."""
    ledger, lines, code = Ledger(state_dir_), [], OK
    try:
        deploy.fetch(repo)
        head = deploy.resolve(repo, MAIN)
    except WriteError as error:
        # Rewritten even now: the last report must never stand in for tonight's.
        head, code = "", error.code
        lines = [f"{name}: plan unavailable — {error.reason}" for name in STACKS]
    for name, stack in STACKS.items() if head else ():
        try:
            planned_ = _read_only_plan(repo, ledger, stack, head)
        except WriteError as error:
            lines.append(f"{name}: plan unavailable — {error.reason}")
            code = UNAVAILABLE
            continue
        found = planned_.found
        lines.append(f"{name}: {'no changes' if not found else f'{len(found)} change(s), sha256:{planned_.hash}'}")
        lines += [f"  {item['address']}: {'/'.join(item['actions'])}" for item in found]
        lines += [f"  {address}: deferred (hard checkpoint)" for address in planned_.deferred]
    text = f"# tofu drift at {head[:12] or 'unknown (origin/main unreadable)'}\n" + "\n".join(lines) + "\n"
    try:
        common.atomic_write_text(output, text)
    except OSError:
        code = UNAVAILABLE
    print(text, end="", file=stdout)
    return code


def _pass_failures(ledger: Ledger, failed: dict[str, Any] | None) -> int | None:
    """Consecutive passes that could not run at all. Three in a row alert once, so a broken remote
    or credential cannot stop every Tofu apply while the unit reports success. None when the
    count could not be written."""
    def bump(facts: dict[str, Any]) -> int:
        known = facts.get("_pass")
        count = 0 if failed is None else (known if isinstance(known, int) else 0) + 1
        if count or "_pass" in facts:
            facts["_pass"] = count
        return count
    try:
        count = _update_facts(ledger, bump)
    except WriteError:
        return None
    if failed is not None and count == ALERT_AFTER_FAILURES:
        _alert(failed, f"skynet: tofu passes failing ({count} in a row)")
    return count


def run_apply(repo: Path, name: str | None, *, revision: str | None, pending_all: bool,
              state_dir_: Path, json_output: bool, stdout: TextIO, ignore_hold: bool = False) -> int:
    ledger = Ledger(state_dir_)
    if pending_all:  # the skynet-tofu timer
        deadline = time.monotonic() + PASS_SECONDS - PASS_MARGIN
        try:
            deploy.fetch(repo)
            results = pending(repo, ledger=ledger, deadline=deadline)
            _pass_failures(ledger, None)
        except (WriteError, OSError) as error:  # the pass itself could not run (git, state)
            unavailable: dict[str, Any] = {
                "target": "tofu", "outcome": "unavailable",
                "reason": (error.reason if isinstance(error, WriteError)
                           else "local tofu files unavailable"),
                "code": error.code if isinstance(error, WriteError) else UNAVAILABLE}
            if _pass_failures(ledger, unavailable) is None:
                return FAILED  # the count cannot be kept: let OnFailure alert instead
            results = [unavailable]
        for result in results:
            writepath.emit(result, json_output, stdout)
        # Recorded outcomes are not unit failures (they alert themselves); an alert that could not
        # be sent is, so OnFailure reaches the phone. 4 = rollback-failed whose alert went out.
        if any(deploy.alert_failed(result) for result in results):
            return FAILED
        codes = [int(result.get("code", 0)) for result in results]
        return writepath.ROLLBACK_FAILED if writepath.ROLLBACK_FAILED in codes else OK
    assert name is not None
    result = writepath.report(apply(repo, name, revision=revision, ledger=ledger,
                                    ignore_hold=ignore_hold))
    writepath.emit(result, json_output, stdout)
    return int(result["code"])

