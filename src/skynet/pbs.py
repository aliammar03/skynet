"""T1 PBS observations: pinned GETs, validated backup groups, atomic publication."""

import hashlib
import http.client
import json
import re
import socket
import ssl
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import quote, urlencode

from skynet.proxmox import CollectionError, publish

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


class HTTPSConnection(http.client.HTTPSConnection):
    """Connect to the configured address while validating the certificate's SNI name."""

    def __init__(self, host: str, port: int, context: ssl.SSLContext, sni: str, timeout: int):
        super().__init__(host, port, context=context, timeout=timeout)
        self._skynet_host = host
        self._skynet_port = port
        self._skynet_context = context
        self._skynet_sni = sni

    def connect(self) -> None:
        sock = socket.create_connection((self._skynet_host, self._skynet_port), self.timeout)
        self.sock = self._skynet_context.wrap_socket(sock, server_hostname=self._skynet_sni)


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
            r"\s*(PBS_HOST|PBS_TOKEN|PBS_PORT|PBS_CACERT|PBS_FINGERPRINT|PBS_SNI)="
            r"(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"]+))\s*(?:#.*)?", line,
        )
        if not match:
            raise CollectionError("invalid credential assignments", 3)
        key = match[1]
        value = next(item for item in match.groups()[1:] if item is not None)
        if key in values or not value or any(char in value for char in "`$\\;|&<>()\r\n\x00"):
            raise CollectionError("invalid credential assignments", 3)
        values[key] = value
    if not {"PBS_HOST", "PBS_TOKEN"} <= values.keys():
        raise CollectionError("required credentials missing", 3)
    return values


def _hostname(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", value))


def _fingerprint(value: str) -> bytes:
    normalized = value.replace(":", "").upper()
    if not re.fullmatch(r"[0-9A-F]{64}", normalized):
        raise CollectionError("invalid certificate fingerprint", 3)
    return bytes.fromhex(normalized)


def _certificate_name(decoded: Any, host: str) -> str:
    if _hostname(host) and not re.fullmatch(r"\d+(?:\.\d+){3}", host):
        return host
    for kind, value in decoded.get("subjectAltName", []):
        if kind == "DNS" and isinstance(value, str) and _hostname(value):
            return value
    for subject in decoded.get("subject", []):
        for key, value in subject:
            if key == "commonName" and isinstance(value, str) and _hostname(value):
                return value
    raise CollectionError("certificate name unavailable", 3)


def _sni_from_certificate(path: str, host: str) -> str:
    try:
        return _certificate_name(ssl._ssl._test_decode_cert(path), host)  # type: ignore[attr-defined]
    except (OSError, ssl.SSLError):
        raise CollectionError("certificate name unavailable", 3) from None


def _sni_from_der(certificate: bytes, host: str) -> str:
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", delete=False) as stream:
            temporary = stream.name
            stream.write(ssl.DER_cert_to_PEM_cert(certificate))
        return _sni_from_certificate(temporary, host)
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink()
            except OSError:
                raise CollectionError("certificate cleanup failed", 3) from None


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
    values = _literal_assignments(path)
    host = values["PBS_HOST"]
    if not _hostname(host):
        raise CollectionError("invalid credential host", 3)
    try:
        port = int(values.get("PBS_PORT", "8007"))
    except ValueError:
        raise CollectionError("invalid credential port", 3) from None
    if not 1 <= port <= 65535:
        raise CollectionError("invalid credential port", 3)
    token = values["PBS_TOKEN"].replace("=", ":", 1)
    if ":" not in token or any(ord(char) < 33 or ord(char) > 126 for char in token):
        raise CollectionError("invalid credential token", 3)
    cafile = values.get("PBS_CACERT")
    if cafile:
        sni = values.get("PBS_SNI") or _sni_from_certificate(cafile, host)
        try:
            context = ssl.create_default_context(cafile=cafile)
        except (OSError, ssl.SSLError, ValueError):
            raise CollectionError("CA unavailable or invalid", 3) from None
    else:
        configured_sni = values.get("PBS_SNI")
        if configured_sni is not None and not _hostname(configured_sni):
            raise CollectionError("invalid certificate name", 3)
        context, certificate = _bootstrap_context(host, port, configured_sni or host, _fingerprint(
            values.get("PBS_FINGERPRINT", DEFAULT_FINGERPRINT)))
        sni = configured_sni or _sni_from_der(certificate, host)
    if not _hostname(sni):
        raise CollectionError("invalid certificate name", 3)
    return Credentials(host, port, token, sni, context)


def get(settings: Credentials, path: str) -> Any:
    """GET one PBS envelope with certificate verification and no redirect acceptance."""
    connection = None
    try:
        connection = HTTPSConnection(settings.host, settings.port, settings.context, settings.sni, TIMEOUT)
        connection.request("GET", "/api2/json/" + path,
                           headers={"Authorization": "PBSAPIToken=" + settings.token})
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
    if not isinstance(envelope, dict) or envelope.get("data") is None:
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
        namespaces = _entries(get(settings, "admin/datastore/" + quote(store, safe="") + "/namespace"))
        namespace_names = ["", *[_string(entry.get("ns")) for entry in namespaces]]
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
                           "unverified": sum(group["verify_state"] is None for group in projected)})
    return {"collected": datetime.now(UTC).isoformat(timespec="seconds"), "host": settings.host,
            "datastores": datastores}


def collect(output: Path, credentials_file: Path, *, json_output: bool, stdout: TextIO) -> int:
    """Collect one atomic PBS snapshot; failure leaves the requested destination untouched."""
    report: dict[str, Any] = {"target": "pbs", "output": str(output)}
    try:
        data = snapshot(credentials(credentials_file))
        publish(output, data)
    except CollectionError as error:
        report.update(outcome="unavailable" if error.code == 3 else "failure",
                      reason=f"{error}; refresh failed; any retained snapshot is previous evidence")
        code = error.code
    else:
        report.update(outcome="success", collected=data["collected"], counts={
            "datastores": len(data["datastores"]),
            "snapshots": sum(store["snapshot_total"] for store in data["datastores"]),
        })
        code = 0
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"pbs: {report['outcome']} → {report['output']}", file=stdout)
        if code:
            print(report["reason"], file=stdout)
    return code
