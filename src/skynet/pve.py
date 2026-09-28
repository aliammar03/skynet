"""Proxmox guest snapshots over the operate token: the rollback point for a Tofu guest update.

`create`, `rollback`, and `delete` each start one Proxmox task and wait for it to stop with
`OK`. Proxmox leaves a rolled-back container stopped unless asked, so `rollback` restarts a guest
that was running and then waits until it is observed running again. The read-only token cannot
snapshot, so a missing operate token fails closed: no snapshot, no apply. Callers refuse excluded guests before they get here. Reasons are fixed text, never
remote error bodies or token values.
"""

from __future__ import annotations

import http.client
import os
import ssl
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from skynet import common, proxmox
from skynet.common import CollectionError
from skynet.writepath import UNAVAILABLE, WriteError

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
                raise WriteError("Proxmox snapshot task failed", UNAVAILABLE)
            return
        if time.monotonic() >= deadline:
            raise WriteError("Proxmox snapshot task did not finish in time", UNAVAILABLE)
        time.sleep(POLL_SECONDS)


def _base(guest: Guest) -> str:
    if guest.kind not in ("lxc", "qemu"):
        raise WriteError("unknown guest kind", UNAVAILABLE)
    return f"nodes/{quote(guest.node)}/{guest.kind}/{guest.vmid}/snapshot"


def create(guest: Guest, name: str) -> None:
    """Snapshot one guest. A VM keeps its RAM so a rollback resumes it in place."""
    fields = {"snapname": name, "description": "skynet tofu: pre-apply rollback point"}
    if guest.kind == "qemu":
        fields["vmstate"] = "1"
    _wait(guest.node, _call(guest.node, "POST", _base(guest), fields))


def status(guest: Guest) -> str:
    """The guest's power state (`running`, `stopped`, ...)."""
    data = _call(guest.node, "GET", f"nodes/{quote(guest.node)}/{guest.kind}/{guest.vmid}/status/current")
    value = data.get("status") if isinstance(data, dict) else None
    if not isinstance(value, str) or not value:
        raise WriteError("Proxmox returned no guest status", UNAVAILABLE)
    return value


# Keys a snapshot itself changes: the config digest, the snapshot parent, and a task's lock.
SNAPSHOT_KEYS = frozenset({"digest", "parent", "lock"})


def config(guest: Guest) -> dict[str, Any]:
    """The guest's current config, without the keys a snapshot itself changes."""
    data = _call(guest.node, "GET", f"nodes/{quote(guest.node)}/{guest.kind}/{guest.vmid}/config")
    if not isinstance(data, dict):
        raise WriteError("Proxmox returned no guest config", UNAVAILABLE)
    return {key: value for key, value in data.items() if key not in SNAPSHOT_KEYS}


def rollback(guest: Guest, name: str, power: str) -> None:
    """Return the guest to the snapshot and to its power state `power`, observed before success."""
    fields = {"start": "1"} if power == "running" else {}
    _wait(guest.node, _call(guest.node, "POST", f"{_base(guest)}/{quote(name)}/rollback", fields))
    deadline = time.monotonic() + TASK_SECONDS
    while status(guest) != power:
        if time.monotonic() >= deadline:
            raise WriteError(f"{guest} did not return to {power} after rollback", UNAVAILABLE)
        time.sleep(POLL_SECONDS)


def exists(guest: Guest, name: str) -> bool:
    """Whether the guest has snapshot `name` (a failed or timed-out create may still have made it)."""
    listed = _call(guest.node, "GET", _base(guest))
    if not isinstance(listed, list):
        raise WriteError("Proxmox returned no snapshot list", UNAVAILABLE)
    return any(isinstance(entry, dict) and entry.get("name") == name for entry in listed)


def delete(guest: Guest, name: str) -> None:
    _wait(guest.node, _call(guest.node, "DELETE", f"{_base(guest)}/{quote(name)}"))
