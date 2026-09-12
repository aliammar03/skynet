"""Behavioral tests for the disposable inventory SQLite projection."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
if os.environ.get("SKYNET_ENTRYPOINT") != "console" and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skynet import cache  # noqa: E402


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    inventory = path / "inventory"
    (inventory / "firewall").mkdir(parents=True)
    write_json(path / "lab.json", {
        "vlans": {"list": [
            {"vlan": 10, "name": "Trusted", "slug": "lan"},
            {"vlan": 100, "name": "DMZ", "slug": "dmz"},
        ]},
        "front_doors": {"aliases": [
            {"alias": "HOST_PROXY_APPS", "ip": "10.10.100.35", "proxy": "caddy-apps"},
        ]},
        "docker_hosts": {"hosts": [
            {"label": "docker-dmz", "vmid": 10015, "guest": "vm-docker-dmz"},
        ]},
    })
    write_json(path / "invariants.json", {
        "entity_conventions": {"declared_vlans": [10, 100], "exceptions": []},
        "excluded_guests": {"guests": []},
    })
    write_json(inventory / "proxmox-core.json", {
        "node": "server-proxmox-core",
        "nodes": [{"type": "node", "node": "server-proxmox-core"}],
        "resources": [
            {"type": "qemu", "vmid": 10015, "name": "vm-docker-dmz", "status": "running"},
            {"type": "lxc", "vmid": 1035, "name": "lxc-ambiguous", "status": "stopped"},
        ],
        "pools": [{"poolid": "ops-managed"}],
    })
    write_json(inventory / "firewall" / "firewall.json", {
        "reservations": [{"ip": "10.10.100.15", "host": "docker", "mac": "aa", "descr": "DMZ"}],
        "aliases": [{"name": "HOST_PROXY_APPS", "type": "host", "content": "10.10.100.35"}],
    })
    write_json(inventory / "dns-zones.json", {
        "records": [{"zone": "", "records": [
            {"name": "apps.example.test", "type": "A", "rData": {"ipAddress": "10.10.100.35"}},
            {"name": "docker.example.test", "type": "A", "rData": {"ipAddress": "10.10.100.15"}},
        ]}],
    })
    write_json(inventory / "docker-docker-dmz.json", {
        "host": "docker-dmz",
        "containers": [{
            "Labels": "com.docker.compose.project=books,com.docker.compose.service=books",
            "State": "running", "Image": "books:1",
        }],
    })
    write_json(inventory / "network-gear.json", {"devices": [{
        "entity_id": "net/switch", "type": "switch", "name": "Switch", "model": "x",
        "mac": "aa", "ip": "10.10.50.2", "firmware": "1", "needs_upgrade": False,
        "connected": True, "clients": 2, "poe": {"support": True}, "site": "lab",
        "ports": [{"port": 1, "name": "uplink", "profile": "trunk", "link": 1, "poe": 0}],
    }]})
    write_json(inventory / "opnsense.json", {"arp": [{
        "ip": "10.10.100.15", "mac": "aa", "hostname": "docker", "intf": "vlan100",
        "manufacturer": "test", "permanent": False,
    }]})
    write_json(inventory / "routes.json", {"routes": [{
        "vhost": "books.example.test", "front_door": "svc/caddy-apps", "backend": "10.10.100.15:80",
        "backend_entity": "guest/docker-dmz-10015", "auth": "plain",
    }]})
    write_json(inventory / "certs.json", {"certs": [{
        "label": "apps", "endpoint": "10.10.100.35:443", "reachable": True,
        "issuer": "test", "not_after": "2030", "days_left": 100,
    }]})
    write_json(
        inventory / "backup-jobs.json",
        [{"entity_id": "guest/docker-dmz-10015", "kind": "restic"}],
    )
    return path


def test_build_preserves_schema_entity_derivation_and_sql_views(repo: Path) -> None:
    result = cache.build(repo)

    assert result.guests == 2
    assert result.containers == 1
    assert cache.query(result.database, "SELECT entity_id, ip FROM guests ORDER BY vmid").rows == (
        ("guest/ambiguous-1035", ""),
        ("guest/docker-dmz-10015", "10.10.100.15"),
    )
    tables = cache.query(
        result.database, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    assert {row[0] for row in tables.rows} == set(cache.SCHEMA)

    host_sql = (ROOT / "scripts/sql/host-map.sql").read_text(encoding="utf-8")
    vhost_sql = (ROOT / "scripts/sql/vhosts.sql").read_text(encoding="utf-8")
    host_rows = [row for row in cache.query(result.database, host_sql).rows
                 if row[0] == "10.10.100.15"]
    assert host_rows[0][0] == "10.10.100.15"
    assert cache.query(result.database, vhost_sql).rows == (
        ("apps.example.test", "10.10.100.35", "caddy-apps"),
    )


@pytest.mark.parametrize("missing", ["lab.json", "invariants.json"])
def test_missing_required_sources_are_explicit(repo: Path, missing: str) -> None:
    (repo / missing).unlink()
    with pytest.raises(cache.CacheError, match="source unavailable") as error:
        cache.build(repo)
    assert error.value.code == 3


def test_cache_rejects_lab_and_invariant_vlan_mismatch_without_replacing_database(
    repo: Path,
) -> None:
    first = cache.build(repo)
    previous = first.database.read_bytes()
    invariants = json.loads((repo / "invariants.json").read_text(encoding="utf-8"))
    invariants["entity_conventions"]["declared_vlans"] = [10]
    write_json(repo / "invariants.json", invariants)

    with pytest.raises(cache.CacheError, match="entity conventions unavailable") as error:
        cache.build(repo)
    assert error.value.code == 3
    assert first.database.read_bytes() == previous


def test_malformed_source_retains_previous_database_and_recovers(repo: Path) -> None:
    first = cache.build(repo)
    previous = first.database.read_bytes()
    (repo / "inventory" / "dns-zones.json").write_text("{broken", encoding="utf-8")

    with pytest.raises(cache.CacheError, match="malformed JSON"):
        cache.build(repo)
    assert first.database.read_bytes() == previous

    write_json(repo / "inventory" / "dns-zones.json", {"records": []})
    recovered = cache.build(repo)
    assert recovered.database == first.database
    assert recovered.database.read_bytes() != previous


def test_atomic_publish_failure_retains_previous_database(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = cache.build(repo)
    previous = first.database.read_bytes()

    def fail_replace(_source: str | os.PathLike[str], _destination: Path) -> None:
        raise OSError("synthetic publish failure")

    monkeypatch.setattr(cache.os, "replace", fail_replace)
    with pytest.raises(cache.CacheError, match="cache rebuild failed"):
        cache.build(repo)
    assert first.database.read_bytes() == previous


def test_sqlite_capability_and_query_failures_are_non_success(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cache, "sqlite3", None)
    with pytest.raises(cache.CacheError, match="sqlite capability unavailable") as error:
        cache.build(repo)
    assert error.value.code == 3

    monkeypatch.undo()
    database = cache.build(repo).database
    with pytest.raises(cache.CacheError, match="query failed"):
        cache.query(database, "SELECT * FROM does_not_exist")


def test_direct_rebuild_does_not_require_freshness_marker(repo: Path) -> None:
    result = cache.build(repo, repo / ".cache" / "historical.db")
    assert result.database.is_file()
