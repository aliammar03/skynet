"""T1 Omada Viewer observations over pinned HTTPS."""

import http.client
import json
import re
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO, cast
from urllib.parse import quote

from skynet.pbs import HTTPSConnection, _sni_from_certificate
from skynet.proxmox import CollectionError, publish

DEFAULT_CREDENTIALS = Path("/opt/skynet-ops/secrets/omada.env")
DEFAULT_PORT = 8043
DEFAULT_SNI = "Omada"
TIMEOUT = 20
SITE_PAGE_SIZE = 1000
_HOST = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?")
_APOSTROPHES = re.compile(r"['’]")
_NON_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Credentials:
    host: str
    port: int
    sni: str
    username: str
    password: str
    context: ssl.SSLContext


def _assignments(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        raise CollectionError("credentials unavailable", 3) from None
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(
            r"\s*(OMADA_HOST|OMADA_PORT|OMADA_SNI|OMADA_USER|OMADA_PASS|OMADA_CACERT)="
            r"(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"]+))\s*(?:#.*)?", line)
        if not match:
            raise CollectionError("invalid credential assignments", 3)
        key = match[1]
        value = next(value for value in match.groups()[1:] if value is not None)
        if key in values or not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise CollectionError("invalid credential assignments", 3)
        values[key] = value
    if not {"OMADA_HOST", "OMADA_USER", "OMADA_PASS", "OMADA_CACERT"} <= values.keys():
        raise CollectionError("required credentials missing", 3)
    return values


def credentials(path: Path) -> Credentials:
    """Read literal assignments: credentials are data, never evaluated shell."""
    values = _assignments(path)
    host = values["OMADA_HOST"]
    if not _HOST.fullmatch(host):
        raise CollectionError("invalid credential host", 3)
    try:
        port = int(values.get("OMADA_PORT", str(DEFAULT_PORT)))
    except ValueError:
        raise CollectionError("invalid credential port", 3) from None
    if not 1 <= port <= 65535:
        raise CollectionError("invalid credential port", 3)
    configured_sni = values.get("OMADA_SNI")
    if configured_sni is not None and not _HOST.fullmatch(configured_sni):
        raise CollectionError("invalid certificate name", 3)
    try:
        context = ssl.create_default_context(cafile=values["OMADA_CACERT"])
    except (OSError, ssl.SSLError, ValueError):
        raise CollectionError("CA unavailable or invalid", 3) from None
    try:
        sni = _sni_from_certificate(values["OMADA_CACERT"], host)
    except CollectionError:
        sni = configured_sni or DEFAULT_SNI
    if not _HOST.fullmatch(sni):
        raise CollectionError("invalid certificate name", 3)
    return Credentials(host, port, sni, values["OMADA_USER"], values["OMADA_PASS"], context)


def _request(settings: Credentials, method: str, path: str, *, body: bytes | None = None,
             cookie: str | None = None, csrf: str | None = None) -> tuple[dict[str, Any], str | None]:
    connection = None
    headers: dict[str, str] = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if cookie is not None:
        headers["Cookie"] = cookie
    if csrf is not None:
        headers["Csrf-Token"] = csrf
    try:
        connection = HTTPSConnection(settings.host, settings.port, settings.context, settings.sni, TIMEOUT)
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise CollectionError("remote HTTP request refused (redirects disabled)", 3)
        raw = response.read()
        session = response.getheader("Set-Cookie")
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
    return payload, session


def _result(payload: dict[str, Any]) -> Any:
    if payload.get("errorCode") != 0 or "result" not in payload:
        raise CollectionError("API request not ok")
    return payload["result"]


def _string(value: Any, *, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str) or any(ord(char) < 32 for char in value) or (required and not value):
        raise CollectionError("missing or malformed field")
    return value


def _integer(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if type(value) is not int or value < 0:
        raise CollectionError("missing or malformed integer field")
    return value


def _number(value: Any) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CollectionError("missing or malformed numeric field")
    return cast(int | float, value)


def _flag(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if type(value) is bool:
        return value
    if type(value) is int and value in (0, 1):
        return bool(value)
    raise CollectionError("missing or malformed flag")


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise CollectionError("missing or malformed required list")
    return value


def _mac(value: Any) -> str:
    mac = _string(value, required=True)
    if not re.fullmatch(r"[0-9A-Fa-f:-]+", mac):
        raise CollectionError("malformed device MAC")
    return mac


def _slug(value: str) -> str:
    return _NON_SLUG.sub("-", _APOSTROPHES.sub("", value.lower())).strip("-")


def _ports(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ports = []
    for row in rows:
        status = row.get("portStatus") or {}
        if not isinstance(status, dict):
            raise CollectionError("malformed switch port status")
        ports.append({"port": _integer(row.get("port")), "name": _string(row.get("name")),
                      "profile": _string(row.get("profileName")),
                      "link": _integer(status.get("linkStatus")), "speed": _number(status.get("speed")),
                      "poe": _number(row.get("poe")), "disabled": _flag(row.get("disable"))})
    return ports


def _device(row: dict[str, Any], site: str, ports: list[dict[str, Any]] | None) -> dict[str, Any]:
    mac = _mac(row.get("mac"))
    name = _string(row.get("name"))
    identity = _slug(name or mac)
    if not identity:
        raise CollectionError("malformed device identity")
    support = _flag(row.get("poeSupport"))
    status = _integer(row.get("statusCategory"))
    poe: dict[str, Any] = {"support": False}
    if support:
        poe = {"support": True, "remain_w": _number(row.get("poeRemain")),
               "total_w": _number(row.get("poeTotalPower"))}
    return {"entity_id": "net/" + identity, "class": "net", "site": site,
            "type": _string(row.get("type"), required=True), "name": name,
            "model": _string(row.get("model")), "mac": mac, "ip": _string(row.get("ip")),
            "firmware": _string(row.get("firmwareVersion")) or _string(row.get("version")),
            "needs_upgrade": _flag(row.get("needUpgrade")), "status": status,
            "connected": status == 1,
            "uptime_s": _integer(row.get("uptimeLong")) or _integer(row.get("uptime")),
            "clients": _integer(row.get("clientNum")), "poe": poe, "ports": ports}


def snapshot(settings: Credentials) -> dict[str, Any]:
    """Read and validate all Viewer endpoints before producing one snapshot."""
    info = _result(_request(settings, "GET", "/api/info")[0])
    if not isinstance(info, dict):
        raise CollectionError("missing or malformed controller info")
    controller_id = _string(info.get("omadacId"), required=True)
    version = _string(info.get("controllerVer"), required=True)
    if not re.fullmatch(r"[0-9A-Za-z]+", controller_id):
        raise CollectionError("malformed controller id")
    login, set_cookie = _request(settings, "POST", f"/{controller_id}/api/v2/login",
                                 body=json.dumps({"username": settings.username,
                                                  "password": settings.password}).encode())
    result = _result(login)
    if not isinstance(result, dict):
        raise CollectionError("missing or malformed login result")
    csrf = _string(result.get("token"), required=True)
    if not isinstance(set_cookie, str) or "=" not in set_cookie.split(";", 1)[0]:
        raise CollectionError("missing session cookie", 3)
    cookie = set_cookie.split(";", 1)[0].strip()
    base = f"/{controller_id}/api/v2/"
    def get(path: str) -> Any:
        return _result(_request(settings, "GET", base + path, cookie=cookie, csrf=csrf)[0])
    page = get(f"sites?currentPage=1&currentPageSize={SITE_PAGE_SIZE}")
    if not isinstance(page, dict):
        raise CollectionError("missing or malformed site listing")
    raw_sites = _rows(page.get("data"))
    total = page.get("totalRows")
    if type(total) is not int or total < 0 or total != len(raw_sites):
        raise CollectionError("incomplete site page")
    sites = [{"id": _string(site.get("id"), required=True), "name": _string(site.get("name"), required=True)}
             for site in raw_sites]
    if len({site["id"] for site in sites}) != len(sites):
        raise CollectionError("duplicate site identity")
    devices: list[dict[str, Any]] = []
    identities: set[str] = set()
    for site in sites:
        for row in _rows(get(f"sites/{quote(site['id'], safe='')}/devices")):
            ports = None
            if _string(row.get("type"), required=True) == "switch":
                ports = _ports(_rows(get(f"sites/{quote(site['id'], safe='')}/switches/"
                                         f"{quote(_mac(row.get('mac')), safe='')}/ports")))
            device = _device(row, site["name"], ports)
            if device["entity_id"] in identities:
                raise CollectionError("duplicate device identity")
            identities.add(device["entity_id"])
            devices.append(device)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    return {"collected": now, "host": settings.host, "controller": {"host": settings.host, "version": version,
            "omadacId": controller_id}, "sites": sites, "devices": devices}


def collect(output: Path, credentials_file: Path, *, json_output: bool, stdout: TextIO) -> int:
    report: dict[str, Any] = {"target": "network-gear", "output": str(output)}
    try:
        data = snapshot(credentials(credentials_file))
        publish(output, data)
    except CollectionError as error:
        report.update(outcome="unavailable" if error.code == 3 else "failure",
                      reason=f"{error}; refresh failed; any retained snapshot is previous evidence")
        code = error.code
    else:
        report.update(outcome="success", collected=data["collected"],
                      counts={"sites": len(data["sites"]), "devices": len(data["devices"])})
        code = 0
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"network-gear: {report['outcome']} → {report['output']}", file=stdout)
        if code:
            print(report["reason"], file=stdout)
    return code
