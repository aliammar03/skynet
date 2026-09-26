"""Shared collector plumbing: literal credential files, verified HTTPS, atomic writes, results.

Credential files are literal `KEY=value` data, never shell. One value rule holds for every
reader: a value is non-empty, unique, and free of control characters; a field-specific check
(host, port, token) follows in the owning module. Every diagnostic is a fixed string; no remote
or credential text reaches a reason.
"""

import http.client
import json
import os
import re
import socket
import ssl
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO, cast

HOST = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?")
_ASSIGNMENT = re.compile(r"\s*([A-Z][A-Z0-9_]*)=(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"]+))\s*(?:#.*)?")
RETAINED = "refresh failed; any retained snapshot is previous evidence"


class CollectionError(Exception):
    """A fixed, safe diagnostic and CLI exit code; never includes external text."""

    def __init__(self, reason: str, code: int = 1):
        super().__init__(reason)
        self.reason = reason
        self.code = code


def read_assignments(path: Path, allowed: Iterable[str], required: Iterable[str], *,
                     error: Callable[[str, int], Exception] = CollectionError,
                     service: str = "") -> dict[str, str]:
    """Parse one literal credential file; anything but known, unique, clean assignments is refused."""
    subject = f"{service} " if service else ""
    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        raise error(f"{subject}credentials unavailable", 3) from None
    known = set(allowed)
    values: dict[str, str] = {}
    for line in contents.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _ASSIGNMENT.fullmatch(line)
        if match is None or match[1] not in known:
            raise error(f"invalid {subject}credential assignments", 3)
        key = match[1]
        value = next(item for item in match.groups()[1:] if item is not None)
        if key in values or not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise error(f"invalid {subject}credential assignments", 3)
        values[key] = value
    if not set(required) <= values.keys():
        raise error(f"required {subject}credentials missing", 3)
    return values


def valid_host(value: str) -> bool:
    """A bare host name or address — never a URL, port override, or userinfo destination."""
    return bool(HOST.fullmatch(value))


def require_host(value: str, reason: str = "invalid credential host") -> str:
    if not valid_host(value):
        raise CollectionError(reason, 3)
    return value


def printable(value: str) -> bool:
    """Visible ASCII only: safe to place in an HTTP header."""
    return bool(value) and all(33 <= ord(char) <= 126 for char in value)


def port(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise CollectionError("invalid credential port", 3) from None
    if not 1 <= number <= 65535:
        raise CollectionError("invalid credential port", 3)
    return number


def ca_context(cafile: str) -> ssl.SSLContext:
    """A verifying TLS context trusting exactly the declared CA file."""
    try:
        return ssl.create_default_context(cafile=cafile)
    except (OSError, ssl.SSLError, ValueError):
        raise CollectionError("CA unavailable or invalid", 3) from None


class SNIConnection(http.client.HTTPSConnection):
    """Connect to the configured address while validating the certificate against `sni`."""

    def __init__(self, host: str, port: int, context: ssl.SSLContext, sni: str, timeout: float):
        super().__init__(host, port, context=context, timeout=timeout)
        self._skynet_host = host
        self._skynet_port = port
        self._skynet_context = context
        self._skynet_sni = sni

    def connect(self) -> None:
        sock = socket.create_connection((self._skynet_host, self._skynet_port), self.timeout)
        self.sock = self._skynet_context.wrap_socket(sock, server_hostname=self._skynet_sni)


def request(connection: http.client.HTTPSConnection, method: str, target: str, *,
            headers: dict[str, str] | None = None,
            body: bytes | None = None) -> tuple[bytes, http.client.HTTPMessage]:
    """One request on a fresh connection: 200 only (no redirects), always closed, safe errors."""
    try:
        connection.request(method, target, body=body, headers=headers or {})
        response = connection.getresponse()
        if response.status != 200:
            raise CollectionError("remote HTTP request refused (redirects disabled)", 3)
        return response.read(), response.msg
    except (OSError, http.client.HTTPException, ValueError):
        raise CollectionError("remote transport unavailable (timeout, TLS or connection)", 3) from None
    finally:
        try:
            connection.close()
        except OSError:
            raise CollectionError("remote connection close failed", 3) from None


def json_object(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise CollectionError("malformed API JSON") from None
    if not isinstance(payload, dict):
        raise CollectionError("missing API data")
    return payload


def certificate_name(decoded: Any, host: str) -> str:
    """The first usable DNS SAN, then CN, then a non-IP host: the name TLS must verify."""
    for kind, value in decoded.get("subjectAltName", []):
        if kind == "DNS" and isinstance(value, str) and valid_host(value):
            return value
    for subject in decoded.get("subject", []):
        for key, value in subject:
            if key == "commonName" and isinstance(value, str) and valid_host(value):
                return value
    if valid_host(host) and not re.fullmatch(r"\d+(?:\.\d+){3}", host):
        return host
    raise CollectionError("certificate name unavailable", 3)


def sni_from_certificate(path: str, host: str) -> str:
    try:
        return certificate_name(ssl._ssl._test_decode_cert(path), host)  # type: ignore[attr-defined]
    except (OSError, ssl.SSLError):
        raise CollectionError("certificate name unavailable", 3) from None


def decode_der(certificate: bytes) -> dict[str, Any]:
    """Decode a DER leaf into the stdlib certificate dictionary via a short-lived PEM file."""
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", delete=False) as stream:
            temporary = stream.name
            stream.write(ssl.DER_cert_to_PEM_cert(certificate))
        return cast(dict[str, Any], ssl._ssl._test_decode_cert(temporary))  # type: ignore[attr-defined]
    except (OSError, ssl.SSLError, ValueError):
        raise CollectionError("malformed certificate") from None
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink()
            except FileNotFoundError:
                pass
            except OSError:
                raise CollectionError("certificate cleanup failed") from None


def atomic_write_text(path: Path, content: str) -> None:
    """Replace `path` only after a complete, flushed sibling write; OSError on any failure."""
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent,
                                         prefix="." + path.name + ".", delete=False) as stream:
            temporary = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def publish_json(path: Path, data: dict[str, Any]) -> None:
    """Serialize first, then replace atomically; a failure leaves the previous bytes."""
    try:
        atomic_write_text(path, json.dumps(data, indent=2, allow_nan=False) + "\n")
    except (OSError, ValueError, TypeError):
        raise CollectionError("local snapshot publication failed") from None


@dataclass(frozen=True)
class Result:
    """One collector outcome. Success means observations were published, not that anything is healthy."""

    target: str
    outputs: tuple[Path, ...]
    code: int
    outcome: str
    collected: str | None = None
    reason: str | None = None
    counts: dict[str, Any] = field(default_factory=dict)

    def report(self) -> dict[str, Any]:
        output: str | list[str] = (str(self.outputs[0]) if len(self.outputs) == 1
                                   else [str(path) for path in self.outputs])
        report: dict[str, Any] = {"target": self.target, "output": output, "outcome": self.outcome}
        if self.code == 0:
            report.update(collected=self.collected, counts=self.counts)
        else:
            report["reason"] = self.reason
        return report


def run(target: str, outputs: tuple[Path, ...],
        read: Callable[[], tuple[dict[str, Any], ...]],
        counts: Callable[..., dict[str, Any]]) -> Result:
    """Read every snapshot, publish each atomically, and describe the outcome safely."""
    try:
        snapshots = read()
        for path, data in zip(outputs, snapshots, strict=True):
            publish_json(path, data)
    except CollectionError as error:
        return Result(target, outputs, error.code, "unavailable" if error.code == 3 else "failure",
                      reason=f"{error.reason}; {RETAINED}")
    return Result(target, outputs, 0, "success", collected=snapshots[0]["collected"],
                  counts=counts(*snapshots))


def emit(result: Result, json_output: bool, stdout: TextIO) -> int:
    """Print one collector outcome and return its exit code."""
    if json_output:
        print(json.dumps(result.report()), file=stdout)
    else:
        print(f"{result.target}: {result.outcome} → {', '.join(map(str, result.outputs))}", file=stdout)
        if result.code:
            print(result.reason, file=stdout)
        else:
            print(f"collected: {result.collected}; " + ", ".join(
                f"{key}: {value}" for key, value in result.counts.items()), file=stdout)
    return result.code
