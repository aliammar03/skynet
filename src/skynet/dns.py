"""T1 Technitium DNS observations: CA-verified GETs, validated zones/records, atomic publication.

Credentials are literal assignments, never shell code. The token travels only in the request
query string and never in a diagnostic. A null, partial or errored response fails the refresh and
leaves the requested destination untouched; an empty-but-valid zone list is a real observation.
"""

import http.client
import json
import re
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlencode

from skynet.proxmox import CollectionError, publish

DEFAULT_CREDENTIALS = Path("/opt/skynet-ops/secrets/technitium.env")
PORT = 53443
TIMEOUT = 15


@dataclass(frozen=True)
class Credentials:
    """Validated Technitium connection data; the token is never serialized into a snapshot."""

    host: str
    token: str
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
            r"\s*(TECH_HOST|TECH_TOKEN|TECH_CACERT)="
            r"(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"]+))\s*(?:#.*)?", line,
        )
        if not match:
            raise CollectionError("invalid credential assignments", 3)
        key = match[1]
        value = next(item for item in match.groups()[1:] if item is not None)
        if key in values or not value or any(char in value for char in "`$\\;|&<>()\r\n\x00"):
            raise CollectionError("invalid credential assignments", 3)
        values[key] = value
    if not {"TECH_HOST", "TECH_TOKEN", "TECH_CACERT"} <= values.keys():
        raise CollectionError("required credentials missing", 3)
    return values


def credentials(path: Path) -> Credentials:
    """Parse literal Technitium credentials and prepare CA-file, hostname-verifying trust."""
    values = _literal_assignments(path)
    host = values["TECH_HOST"]
    # The contract is a host, not a URL, port override, or userinfo destination.
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host):
        raise CollectionError("invalid credential host", 3)
    token = values["TECH_TOKEN"]
    if any(ord(char) < 33 or ord(char) > 126 for char in token):
        raise CollectionError("invalid credential token", 3)
    try:
        context = ssl.create_default_context(cafile=values["TECH_CACERT"])
    except (OSError, ssl.SSLError, ValueError):
        raise CollectionError("CA unavailable or invalid", 3) from None
    return Credentials(host, token, context)


def get(settings: Credentials, path: str, params: dict[str, str]) -> dict[str, Any]:
    """GET one Technitium API envelope with CA/hostname verification and no redirect handling."""
    query = urlencode({**params, "token": settings.token})
    connection = None
    try:
        connection = http.client.HTTPSConnection(
            settings.host, PORT, context=settings.context, timeout=TIMEOUT)
        connection.request("GET", "/api/" + path + "?" + query)
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
    if not isinstance(envelope, dict) or envelope.get("status") != "ok":
        raise CollectionError("API request not ok")
    data = envelope.get("response")
    if not isinstance(data, dict):
        raise CollectionError("missing API response")
    return data


def _zone_name(zone: Any) -> str:
    """Require a zone object with a control-free string name; the root zone name is ''."""
    if not isinstance(zone, dict):
        raise CollectionError("missing or malformed zone")
    name = zone.get("name")
    if not isinstance(name, str) or any(ord(char) < 32 for char in name):
        raise CollectionError("missing or malformed zone name")
    return name


def _record(record: Any) -> dict[str, Any]:
    """Preserve a full record after checking the fields SQLite and the renderer consume."""
    if not isinstance(record, dict):
        raise CollectionError("missing or malformed record")
    name = record.get("name")
    kind = record.get("type")
    data = record.get("rData")
    if not isinstance(name, str) or any(ord(char) < 32 for char in name):
        raise CollectionError("missing or malformed record name")
    if not isinstance(kind, str) or not kind or any(ord(char) < 32 for char in kind):
        raise CollectionError("missing or malformed record type")
    if not isinstance(data, dict):
        raise CollectionError("missing or malformed record data")
    return record


def snapshot(settings: Credentials) -> dict[str, Any]:
    """Require the zone listing and every zone's record list before returning an observation."""
    listing = get(settings, "zones/list", {})
    zones = listing.get("zones")
    if not isinstance(zones, list):
        raise CollectionError("missing or malformed zone list")
    names = [_zone_name(zone) for zone in zones]
    if len(set(names)) != len(names):
        raise CollectionError("duplicate zone identity")
    records = []
    for name in names:
        detail = get(settings, "zones/records/get",
                     {"domain": name, "zone": name, "listZone": "true"})
        zone_records = detail.get("records")
        if not isinstance(zone_records, list):
            raise CollectionError("missing or malformed record list")
        records.append({"zone": name, "records": [_record(record) for record in zone_records]})
    return {"collected": datetime.now(UTC).isoformat(timespec="seconds"), "host": settings.host,
            "zones": zones, "records": records}


def collect(output: Path, credentials_file: Path, *, json_output: bool, stdout: TextIO) -> int:
    """Collect one atomic DNS snapshot; failure leaves the requested destination untouched."""
    report: dict[str, Any] = {"target": "dns", "output": str(output)}
    try:
        data = snapshot(credentials(credentials_file))
        publish(output, data)
    except CollectionError as error:
        report.update(outcome="unavailable" if error.code == 3 else "failure",
                      reason=f"{error}; refresh failed; any retained snapshot is previous evidence")
        code = error.code
    else:
        report.update(outcome="success", collected=data["collected"], counts={
            "zones": len(data["zones"]),
            "records": sum(len(zone["records"]) for zone in data["records"]),
        })
        code = 0
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"dns: {report['outcome']} → {report['output']}", file=stdout)
        if code:
            print(report["reason"], file=stdout)
    return code
