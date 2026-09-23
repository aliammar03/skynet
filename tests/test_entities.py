"""The VMID/IP law (ADR 0001) and the running-entity audit over committed inventory."""

from pathlib import Path

import pytest

from skynet import entities


@pytest.mark.parametrize(("vmid", "ip"), [(10015, "10.10.100.15"), (7031, "10.10.70.31"),
                                          (2020, "10.10.20.20")])
def test_vmid_and_ip_round_trip(vmid: int, ip: str) -> None:
    assert entities.vmid_to_ip(vmid) == ip
    assert entities.ip_to_vmid(ip) == vmid


@pytest.mark.parametrize("vmid", [99, 4015, "abc"])
def test_off_convention_vmid_is_refused(vmid: int | str) -> None:
    with pytest.raises(entities.EntityError):
        entities.vmid_to_ip(vmid)


def test_entity_ids_are_stable() -> None:
    assert entities.guest_id(10015, "vm-docker-dmz") == "guest/docker-dmz-10015"
    assert entities.svc_id("karakeep") == "svc/karakeep"


def test_committed_inventory_has_no_running_unmapped_entity(repo_copy: Path) -> None:
    report = entities.audit(repo_copy)
    assert report["outcome"] == "success"
