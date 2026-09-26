"""Read-only deployment verification over a Docker context.

The verifier compares what the executor intended (one revision, one set of Compose services)
with what Docker reports. Every container in the project must carry the expected
`skynet.revision` label, be running, and report a healthy healthcheck; every expected service must
have a container; no stray container may remain. Declared ingress routes for the service are then
probed from the DMZ network by a bounded ephemeral container using a pinned image.

This module never deploys, rolls back, or changes persistent state. The route probe may
create/remove an ephemeral container and pull/cache its reviewed image; the result says so.
Reports carry fixed reasons only, never remote error text.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from skynet import routes

DEFAULT_CONTEXT = "docker-dmz"
DEFAULT_TIMEOUT = 15.0
REVISION_LABEL = "skynet.revision"
PROJECT_LABEL = "com.docker.compose.project"
SERVICE_LABEL = "com.docker.compose.service"

# A reviewed, immutable probe image, supplied as an argv item; route data cannot select an image.
CURL_IMAGE = "curlimages/curl:8.16.0@sha256:463eaf6072688fe96ac64fa623fe73e1dbe25d8ad6c34404a669ad3ce1f104b6"
INGRESS_NETWORK = "dmz"
INGRESS_IP = "10.10.100.35"

REVISION = re.compile(r"[0-9a-f]{40}")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_HOST = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+aliammar\.net")
_ENTITY = re.compile(
    r"(?:svc|guest)/[A-Za-z0-9][A-Za-z0-9_.:-]*|host:[A-Za-z0-9][A-Za-z0-9_.:-]*"
)
_AUTH_VALUES = frozenset({"own-auth/plain", "forward_auth (authentik)", "identity (authentik)"})
_MAX_OUTPUT = 4 * 1024 * 1024


class VerificationError(Exception):
    """A safe verification outcome with a stable process exit code."""

    def __init__(self, reason: str, code: int = 1):
        super().__init__(reason)
        self.reason = reason
        self.code = code


def _docker(args: list[str], timeout: float) -> str:
    """Run one fixed Docker observation with no shell and bounded capture."""
    try:
        result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise VerificationError("Docker command unavailable", 3) from None
    if result.returncode != 0:
        raise VerificationError("Docker command unavailable", 3)
    if len(result.stdout) > _MAX_OUTPUT:
        raise VerificationError("malformed Docker command output", 3)
    return result.stdout


def inspect_project(context: str, service: str, timeout: float) -> list[dict[str, Any]]:
    """Every container (any state) labelled with this Compose project, as `docker inspect` rows."""
    ids = _docker(["docker", "--context", context, "ps", "--all", "--quiet", "--no-trunc",
                   "--filter", f"label={PROJECT_LABEL}={service}"], timeout).split()
    if not ids:
        return []
    try:
        rows = json.loads(_docker(["docker", "--context", context, "inspect", *ids], timeout))
    except ValueError:
        raise VerificationError("malformed Docker container observation", 3) from None
    if not isinstance(rows, list) or len(rows) != len(ids):
        raise VerificationError("Docker container observation is partial", 3)
    return rows


def running_revision(rows: Iterable[dict[str, Any]]) -> str | None:
    """The single revision every container carries, or None when absent or mixed."""
    revisions = {_labels(row).get(REVISION_LABEL) for row in rows}
    if len(revisions) != 1:
        return None
    revision = revisions.pop()
    return revision if isinstance(revision, str) and REVISION.fullmatch(revision) else None


def _labels(row: Any) -> dict[str, Any]:
    labels = row.get("Config", {}).get("Labels") if isinstance(row, dict) else None
    if not isinstance(labels, dict):
        raise VerificationError("malformed Docker container observation", 3)
    return labels


def check_containers(rows: list[dict[str, Any]], service: str, revision: str,
                     expected: Iterable[str]) -> dict[str, Any]:
    """Require the complete expected set, at the revision, running and healthy; nothing stray."""
    wanted = set(expected)
    if not wanted:
        raise VerificationError("expected service set is empty", 2)
    if not rows:
        raise VerificationError("no containers observed for the project", 1)
    seen: set[str] = set()
    for row in rows:
        labels = _labels(row)
        if labels.get(PROJECT_LABEL) != service:
            raise VerificationError("Docker project identity mismatch", 1)
        name = labels.get(SERVICE_LABEL)
        if not isinstance(name, str) or name not in wanted:
            raise VerificationError("stray container in the project", 1)
        if labels.get(REVISION_LABEL) != revision:
            raise VerificationError("container revision mismatch", 1)
        state = row.get("State")
        if not isinstance(state, dict):
            raise VerificationError("malformed Docker container observation", 3)
        if state.get("Status") != "running" or state.get("Restarting") is True:
            raise VerificationError("container is not running", 1)
        health = state.get("Health")
        if not isinstance(health, dict):
            raise VerificationError("container has no healthcheck", 1)
        if health.get("Status") != "healthy":
            raise VerificationError("container is not healthy", 1)
        seen.add(name)
    if seen != wanted:
        raise VerificationError("expected service has no container", 1)
    return {"container_count": len(rows), "services": sorted(seen)}


def route_vhosts(route_repo: Path, service: str) -> list[str]:
    """Every committed vhost whose backend is this service, from a checkout at the revision."""
    try:
        data = routes.snapshot(route_repo)
    except Exception:
        raise VerificationError("route observation unavailable", 3) from None
    rows = data.get("routes") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        raise VerificationError("malformed route observation", 3)
    vhosts: list[str] = []
    seen: set[str] = set()
    for route in rows:
        if not isinstance(route, dict):
            raise VerificationError("malformed route observation", 3)
        vhost, backend, entity = route.get("vhost"), route.get("backend"), route.get("backend_entity")
        if (not isinstance(vhost, str) or not _HOST.fullmatch(vhost)
                or not isinstance(backend, str) or not routes.ADDR.fullmatch(backend)
                or not isinstance(entity, str) or not _ENTITY.fullmatch(entity)
                or route.get("auth") not in _AUTH_VALUES):
            raise VerificationError("malformed route observation", 3)
        if route.get("front_door") != routes.FRONT_DOOR:
            raise VerificationError("route front door mismatch", 1)
        if vhost in seen:
            raise VerificationError("duplicate route vhost", 1)
        seen.add(vhost)
        if entity == f"svc/{service}":
            vhosts.append(vhost)
    return vhosts


def probe(context: str, vhost: str, timeout: float) -> dict[str, Any]:
    """One HTTPS request to a vhost through the apps front door, from the DMZ network."""
    seconds = str(max(1, int(timeout)))
    args = ["docker", "--context", context, "run", "--rm", "--network", INGRESS_NETWORK, CURL_IMAGE,
            "--silent", "--show-error", "--output", "/dev/null",
            "--write-out", "%{http_code} %{ssl_verify_result} %{redirect_url}",
            "--connect-timeout", seconds, "--max-time", seconds,
            "--resolve", f"{vhost}:443:{INGRESS_IP}", f"https://{vhost}/"]
    try:
        # Docker needs time for curl to hit --max-time and then remove the --rm container.
        result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                timeout=timeout + 5.0, check=False)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise VerificationError("route probe unavailable", 3) from None
    if result.returncode in {125, 126, 127}:
        raise VerificationError("route probe unavailable", 3)
    match = re.fullmatch(r"\s*(\d{3})\s+(\d+)(?:\s+(\S*))?\s*", result.stdout)
    if match is None:
        if result.returncode != 0:
            raise VerificationError("declared route is unreachable", 1)
        raise VerificationError("malformed route probe result", 3)
    status, tls = int(match[1]), int(match[2])
    if tls != 0:
        raise VerificationError("declared route TLS verification failed", 1)
    if status < 100 or status >= 500 or result.returncode != 0:
        raise VerificationError("declared route is unreachable", 1)
    return {"vhost": vhost, "http_code": status, "redirect": match[3] or ""}


def verify(service: str, revision: str, expected: Iterable[str], route_repo: Path, *,
           context: str = DEFAULT_CONTEXT, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Return complete evidence, or raise VerificationError. Nothing partial reads as healthy."""
    if not NAME.fullmatch(service):
        raise VerificationError("invalid service name", 2)
    if not REVISION.fullmatch(revision):
        raise VerificationError("expected revision must be a full 40-hex commit", 2)
    if not NAME.fullmatch(context):
        raise VerificationError("invalid Docker context", 2)
    if not 0 < timeout <= 300:
        raise VerificationError("invalid verification timeout", 2)
    containers = check_containers(inspect_project(context, service, timeout), service, revision,
                                  expected)
    probes = [probe(context, vhost, timeout) for vhost in route_vhosts(route_repo, service)]
    return {
        "service": service,
        "revision": revision,
        **containers,
        "routes": probes,
        "route_status": "verified" if probes else "skipped (no declared route)",
        "route_probe": f"ephemeral {CURL_IMAGE.split('@')[0]} on network {INGRESS_NETWORK}"
        if probes else "not run",
    }
