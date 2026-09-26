"""T1 Proxmox observations: verified GETs, validated snapshot, atomic local publication.

Credentials are literal assignments, never shell code. Collection success says nothing
about guest/service health. A failed refresh leaves the requested destination unchanged.
"""

import http.client
import ssl
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import quote, urlencode

from skynet import common
from skynet.common import CollectionError

DEFAULT_CREDENTIALS = {
    "core": Path("/opt/skynet-ops/secrets/proxmox-core.env"),
    "network": Path("/opt/skynet-ops/secrets/proxmox-network.env"),
}
TIMEOUT = 15
_KEYS = ("PVE_HOST", "PVE_TOKEN", "PVE_CACERT", "PVE_TOKEN_OPERATE")


def credentials(path: Path, token_name: str = "PVE_TOKEN") -> tuple[str, str, ssl.SSLContext]:
    """Parse literal credentials and select exactly one declared token for HTTPS."""
    values = common.read_assignments(path, _KEYS, ("PVE_HOST", "PVE_CACERT", token_name))
    host = common.require_host(values["PVE_HOST"])
    if not common.printable(values[token_name]):
        raise CollectionError("invalid credential token", 3)
    return host, values[token_name], common.ca_context(values["PVE_CACERT"])


def get(host: str, token: str, context: ssl.SSLContext, path: str) -> Any:
    """GET one API envelope without redirect handling or proxy/header forwarding."""
    connection = http.client.HTTPSConnection(host, 8006, context=context, timeout=TIMEOUT)
    raw, _ = common.request(connection, "GET", "/api2/json/" + path,
                            headers={"Authorization": "PVEAPIToken=" + token})
    envelope = common.json_object(raw)
    if envelope.get("data") is None:
        raise CollectionError("missing API data")
    return envelope["data"]


def entries(value: Any, *, nonempty: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (nonempty and not value):
        raise CollectionError("missing or malformed required list")
    if any(not isinstance(entry, dict) for entry in value):
        raise CollectionError("malformed API entry")
    return value


def string(entry: dict[str, Any], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise CollectionError("missing or malformed identity/status field")
    return value


def optional(entry: dict[str, Any], key: str, kind: type) -> None:
    value = entry.get(key)
    if value is not None and type(value) is not kind:
        raise CollectionError("malformed optional field")


def guest_identity(entry: dict[str, Any]) -> None:
    string(entry, "node")
    if type(entry.get("vmid")) is not int or entry["vmid"] <= 0:
        raise CollectionError("missing or malformed guest VMID")
    if entry["id"] != f"{entry['type']}/{entry['vmid']}":
        raise CollectionError("inconsistent guest identity")


def unique(rows: list[dict[str, Any]], field: str) -> None:
    identifiers = [string(row, field) for row in rows]
    if len(set(identifiers)) != len(identifiers):
        raise CollectionError("duplicate API identity")


def snapshot(target: str, host: str, token: str, context: ssl.SSLContext) -> dict[str, Any]:
    """Require every endpoint; preserve consumer fields, project volatile pool details."""
    def api(path: str) -> Any:
        return get(host, token, context, path)

    nodes = entries(api("nodes"), nonempty=True)
    unique(nodes, "node")
    for node in nodes:
        if string(node, "type") != "node":
            raise CollectionError("malformed node type")
        string(node, "status")
    resources = entries(api("cluster/resources"), nonempty=True)
    unique(resources, "id")
    for resource in resources:
        kind = string(resource, "type")
        if kind in {"qemu", "lxc"}:
            guest_identity(resource)
            string(resource, "name")
            string(resource, "status")
            optional(resource, "template", int)
        elif kind != "pool":
            string(resource, "node")
            string(resource, "status")
        optional(resource, "pool", str)
        if kind != "pool" and resource["node"] not in {node["node"] for node in nodes}:
            raise CollectionError("resource references an unobserved node")
    pool_list = entries(api("pools"))
    unique(pool_list, "poolid")
    pools = []
    for pool in pool_list:
        poolid = string(pool, "poolid")
        detail = api("pools/" + quote(poolid, safe=""))
        if not isinstance(detail, dict):
            raise CollectionError("malformed pool detail")
        if "poolid" in detail and detail["poolid"] != poolid:
            raise CollectionError("inconsistent pool identity")
        optional(detail, "comment", str)
        members = entries(detail.get("members"))
        unique(members, "id")
        for member in members:
            kind = string(member, "type")
            if kind in {"qemu", "lxc"}:
                guest_identity(member)
            elif kind == "storage":
                string(member, "node")
                optional(member, "vmid", int)
            else:
                raise CollectionError("malformed pool member type")
        pools.append({"poolid": poolid, "comment": detail.get("comment"), "members": [
            {key: member.get(key) for key in ("id", "type", "vmid", "node")}
            for member in members
        ]})
    jobs = entries(api("cluster/backup"))
    unique(jobs, "id")
    job_keys = ("id", "schedule", "storage", "enabled", "all", "vmid", "pool", "mode", "node")
    for job in jobs:
        for key in ("schedule", "storage", "vmid", "pool", "mode", "node"):
            optional(job, key, str)
        for key in ("enabled", "all"):
            optional(job, key, int)
            if job.get(key) not in (None, 0, 1):
                raise CollectionError("malformed backup flag")
    last = []
    for node in nodes:
        tasks = entries(api("nodes/" + quote(node["node"], safe="") + "/tasks?" +
                            urlencode({"typefilter": "vzdump", "limit": 5})))
        for task in tasks:
            # A task without status can still be running; no tasks is a valid observation.
            if type(task.get("starttime")) is not int or task["starttime"] < 0:
                raise CollectionError("missing or malformed backup task time")
            optional(task, "status", str)
        completed = [task for task in tasks if task.get("status")]
        latest = max(completed, key=lambda task: task["starttime"], default={})
        last.append({"node": node["node"], "starttime": latest.get("starttime"),
                     "status": latest.get("status")})
    return {"node": target, "collected": datetime.now(UTC).isoformat(timespec="seconds"),
            "nodes": nodes, "resources": resources, "pools": pools,
            "backup_jobs": [{key: job.get(key) for key in job_keys} for job in jobs],
            "backup_last": last}


def run(target: str, output: Path, credentials_file: Path) -> common.Result:
    """Collect one validated Proxmox node shape with its read-only token."""
    return common.run(
        f"proxmox-{target}", (output,),
        lambda: (snapshot(target, *credentials(credentials_file)),),
        lambda data: {"nodes": len(data["nodes"]),
                      "guests": sum(r["type"] in {"qemu", "lxc"} for r in data["resources"]),
                      "pools": len(data["pools"])},
    )


def collect(target: str, output: Path, credentials_file: Path, *, json_output: bool,
            stdout: TextIO) -> int:
    return common.emit(run(target, output, credentials_file), json_output, stdout)


def acl_snapshot(target: str, host: str, token: str, context: ssl.SSLContext) -> dict[str, Any]:
    """Collect one operate token's own effective permissions, never an ACL configuration."""
    permissions = get(host, token, context, "access/permissions")
    if not isinstance(permissions, dict) or not permissions:
        raise CollectionError("missing or malformed permissions")
    for path, grants in permissions.items():
        if not isinstance(path, str) or not path.startswith("/") or not isinstance(grants, dict):
            raise CollectionError("missing or malformed permissions")
        if any(not isinstance(name, str) or type(value) is not int or value not in (0, 1)
               for name, value in grants.items()):
            raise CollectionError("missing or malformed permissions")
    token_id, separator, _ = token.partition("=")
    if not separator or not token_id:
        raise CollectionError("invalid operate token", 3)
    return {"node": f"server-proxmox-{target}", "token": token_id,
            "collected": datetime.now(UTC).isoformat(timespec="seconds"),
            "permissions": permissions}


def run_acl(target: str, output: Path, credentials_file: Path) -> common.Result:
    """Collect one validated operate-token ACL observation without exposing its token."""
    return common.run(
        f"proxmox-{target}-acl", (output,),
        lambda: (acl_snapshot(target, *credentials(credentials_file, "PVE_TOKEN_OPERATE")),),
        lambda data: {"paths": len(data["permissions"])},
    )


def collect_acl(target: str, output: Path, credentials_file: Path, *, json_output: bool,
                stdout: TextIO) -> int:
    return common.emit(run_acl(target, output, credentials_file), json_output, stdout)
