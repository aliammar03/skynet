"""T1 core observations: verified GETs, validated snapshot, atomic local publication.

Credentials are literal assignments, never shell code. Collection success says nothing
about guest/service health. A failed refresh leaves the requested destination unchanged.
"""

import http.client
import json
import os
import re
import ssl
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import quote, urlencode

DEFAULT_CREDENTIALS = Path("/opt/skynet-ops/secrets/proxmox-core.env")
TIMEOUT = 15


class CollectionError(Exception):
    """A fixed, safe diagnostic and CLI exit code; never includes external text."""

    def __init__(self, reason: str, code: int = 1):
        super().__init__(reason)
        self.code = code


def credentials(path: Path) -> tuple[str, str, ssl.SSLContext]:
    """Read only the three required literal assignments and construct verified TLS."""
    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        raise CollectionError("credentials unavailable", 3) from None
    values: dict[str, str] = {}
    for line in contents.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(
            r"\s*(PVE_HOST|PVE_TOKEN|PVE_CACERT)=(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"]+))"
            r"\s*(?:#.*)?", line,
        )
        if not match:
            raise CollectionError("invalid credential assignments", 3)
        key = match[1]
        value = next(v for v in match.groups()[1:] if v is not None)
        if key in values or not value or any(c in value for c in "`$\\;|&<>()\r\n\x00"):
            raise CollectionError("invalid credential assignments", 3)
        values[key] = value
    if set(values) != {"PVE_HOST", "PVE_TOKEN", "PVE_CACERT"}:
        raise CollectionError("required credentials missing", 3)
    # The contract is a host, not a URL, port override, or userinfo destination.
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", values["PVE_HOST"]):
        raise CollectionError("invalid credential host", 3)
    if any(ord(c) < 33 or ord(c) > 126 for c in values["PVE_TOKEN"]):
        raise CollectionError("invalid credential token", 3)
    try:
        context = ssl.create_default_context(cafile=values["PVE_CACERT"])
    except (OSError, ValueError):
        raise CollectionError("CA unavailable or invalid", 3) from None
    return values["PVE_HOST"], values["PVE_TOKEN"], context


def get(host: str, token: str, context: ssl.SSLContext, path: str) -> Any:
    """GET one API envelope without redirect handling or proxy/header forwarding."""
    connection = None
    try:
        connection = http.client.HTTPSConnection(host, 8006, context=context, timeout=TIMEOUT)
        connection.request("GET", "/api2/json/" + path,
                           headers={"Authorization": "PVEAPIToken=" + token})
        response = connection.getresponse()
        if response.status != 200:
            raise CollectionError("remote HTTP request refused (redirects disabled)", 3)
        raw = response.read()
    except (OSError, http.client.HTTPException, ValueError):
        raise CollectionError("remote transport unavailable (timeout, TLS or connection)", 3) from None
    finally:
        if connection is not None:
            try:
                connection.close()
            except OSError:
                raise CollectionError("remote connection close failed", 3) from None
    try:
        envelope = json.loads(raw)
    except (ValueError, UnicodeError):
        raise CollectionError("malformed API JSON") from None
    if not isinstance(envelope, dict) or envelope.get("data") is None:
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


def snapshot(host: str, token: str, context: ssl.SSLContext) -> dict[str, Any]:
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
    return {"node": "core", "collected": datetime.now(UTC).isoformat(timespec="seconds"),
            "nodes": nodes, "resources": resources, "pools": pools,
            "backup_jobs": [{key: job.get(key) for key in job_keys} for job in jobs],
            "backup_last": last}


def publish(output: Path, data: dict[str, Any]) -> None:
    """Replace only after serialization and a complete, flushed sibling write."""
    temporary: str | None = None
    try:
        payload = json.dumps(data, indent=2, allow_nan=False) + "\n"
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix="." + output.name + ".", delete=False) as stream:
            temporary = stream.name
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    except (OSError, ValueError, TypeError):
        raise CollectionError("local snapshot publication failed") from None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            except OSError:
                raise CollectionError("local temporary cleanup failed") from None


def collect(output: Path, credentials_file: Path, *, json_output: bool, stdout: TextIO) -> int:
    report: dict[str, Any] = {"target": "proxmox-core", "output": str(output)}
    try:
        data = snapshot(*credentials(credentials_file))
        publish(output, data)
    except CollectionError as error:
        report.update(outcome="unavailable" if error.code == 3 else "failure",
                      reason=f"{error}; refresh failed; any retained snapshot is previous evidence")
        code = error.code
    else:
        report.update(outcome="success", collected=data["collected"], counts={
            "nodes": len(data["nodes"]),
            "guests": sum(r["type"] in {"qemu", "lxc"} for r in data["resources"]),
            "pools": len(data["pools"]),
        })
        code = 0
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"{report['target']}: {report['outcome']} → {report['output']}", file=stdout)
        if code:
            print(report["reason"], file=stdout)
        else:
            print(f"collected: {report['collected']}; " + ", ".join(
                f"{key}: {value}" for key, value in report["counts"].items()), file=stdout)
    return code
