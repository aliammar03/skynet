"""Build and query Skynet's disposable inventory SQLite projection.

The repository and its collected JSON are authoritative.  This module only creates a
throw-away SQLite view in ``.cache/``; a failed rebuild never removes or replaces the
previous view.  The schema deliberately stays flat because the consumers are the two
small SQL views in ``scripts/sql/`` and bounded ad-hoc queries.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from skynet import entities

try:
    import sqlite3
except ImportError:  # pragma: no cover - exercised by a capability-failure environment.
    sqlite3 = None  # type: ignore[assignment]


class CacheError(Exception):
    """A safe, user-facing cache build or query failure."""

    def __init__(self, reason: str, code: int = 1) -> None:
        super().__init__(reason)
        self.code = code


# Keep these columns in the same order as the original build-db.sh projection.  The
# SQL views and existing ad-hoc queries rely on the names, not on a migration layer.
SCHEMA: dict[str, tuple[tuple[str, str], ...]] = {
    "guests": (
        ("entity_id", "TEXT"), ("vmid", "INTEGER"), ("name", "TEXT"), ("node", "TEXT"),
        ("status", "TEXT"), ("template", "INTEGER"), ("pool", "TEXT"), ("ip", "TEXT"),
    ),
    "pools": (("node", "TEXT"), ("pool", "TEXT")),
    "reservations": (("ip", "TEXT"), ("host", "TEXT"), ("mac", "TEXT"), ("descr", "TEXT")),
    "aliases": (
        ("name", "TEXT"), ("type", "TEXT"), ("ip", "TEXT"), ("nmembers", "INTEGER"),
        ("descr", "TEXT"),
    ),
    "dns_a": (("name", "TEXT"), ("ip", "TEXT")),
    "containers": (
        ("project", "TEXT"), ("host_label", "TEXT"), ("hosted_on", "TEXT"),
        ("state", "TEXT"), ("image", "TEXT"),
    ),
    "front_doors": (("alias", "TEXT"), ("ip", "TEXT"), ("proxy", "TEXT")),
    "vlans": (("vlan", "INTEGER"), ("name", "TEXT"), ("slug", "TEXT")),
    "backup_jobs": (("entity_id", "TEXT"), ("kind", "TEXT")),
    "netgear": (
        ("entity_id", "TEXT"), ("type", "TEXT"), ("name", "TEXT"), ("model", "TEXT"),
        ("mac", "TEXT"), ("ip", "TEXT"), ("firmware", "TEXT"), ("needs_upgrade", "INTEGER"),
        ("connected", "INTEGER"), ("clients", "INTEGER"), ("poe_support", "INTEGER"),
        ("site", "TEXT"),
    ),
    "netports": (
        ("switch", "TEXT"), ("port", "INTEGER"), ("name", "TEXT"), ("profile", "TEXT"),
        ("link", "INTEGER"), ("poe", "INTEGER"),
    ),
    "arp": (
        ("ip", "TEXT"), ("mac", "TEXT"), ("hostname", "TEXT"), ("intf", "TEXT"),
        ("manufacturer", "TEXT"), ("permanent", "INTEGER"),
    ),
    "routes": (
        ("vhost", "TEXT"), ("front_door", "TEXT"), ("backend", "TEXT"),
        ("backend_entity", "TEXT"), ("auth", "TEXT"),
    ),
    "certs": (
        ("label", "TEXT"), ("endpoint", "TEXT"), ("reachable", "INTEGER"),
        ("issuer", "TEXT"), ("not_after", "TEXT"), ("days_left", "INTEGER"),
    ),
}

_IP_RE = re.compile(r"^10\.10\.[0-9]+\.[0-9]+$")
_ALIAS_IP_RE = re.compile(r"^10\.10\.[0-9]+\.[0-9]+$")
_PROJECT_RE = re.compile(r"(?:^|,)com\.docker\.compose\.project=(?P<project>[^,]+)(?:,|$)")


@dataclass(frozen=True)
class BuildResult:
    """Counts emitted by a successful cache rebuild."""

    database: Path
    guests: int
    hosts: int
    containers: int


@dataclass(frozen=True)
class QueryResult:
    """A query's column names and rows, suitable for CLI or caller formatting."""

    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]


def _source_error(path: Path, reason: str, code: int = 1) -> CacheError:
    return CacheError(f"{path.name}: {reason}", code)


def _sqlite_module() -> Any:
    if sqlite3 is None:
        raise CacheError("sqlite capability unavailable", 3)
    return sqlite3


def _read_json(path: Path) -> Any:
    """Read one UTF-8 JSON source and turn parse/I/O failures into CacheError."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise _source_error(path, "source unavailable", 3) from None
    if not raw.strip():
        raise _source_error(path, "source is empty")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeError):
        raise _source_error(path, "malformed JSON") from None


def _object(value: Any, path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _source_error(path, "top-level object required")
    return value


def _list(value: Mapping[str, Any], key: str, path: Path, *, required: bool = True) -> list[Any]:
    raw = value.get(key)
    if raw is None and not required:
        return []
    if not isinstance(raw, list):
        raise _source_error(path, f"{key} must be a list")
    return raw


def _row(value: Any, path: Path, kind: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _source_error(path, f"{kind} entry must be an object")
    return value


def _text(
    value: Any, path: Path, field: str, *, default: str = "", allow_controls: bool = False
) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or (not allow_controls and any(ord(char) < 32 for char in value)):
        raise _source_error(path, f"{field} must be a string")
    return value


def _integer(value: Any, path: Path, field: str, *, default: int = 0) -> int:
    if value is None:
        return default
    if type(value) is not int:
        raise _source_error(path, f"{field} must be an integer")
    return value


def _boolean_int(value: Any, path: Path, field: str, *, default: bool = False) -> int:
    if value is None:
        return int(default)
    if type(value) is not bool:
        raise _source_error(path, f"{field} must be a boolean")
    return int(value)


def _docker_hosts(lab: Mapping[str, Any], path: Path) -> dict[str, tuple[int, str]]:
    section = lab.get("docker_hosts")
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise _source_error(path, "docker_hosts must be an object")
    entries = section.get("hosts")
    if not isinstance(entries, list):
        raise _source_error(path, "docker_hosts.hosts must be a list")
    hosts: dict[str, tuple[int, str]] = {}
    for item in entries:
        row = _row(item, path, "Docker host")
        label = _text(row.get("label"), path, "label")
        guest = _text(row.get("guest"), path, "guest")
        vmid = _integer(row.get("vmid"), path, "vmid", default=0)
        if not label or not guest or vmid <= 0 or label in hosts:
            raise _source_error(
                path, "docker host entries must have unique label/vmid/guest values"
            )
        hosts[label] = (vmid, guest)
    return hosts


def _front_doors(lab: Mapping[str, Any], path: Path) -> list[tuple[str, str, str]]:
    section = lab.get("front_doors")
    if not isinstance(section, dict):
        raise _source_error(path, "front_doors must be an object")
    entries = section.get("aliases")
    if not isinstance(entries, list):
        raise _source_error(path, "front_doors.aliases must be a list")
    result: list[tuple[str, str, str]] = []
    for item in entries:
        row = _row(item, path, "front door")
        alias = _text(row.get("alias"), path, "alias")
        ip = _text(row.get("ip"), path, "ip")
        proxy = _text(row.get("proxy"), path, "proxy")
        if not alias or not ip or not proxy:
            raise _source_error(path, "front door entries require alias, ip and proxy")
        result.append((alias, ip, proxy))
    return result


def _guest_fields(
    vmid: int,
    name: str,
    declared: set[int],
    slugs: Mapping[int, str],
) -> tuple[str, str]:
    """Derive guest identity through the packaged entity grammar."""
    declared_vlans = tuple(sorted(declared))
    try:
        entity_id = entities.guest_id(vmid, name, declared_vlans, dict(slugs))
    except entities.EntityError:
        entity_id = f"guest/{name.removeprefix('vm-').removeprefix('lxc-')}-{vmid}"
    try:
        ip = entities.vmid_to_ip(vmid, declared_vlans)
    except entities.EntityError:
        ip = ""
    return entity_id, ip


def _proxmox_rows(
    inventory: Path,
    declared: set[int],
    slugs: Mapping[int, str],
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    guests: list[tuple[Any, ...]] = []
    pools: list[tuple[Any, ...]] = []
    for path in sorted(inventory.glob("proxmox-*.json")):
        data = _object(_read_json(path), path)
        # ACL snapshots share the prefix but have no resource/pool projection.
        if "resources" not in data and "pools" not in data:
            continue
        resources = _list(data, "resources", path)
        raw_nodes = data.get("nodes", [])
        if not isinstance(raw_nodes, list):
            raise _source_error(path, "nodes must be a list")
        node = _text(data.get("node"), path, "node")
        for item in raw_nodes:
            row = _row(item, path, "node")
            if row.get("type") == "node":
                node = _text(row.get("node"), path, "node")
                break
        raw_pools = _list(data, "pools", path, required=False)
        for item in resources:
            row = _row(item, path, "resource")
            kind = _text(row.get("type"), path, "type")
            if kind not in {"qemu", "lxc"}:
                continue
            vmid = _integer(row.get("vmid"), path, "vmid", default=0)
            name = _text(row.get("name"), path, "name")
            status = _text(row.get("status"), path, "status")
            if vmid <= 0 or not name or not status:
                raise _source_error(path, "guest requires positive vmid, name and status")
            template = _integer(row.get("template"), path, "template", default=0)
            if template not in (0, 1):
                raise _source_error(path, "template must be 0 or 1")
            pool = _text(row.get("pool"), path, "pool")
            entity_id, ip = _guest_fields(vmid, name, declared, slugs)
            guests.append((entity_id, vmid, name, node, status, template, pool, ip))
        for item in raw_pools:
            row = _row(item, path, "pool")
            pool = _text(row.get("poolid"), path, "poolid")
            if pool:
                pools.append((node, pool))
    return guests, pools


def _firewall_rows(inventory: Path) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    path = inventory / "firewall" / "firewall.json"
    if not path.exists():
        return [], []
    data = _object(_read_json(path), path)
    reservations: list[tuple[Any, ...]] = []
    for item in _list(data, "reservations", path):
        row = _row(item, path, "reservation")
        ip = _text(row.get("ip") or row.get("address"), path, "ip")
        if not _IP_RE.match(ip):
            continue
        reservations.append((
            ip,
            _text(row.get("host"), path, "host"),
            _text(row.get("mac") or row.get("hwaddr"), path, "mac"),
            _text(row.get("descr"), path, "descr"),
        ))
    aliases: list[tuple[Any, ...]] = []
    for item in _list(data, "aliases", path):
        row = _row(item, path, "alias")
        if _text(row.get("type"), path, "type") != "host":
            continue
        content = _text(row.get("content"), path, "content", allow_controls=True)
        ips = [line for line in content.splitlines() if _ALIAS_IP_RE.match(line)]
        aliases.extend((
            _text(row.get("name"), path, "name"),
            "host",
            ip,
            len(ips),
            _text(row.get("description"), path, "description"),
        ) for ip in ips)
    return reservations, aliases


def _dns_rows(inventory: Path) -> list[tuple[Any, ...]]:
    path = inventory / "dns-zones.json"
    if not path.exists():
        return []
    data = _object(_read_json(path), path)
    result: list[tuple[Any, ...]] = []
    for zone_item in _list(data, "records", path):
        zone = _row(zone_item, path, "DNS zone")
        raw_records = zone.get("records")
        if raw_records is None:
            continue
        if not isinstance(raw_records, list):
            raise _source_error(path, "DNS zone records must be a list or null")
        for item in raw_records:
            row = _row(item, path, "DNS record")
            if _text(row.get("type"), path, "type") != "A":
                continue
            rdata = row.get("rData")
            if not isinstance(rdata, dict):
                raise _source_error(path, "A record rData must be an object")
            ip = _text(rdata.get("ipAddress"), path, "ipAddress")
            if _IP_RE.match(ip):
                result.append((_text(row.get("name"), path, "name"), ip))
    return result


def _container_rows(
    inventory: Path,
    docker_hosts: Mapping[str, tuple[int, str]],
    declared: set[int],
    slugs: Mapping[int, str],
) -> list[tuple[Any, ...]]:
    result: list[tuple[Any, ...]] = []
    for path in sorted(inventory.glob("docker-*.json")):
        data = _object(_read_json(path), path)
        label = _text(data.get("host"), path, "host")
        if not label:
            raise _source_error(path, "host is required")
        containers = _list(data, "containers", path)
        hosted = f"host:{label}?"
        if label in docker_hosts:
            vmid, guest = docker_hosts[label]
            hosted = _guest_fields(vmid, guest, declared, slugs)[0]
        projects: dict[str, dict[str, Any]] = {}
        for item in containers:
            row = _row(item, path, "container")
            labels = row.get("Labels")
            if labels is None:
                continue
            if not isinstance(labels, str):
                raise _source_error(path, "container Labels must be a string")
            match = _PROJECT_RE.search(labels)
            if match and match["project"] not in projects:
                projects[match["project"]] = row
        for project, row in projects.items():
            result.append((
                project,
                label,
                hosted,
                _text(row.get("State"), path, "State"),
                _text(row.get("Image"), path, "Image"),
            ))
    return result


def _lab_rows(
    lab: Mapping[str, Any], path: Path
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    front_doors = _front_doors(lab, path)
    vlans_section = lab["vlans"]
    if not isinstance(vlans_section, dict):  # entities.conventions already checks; keep mypy narrow.
        raise _source_error(path, "vlans must be an object")
    vlan_rows: list[tuple[Any, ...]] = []
    entries = vlans_section.get("list")
    if not isinstance(entries, list):
        raise _source_error(path, "vlans.list must be a list")
    for item in entries:
        row = _row(item, path, "VLAN")
        vlan_rows.append((
            _integer(row.get("vlan"), path, "vlan"),
            _text(row.get("name"), path, "name"),
            _text(row.get("slug"), path, "slug"),
        ))
    return front_doors, vlan_rows


def _network_rows(inventory: Path) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    path = inventory / "network-gear.json"
    if not path.exists():
        return [], []
    data = _object(_read_json(path), path)
    devices = _list(data, "devices", path)
    gear: list[tuple[Any, ...]] = []
    ports: list[tuple[Any, ...]] = []
    for item in devices:
        row = _row(item, path, "network device")
        entity_id = _text(row.get("entity_id"), path, "entity_id")
        if not entity_id:
            raise _source_error(path, "network device entity_id is required")
        poe = row.get("poe")
        if poe is not None and not isinstance(poe, dict):
            raise _source_error(path, "network device poe must be an object")
        poe_support = _boolean_int((poe or {}).get("support"), path, "poe.support")
        clients = _integer(row.get("clients"), path, "clients")
        gear.append((
            entity_id,
            _text(row.get("type"), path, "type"),
            _text(row.get("name"), path, "name"),
            _text(row.get("model"), path, "model"),
            _text(row.get("mac"), path, "mac"),
            _text(row.get("ip"), path, "ip"),
            _text(row.get("firmware"), path, "firmware"),
            _boolean_int(row.get("needs_upgrade"), path, "needs_upgrade"),
            _boolean_int(row.get("connected"), path, "connected"),
            clients,
            poe_support,
            _text(row.get("site"), path, "site"),
        ))
        raw_ports = row.get("ports")
        if raw_ports is None:
            continue
        if not isinstance(raw_ports, list):
            raise _source_error(path, "network device ports must be a list")
        for item_port in raw_ports:
            port = _row(item_port, path, "network port")
            ports.append((
                entity_id,
                _integer(port.get("port"), path, "port"),
                _text(port.get("name"), path, "name"),
                _text(port.get("profile"), path, "profile"),
                _integer(port.get("link"), path, "link"),
                _integer(port.get("poe"), path, "poe"),
            ))
    return gear, ports


def _arp_rows(inventory: Path) -> list[tuple[Any, ...]]:
    path = inventory / "opnsense.json"
    if not path.exists():
        return []
    data = _object(_read_json(path), path)
    result: list[tuple[Any, ...]] = []
    for item in _list(data, "arp", path):
        row = _row(item, path, "ARP")
        result.append((
            _text(row.get("ip"), path, "ip"),
            _text(row.get("mac"), path, "mac"),
            _text(row.get("hostname"), path, "hostname"),
            _text(row.get("intf"), path, "intf"),
            _text(row.get("manufacturer"), path, "manufacturer"),
            _boolean_int(row.get("permanent"), path, "permanent"),
        ))
    return result


def _route_rows(inventory: Path) -> list[tuple[Any, ...]]:
    path = inventory / "routes.json"
    if not path.exists():
        return []
    data = _object(_read_json(path), path)
    return [
        (
            _text(row.get("vhost"), path, "vhost"),
            _text(row.get("front_door"), path, "front_door"),
            _text(row.get("backend"), path, "backend"),
            _text(row.get("backend_entity"), path, "backend_entity"),
            _text(row.get("auth"), path, "auth"),
        )
        for item in _list(data, "routes", path)
        for row in (_row(item, path, "route"),)
    ]


def _cert_rows(inventory: Path) -> list[tuple[Any, ...]]:
    path = inventory / "certs.json"
    if not path.exists():
        return []
    data = _object(_read_json(path), path)
    result: list[tuple[Any, ...]] = []
    for item in _list(data, "certs", path):
        row = _row(item, path, "certificate")
        result.append((
            _text(row.get("label"), path, "label"),
            _text(row.get("endpoint"), path, "endpoint"),
            _boolean_int(row.get("reachable"), path, "reachable"),
            _text(row.get("issuer"), path, "issuer"),
            _text(row.get("not_after"), path, "not_after"),
            _integer(row.get("days_left"), path, "days_left", default=-1),
        ))
    return result


def _backup_rows(inventory: Path) -> list[tuple[Any, ...]]:
    path = inventory / "backup-jobs.json"
    if not path.exists():
        return []
    raw = _read_json(path)
    if not isinstance(raw, list):
        raise _source_error(path, "top-level list required")
    result: list[tuple[Any, ...]] = []
    for item in raw:
        row = _row(item, path, "backup job")
        result.append((
            _text(row.get("entity_id"), path, "entity_id"),
            _text(row.get("kind"), path, "kind"),
        ))
    return result


def _create_schema(connection: Any) -> None:
    for table, columns in SCHEMA.items():
        fields = ", ".join(f"{name} {kind}" for name, kind in columns)
        connection.execute(f"CREATE TABLE {table} ({fields})")


def _insert(connection: Any, table: str, rows: Iterable[tuple[Any, ...]]) -> None:
    columns = SCHEMA[table]
    names = ", ".join(name for name, _kind in columns)
    placeholders = ", ".join("?" for _ in columns)
    connection.executemany(f"INSERT INTO {table} ({names}) VALUES ({placeholders})", rows)


def _validate(connection: Any) -> None:
    check = connection.execute("PRAGMA integrity_check").fetchone()
    if check != ("ok",):
        raise CacheError("cache integrity check failed")
    for table, columns in SCHEMA.items():
        actual = tuple(row[1] for row in connection.execute(f"PRAGMA table_info({table})"))
        expected = tuple(name for name, _kind in columns)
        if actual != expected:
            raise CacheError("cache schema validation failed")


def _load_rows(repo: Path) -> dict[str, list[tuple[Any, ...]]]:
    inventory = repo / "inventory"
    lab_path = repo / "lab.json"
    if not inventory.is_dir():
        raise CacheError("inventory: source directory unavailable", 3)
    if not lab_path.is_file():
        raise CacheError("lab.json: source unavailable", 3)
    lab = _object(_read_json(lab_path), lab_path)
    try:
        declared_values, slugs, _, _ = entities.conventions(repo)
    except entities.EntityError as error:
        raise CacheError(f"entity conventions unavailable: {error}", 3) from None
    declared = set(declared_values)
    docker_hosts = _docker_hosts(lab, lab_path)
    front_doors, vlans = _lab_rows(lab, lab_path)
    guests, pools = _proxmox_rows(inventory, declared, slugs)
    reservations, aliases = _firewall_rows(inventory)
    netgear, netports = _network_rows(inventory)
    return {
        "guests": guests,
        "pools": pools,
        "reservations": reservations,
        "aliases": aliases,
        "dns_a": _dns_rows(inventory),
        "containers": _container_rows(inventory, docker_hosts, declared, slugs),
        "front_doors": front_doors,
        "vlans": vlans,
        "backup_jobs": _backup_rows(inventory),
        "netgear": netgear,
        "netports": netports,
        "arp": _arp_rows(inventory),
        "routes": _route_rows(inventory),
        "certs": _cert_rows(inventory),
    }


def _count_hosts(connection: Any) -> int:
    row = connection.execute(
        "SELECT COUNT(DISTINCT ip) FROM ("
        "SELECT ip FROM guests WHERE ip<>'' UNION SELECT ip FROM reservations "
        "UNION SELECT ip FROM aliases UNION SELECT ip FROM dns_a)"
    ).fetchone()
    return int(row[0])


def build(repo: Path, output: Path | None = None) -> BuildResult:
    """Atomically rebuild the disposable cache from one repository checkout."""
    sqlite = _sqlite_module()
    repo = repo.resolve()
    target = (output or repo / ".cache/inventory.db").resolve()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise CacheError("cache directory unavailable", 3) from None
    try:
        rows = _load_rows(repo)
    except CacheError:
        raise
    except Exception:
        raise CacheError("cache source projection failed") from None

    temporary: Path | None = None
    connection: Any = None
    counts: tuple[int, int, int] | None = None
    try:
        fd, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        os.close(fd)
        temporary = Path(name)
        try:
            connection = sqlite.connect(str(temporary))
        except Exception:
            raise CacheError("sqlite capability unavailable", 3) from None
        _create_schema(connection)
        for table, table_rows in rows.items():
            _insert(connection, table, table_rows)
        connection.commit()
        _validate(connection)
        counts = (
            int(connection.execute("SELECT COUNT(*) FROM guests").fetchone()[0]),
            _count_hosts(connection),
            int(connection.execute("SELECT COUNT(*) FROM containers").fetchone()[0]),
        )
        connection.close()
        connection = None
        os.replace(temporary, target)
        temporary = None
    except CacheError:
        raise
    except Exception:
        raise CacheError("cache rebuild failed") from None
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
        if temporary is not None:
            for path in (temporary, Path(f"{temporary}-journal"), Path(f"{temporary}-wal"),
                         Path(f"{temporary}-shm")):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    pass

    if counts is None:
        raise CacheError("cache verification failed")
    return BuildResult(target, *counts)


def query(database: Path, statement: str) -> QueryResult:
    """Execute one ad-hoc SQL statement and raise explicit failures."""
    sqlite = _sqlite_module()
    if not statement.strip():
        raise CacheError("query is empty")
    if not database.is_file():
        raise CacheError("cache database unavailable", 3)
    connection: Any = None
    try:
        connection = sqlite.connect(str(database))
        cursor = connection.execute(statement)
        columns = tuple(description[0] for description in (cursor.description or ()))
        rows = tuple(tuple(row) for row in cursor.fetchall())
        return QueryResult(columns, rows)
    except Exception:
        raise CacheError("query failed") from None
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def _render_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _print_query(result: QueryResult, stdout: TextIO, *, headers: bool, tabs: bool) -> None:
    if tabs:
        writer = csv.writer(stdout, delimiter="\t", lineterminator="\n")
        if headers:
            writer.writerow(result.columns)
        for row in result.rows:
            writer.writerow([_render_value(value) for value in row])
        return
    if headers:
        stdout.write("  ".join(result.columns) + "\n")
    for row in result.rows:
        stdout.write("  ".join(_render_value(value) for value in row) + "\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or query Skynet's disposable inventory cache."
    )
    parser.add_argument("--repo", type=Path, required=True, help="repository checkout")
    parser.add_argument(
        "--output", type=Path, help="cache destination (default .cache/inventory.db)"
    )
    parser.add_argument("--query", help="execute one SQL statement after/beside a build")
    parser.add_argument(
        "--database", type=Path, help="query an existing database instead of the repo default"
    )
    parser.add_argument("--sql-file", type=Path, help="read the query from a maintained SQL file")
    parser.add_argument("--format", choices=("tabs", "plain"), default="plain")
    parser.add_argument("--no-header", action="store_true", help="omit query column names")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None,
         stderr: TextIO | None = None) -> int:
    args = _parser().parse_args(argv)
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    try:
        database = args.database or args.output or args.repo / ".cache/inventory.db"
        if args.query is None and args.sql_file is None:
            result = build(args.repo, args.output)
            print(f"build-db: {result.database} — {result.guests} guests, "
                  f"{result.hosts} distinct IPs, {result.containers} containers", file=out)
            return 0
        if not database.exists():
            raise CacheError("cache database unavailable", 3)
        statement = args.query
        if args.sql_file is not None:
            try:
                statement = args.sql_file.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                raise CacheError("query source unavailable", 3) from None
        if not isinstance(statement, str):
            raise CacheError("query is empty")
        _print_query(query(database, statement), out, headers=not args.no_header,
                     tabs=args.format == "tabs")
        return 0
    except CacheError as error:
        print(f"cache: {error}", file=err)
        return error.code


if __name__ == "__main__":
    raise SystemExit(main())
