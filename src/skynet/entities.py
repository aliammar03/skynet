"""T1 entity derivation and audit over committed repository observations.

Entity IDs are deliberately small functions over authored conventions and collected inventory.  This
module has no network, credential, or mutation path.  The command-line entry point is also used by
the two temporary shell compatibility wrappers while their remaining callers are migrated.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, TextIO


DEFAULT_VLANS = (10, 20, 30, 50, 60, 70, 80, 90, 100)
DEFAULT_VLAN_SLUGS = {
    10: "lan",
    20: "servers",
    30: "iot",
    50: "mgmt",
    60: "admin",
    70: "netsvc",
    80: "identity",
    90: "ops",
    100: "dmz",
}
_IP = re.compile(r"^10\.10\.(\d+)\.(\d+)$")
_PROJECT = re.compile(r"(?:^|,)com\.docker\.compose\.project=([^,]+)(?:,|$)")


class EntityError(ValueError):
    """A safe, deterministic entity error with a process-compatible exit code."""

    def __init__(self, reason: str, code: int = 2):
        super().__init__(reason)
        self.code = code


def _vmid(value: int | str) -> int:
    if isinstance(value, bool):
        raise EntityError("invalid VMID", 1)
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        number = int(value)
    else:
        raise EntityError("invalid VMID", 1)
    if number < 0:
        raise EntityError("invalid VMID", 1)
    return number


def vlan_candidates(vmid: int | str, declared_vlans: tuple[int, ...] = DEFAULT_VLANS) -> tuple[int, ...]:
    """Return canonical then legacy VLAN candidates for a VMID."""
    number = _vmid(vmid)
    prefix = number // 100
    declared = set(declared_vlans)
    candidates: list[int] = []
    if prefix in declared:
        candidates.append(prefix)
    legacy = prefix * 10
    if legacy in declared and legacy not in candidates:
        candidates.append(legacy)
    return tuple(candidates)


def vmid_to_ip(vmid: int | str, declared_vlans: tuple[int, ...] = DEFAULT_VLANS) -> str:
    """Derive the unique static address encoded by a VMID.

    ``EntityError.code`` is 1 for an off-convention VMID and 2 for the genuinely ambiguous 10xx
    prefix.  Keeping the ambiguity explicit lets callers resolve it from an observed firewall fact.
    """
    number = _vmid(vmid)
    candidates = vlan_candidates(number, declared_vlans)
    if len(candidates) == 0:
        raise EntityError("off-convention VMID", 1)
    if len(candidates) > 1:
        raise EntityError("ambiguous VMID", 2)
    return f"10.10.{candidates[0]}.{number % 100}"


def vlan_of_vmid(vmid: int | str, declared_vlans: tuple[int, ...] = DEFAULT_VLANS) -> int:
    """Return the unique VLAN encoded by a VMID, preserving the VMID error distinction."""
    candidates = vlan_candidates(vmid, declared_vlans)
    if len(candidates) == 0:
        raise EntityError("off-convention VMID", 1)
    if len(candidates) > 1:
        raise EntityError("ambiguous VMID", 2)
    return candidates[0]


def candidate_ips(vmid: int | str, declared_vlans: tuple[int, ...] = DEFAULT_VLANS) -> tuple[str, ...]:
    """Return all addresses a VMID could encode, used only for fact-based ambiguity resolution."""
    number = _vmid(vmid)
    return tuple(f"10.10.{vlan}.{number % 100}" for vlan in vlan_candidates(number, declared_vlans))


def ip_to_vmid(ip: str, declared_vlans: tuple[int, ...] = DEFAULT_VLANS) -> int:
    """Return the canonical VMID represented by a declared 10.10 VLAN address."""
    match = _IP.fullmatch(ip)
    if match is None:
        raise EntityError("invalid guest IP", 1)
    vlan, octet = (int(part) for part in match.groups())
    if vlan not in set(declared_vlans) or not 0 <= vlan <= 255 or not 0 <= octet <= 255:
        raise EntityError("off-convention guest IP", 1)
    return vlan * 100 + octet


def guest_id(vmid: int | str, name: str, declared_vlans: tuple[int, ...] = DEFAULT_VLANS,
             vlan_slugs: dict[int, str] | None = None) -> str:
    """Build a stable guest ID; the VMID remains authoritative when its slug is unavailable."""
    if not isinstance(name, str):
        raise EntityError("invalid guest name", 1)
    role = name
    if role.startswith("vm-"):
        role = role[3:]
    if role.startswith("lxc-"):
        role = role[4:]
    slugs = DEFAULT_VLAN_SLUGS if vlan_slugs is None else vlan_slugs
    try:
        slug = slugs[vlan_of_vmid(vmid, declared_vlans)]
    except (EntityError, KeyError):
        return f"guest/{role}-{vmid}"
    if role == slug or role.endswith("-" + slug):
        return f"guest/{role}-{vmid}"
    return f"guest/{role}-{slug}-{vmid}"


def svc_id(key: str) -> str:
    return f"svc/{key}"


def node_id(key: str) -> str:
    return f"node/{key}"


def vhost_id(key: str) -> str:
    return f"vhost/{key}"


def net_id(key: str) -> str:
    return f"net/{key}"


def _json(path: Path, *, required: bool = True) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if not required:
            return None
        raise EntityError(f"required source unavailable: {path}") from None
    except (OSError, UnicodeError):
        raise EntityError(f"required source unavailable: {path}") from None
    try:
        return json.loads(text)
    except (ValueError, UnicodeError):
        raise EntityError(f"malformed JSON source: {path}") from None


def _object(value: Any, source: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EntityError(f"malformed JSON source: {source}")
    return value


def _list(value: Any, source: Path, field: str, *, required: bool = True) -> list[Any]:
    if value is None and not required:
        return []
    if not isinstance(value, list):
        raise EntityError(f"malformed {field} in {source}")
    return value


def _string(value: Any, source: Path, field: str, *, required: bool = True) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value) or any(ord(char) < 32 for char in value):
        raise EntityError(f"malformed {field} in {source}")
    return value


def _bool(value: Any, source: Path, field: str, *, required: bool = True) -> bool:
    if value is None and not required:
        return False
    if type(value) is not bool:
        raise EntityError(f"malformed {field} in {source}")
    return value


def _conventions(repo: Path) -> tuple[tuple[int, ...], dict[int, str], set[int], dict[str, tuple[int, str]]]:
    """Load authored VLAN and exception facts without making them Python authority."""
    inv_path = repo / "invariants.json"
    inv = _object(_json(inv_path), inv_path)
    convention = _object(inv.get("entity_conventions"), inv_path)
    raw_vlans = _list(convention.get("declared_vlans"), inv_path, "entity_conventions.declared_vlans")
    if any(type(vlan) is not int or vlan <= 0 for vlan in raw_vlans):
        raise EntityError(f"malformed entity_conventions.declared_vlans in {inv_path}")
    vlans = tuple(raw_vlans)
    if len(set(vlans)) != len(vlans):
        raise EntityError(f"duplicate entity_conventions.declared_vlans in {inv_path}")

    lab_path = repo / "lab.json"
    lab = _object(_json(lab_path), lab_path)
    raw_display = _list(_object(lab.get("vlans"), lab_path).get("list"), lab_path, "vlans.list")
    slugs: dict[int, str] = {}
    for row in raw_display:
        display = _object(row, lab_path)
        vlan = display.get("vlan")
        if type(vlan) is not int or vlan not in vlans:
            raise EntityError(f"malformed vlans.list in {lab_path}")
        slug = _string(display.get("slug"), lab_path, "vlan slug")
        if vlan in slugs or slug in slugs.values():
            raise EntityError(f"duplicate VLAN slug in {lab_path}")
        slugs[vlan] = slug
    if set(slugs) != set(vlans):
        raise EntityError(f"vlans.list does not cover declared VLANs in {lab_path}")

    exceptions: set[int] = set()
    exception_sources: dict[str, tuple[int, str]] = {}
    excluded = _object(inv.get("excluded_guests"), inv_path)
    for field, label in (("guests", "excluded_guests.guests"),):
        for row in _list(excluded.get(field), inv_path, label):
            entry = _object(row, inv_path)
            vmid = entry.get("vmid")
            why = _string(entry.get("why"), inv_path, f"{label}.why")
            if type(vmid) is not int or vmid < 0:
                raise EntityError(f"malformed {label}.vmid in {inv_path}")
            exceptions.add(vmid)
            exception_sources[str(vmid)] = (vmid, "excluded guest: " + why)
    for row in _list(convention.get("exceptions"), inv_path, "entity_conventions.exceptions"):
        entry = _object(row, inv_path)
        vmid = entry.get("vmid")
        why = _string(entry.get("why"), inv_path, "entity_conventions.exceptions.why")
        if type(vmid) is not int or vmid < 0:
            raise EntityError("malformed entity_conventions.exceptions.vmid in invariants.json")
        exceptions.add(vmid)
        exception_sources[str(vmid)] = (vmid, "declared exception: " + why)
    return vlans, slugs, exceptions, exception_sources


def conventions(repo: Path) -> tuple[tuple[int, ...], dict[int, str], set[int], dict[str, tuple[int, str]]]:
    """Load the authored entity convention facts for another repository-only consumer."""
    return _conventions(repo)


def _firewall_ips(repo: Path) -> set[str]:
    path = repo / "inventory" / "firewall" / "firewall.json"
    data = _object(_json(path), path)
    addresses: set[str] = set()
    aliases = _list(data.get("aliases"), path, "firewall aliases")
    for row in aliases:
        alias = _object(row, path)
        if alias.get("type") != "host":
            continue
        content = alias.get("content", "")
        if not isinstance(content, str):
            raise EntityError(f"malformed firewall alias content in {path}")
        addresses.update(part for part in re.split(r"[\s,]+", content) if _IP.fullmatch(part))
    reservations = _list(data.get("reservations"), path, "firewall reservations")
    for row in reservations:
        reservation = _object(row, path)
        value = reservation.get("ip") or reservation.get("address", "")
        if value and (not isinstance(value, str) or not _IP.fullmatch(value)):
            raise EntityError(f"malformed firewall reservation address in {path}")
        if value:
            addresses.add(value)
    return addresses


def firewall_ips(repo: Path) -> set[str]:
    """Return host facts for callers such as the static route collector."""
    return _firewall_ips(repo)


def _liveness(repo: Path) -> tuple[set[str], set[str], set[str], bool]:
    path = repo / "inventory" / "opnsense.json"
    if not path.is_file():
        return set(), set(), set(), False
    data = _object(_json(path), path)
    live: set[str] = set()
    down: set[str] = set()
    presence = _list(data.get("presence"), path, "OPNsense presence")
    for row in presence:
        entry = _object(row, path)
        ip = _string(entry.get("ip"), path, "presence ip")
        if type(entry.get("live")) is not bool:
            raise EntityError(f"malformed OPNsense presence in {path}")
        if _IP.fullmatch(ip):
            (live if entry["live"] else down).add(ip)
    raw_arp: set[str] = set()
    arp = _list(data.get("arp"), path, "OPNsense ARP")
    for row in arp:
        entry = _object(row, path)
        ip = _string(entry.get("ip"), path, "ARP ip")
        if _IP.fullmatch(ip):
            raw_arp.add(ip)
    return live, down, raw_arp, bool(live or down)


def _guest_address(vmid: int, firewall: set[str], vlans: tuple[int, ...]) -> tuple[str, str]:
    try:
        return vmid_to_ip(vmid, vlans), ""
    except EntityError as error:
        if error.code != 2:
            return "", str(error)
    candidates = candidate_ips(vmid, vlans)
    mapped = [candidate for candidate in candidates if candidate in firewall]
    if len(mapped) == 1:
        return mapped[0], "ambiguous VMID, resolved by firewall fact"
    if len(mapped) > 1:
        return "", "ambiguous VMID (10xx), multiple firewall facts"
    return "", "ambiguous VMID (10xx), no fact to resolve"


def _record(entity_id: str, entity_class: str, *, address: str = "", status: str = "",
            bucket: str, note: str = "", hosted_on: str = "", **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "entity_id": entity_id,
        "class": entity_class,
        "address": address,
        "status": status,
        "bucket": bucket,
        "note": note,
    }
    if hosted_on:
        result["hosted_on"] = hosted_on
    result.update(extra)
    return result


def _proxmox_guests(repo: Path, vlans: tuple[int, ...], slugs: dict[int, str],
                    exceptions: set[int], exception_sources: dict[str, tuple[int, str]],
                    firewall: set[str], live: set[str], down: set[str], raw_arp: set[str],
                    have_liveness: bool) -> tuple[list[dict[str, Any]], list[str]]:
    inventory = repo / "inventory"
    files = sorted(path for path in inventory.glob("proxmox-*.json")
                   if not path.name.endswith("-acl.json"))
    if not files:
        raise EntityError("required source unavailable: inventory/proxmox-*.json")
    records: list[dict[str, Any]] = []
    holes: list[str] = []
    seen: set[int] = set()
    for path in files:
        data = _object(_json(path), path)
        resources = _list(data.get("resources"), path, "Proxmox resources")
        for raw in resources:
            resource = _object(raw, path)
            if resource.get("type") not in {"qemu", "lxc"}:
                continue
            vmid = resource.get("vmid")
            if type(vmid) is not int or vmid < 0:
                raise EntityError(f"malformed guest VMID in {path}")
            name = _string(resource.get("name"), path, "guest name")
            status = _string(resource.get("status"), path, "guest status")
            template = resource.get("template", 0)
            if type(template) is not int or template not in {0, 1}:
                raise EntityError(f"malformed guest template flag in {path}")
            if vmid in seen:
                raise EntityError(f"duplicate guest VMID in inventory: {vmid}")
            seen.add(vmid)
            identity = guest_id(vmid, name, vlans, slugs)
            if template == 1:
                try:
                    address = vmid_to_ip(vmid, vlans)
                except EntityError:
                    address = ""
                records.append(_record(identity, "guest", address=address, status="template",
                                       bucket="template", note="clone source — keep; never destroy as stale",
                                       vmid=vmid, template=True))
                continue
            address, note = _guest_address(vmid, firewall, vlans)
            if vmid in exceptions:
                source_note = exception_sources.get(str(vmid), (vmid, "declared exception"))[1]
                records.append(_record(identity, "guest", address=address, status=status,
                                       bucket="exception", note=source_note, vmid=vmid, template=False))
                continue
            if status == "running" and address and address in firewall:
                liveness = ""
                if have_liveness:
                    if address in live:
                        liveness = "✓ live"
                    elif address in down:
                        liveness = "⚠ no ARP/ping response"
                records.append(_record(identity, "guest", address=address, status=status,
                                       bucket="matched", note="; ".join(part for part in (note, liveness) if part),
                                       vmid=vmid, template=False))
            elif status != "running":
                if address in firewall and address:
                    note = "; ".join(part for part in (note, f"⚠ still holds firewall alias {address}") if part)
                records.append(_record(identity, "guest", address=address, status=status,
                                       bucket="stale", note=note or "cleanup proposal", vmid=vmid,
                                       template=False))
            else:
                presence_note = ""
                if have_liveness and address in raw_arp:
                    presence_note = "⚠ present in ARP (live, unaliased)"
                note = "; ".join(part for part in (note, presence_note, "no firewall/DNS host fact") if part)
                records.append(_record(identity, "guest", address=address, status=status,
                                       bucket="running-unmapped", note=note, vmid=vmid,
                                       template=False))
                holes.append(identity)
    return records, holes


def _lab_hosts(repo: Path) -> dict[str, tuple[int, str]]:
    path = repo / "lab.json"
    data = _object(_json(path), path)
    docker = _object(data.get("docker_hosts"), path)
    rows = _list(docker.get("hosts"), path, "docker_hosts.hosts")
    hosts: dict[str, tuple[int, str]] = {}
    for raw in rows:
        row = _object(raw, path)
        label = _string(row.get("label"), path, "docker host label")
        vmid = row.get("vmid")
        guest = _string(row.get("guest"), path, "docker host guest")
        if type(vmid) is not int or vmid < 0 or label in hosts:
            raise EntityError(f"malformed docker_hosts.hosts in {path}")
        hosts[label] = (vmid, guest)
    return hosts


def _service_records(repo: Path, vlans: tuple[int, ...], slugs: dict[int, str], firewall: set[str],
                     lab_hosts: dict[str, tuple[int, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    holes: list[str] = []
    compose = repo / "compose"
    if not compose.is_dir():
        raise EntityError("required source unavailable: compose/")
    compose_dirs = {entry.name for entry in compose.iterdir() if entry.is_dir()}
    seen: set[tuple[str, str]] = set()
    for path in sorted((repo / "inventory").glob("docker-*.json")):
        data = _object(_json(path), path)
        host = _string(data.get("host"), path, "Docker host")
        containers = _list(data.get("containers"), path, "Docker containers")
        hosted = "host:" + host + "?"
        if host in lab_hosts:
            vmid, name = lab_hosts[host]
            hosted = guest_id(vmid, name, vlans, slugs)
        for raw in containers:
            container = _object(raw, path)
            labels = _string(container.get("Labels"), path, "container labels", required=False)
            match = _PROJECT.search(labels)
            if match is None or not match[1]:
                continue
            project = match[1]
            key = (project, host)
            if key in seen:
                continue
            seen.add(key)
            identity = svc_id(project)
            if project in compose_dirs:
                records.append(_record(identity, "service", status="running", bucket="matched",
                                       hosted_on=hosted, host=host))
            else:
                records.append(_record(identity, "service", status="running",
                                       bucket="running-unmapped", hosted_on=hosted,
                                       note=f"no compose/{project}/ in git — deployed outside the GitOps loop",
                                       host=host))
                holes.append(identity)
    for project in sorted(compose_dirs):
        if not any(record.get("entity_id") == svc_id(project) for record in records):
            records.append(_record(svc_id(project), "service", status="not-running",
                                   bucket="declared-idle", note=f"compose/{project}/ in git, no running project"))
    return records, holes


def _node_records(repo: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((repo / "inventory").glob("proxmox-*.json")):
        if path.name.endswith("-acl.json"):
            continue
        data = _object(_json(path), path)
        nodes = _list(data.get("nodes"), path, "Proxmox nodes", required=False)
        for raw in nodes:
            node = _object(raw, path)
            if node.get("type") != "node":
                continue
            name = _string(node.get("node"), path, "node name")
            records.append(_record(node_id(name), "node", bucket="matched", note="Proxmox node"))
    unique: dict[str, dict[str, Any]] = {record["entity_id"]: record for record in records}
    return [unique[key] for key in sorted(unique)]


def _route_records(repo: Path, known: set[str]) -> list[dict[str, Any]]:
    path = repo / "inventory" / "routes.json"
    if not path.is_file():
        return []
    data = _object(_json(path), path)
    routes = _list(data.get("routes"), path, "routes")
    records: list[dict[str, Any]] = []
    for raw in routes:
        route = _object(raw, path)
        vhost = _string(route.get("vhost"), path, "route vhost")
        backend = route.get("backend_entity", "")
        if not isinstance(backend, str):
            raise EntityError(f"malformed route backend entity in {path}")
        auth = _string(route.get("auth", ""), path, "route auth", required=False)
        unresolved = not backend or backend in {"—", "-"} or backend.startswith("host:") or backend not in known
        bucket = "unresolved" if unresolved else "matched"
        note = "backend not an entity" if unresolved else auth
        records.append(_record(vhost_id(vhost), "vhost", address=backend, status="route",
                               bucket=bucket, note=note, backend_entity=backend, auth=auth))
    return records


def _network_records(repo: Path, firewall: set[str]) -> list[dict[str, Any]]:
    path = repo / "inventory" / "network-gear.json"
    if not path.is_file():
        return []
    data = _object(_json(path), path)
    devices = _list(data.get("devices"), path, "network devices")
    records: list[dict[str, Any]] = []
    for raw in devices:
        device = _object(raw, path)
        identity = _string(device.get("entity_id"), path, "network entity id")
        ip = _string(device.get("ip"), path, "network IP", required=False)
        typ = _string(device.get("type"), path, "network type")
        connected = _bool(device.get("connected"), path, "network connected")
        if not identity.startswith("net/") or (ip and not _IP.fullmatch(ip)):
            raise EntityError(f"malformed network device identity in {path}")
        state = "connected" if connected else "offline"
        if ip in firewall:
            records.append(_record(identity, "network", address=ip, status=state, bucket="matched",
                                   note=f"{typ} in firewall estate alias", device_type=typ))
        else:
            records.append(_record(identity, "network", address=ip, status=state, bucket="unlisted",
                                   note=f"{typ} not in a firewall INFRASTRUCTURE alias — drift",
                                   device_type=typ))
    return records


def audit(repo: Path) -> dict[str, Any]:
    """Audit all available entity classes and return a serializable report.

    Guest and service running-unmapped records are the only failing condition.  Template, stale,
    exception, vhost-unresolved, and network-unlisted records remain visible but do not fail the
    audit.  OPNsense contributes only liveness notes; it never enters the mapping decision.
    """
    root = Path(repo)
    if not root.is_dir():
        raise EntityError(f"required source unavailable: {root}")
    vlans, slugs, exceptions, exception_sources = _conventions(root)
    firewall = _firewall_ips(root)
    live, down, raw_arp, have_liveness = _liveness(root)
    guests, guest_holes = _proxmox_guests(root, vlans, slugs, exceptions, exception_sources,
                                          firewall, live, down, raw_arp, have_liveness)
    services, service_holes = _service_records(root, vlans, slugs, firewall, _lab_hosts(root))
    nodes = _node_records(root)
    known = {str(record["entity_id"]) for record in guests + services + nodes}
    known.update(svc_id(entry.name) for entry in (root / "compose").iterdir() if entry.is_dir())
    vhosts = _route_records(root, known)
    networks = _network_records(root, firewall)
    records = guests + services + nodes + vhosts + networks
    counts: dict[str, dict[str, int]] = {
        name: {} for name in ("guest", "service", "node", "vhost", "network")
    }
    for record in records:
        entity_class = str(record["class"])
        bucket = str(record["bucket"])
        counts[entity_class][bucket] = counts[entity_class].get(bucket, 0) + 1
    holes = guest_holes + service_holes
    return {
        "target": "entities",
        "outcome": "failure" if holes else "success",
        "records": records,
        "entities": records,
        "counts": counts,
        "holes": holes,
        "exit_code": 1 if holes else 0,
    }


audit_entities = audit


def _row(entity_id: str, address: str, status: str, bucket: str, note: str, second: str = "") -> str:
    return f"  {entity_id:<40} {address or second or '—':<22} {status:<11} {bucket:<16} {note}"


def render(report: dict[str, Any], stdout: TextIO) -> None:
    """Render the stable human audit view used by operators and invariant diagnostics."""
    grouped = {name: [record for record in report["records"] if record["class"] == name]
               for name in ("guest", "service", "node", "vhost", "network")}
    print("== entity audit :: guest (VMID -> IP, ADR 0001) ==", file=stdout)
    print(_row("ENTITY ID", "ADDRESS", "STATUS", "BUCKET", "NOTE"), file=stdout)
    for record in grouped["guest"]:
        marker = "✓ " if record["bucket"] == "matched" else "✗ " if record["bucket"] == "running-unmapped" else ""
        print(_row(marker + str(record["entity_id"]), str(record["address"]), str(record["status"]),
                   str(record["bucket"]), str(record["note"])), file=stdout)
    guest_counts = report["counts"].get("guest", {})
    print("  ── guests: " + " · ".join(
        f"{guest_counts.get(bucket, 0)} {bucket}" for bucket in
        ("matched", "stale", "running-unmapped", "exception", "template")), file=stdout)
    print(file=stdout)
    print("== entity audit :: svc (compose project name) ==", file=stdout)
    print(_row("ENTITY ID", "HOSTED_ON", "STATUS", "BUCKET", "NOTE"), file=stdout)
    for record in grouped["service"]:
        marker = "✓ " if record["bucket"] == "matched" else "✗ " if record["bucket"] == "running-unmapped" else ""
        print(_row(marker + str(record["entity_id"]), "", str(record["status"]), str(record["bucket"]),
                   str(record["note"]), str(record.get("hosted_on", "—"))), file=stdout)
    service_counts = report["counts"].get("service", {})
    print("  ── services: " + " · ".join(
        f"{service_counts.get(bucket, 0)} {bucket}" for bucket in
        ("matched", "running-unmapped", "declared-idle")), file=stdout)
    print(file=stdout)
    print("== entity audit :: node ==", file=stdout)
    for record in grouped["node"]:
        print(_row(str(record["entity_id"]), "—", "—", "matched", "Proxmox node"), file=stdout)
    print(file=stdout)
    print("== entity audit :: vhost (Caddy routes) ==", file=stdout)
    for record in grouped["vhost"]:
        marker = "⚠ " if record["bucket"] == "unresolved" else ""
        print(_row(marker + str(record["entity_id"]), "→ " + str(record["address"]), "route",
                   str(record["bucket"]), str(record["note"])), file=stdout)
    if not grouped["vhost"]:
        print("  (no inventory/routes.json yet — run the routes collector)", file=stdout)
    vhost_counts = report["counts"].get("vhost", {})
    print(f"  ── vhost: {vhost_counts.get('matched', 0)} resolved · "
          f"{vhost_counts.get('unresolved', 0)} unresolved-backend (informational)", file=stdout)
    print(file=stdout)
    print("== entity audit :: net (Omada estate) ==", file=stdout)
    for record in grouped["network"]:
        marker = "⚠ " if record["bucket"] == "unlisted" else ""
        print(_row(marker + str(record["entity_id"]), str(record["address"]), str(record["status"]),
                   str(record["bucket"]), str(record["note"])), file=stdout)
    if not grouped["network"]:
        print("  (no inventory/network-gear.json yet — run the network-gear collector)", file=stdout)
    network_counts = report["counts"].get("network", {})
    print(f"  ── net: {network_counts.get('matched', 0)} matched · "
          f"{network_counts.get('unlisted', 0)} unlisted-in-firewall (informational, not a hole)",
          file=stdout)
    print(file=stdout)
    if report["holes"]:
        print("audit-entities: ✗ running entities with no home — resolve each or declare an exception.",
              file=stdout)
    else:
        print("audit-entities: ✓ every running entity is mapped or a declared exception.", file=stdout)


def run_audit(repo: Path, *, json_output: bool, stdout: TextIO, stderr: TextIO | None = None) -> int:
    """Run the packaged audit command, keeping required-source errors explicit."""
    error_stream = sys.stderr if stderr is None else stderr
    try:
        report = audit(repo)
    except EntityError as error:
        result = {"target": "entities", "outcome": "unavailable" if error.code == 2 else "failure",
                  "reason": str(error)}
        if json_output:
            print(json.dumps(result), file=stdout)
        else:
            print(f"audit-entities: {result['outcome']}: {result['reason']}", file=error_stream)
        return error.code
    if json_output:
        print(json.dumps(report, ensure_ascii=False), file=stdout)
    else:
        render(report, stdout)
    return int(report["exit_code"])


def _command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m skynet.entities")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, function in (("vmid-to-ip", vmid_to_ip), ("ip-to-vmid", ip_to_vmid),
                           ("vlan-of-vmid", vlan_of_vmid), ("guest-id", guest_id),
                           ("svc-id", svc_id), ("node-id", node_id), ("vhost-id", vhost_id),
                           ("net-id", net_id)):
        command = commands.add_parser(name)
        command.add_argument("values", nargs="*")
        command.set_defaults(function=function)
    audit_command = commands.add_parser("audit")
    audit_command.add_argument("--repo", type=Path, required=True)
    audit_command.add_argument("--json", action="store_true", dest="json_output")
    arguments = parser.parse_args(argv)
    if arguments.command == "audit":
        return run_audit(arguments.repo, json_output=arguments.json_output, stdout=sys.stdout)
    try:
        if arguments.command == "guest-id":
            if len(arguments.values) != 2:
                raise EntityError("usage: guest-id <vmid> <name>", 2)
            value = arguments.function(arguments.values[0], arguments.values[1])
        else:
            if len(arguments.values) != 1:
                raise EntityError(f"usage: {arguments.command} <value>", 2)
            value = arguments.function(arguments.values[0])
    except EntityError as error:
        print(f"entity: {error}", file=sys.stderr)
        return error.code
    print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(_command(sys.argv[1:]))
