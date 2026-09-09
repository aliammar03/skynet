"""Behavioral tests for the offline OPNsense config.xml mirror parser (DR rebuild)."""

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

from skynet.cli import main  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "firewall" / "config.xml"


def collect(tmp_path: Path, config: Path,
            capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, Any], Path]:
    output = tmp_path / "firewall.json"
    code = main(["collect", "firewall", "--output", str(output), "--config", str(config), "--json"])
    return code, json.loads(capsys.readouterr().out), output


def test_parses_user_view_shape_and_provenance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    code, report, output = collect(tmp_path, FIXTURE, capsys)
    assert code == 0 and report["outcome"] == "success"
    data = json.loads(output.read_text())
    assert data["source"] == str(FIXTURE)
    assert data["counts"] == {"aliases": 2, "rules": 1, "reservations": 1}
    assert [alias["name"] for alias in data["aliases"]] == [
        "HOST_ADMIN_WORKSTATION", "NET_SKYNET"]
    host = data["aliases"][0]
    assert host["type"] == "host" and host["content"] == "10.10.10.50"
    assert data["rules"][0]["sequence"] == "100" and data["rules"][0]["action"] == "pass"
    assert data["reservations"][0]["ip_address"] == "10.10.10.50"


def test_sensitive_child_tags_are_dropped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    code, _, output = collect(tmp_path, FIXTURE, capsys)
    assert code == 0
    data = json.loads(output.read_text())
    # The rule carried an <apikey>; defense-in-depth must drop it from the committed inventory.
    assert "apikey" not in data["rules"][0]
    blob = output.read_text()
    assert "SHOULD-BE-REDACTED" not in blob
    # Secrets outside alias/rule/reservation rows (system user) are never parsed at all.
    assert "HASHED-NEVER-PARSED" not in blob and "ACCOUNT-KEY-NEVER-PARSED" not in blob


def test_offline_parse_is_not_a_live_freshness_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    code, _, output = collect(tmp_path, FIXTURE, capsys)
    assert code == 0
    data = json.loads(output.read_text())
    # No host field and no receipt-bound marker, so collect-status can never bless the offline rebuild.
    assert "host" not in data
    assert not list(output.parent.glob("collection-*.json"))


def test_missing_mirror_is_unavailable_and_retains_bytes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "firewall.json"
    output.write_text('{"previous": true}\n')
    previous = output.read_bytes()
    code = main(["collect", "firewall", "--output", str(output),
                 "--config", str(tmp_path / "absent.xml"), "--json"])
    report = json.loads(capsys.readouterr().out)
    assert code == 3 and report["outcome"] == "unavailable"
    assert output.read_bytes() == previous


@pytest.mark.parametrize("contents,expected", [
    ("<opnsense><OPNsense></OPNsense", "failure"),          # malformed XML
    ("<router><filter/></router>", "failure"),               # unexpected root
])
def test_malformed_or_unexpected_config_fails_and_retains_bytes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], contents: str, expected: str,
) -> None:
    output = tmp_path / "firewall.json"
    output.write_text('{"previous": true}\n')
    previous = output.read_bytes()
    config = tmp_path / "config.xml"
    config.write_text(contents)
    code = main(["collect", "firewall", "--output", str(output), "--config", str(config), "--json"])
    report = json.loads(capsys.readouterr().out)
    assert code == 1 and report["outcome"] == expected
    assert output.read_bytes() == previous


def test_legacy_alias_and_rule_paths_are_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    config = tmp_path / "config.xml"
    config.write_text(
        "<opnsense><aliases><alias><name>LEGACY</name><type>host</type>"
        "<content>10.10.1.1</content></alias></aliases>"
        "<filter><rule><descr>legacy rule</descr></rule></filter></opnsense>"
    )
    code, report, output = collect(tmp_path, config, capsys)
    assert code == 0
    data = json.loads(output.read_text())
    assert data["aliases"][0]["name"] == "LEGACY" and data["counts"]["rules"] == 1
