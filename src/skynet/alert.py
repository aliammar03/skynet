"""The alert channel: Pushover messages and the external dead-man's-switch ping.

One credential file, `/opt/skynet-ops/secrets/alerts.env` (sops `secrets/alerts.env.sops`), holds
`PUSHOVER_TOKEN`, `PUSHOVER_USER`, and `HEALTHCHECK_URL`. `send` pushes one message; `ping` tells
the external check (healthchecks.io) that `skynet watch` ran, so a dead ops VM or a dead timer still
reaches the phone through that service. Neither ever raises into a caller: an alert that cannot be
sent is reported as a fixed reason, and no credential text reaches a reason.
"""

from __future__ import annotations

import http.client
import os
import ssl
import urllib.parse
from pathlib import Path

from skynet import common
from skynet.common import CollectionError

DEFAULT_CREDENTIALS = Path("/opt/skynet-ops/secrets/alerts.env")
PUSHOVER_HOST = "api.pushover.net"
TIMEOUT = 15.0
_KEYS = ("PUSHOVER_TOKEN", "PUSHOVER_USER", "HEALTHCHECK_URL")


class AlertError(Exception):
    """A fixed, safe reason an alert or ping did not go out."""

    def __init__(self, reason: str, code: int = 3):
        super().__init__(reason)
        self.reason = reason
        self.code = code


def credentials_path() -> Path:
    return Path(os.environ.get("SKYNET_ALERTS_FILE", DEFAULT_CREDENTIALS))


def credentials(path: Path | None = None) -> dict[str, str]:
    values = common.read_assignments(path or credentials_path(), _KEYS, _KEYS, error=AlertError,
                                     service="alert")
    if not all(common.printable(values[key]) for key in ("PUSHOVER_TOKEN", "PUSHOVER_USER")):
        raise AlertError("invalid alert credential assignments")
    _ping_target(values["HEALTHCHECK_URL"])
    return values


def _ping_target(url: str) -> tuple[str, str]:
    """`https://<host>/<path>` only: no userinfo, port, query, or fragment."""
    parts = urllib.parse.urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.port is not None
            or parts.username or parts.password or parts.query or parts.fragment
            or not common.valid_host(parts.hostname) or not parts.path.startswith("/")
            or not common.printable(parts.path)):
        raise AlertError("invalid alert credential assignments")
    return parts.hostname, parts.path.rstrip("/")


def _connection(host: str) -> http.client.HTTPSConnection:
    return http.client.HTTPSConnection(host, 443, context=ssl.create_default_context(),
                                       timeout=TIMEOUT)


def _request(host: str, method: str, target: str, body: bytes | None = None,
             headers: dict[str, str] | None = None) -> None:
    try:
        common.request(_connection(host), method, target, body=body, headers=headers)
    except CollectionError:
        raise AlertError(f"{host} unreachable or refused the request") from None


def send(title: str, message: str, *, priority: int = 0, path: Path | None = None) -> str | None:
    """Push one message. Returns None when sent, else the fixed reason it was not."""
    try:
        values = credentials(path)
        body = urllib.parse.urlencode({
            "token": values["PUSHOVER_TOKEN"], "user": values["PUSHOVER_USER"],
            "title": title[:250], "message": message[:1024], "priority": str(priority),
        }).encode()
        _request(PUSHOVER_HOST, "POST", "/1/messages.json", body,
                 {"Content-Type": "application/x-www-form-urlencoded"})
    except AlertError as error:
        return error.reason
    return None


def ping(ok: bool = True, *, path: Path | None = None) -> str | None:
    """Tell the dead-man's switch this run happened (`/fail` when the monitor is unavailable)."""
    try:
        host, target = _ping_target(credentials(path)["HEALTHCHECK_URL"])
        _request(host, "GET", target + ("" if ok else "/fail"))
    except AlertError as error:
        return error.reason
    return None
