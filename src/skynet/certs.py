"""T1 TLS certificate inventory: unverified peer-cert reads, expiry, atomic publication.

This collector inventories certificates; it does not trust them. Each endpoint is reached with a
deliberately unverified TLS handshake solely to read the leaf it presents, so self-signed and
mismatched certificates are recorded rather than rejected — a probe, never an authenticated read.
Vantage is explicit: the ops VM on VLAN 90. An endpoint it cannot reach is recorded unreachable,
never dropped. A parse or publication failure leaves the requested destination untouched.
"""

import socket
import ssl
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from skynet import common
from skynet.common import CollectionError

DEFAULT_OUTPUT = Path("inventory/certs.json")
TIMEOUT = 8
SOURCE = "tls probe (python ssl, unverified peer-cert read)"
# The infra endpoints the ops VM reaches on VLAN 90. sni is None for IP-addressed services that
# present a single cert; a name matters only where SNI selects a vhost or the SAN is a name.
ENDPOINTS: tuple[tuple[str, str, int, str | None], ...] = (
    ("opnsense", "10.10.90.1", 443, "OPNsense.internal"),
    ("omada", "10.10.50.25", 8043, "Omada"),
    ("proxmox-core", "10.10.50.11", 8006, None),
    ("proxmox-network", "10.10.50.10", 8006, None),
    ("pbs", "10.10.20.40", 8007, None),
    ("technitium-core", "10.10.70.51", 53443, None),
    ("technitium-network", "10.10.70.50", 53443, None),
)
_RDN_SHORT = {
    "commonName": "CN", "countryName": "C", "stateOrProvinceName": "ST", "localityName": "L",
    "organizationName": "O", "organizationalUnitName": "OU",
}


def _probe(host: str, port: int, sni: str | None) -> bytes | None:
    """Read one leaf certificate over an unverified handshake; unreachable returns None."""
    context = ssl._create_unverified_context()
    try:
        raw = socket.create_connection((host, port), TIMEOUT)
        try:
            with context.wrap_socket(raw, server_hostname=sni) as wrapped:
                return wrapped.getpeercert(binary_form=True)
        except BaseException:
            raw.close()
            raise
    except (OSError, ssl.SSLError, ValueError):
        return None


def _name(rdns: Any) -> str:
    if not isinstance(rdns, (list, tuple)):
        raise CollectionError("malformed certificate name")
    parts = []
    for rdn in rdns:
        if not isinstance(rdn, (list, tuple)):
            raise CollectionError("malformed certificate name")
        for pair in rdn:
            if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                    or not all(isinstance(item, str) for item in pair)):
                raise CollectionError("malformed certificate name")
            attribute, value = pair
            parts.append(f"{_RDN_SHORT.get(attribute, attribute)}={value}")
    return ", ".join(parts)


def _sans(decoded: dict[str, Any]) -> list[str]:
    names = decoded.get("subjectAltName", ())
    if not isinstance(names, (list, tuple)):
        raise CollectionError("malformed certificate SANs")
    sans = []
    for pair in names:
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                or not isinstance(pair[1], str)):
            raise CollectionError("malformed certificate SANs")
        sans.append(pair[1])
    return sans


def _endpoint(label: str, host: str, port: int, sni: str | None, now: int) -> dict[str, Any]:
    endpoint = f"{host}:{port}"
    certificate = _probe(host, port, sni)
    if certificate is None:
        return {"label": label, "endpoint": endpoint, "reachable": False}
    decoded = common.decode_der(certificate)
    not_after = decoded.get("notAfter")
    if not isinstance(not_after, str):
        raise CollectionError("malformed certificate expiry")
    try:
        expiry = ssl.cert_time_to_seconds(not_after)
    except ValueError:
        raise CollectionError("malformed certificate expiry") from None
    return {"label": label, "endpoint": endpoint, "reachable": True,
            "issuer": _name(decoded.get("issuer", ())),
            "subject": _name(decoded.get("subject", ())),
            "sans": _sans(decoded), "not_after": not_after,
            "days_left": (expiry - now) // 86400}


def snapshot() -> dict[str, Any]:
    """Probe every endpoint from the ops vantage; a per-endpoint failure is a recorded observation."""
    now = int(datetime.now(UTC).timestamp())
    certs = [_endpoint(label, host, port, sni, now) for label, host, port, sni in ENDPOINTS]
    return {"collected": datetime.now(UTC).isoformat(timespec="seconds"),
            "host": socket.gethostname(), "source": SOURCE,
            "counts": {"probed": len(certs),
                       "reachable": sum(cert["reachable"] for cert in certs)},
            "certs": certs}


def run(output: Path) -> common.Result:
    """Collect one atomic certificate snapshot; failure leaves the requested destination untouched."""
    return common.run("certs", (output,), lambda: (snapshot(),), lambda data: data["counts"])


def collect(output: Path, *, json_output: bool, stdout: TextIO) -> int:
    return common.emit(run(output), json_output, stdout)
