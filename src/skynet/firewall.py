"""Offline OPNsense config.xml parsing for DR rebuild — never a live-freshness source.

`collect-opnsense.sh`/`src/skynet/opnsense.py` is the live T1 collector. This parses the
git-mirrored `config.xml` so firewall.json can be rebuilt when the API is unreachable or OPNsense
is not up yet. It performs no network or git operation — the operator refreshes the mirror first —
and it writes no receipt-bound marker, so an offline parse can never satisfy the default freshness
contract. config.xml carries hashed secrets, so any sensitive-looking child tag is dropped whether
or not it currently holds a value.
"""

import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from skynet.proxmox import CollectionError, publish

DEFAULT_CONFIG = Path("/opt/skynet-ops/mirror/skynet-opnsense/config.xml")
# Defense in depth: a committed inventory must never carry a secret from config.xml.
SENSITIVE = ("password", "passwordagain", "secret", "sharedsecret", "shared_secret",
             "pre_shared_key", "psk", "privatekey", "private_key", "passphrase",
             "apikey", "api_key", "token", "md5password", "cryptokey", "key", "hash")


def _sensitive(tag: str) -> bool:
    lowered = tag.lower()
    return any(marker in lowered for marker in SENSITIVE)


def _row(element: ET.Element) -> dict[str, str]:
    return {child.tag: (child.text or "") for child in element if not _sensitive(child.tag)}


def _find(root: ET.Element, path: str) -> list[dict[str, str]]:
    return [_row(element) for element in root.findall(path)]


def parse(config: Path) -> dict[str, Any]:
    """Parse the mirrored config.xml into the firewall.json shape, dropping sensitive tags."""
    try:
        text = config.read_bytes()
    except (OSError, ValueError):
        raise CollectionError("config mirror unavailable", 3) from None
    try:
        # The source is the operator's own git-mirrored backup, not untrusted network input.
        root = ET.fromstring(text)
    except ET.ParseError:
        raise CollectionError("malformed config XML") from None
    if root.tag != "opnsense":
        raise CollectionError("unexpected config root")
    aliases = (_find(root, "./OPNsense/Firewall/Alias/aliases/alias")
               or _find(root, "./aliases/alias"))
    rules = _find(root, "./filter/rule") + _find(root, "./OPNsense/Firewall/Filter/rules/rule")
    reservations: list[dict[str, str]] = []
    for path in (".//OPNsense/Kea/dhcp4/reservations/reservation",
                 "./dhcpd/lan/staticmap", "./dnsmasq/hosts"):
        reservations += _find(root, path)
    return {"collected": datetime.now(UTC).isoformat(timespec="seconds"), "source": str(config),
            "counts": {"aliases": len(aliases), "rules": len(rules),
                       "reservations": len(reservations)},
            "aliases": aliases, "rules": rules, "reservations": reservations}


def collect(output: Path, config: Path, *, json_output: bool, stdout: TextIO) -> int:
    """Parse the offline mirror into firewall.json; failure leaves the destination untouched.

    This is a DR rebuild only. It writes no freshness marker, so the result never satisfies the
    default collection freshness contract; run the live collector for current evidence.
    """
    report: dict[str, Any] = {"target": "firewall", "output": str(output), "source": str(config)}
    try:
        data = parse(config)
        publish(output, data)
    except CollectionError as error:
        report.update(outcome="unavailable" if error.code == 3 else "failure",
                      reason=f"{error}; parse failed; any retained snapshot is previous evidence")
        code = error.code
    else:
        report.update(outcome="success", collected=data["collected"], counts=data["counts"])
        code = 0
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"firewall (offline mirror): {report['outcome']} → {report['output']}", file=stdout)
        if code:
            print(report["reason"], file=stdout)
        else:
            print("offline DR rebuild; not a live-freshness source", file=stdout)
    return code
