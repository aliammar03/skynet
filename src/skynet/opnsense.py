"""T1 live OPNsense observations: pinned GET/search reads, user-view config, paired publication.

One collection produces two paired snapshots — the firewall configuration (aliases/rules/
reservations, filtered to the user view the mirror showed) and live state the mirror cannot give
(firmware, ARP, interfaces, declared-host presence). Every required read and validation completes
before either file is published, so a read or validation failure leaves both destinations
untouched. Publication is deliberately two separate atomic file replacements: the default
collection markers bind the pair for freshness, but a publication failure may leave one new file
beside one previous file. Credentials are literal assignments, never shell code; the API key/secret
travel only in the Basic auth header and never in a diagnostic. This collector only reads: the
enumerated GETs plus the read-only search POSTs.
"""

import base64
import json
import re
import ssl
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO, cast

from skynet import common
from skynet.common import CollectionError

DEFAULT_CREDENTIALS = Path("/opt/skynet-ops/secrets/opnsense.env")
TIMEOUT = 25
# The live API returns OPNsense's built-in aliases; the mirror never did. Drop them to keep the
# user view identical: auto interface aliases and the named built-ins.
BUILTIN_ALIAS = re.compile(r"^__.*_network$|^(?:bogons|bogonsv6|sshlockout|virusprot)$")
HOST_IP = re.compile(r"^10\.10\.\d{1,3}\.\d{1,3}$")
SEARCH_BODY = json.dumps({"current": 1, "rowCount": 2000}).encode()
PING_WORKERS = 16


@dataclass(frozen=True)
class Credentials:
    """Validated OPNsense connection data; the key/secret are never serialized into a snapshot."""

    host: str
    port: int
    sni: str
    authorization: str
    context: ssl.SSLContext


def credentials(path: Path) -> Credentials:
    """Parse literal OPNsense credentials and derive the pinned-cert SNI and Basic authorization."""
    values = common.read_assignments(
        path, ("OPN_HOST", "OPN_USER", "OPN_KEY", "OPN_SECRET", "OPN_PORT", "OPN_CACERT", "OPN_SNI"),
        ("OPN_HOST", "OPN_KEY", "OPN_SECRET", "OPN_CACERT"))
    host = common.require_host(values["OPN_HOST"])
    port = common.port(values.get("OPN_PORT", "443"))
    key, secret = values["OPN_KEY"], values["OPN_SECRET"]
    if not common.printable(key + secret):
        raise CollectionError("invalid credential key", 3)
    cafile = values["OPN_CACERT"]
    context = common.ca_context(cafile)
    configured_sni = values.get("OPN_SNI")
    if configured_sni is not None:
        common.require_host(configured_sni, "invalid certificate name")
    # Derive the SNI from the pinned certificate so a stale configured name cannot break trust.
    # OPN_SNI remains a compatibility fallback only when no certificate name is available.
    try:
        sni = common.sni_from_certificate(cafile, host)
    except CollectionError:
        sni = configured_sni or host
    authorization = "Basic " + base64.b64encode(f"{key}:{secret}".encode()).decode()
    return Credentials(host, port, sni, authorization, context)


def _read(settings: Credentials, method: str, path: str, body: bytes | None) -> dict[str, Any]:
    """One pinned GET or read-only search POST; no redirect handling, key only in the header."""
    headers = {"Authorization": settings.authorization}
    if body is not None:
        headers["Content-Type"] = "application/json"
    connection = common.SNIConnection(settings.host, settings.port, settings.context,
                                      settings.sni, TIMEOUT)
    raw, _ = common.request(connection, method, "/api/" + path, headers=headers, body=body)
    payload = common.json_object(raw)
    if "error" in payload or "errors" in payload:
        raise CollectionError("API returned an error")
    return payload


def get(settings: Credentials, path: str) -> dict[str, Any]:
    return _read(settings, "GET", path, None)


def search(settings: Credentials, path: str) -> list[dict[str, Any]]:
    """Run a read-only search POST and require the returned page to be complete."""
    payload = _read(settings, "POST", path, SEARCH_BODY)
    rows = payload.get("rows")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise CollectionError("malformed search rows")
    total = payload.get("total")
    if isinstance(total, bool):
        raise CollectionError("malformed search total")
    if isinstance(total, int):
        if total < 0:
            raise CollectionError("malformed search total")
    elif isinstance(total, str) and re.fullmatch(r"(?:0|[1-9][0-9]*)", total):
        total = int(total)
    else:
        raise CollectionError("malformed search total")
    # A page smaller than the reported total means the fixed row budget truncated results.
    if total != len(rows):
        raise CollectionError("incomplete search page")
    return rows


def _text(value: Any, *, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str) or any(ord(char) < 32 for char in value):
        raise CollectionError("missing or malformed field")
    if required and not value:
        raise CollectionError("missing required field")
    return value


def _selected(value: Any, *, join: bool, required: bool = False) -> str:
    """OPNsense form fields arrive either as a plain string or a {key: {selected, value}} map."""
    if isinstance(value, dict):
        if not value:
            if join:
                return ""
            raise CollectionError("malformed form selection")
        if any(not isinstance(key, str) or not isinstance(option, dict)
                            or type(option.get("selected")) is not int
                            or option["selected"] not in (0, 1)
                            for key, option in value.items()):
            raise CollectionError("malformed form selection")
        chosen = [key for key, option in value.items() if option["selected"] == 1]
        if (required and not chosen) or (not join and (not chosen or len(chosen) > 1)):
            raise CollectionError("malformed form selection")
        return "\n".join(chosen) if join else chosen[0]
    selected = _text(value)
    if required and not selected:
        raise CollectionError("malformed form selection")
    return selected


def _container(root: dict[str, Any], *keys: str, label: str) -> dict[str, Any]:
    """Require each API container level while allowing an explicitly empty final mapping."""
    value: Any = root
    for key in keys:
        if not isinstance(value, dict) or key not in value or not isinstance(value[key], dict):
            raise CollectionError(f"malformed {label} container")
        value = value[key]
    return cast(dict[str, Any], value)


def _flag(value: Any, *, default: bool | None = None) -> bool:
    if value is None and default is not None:
        return default
    if type(value) is bool:
        return value
    if type(value) is int and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value in ("0", "1"):
        return value == "1"
    raise CollectionError("missing or malformed flag")


def _aliases(settings: Credentials) -> list[dict[str, Any]]:
    root = get(settings, "firewall/alias/get")
    container = _container(root, "alias", "aliases", "alias", label="alias")
    aliases = []
    for entry in container.values():
        if not isinstance(entry, dict):
            raise CollectionError("malformed alias entry")
        name = _text(entry.get("name"), required=True)
        if BUILTIN_ALIAS.match(name):
            continue
        enabled = entry.get("enabled")
        if enabled in (None, ""):
            enabled = "1"
        if not isinstance(enabled, str) or enabled not in ("0", "1"):
            raise CollectionError("missing or malformed field")
        aliases.append({"name": name, "type": _selected(entry.get("type"), join=False,
                                                             required=True),
                        "content": _selected(entry.get("content"), join=True),
                        "description": _text(entry.get("description")),
                        "enabled": enabled})
    return aliases


def _rules(settings: Credentials) -> list[dict[str, Any]]:
    configured = get(settings, "firewall/filter/get")
    rule_map = _container(configured, "filter", "rules", "rule", label="rule")
    sequences: dict[str, Any] = {}
    for uuid, rule in rule_map.items():
        if not isinstance(uuid, str) or not uuid or not isinstance(rule, dict):
            raise CollectionError("malformed rule entry")
        sequences[uuid] = _text(rule.get("sequence"), required=True)
    rules = []
    seen: set[str] = set()
    for row in search(settings, "firewall/filter/searchRule"):
        uuid = _text(row.get("uuid"), required=True)
        if uuid in seen:
            raise CollectionError("duplicate rule row")
        seen.add(uuid)
        # Intersect the flat display rows with the configured user rules; internal/auto rules
        # are absent from filter/get and excluded for free.
        if uuid not in sequences:
            continue
        rules.append({"sequence": sequences[uuid], "action": _text(row.get("action")),
                      "protocol": _text(row.get("protocol")),
                      "interface": (_text(row.get("interface")) or None),
                      "source_net": _text(row.get("source_net")),
                      "destination_net": _text(row.get("destination_net")),
                      "destination_port": _text(row.get("destination_port")),
                      "description": _text(row.get("description")), "uuid": uuid,
                      "enabled": _flag(row.get("enabled"), default=False)})
    configured_ids = set(sequences)
    displayed_ids = {rule["uuid"] for rule in rules}
    if displayed_ids != configured_ids or len(rules) != len(configured_ids):
        raise CollectionError("incomplete configured rule rows")
    return rules


def _reservations(settings: Credentials) -> list[dict[str, Any]]:
    keys = ("host", "domain", "ip", "hwaddr", "client_id", "descr", "aliases", "comments")
    return [{key: _text(row.get(key)) for key in keys}
            for row in search(settings, "dnsmasq/settings/searchHost")]


def _arp(settings: Credentials) -> list[dict[str, Any]]:
    rows = search(settings, "diagnostics/interface/searchArp")
    arp = []
    for row in rows:
        arp.append({"ip": _text(row.get("ip"), required=True), "mac": _text(row.get("mac")),
                    "hostname": _text(row.get("hostname")), "intf": _text(row.get("intf")),
                    "intf_description": _text(row.get("intf_description")),
                    "manufacturer": _text(row.get("manufacturer")),
                    "permanent": row.get("permanent") in ("1", 1, True),
                    "expired": row.get("expired") in ("1", 1, True),
                    "expires": row.get("expires")})
    return arp


def _interfaces(settings: Credentials) -> list[dict[str, Any]]:
    payload = get(settings, "interfaces/overview/interfacesInfo")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise CollectionError("malformed interface list")
    if "total" in payload:
        total = payload["total"]
        if isinstance(total, bool):
            raise CollectionError("malformed interface total")
        if isinstance(total, int):
            if total < 0:
                raise CollectionError("malformed interface total")
        elif isinstance(total, str) and re.fullmatch(r"(?:0|[1-9][0-9]*)", total):
            total = int(total)
        else:
            raise CollectionError("malformed interface total")
        if total != len(rows):
            raise CollectionError("incomplete interface page")
    interfaces = []
    for row in rows:
        if not isinstance(row, dict):
            raise CollectionError("malformed interface entry")
        interfaces.append({"device": _text(row.get("device"), required=True),
                           "description": _text(row.get("description")),
                           "status": _text(row.get("status")),
                           "enabled": _flag(row.get("enabled"), default=False),
                           "identifier": _text(row.get("identifier"))})
    return interfaces


def _ping(ip: str) -> bool | None:
    try:
        result = subprocess.run(["ping", "-c1", "-W1", ip], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=5)
        if result.returncode == 0:
            return True
        if result.returncode == 1:
            return False
        return None
    except (OSError, subprocess.SubprocessError):
        return None


def _presence(aliases: list[dict[str, Any]], arp: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Declared-host liveness from the ops vantage: ARP first, then ICMP for ARP-silent hosts.

    The vantage is explicit in `via`. `no-arp,no-icmp` means not observed live from here (down or
    ICMP-unreachable), not proven down; `icmp-unavailable` marks a probe that could not run at all.
    """
    arp_ips = {row["ip"] for row in arp}
    host_ips = sorted({ip for alias in aliases if alias["type"] == "host"
                       for ip in alias["content"].splitlines() if HOST_IP.match(ip)})
    silent = [ip for ip in host_ips if ip not in arp_ips]
    ping_available = _ping_available()
    answered: set[str] = set()
    unavailable: set[str] = set()
    if silent and ping_available:
        with ThreadPoolExecutor(max_workers=PING_WORKERS) as pool:
            results = dict(zip(silent, pool.map(_ping, silent)))
            answered = {ip for ip, up in results.items() if up is True}
            unavailable = {ip for ip, up in results.items() if up is None}
    presence = []
    for ip in host_ips:
        if ip in arp_ips:
            presence.append({"ip": ip, "live": True, "via": "arp"})
        elif ip in answered:
            presence.append({"ip": ip, "live": True, "via": "icmp"})
        elif not ping_available or ip in unavailable:
            presence.append({"ip": ip, "live": False, "via": "no-arp,icmp-unavailable"})
        else:
            presence.append({"ip": ip, "live": False, "via": "no-arp,no-icmp"})
    return presence


def _ping_available() -> bool:
    try:
        result = subprocess.run(["ping", "-c1", "-W1", "127.0.0.1"], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return result.returncode in (0, 1)
    except (OSError, subprocess.SubprocessError):
        return False


def snapshot(settings: Credentials) -> tuple[dict[str, Any], dict[str, Any]]:
    """Collect every required read before projecting the paired config and live-state snapshots."""
    firmware = get(settings, "core/firmware/status")
    status = _text(firmware.get("status"), required=True)
    aliases = _aliases(settings)
    rules = _rules(settings)
    reservations = _reservations(settings)
    arp = _arp(settings)
    interfaces = _interfaces(settings)
    presence = _presence(aliases, arp)
    collected = datetime.now(UTC).isoformat(timespec="seconds")
    config = {
        "collected": collected, "source": "opnsense-api (live, T1 read-only; user view)",
        "host": settings.host,
        "counts": {"aliases": len(aliases), "rules": len(rules), "reservations": len(reservations)},
        "aliases": aliases, "rules": rules, "reservations": reservations,
    }
    live = {
        "collected": collected, "source": "opnsense-api (live read-only)", "host": settings.host,
        "firmware": {"status": status,
                     "product": firmware.get("product_version") or firmware.get("product_id") or None,
                     "needs_upgrade": status == "update"},
        "counts": {"arp": len(arp), "interfaces": len(interfaces),
                   "live": sum(entry["live"] for entry in presence),
                   "silent": sum(not entry["live"] for entry in presence)},
        "arp": arp, "interfaces": interfaces, "presence": presence,
    }
    return config, live


def run(firewall_output: Path, state_output: Path, credentials_file: Path) -> common.Result:
    """Collect one paired OPNsense observation; reads preserve both, publication may not."""
    # Both snapshots are fully validated before either is written, so a failed read leaves both
    # destinations untouched. Separate atomic replacements may partially publish; the default
    # path's paired markers gate freshness until both are finalized.
    return common.run(
        "opnsense", (firewall_output, state_output),
        lambda: snapshot(credentials(credentials_file)),
        lambda config, live: {"aliases": len(config["aliases"]), "rules": len(config["rules"]),
                              "arp": len(live["arp"]), "interfaces": len(live["interfaces"])},
    )


def collect(firewall_output: Path, state_output: Path, credentials_file: Path, *,
            json_output: bool, stdout: TextIO) -> int:
    return common.emit(run(firewall_output, state_output, credentials_file), json_output, stdout)
