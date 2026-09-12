"""Focused behavioral coverage for the packaged entity spine and audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skynet import entities  # noqa: E402
from skynet.cli import main  # noqa: E402


SLUGS = {
    10: "lan", 20: "servers", 30: "iot", 50: "mgmt", 60: "admin", 70: "netsvc",
    80: "identity", 90: "ops", 100: "dmz",
}


def write_repo(tmp_path: Path, *, guests: list[dict[str, Any]], firewall: list[str] | None = None,
               exceptions: list[dict[str, Any]] | None = None,
               presence: list[dict[str, Any]] | None = None,
               routes: list[dict[str, Any]] | None = None,
               devices: list[dict[str, Any]] | None = None,
               projects: list[str] | None = None) -> Path:
    repo = tmp_path / "repo"
    (repo / "inventory" / "firewall").mkdir(parents=True)
    (repo / "compose" / "books").mkdir(parents=True)
    (repo / "compose" / "books" / "compose.yaml").write_text("services: {}\n")
    for project in projects or []:
        (repo / "compose" / project).mkdir()
    (repo / "invariants.json").write_text(json.dumps({
        "entity_conventions": {"declared_vlans": list(SLUGS), "exceptions": exceptions or []},
        "excluded_guests": {"guests": []},
    }))
    (repo / "lab.json").write_text(json.dumps({
        "vlans": {"list": [{"vlan": vlan, "name": str(vlan), "slug": slug}
                              for vlan, slug in SLUGS.items()]},
        "docker_hosts": {"hosts": [{"label": "docker-dmz", "vmid": 10015,
                                      "guest": "vm-docker-dmz"}]},
    }))
    (repo / "inventory" / "proxmox-core.json").write_text(json.dumps({
        "nodes": [{"type": "node", "node": "server-proxmox-core"}], "resources": guests,
    }))
    (repo / "inventory" / "firewall" / "firewall.json").write_text(json.dumps({
        "aliases": [{"type": "host", "content": "\n".join(firewall or [])}],
        "reservations": [],
    }))
    if presence is not None:
        (repo / "inventory" / "opnsense.json").write_text(json.dumps({
            "presence": presence, "arp": [{"ip": row["ip"]} for row in presence],
        }))
    if routes is not None:
        (repo / "inventory" / "routes.json").write_text(json.dumps({"routes": routes}))
    if devices is not None:
        (repo / "inventory" / "network-gear.json").write_text(json.dumps({"devices": devices}))
    if projects is not None:
        (repo / "inventory" / "docker-dmz.json").write_text(json.dumps({
            "host": "docker-dmz",
            "containers": [{"Labels": f"com.docker.compose.project={project}"} for project in projects],
        }))
    return repo


def record(report: dict[str, Any], entity_id: str) -> dict[str, Any]:
    return next(row for row in report["records"] if row["entity_id"] == entity_id)


def test_entity_grammar_preserves_canonical_legacy_and_ambiguous_vmid_rules() -> None:
    assert entities.vmid_to_ip(10015) == "10.10.100.15"
    assert entities.vmid_to_ip(240) == "10.10.20.40"
    assert entities.ip_to_vmid("10.10.100.15") == 10015
    assert entities.guest_id(10015, "vm-docker-dmz") == "guest/docker-dmz-10015"
    assert entities.guest_id(837, "lxc-authentik") == "guest/authentik-identity-837"
    with pytest.raises(entities.EntityError) as error:
        entities.vmid_to_ip(1035)
    assert error.value.code == 2


def test_audit_resolves_ambiguous_vmid_from_firewall_fact_and_keeps_liveness_annotation(
    tmp_path: Path,
) -> None:
    repo = write_repo(
        tmp_path,
        guests=[{"type": "qemu", "vmid": 1035, "name": "vm-edge", "status": "running"}],
        firewall=["10.10.100.35"],
        presence=[{"ip": "10.10.100.35", "live": True}],
    )
    report = entities.audit(repo)
    guest = record(report, "guest/edge-1035")
    assert report["outcome"] == "success"
    assert guest["bucket"] == "matched"
    assert guest["address"] == "10.10.100.35"
    assert "resolved by firewall fact" in guest["note"]
    assert "live" in guest["note"]


def test_audit_classifies_exception_template_and_stale_without_holes(tmp_path: Path) -> None:
    repo = write_repo(
        tmp_path,
        guests=[
            {"type": "qemu", "vmid": 5001, "name": "vm-opnsense", "status": "running"},
            {"type": "qemu", "vmid": 9000, "name": "vm-ubuntu-2404-base", "status": "stopped", "template": 1},
            {"type": "qemu", "vmid": 10015, "name": "vm-docker-dmz", "status": "stopped"},
        ],
        firewall=["10.10.100.15"],
    )
    (repo / "invariants.json").write_text(json.dumps({
        "entity_conventions": {"declared_vlans": list(SLUGS),
                                "exceptions": [{"vmid": 5001, "why": "firewall"}]},
        "excluded_guests": {"guests": []},
    }))
    report = entities.audit(repo)
    assert report["outcome"] == "success"
    assert record(report, "guest/opnsense-mgmt-5001")["bucket"] == "exception"
    assert record(report, "guest/ubuntu-2404-base-ops-9000")["bucket"] == "template"
    assert record(report, "guest/docker-dmz-10015")["bucket"] == "stale"


def test_running_unmapped_guest_fails_but_vhost_and_network_unresolved_are_informational(
    tmp_path: Path,
) -> None:
    repo = write_repo(
        tmp_path,
        guests=[{"type": "qemu", "vmid": 10015, "name": "vm-docker-dmz", "status": "running"}],
        firewall=[],
        presence=[{"ip": "10.10.100.15", "live": True}],
        routes=[{"vhost": "unknown.aliammar.net", "backend_entity": "host:10.10.99.9", "auth": "plain"}],
        devices=[{"entity_id": "net/unknown", "ip": "10.10.50.99", "type": "ap", "connected": False}],
    )
    report = entities.audit(repo)
    assert report["outcome"] == "failure"
    assert report["holes"] == ["guest/docker-dmz-10015"]
    assert "firewall/DNS host fact" in record(report, "guest/docker-dmz-10015")["note"]
    assert record(report, "vhost/unknown.aliammar.net")["bucket"] == "unresolved"
    assert record(report, "net/unknown")["bucket"] == "unlisted"


@pytest.mark.parametrize("missing", ["invariants.json", "lab.json", "inventory/firewall/firewall.json"])
def test_audit_fails_explicitly_for_missing_required_sources(tmp_path: Path, missing: str) -> None:
    repo = write_repo(tmp_path, guests=[])
    (repo / missing).unlink()
    with pytest.raises(entities.EntityError) as error:
        entities.audit(repo)
    assert error.value.code == 2


def test_audit_fails_explicitly_for_malformed_required_source(tmp_path: Path) -> None:
    repo = write_repo(tmp_path, guests=[])
    (repo / "inventory/firewall/firewall.json").write_text("not-json")
    with pytest.raises(entities.EntityError, match="malformed JSON"):
        entities.audit(repo)


def test_cli_entity_audit_emits_packaged_json_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = write_repo(
        tmp_path,
        guests=[{"type": "qemu", "vmid": 10015, "name": "vm-docker-dmz", "status": "running"}],
        firewall=["10.10.100.15"],
    )
    assert main(["entities", "--repo", str(repo), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["target"] == "entities" and report["outcome"] == "success"
