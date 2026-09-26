"""T1 Technitium DNS observations: CA-verified GETs, validated zones/records, atomic publication.

Credentials are literal assignments, never shell code. The token travels only in the request
query string and never in a diagnostic. A null, partial or errored response fails the refresh and
leaves the requested destination untouched; an empty-but-valid zone list is a real observation.
"""

import http.client
import ipaddress
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlencode

from skynet import common
from skynet.common import CollectionError

DEFAULT_CREDENTIALS = Path("/opt/skynet-ops/secrets/technitium.env")
PORT = 53443
TIMEOUT = 15


@dataclass(frozen=True)
class Credentials:
    """Validated Technitium connection data; the token is never serialized into a snapshot."""

    host: str
    token: str
    context: ssl.SSLContext


def credentials(path: Path) -> Credentials:
    """Parse literal Technitium credentials and prepare CA-file, hostname-verifying trust."""
    keys = ("TECH_HOST", "TECH_TOKEN", "TECH_CACERT")
    values = common.read_assignments(path, keys, keys)
    host = common.require_host(values["TECH_HOST"])
    if not common.printable(values["TECH_TOKEN"]):
        raise CollectionError("invalid credential token", 3)
    return Credentials(host, values["TECH_TOKEN"], common.ca_context(values["TECH_CACERT"]))


def get(settings: Credentials, path: str, params: dict[str, str]) -> dict[str, Any]:
    """GET one Technitium API envelope with CA/hostname verification and no redirect handling."""
    query = urlencode({**params, "token": settings.token})
    connection = http.client.HTTPSConnection(settings.host, PORT, context=settings.context,
                                             timeout=TIMEOUT)
    raw, _ = common.request(connection, "GET", "/api/" + path + "?" + query)
    envelope = common.json_object(raw)
    if envelope.get("status") != "ok":
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


def _zone_identity(name: str) -> str:
    """Treat the API's dotted root spelling as the same identity as the empty root."""
    return "" if name == "." else name


def _zone_request_name(name: str) -> str:
    """Use Technitium's accepted root spelling only in request parameters."""
    return "." if name == "" else name


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
    if kind in {"A", "AAAA"}:
        address = data.get("ipAddress")
        if not isinstance(address, str):
            raise CollectionError("missing or malformed record IP address")
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            raise CollectionError("missing or malformed record IP address") from None
        expected_version = 4 if kind == "A" else 6
        if parsed.version != expected_version:
            raise CollectionError("record IP address family mismatch")
    elif kind == "CNAME":
        cname = data.get("cname")
        if not isinstance(cname, str) or not cname or any(ord(char) < 32 for char in cname):
            raise CollectionError("missing or malformed CNAME target")
    return record


def snapshot(settings: Credentials) -> dict[str, Any]:
    """Require the zone listing and every zone's record list before returning an observation."""
    listing = get(settings, "zones/list", {})
    zones = listing.get("zones")
    if not isinstance(zones, list):
        raise CollectionError("missing or malformed zone list")
    names = [_zone_name(zone) for zone in zones]
    if len({_zone_identity(name) for name in names}) != len(names):
        raise CollectionError("duplicate zone identity")
    records = []
    for name in names:
        request_name = _zone_request_name(name)
        detail = get(settings, "zones/records/get",
                     {"domain": request_name, "zone": request_name, "listZone": "true"})
        if "zone" in detail:
            detail_zone = detail["zone"]
            if not isinstance(detail_zone, dict):
                raise CollectionError("missing or malformed detail zone")
            if "name" in detail_zone:
                detail_name = _zone_name(detail_zone)
                if _zone_identity(detail_name) != _zone_identity(name):
                    raise CollectionError("inconsistent zone identity")
        zone_records = detail.get("records")
        if not isinstance(zone_records, list):
            raise CollectionError("missing or malformed record list")
        records.append({"zone": name, "records": [_record(record) for record in zone_records]})
    return {"collected": datetime.now(UTC).isoformat(timespec="seconds"), "host": settings.host,
            "zones": zones, "records": records}


def run(output: Path, credentials_file: Path) -> common.Result:
    """Collect one atomic DNS snapshot; failure leaves the requested destination untouched."""
    return common.run(
        "dns", (output,), lambda: (snapshot(credentials(credentials_file)),),
        lambda data: {"zones": len(data["zones"]),
                      "records": sum(len(zone["records"]) for zone in data["records"])},
    )


def collect(output: Path, credentials_file: Path, *, json_output: bool, stdout: TextIO) -> int:
    return common.emit(run(output, credentials_file), json_output, stdout)
