"""Proxmox guest config restore over the operate token: the automatic inverse of a Tofu guest update.

A failed update is undone by writing the guest's pre-apply config back (`restore`), never by a
snapshot rollback: a guest's disk and RAM carry payload data written after the snapshot. Each apply
still takes a disk-only snapshot (`create`) as the operator's fallback. Task calls wait for the
Proxmox task to stop with `OK`. Every write refuses a constitutionally excluded guest itself, whatever
its caller checked. The read-only token cannot write, so a missing operate token fails closed.
Reasons are fixed text, never remote error bodies or token values.
"""

from __future__ import annotations

import http.client
import os
import ssl
import time
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from skynet import common, proxmox
from skynet.common import CollectionError
from skynet.writepath import UNAVAILABLE, USAGE, WriteError

SECRETS = Path("/opt/skynet-ops/secrets")
NODE_CREDENTIALS = {
    "server-proxmox-core": "proxmox-core.env",
    "server-proxmox-network": "proxmox-network.env",
}
TIMEOUT = 30
TASK_SECONDS = 300.0
POLL_SECONDS = 2.0


@dataclass(frozen=True)
class Guest:
    node: str
    kind: str  # "lxc" or "qemu", the API path segment
    vmid: int

    def __str__(self) -> str:
        return f"{self.kind}/{self.vmid}@{self.node}"


def _client(node: str) -> tuple[str, str, ssl.SSLContext]:
    name = NODE_CREDENTIALS.get(node)
    if name is None:
        raise WriteError("unknown Proxmox node", UNAVAILABLE)
    secrets = Path(os.environ.get("SKYNET_SECRETS_DIR", SECRETS))
    try:
        return proxmox.credentials(secrets / name, "PVE_TOKEN_OPERATE")
    except CollectionError:
        raise WriteError("Proxmox operate credentials unavailable", UNAVAILABLE) from None


def _call(node: str, method: str, path: str, fields: dict[str, str] | None = None) -> Any:
    host, token, context = _client(node)
    connection = http.client.HTTPSConnection(host, 8006, context=context, timeout=TIMEOUT)
    headers = {"Authorization": "PVEAPIToken=" + token}
    body = None
    if fields is not None:
        body = urlencode(fields).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        raw, _ = common.request(connection, method, "/api2/json/" + path, headers=headers, body=body)
        return common.json_object(raw).get("data")
    except CollectionError:
        raise WriteError("Proxmox API request failed", UNAVAILABLE) from None


def _wait(node: str, upid: Any) -> None:
    if not isinstance(upid, str) or not upid.startswith("UPID:"):
        raise WriteError("Proxmox returned no task", UNAVAILABLE)
    deadline = time.monotonic() + TASK_SECONDS
    while True:
        status = _call(node, "GET", f"nodes/{quote(node)}/tasks/{quote(upid, safe='')}/status")
        if isinstance(status, dict) and status.get("status") == "stopped":
            if status.get("exitstatus") != "OK":
                raise WriteError("Proxmox task failed", UNAVAILABLE)
            return
        if time.monotonic() >= deadline:
            raise WriteError("Proxmox task did not finish in time", UNAVAILABLE)
        time.sleep(POLL_SECONDS)


def _guest_path(guest: Guest) -> str:
    if guest.kind not in ("lxc", "qemu"):
        raise WriteError("unknown guest kind", UNAVAILABLE)
    return f"nodes/{quote(guest.node)}/{guest.kind}/{guest.vmid}"


def _base(guest: Guest) -> str:
    return f"{_guest_path(guest)}/snapshot"


def _guard(guest: Guest, excluded: Collection[int]) -> None:
    if guest.vmid in excluded:
        raise WriteError(f"{guest} is excluded; use its privileged path", USAGE)


def create(guest: Guest, name: str, *, excluded: Collection[int]) -> None:
    """A disk-only snapshot: the operator's fallback, never restored automatically."""
    _guard(guest, excluded)
    fields = {"snapname": name, "description": "skynet tofu: pre-apply fallback (operator only)"}
    _wait(guest.node, _call(guest.node, "POST", _base(guest), fields))


def status(guest: Guest) -> str:
    """The guest's power state (`running`, `stopped`, ...)."""
    data = _call(guest.node, "GET", f"{_guest_path(guest)}/status/current")
    value = data.get("status") if isinstance(data, dict) else None
    if not isinstance(value, str) or not value:
        raise WriteError("Proxmox returned no guest status", UNAVAILABLE)
    return value


# Keys a snapshot or a config write itself changes: the config digest, the snapshot parent, a lock.
SNAPSHOT_KEYS = frozenset({"digest", "parent", "lock"})


def _raw_config(guest: Guest) -> dict[str, Any]:
    data = _call(guest.node, "GET", f"{_guest_path(guest)}/config")
    if not isinstance(data, dict):
        raise WriteError("Proxmox returned no guest config", UNAVAILABLE)
    return data


def config(guest: Guest) -> dict[str, Any]:
    """The guest's config (pending values included), without the keys a snapshot changes."""
    return {key: value for key, value in _raw_config(guest).items() if key not in SNAPSHOT_KEYS}


def pending(guest: Guest) -> list[str]:
    """The config keys (names only) with a change waiting for the next guest restart."""
    listed = _call(guest.node, "GET", f"{_guest_path(guest)}/pending")
    if not isinstance(listed, list):
        raise WriteError("Proxmox returned no pending list", UNAVAILABLE)
    return sorted(str(entry.get("key")) for entry in listed
                  if isinstance(entry, dict) and ("pending" in entry or "delete" in entry))


def _set_power(guest: Guest, power: str) -> None:
    """Start or shut down (forced after a grace period) to reach `power`, then observe it."""
    if status(guest) != power:
        if power == "running":
            action, fields = "start", {}
        elif power == "stopped":
            action, fields = "shutdown", {"forceStop": "1", "timeout": "120"}
        else:
            raise WriteError(f"{guest} cannot be returned to {power}", UNAVAILABLE)
        _wait(guest.node, _call(guest.node, "POST", f"{_guest_path(guest)}/status/{action}", fields))
    _observe(guest, power)


def _observe(guest: Guest, power: str) -> None:
    deadline = time.monotonic() + TASK_SECONDS
    while status(guest) != power:
        if time.monotonic() >= deadline:
            raise WriteError(f"{guest} did not return to {power}", UNAVAILABLE)
        time.sleep(POLL_SECONDS)


def restore(guest: Guest, saved: dict[str, Any], power: str, *, excluded: Collection[int]) -> None:
    """Write `saved` (a `config()` copy) back and return the guest to `power`. Only keys that
    differ are sent; keys the failed apply added are deleted; the current digest makes the write a
    compare-and-swap. A guest that should stay stopped is stopped first, so the write applies at
    once; a running one is rebooted only when the write left changes pending."""
    _guard(guest, excluded)
    if power == "stopped":
        _set_power(guest, power)
    raw = _raw_config(guest)
    current = {key: value for key, value in raw.items() if key not in SNAPSHOT_KEYS}
    fields = {key: str(value) for key, value in saved.items() if current.get(key) != value}
    removed = sorted(key for key in current if key not in saved)
    if removed:
        fields["delete"] = ",".join(removed)
    if fields:
        if isinstance(raw.get("digest"), str):
            fields["digest"] = raw["digest"]
        result = _call(guest.node, "PUT", f"{_guest_path(guest)}/config", fields)
        if isinstance(result, str) and result.startswith("UPID:"):
            _wait(guest.node, result)
    if power == "running" and pending(guest) and status(guest) == "running":
        _wait(guest.node, _call(guest.node, "POST", f"{_guest_path(guest)}/status/reboot", {}))
        _observe(guest, power)
    else:
        _set_power(guest, power)


def exists(guest: Guest, name: str) -> bool:
    """Whether the guest has snapshot `name` (a failed or timed-out create may still have made it)."""
    listed = _call(guest.node, "GET", _base(guest))
    if not isinstance(listed, list):
        raise WriteError("Proxmox returned no snapshot list", UNAVAILABLE)
    return any(isinstance(entry, dict) and entry.get("name") == name for entry in listed)


def delete(guest: Guest, name: str, *, excluded: Collection[int]) -> None:
    _guard(guest, excluded)
    _wait(guest.node, _call(guest.node, "DELETE", f"{_base(guest)}/{quote(name)}"))
