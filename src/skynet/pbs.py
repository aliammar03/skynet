"""T1 PBS observations: pinned GETs, validated backup groups, atomic publication."""

import hashlib
import math
import re
import socket
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO, cast
from urllib.parse import quote, urlencode

from skynet import common
from skynet.common import CollectionError

DEFAULT_CREDENTIALS = Path("/opt/skynet-ops/secrets/pbs.env")
DEFAULT_FINGERPRINT = "BA:C3:32:F3:92:6B:4D:8F:FB:39:0D:D9:C4:B5:27:1D:D1:28:8A:41:F6:49:11:D0:FF:BE:21:9E:77:53:53:2C"
TIMEOUT = 20


@dataclass(frozen=True)
class Credentials:
    """Validated PBS connection data; the token is never serialized into a snapshot."""

    host: str
    port: int
    token: str
    sni: str
    context: ssl.SSLContext


def _fingerprint(value: str) -> bytes:
    normalized = value.replace(":", "").upper()
    if not re.fullmatch(r"[0-9A-F]{64}", normalized):
        raise CollectionError("invalid certificate fingerprint", 3)
    return bytes.fromhex(normalized)


def _sni_from_der(certificate: bytes, host: str) -> str:
    return common.certificate_name(common.decode_der(certificate), host)


def _bootstrap_context(host: str, port: int, sni: str,
                       fingerprint: bytes) -> tuple[ssl.SSLContext, bytes]:
    """Pin an explicitly configured leaf before creating a normal verifying context."""
    try:
        raw = socket.create_connection((host, port), TIMEOUT)
        try:
            with ssl._create_unverified_context().wrap_socket(raw, server_hostname=sni) as wrapped:
                certificate = wrapped.getpeercert(binary_form=True)
        except BaseException:
            raw.close()
            raise
    except (OSError, ssl.SSLError, ValueError):
        raise CollectionError("remote transport unavailable (timeout, TLS or connection)", 3) from None
    if certificate is None or hashlib.sha256(certificate).digest() != fingerprint:
        raise CollectionError("certificate fingerprint mismatch", 3)
    try:
        return ssl.create_default_context(cadata=ssl.DER_cert_to_PEM_cert(certificate)), certificate
    except (ssl.SSLError, ValueError):
        raise CollectionError("certificate pin unavailable", 3) from None


def credentials(path: Path) -> Credentials:
    """Parse literal PBS credentials and prepare CA-file or configured-fingerprint trust."""
    values = common.read_assignments(
        path, ("PBS_HOST", "PBS_TOKEN", "PBS_PORT", "PBS_CACERT", "PBS_FINGERPRINT", "PBS_SNI"),
        ("PBS_HOST", "PBS_TOKEN"))
    host = common.require_host(values["PBS_HOST"])
    port = common.port(values.get("PBS_PORT", "8007"))
    token = values["PBS_TOKEN"].replace("=", ":", 1)
    if ":" not in token or not common.printable(token):
        raise CollectionError("invalid credential token", 3)
    configured_sni = values.get("PBS_SNI")
    if configured_sni is not None:
        common.require_host(configured_sni, "invalid certificate name")
    cafile = values.get("PBS_CACERT")
    if cafile:
        sni = configured_sni or common.sni_from_certificate(cafile, host)
        context = common.ca_context(cafile)
    else:
        context, certificate = _bootstrap_context(host, port, configured_sni or host, _fingerprint(
            values.get("PBS_FINGERPRINT", DEFAULT_FINGERPRINT)))
        sni = configured_sni or _sni_from_der(certificate, host)
    return Credentials(host, port, token, common.require_host(sni, "invalid certificate name"),
                       context)


def get(settings: Credentials, path: str) -> Any:
    """GET one PBS envelope with certificate verification and no redirect acceptance."""
    connection = common.SNIConnection(settings.host, settings.port, settings.context, settings.sni,
                                      TIMEOUT)
    raw, _ = common.request(connection, "GET", "/api2/json/" + path,
                            headers={"Authorization": "PBSAPIToken=" + settings.token})
    envelope = common.json_object(raw)
    if envelope.get("data") is None:
        raise CollectionError("missing API data")
    return envelope["data"]


def _string(value: Any) -> str:
    if not isinstance(value, str) or not value or any(ord(char) < 32 for char in value):
        raise CollectionError("missing or malformed identity/status field")
    return value


def _entries(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(entry, dict) for entry in value):
        raise CollectionError("missing or malformed required list")
    return value


def _usage_number(value: Any) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CollectionError("missing or malformed datastore status")
    # Integers are finite by definition; converting an arbitrarily large one to
    # float for math.isfinite() can itself overflow before validation completes.
    if isinstance(value, float) and not math.isfinite(value):
        raise CollectionError("missing or malformed datastore status")
    if value < 0:
        raise CollectionError("missing or malformed datastore status")
    return cast(int | float, value)


def snapshot(settings: Credentials) -> dict[str, Any]:
    """Require every datastore status and namespace snapshot before returning an observation."""
    stores = _entries(get(settings, "admin/datastore"))
    names = [_string(store.get("store")) for store in stores]
    if len(set(names)) != len(names):
        raise CollectionError("duplicate API identity")
    datastores: list[dict[str, Any]] = []
    for store in names:
        status = get(settings, "admin/datastore/" + quote(store, safe="") + "/status")
        if not isinstance(status, dict):
            raise CollectionError("missing or malformed datastore status")
        used = _usage_number(status.get("used"))
        total = _usage_number(status.get("total"))
        if used > total:
            raise CollectionError("missing or malformed datastore status")
        namespaces = _entries(get(settings, "admin/datastore/" + quote(store, safe="") + "/namespace"))
        namespace_names = [""]
        for entry in namespaces:
            namespace = entry.get("ns")
            if namespace == "":
                continue
            namespace_names.append(_string(namespace))
        if len(set(namespace_names)) != len(namespace_names):
            raise CollectionError("duplicate API identity")
        snapshots: list[dict[str, Any]] = []
        for namespace in namespace_names:
            path = "admin/datastore/" + quote(store, safe="") + "/snapshots"
            if namespace:
                path += "?" + urlencode({"ns": namespace})
            for item in _entries(get(settings, path)):
                backup_type = _string(item.get("backup-type"))
                backup_id = _string(item.get("backup-id"))
                backup_time = item.get("backup-time")
                if type(backup_time) is not int or backup_time < 0:
                    raise CollectionError("missing or malformed backup time")
                owner = item.get("owner")
                if owner is not None:
                    _string(owner)
                verification = item.get("verification")
                if verification is None:
                    verify_state = None
                elif isinstance(verification, dict):
                    verify_state = verification.get("state")
                    if verify_state is not None:
                        _string(verify_state)
                else:
                    raise CollectionError("malformed verification state")
                snapshots.append({"ns": namespace, "backup_type": backup_type, "backup_id": backup_id,
                                  "backup_time": backup_time, "owner": owner,
                                  "verify_state": verify_state})
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for item in snapshots:
            groups.setdefault((item["ns"], item["backup_type"], item["backup_id"]), []).append(item)
        projected = []
        for key in sorted(groups):
            members = sorted(groups[key], key=lambda item: item["backup_time"])
            latest = members[-1]
            projected.append({"ns": key[0], "backup_type": key[1], "backup_id": key[2],
                              "owner": latest["owner"], "backup_count": len(members),
                              "last_backup": latest["backup_time"],
                              "verify_state": latest["verify_state"]})
        datastores.append({"store": store, "status": status, "groups": projected,
                           "group_count": len(projected),
                           "snapshot_total": len(snapshots),
                           "unverified": sum(group["verify_state"] != "ok" for group in projected)})
    return {"collected": datetime.now(UTC).isoformat(timespec="seconds"), "host": settings.host,
            "datastores": datastores}


def run(output: Path, credentials_file: Path) -> common.Result:
    """Collect one atomic PBS snapshot; failure leaves the requested destination untouched."""
    return common.run(
        "pbs", (output,), lambda: (snapshot(credentials(credentials_file)),),
        lambda data: {"datastores": len(data["datastores"]),
                      "snapshots": sum(store["snapshot_total"] for store in data["datastores"])},
    )


def collect(output: Path, credentials_file: Path, *, json_output: bool, stdout: TextIO) -> int:
    return common.emit(run(output, credentials_file), json_output, stdout)
