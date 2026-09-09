"""T1 live OPNsense observations: pinned GET/search reads, user-view config, atomic dual publication.

One collection produces two paired snapshots — the firewall configuration (aliases/rules/
reservations, filtered to the user view the mirror showed) and live state the mirror cannot give
(firmware, ARP, interfaces, declared-host presence). Every required read and validation completes
before either file is published, so a read or validation failure leaves both destinations
untouched; the default path additionally binds both to one receipt so neither is ever blessed as
fresh without the other. Credentials are literal assignments, never shell code; the API key/secret
travel only in the Basic auth header and never in a diagnostic. This collector only reads: the
enumerated GETs plus the read-only search POSTs.
"""

import base64
import http.client
import json
import re
import ssl
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from skynet.pbs import HTTPSConnection, _sni_from_certificate
from skynet.proxmox import CollectionError, publish

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


def _literal_assignments(path: Path) -> dict[str, str]:
    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        raise CollectionError("credentials unavailable", 3) from None
    values: dict[str, str] = {}
    for line in contents.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(
            r"\s*(OPN_HOST|OPN_KEY|OPN_SECRET|OPN_PORT|OPN_CACERT|OPN_SNI)="
            r"(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"]+))\s*(?:#.*)?", line,
        )
        if not match:
            raise CollectionError("invalid credential assignments", 3)
        key = match[1]
        value = next(item for item in match.groups()[1:] if item is not None)
        # The key/secret are quoted base64-style values; forbid only control characters, never eval.
        if key in values or not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise CollectionError("invalid credential assignments", 3)
        values[key] = value
    if not {"OPN_HOST", "OPN_KEY", "OPN_SECRET", "OPN_CACERT"} <= values.keys():
        raise CollectionError("required credentials missing", 3)
    return values


def credentials(path: Path) -> Credentials:
    """Parse literal OPNsense credentials and derive the pinned-cert SNI and Basic authorization."""
    values = _literal_assignments(path)
    host = values["OPN_HOST"]
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host):
        raise CollectionError("invalid credential host", 3)
    try:
        port = int(values.get("OPN_PORT", "443"))
    except ValueError:
        raise CollectionError("invalid credential port", 3) from None
    if not 1 <= port <= 65535:
        raise CollectionError("invalid credential port", 3)
    key, secret = values["OPN_KEY"], values["OPN_SECRET"]
    if any(ord(char) < 33 or ord(char) > 126 for char in key + secret):
        raise CollectionError("invalid credential key", 3)
    cafile = values["OPN_CACERT"]
    try:
        context = ssl.create_default_context(cafile=cafile)
    except (OSError, ssl.SSLError, ValueError):
        raise CollectionError("CA unavailable or invalid", 3) from None
    configured_sni = values.get("OPN_SNI")
    if configured_sni is not None and not re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", configured_sni):
        raise CollectionError("invalid certificate name", 3)
    # Derive the SNI from the pinned certificate so a stale configured name cannot break trust.
    sni = configured_sni or _sni_from_certificate(cafile, host)
    authorization = "Basic " + base64.b64encode(f"{key}:{secret}".encode()).decode()
    return Credentials(host, port, sni, authorization, context)


def _read(settings: Credentials, method: str, path: str, body: bytes | None) -> dict[str, Any]:
    """One pinned GET or read-only search POST; no redirect handling, key only in the header."""
    connection = None
    headers = {"Authorization": settings.authorization}
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        connection = HTTPSConnection(settings.host, settings.port, settings.context,
                                     settings.sni, TIMEOUT)
        connection.request(method, "/api/" + path, body=body, headers=headers)
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
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise CollectionError("malformed API JSON") from None
    if not isinstance(payload, dict):
        raise CollectionError("missing API data")
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
    if total is not None:
        try:
            total = int(total)
        except (TypeError, ValueError):
            raise CollectionError("malformed search total") from None
        # A page smaller than the reported total means the fixed row budget truncated results.
        if total != len(rows):
            raise CollectionError("incomplete search page")
    return rows


def _text(value: Any, *, required: bool = False) -> str:
    if value is None or isinstance(value, (int, float)) and not isinstance(value, bool):
        value = "" if value is None else str(value)
    if not isinstance(value, str) or any(ord(char) < 32 for char in value):
        raise CollectionError("missing or malformed field")
    if required and not value:
        raise CollectionError("missing required field")
    return value


def _selected(value: Any, *, join: bool) -> str:
    """OPNsense form fields arrive either as a plain string or a {key: {selected, value}} map."""
    if isinstance(value, dict):
        chosen = [key for key, option in value.items()
                  if isinstance(option, dict) and option.get("selected") == 1]
        return "\n".join(chosen) if join else (chosen[0] if chosen else "")
    return _text(value)


def _aliases(settings: Credentials) -> list[dict[str, Any]]:
    root = get(settings, "firewall/alias/get")
    container = (((root.get("alias") or {}).get("aliases") or {}).get("alias"))
    if container is None:
        container = {}
    if not isinstance(container, dict):
        raise CollectionError("malformed alias container")
    aliases = []
    for entry in container.values():
        if not isinstance(entry, dict):
            raise CollectionError("malformed alias entry")
        name = _text(entry.get("name"), required=True)
        if BUILTIN_ALIAS.match(name):
            continue
        aliases.append({"name": name, "type": _selected(entry.get("type"), join=False),
                        "content": _selected(entry.get("content"), join=True),
                        "description": _text(entry.get("description")),
                        "enabled": _text(entry.get("enabled") if entry.get("enabled") not in (None, "")
                                         else "1")})
    return aliases


def _rules(settings: Credentials) -> list[dict[str, Any]]:
    configured = get(settings, "firewall/filter/get")
    rule_map = (((configured.get("filter") or {}).get("rules") or {}).get("rule"))
    if rule_map is None:
        rule_map = {}
    if not isinstance(rule_map, dict):
        raise CollectionError("malformed rule container")
    sequences: dict[str, Any] = {}
    for uuid, rule in rule_map.items():
        if not isinstance(rule, dict):
            raise CollectionError("malformed rule entry")
        sequences[uuid] = rule.get("sequence")
    rules = []
    for row in search(settings, "firewall/filter/searchRule"):
        uuid = _text(row.get("uuid"), required=True)
        # Intersect the flat display rows with the configured user rules; internal/auto rules
        # are absent from filter/get and excluded for free.
        if uuid not in sequences:
            continue
        enabled = row.get("enabled")
        rules.append({"sequence": sequences[uuid], "action": _text(row.get("action")),
                      "protocol": _text(row.get("protocol")),
                      "interface": (_text(row.get("interface")) or None),
                      "source_net": _text(row.get("source_net")),
                      "destination_net": _text(row.get("destination_net")),
                      "destination_port": _text(row.get("destination_port")),
                      "description": _text(row.get("description")), "uuid": uuid,
                      "enabled": enabled in ("1", 1, True)})
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
    rows = payload.get("rows", payload)
    if isinstance(rows, dict):
        rows = list(rows.values())
    if not isinstance(rows, list):
        raise CollectionError("malformed interface list")
    interfaces = []
    for row in rows:
        if not isinstance(row, dict):
            raise CollectionError("malformed interface entry")
        interfaces.append({"device": _text(row.get("device")),
                           "description": _text(row.get("description")),
                           "status": _text(row.get("status")),
                           "enabled": row.get("enabled") in ("1", 1, True),
                           "identifier": _text(row.get("identifier"))})
    return interfaces


def _ping(ip: str) -> bool:
    try:
        return subprocess.run(["ping", "-c1", "-W1", ip], stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


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
    if silent and ping_available:
        with ThreadPoolExecutor(max_workers=PING_WORKERS) as pool:
            answered = {ip for ip, up in zip(silent, pool.map(_ping, silent)) if up}
    presence = []
    for ip in host_ips:
        if ip in arp_ips:
            presence.append({"ip": ip, "live": True, "via": "arp"})
        elif ip in answered:
            presence.append({"ip": ip, "live": True, "via": "icmp"})
        elif not ping_available:
            presence.append({"ip": ip, "live": False, "via": "no-arp,icmp-unavailable"})
        else:
            presence.append({"ip": ip, "live": False, "via": "no-arp,no-icmp"})
    return presence


def _ping_available() -> bool:
    try:
        subprocess.run(["ping", "-c1", "-W1", "127.0.0.1"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return True
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


def collect(firewall_output: Path, state_output: Path, credentials_file: Path, *,
            json_output: bool, stdout: TextIO) -> int:
    """Collect one paired OPNsense observation; both files publish or neither does."""
    report: dict[str, Any] = {"target": "opnsense",
                              "output": {"firewall": str(firewall_output), "state": str(state_output)}}
    try:
        config, live = snapshot(credentials(credentials_file))
        # Both snapshots are fully validated before either is written, so a failed read leaves
        # both destinations untouched; the default path's paired markers gate freshness.
        publish(firewall_output, config)
        publish(state_output, live)
    except CollectionError as error:
        report.update(outcome="unavailable" if error.code == 3 else "failure",
                      reason=f"{error}; refresh failed; any retained snapshots are previous evidence")
        code = error.code
    else:
        report.update(outcome="success", collected=config["collected"], counts={
            "aliases": len(config["aliases"]), "rules": len(config["rules"]),
            "arp": len(live["arp"]), "interfaces": len(live["interfaces"]),
        })
        code = 0
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"opnsense: {report['outcome']} → {firewall_output}, {state_output}", file=stdout)
        if code:
            print(report["reason"], file=stdout)
    return code
