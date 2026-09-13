"""Read-only deployment health and ingress verification.

The deploy verifier is deliberately a small, synchronous observer.  It compares the revision that
the caller explicitly supplied with both Arcane GitOps and project observations, then reconciles
the project counts with the Docker containers visible through a named context.  If a route for the
service is declared in the checkout, the route is also tested from the DMZ ingress network by a
bounded ephemeral probe container using a pinned image.

This module never deploys, rolls back, edits a checkout, or changes persistent Docker/Arcane
configuration.  A route probe may create/remove an ephemeral container and pull/cache its reviewed
image; that bounded side effect is stated in the result.  It does not include remote error text in
reports: API keys, transport details, and server response bodies must remain outside evidence.
"""

from __future__ import annotations

import http.client
import json
import re
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, TextIO, cast

from skynet import routes

DEFAULT_CREDENTIALS = Path("/opt/skynet-ops/secrets/arcane.env")
DEFAULT_CONTEXT = "docker-dmz"
DEFAULT_ENVIRONMENT_ID = "0"
DEFAULT_TIMEOUT = 15.0

# This is a reviewed, immutable probe image.  The image is supplied as an argv item to Docker;
# no shell is involved and no unpinned image can be selected by route data.
CURL_IMAGE = "curlimages/curl:8.16.0@sha256:463eaf6072688fe96ac64fa623fe73e1dbe25d8ad6c34404a669ad3ce1f104b6"
INGRESS_NETWORK = "dmz"
INGRESS_IP = "10.10.100.35"

_REVISION = re.compile(r"[0-9a-f]{40}", re.IGNORECASE)
_SERVICE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_CONTEXT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_ENVIRONMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_HOST = re.compile(
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+aliammar\.net"
)
_ENTITY = re.compile(
    r"(?:svc|guest)/[A-Za-z0-9][A-Za-z0-9_.:-]*|host:[A-Za-z0-9][A-Za-z0-9_.:-]*"
)
_AUTH_VALUES = frozenset({"own-auth/plain", "forward_auth (authentik)", "identity (authentik)"})
_ASSIGNMENT = re.compile(
    r"\s*(ARCANE_URL|ARCANE_TOKEN|ARCANE_ENV_ID|ARCANE_AUTH_HEADER)="
    r"(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"]+))\s*(?:#.*)?"
)
_MAX_RESPONSE = 1024 * 1024
_MAX_COMMAND_OUTPUT = 64 * 1024


class VerificationError(Exception):
    """A safe verification outcome with a stable process exit code."""

    def __init__(self, reason: str, code: int = 1):
        super().__init__(reason)
        self.reason = reason
        self.code = code


@dataclass(frozen=True)
class Credentials:
    """Validated Arcane endpoint data; the token is never serialized or repr-ed."""

    url: str
    token: str = field(repr=False)
    auth_header: str
    environment_id: str
    tls_context: ssl.SSLContext


def _assignment_values(path: Path) -> dict[str, str]:
    """Read literal Arcane assignments without evaluating shell syntax."""
    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        raise VerificationError("Arcane credentials unavailable", 3) from None
    values: dict[str, str] = {}
    for line in contents.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _ASSIGNMENT.fullmatch(line)
        if match is None:
            raise VerificationError("invalid Arcane credential assignments", 3)
        key = match[1]
        value = next(item for item in match.groups()[1:] if item is not None)
        if key in values or not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise VerificationError("invalid Arcane credential assignments", 3)
        values[key] = value
    if not {"ARCANE_URL", "ARCANE_TOKEN"} <= values.keys():
        raise VerificationError("required Arcane credentials missing", 3)
    return values


def _endpoint(url: str) -> urllib.parse.SplitResult:
    """Validate a base URL while preserving HTTPS certificate verification."""
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        raise VerificationError("invalid Arcane URL", 3) from None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise VerificationError("invalid Arcane URL", 3)
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise VerificationError("invalid Arcane URL", 3)
    try:
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise VerificationError("invalid Arcane URL", 3) from None
    if not hostname or port is not None and not 1 <= port <= 65535:
        raise VerificationError("invalid Arcane URL", 3)
    # A path is allowed for installations mounted below a prefix, but control characters are not.
    if any(ord(char) < 33 or ord(char) == 127 for char in parsed.path):
        raise VerificationError("invalid Arcane URL", 3)
    return parsed


def credentials(path: Path = DEFAULT_CREDENTIALS, *, environment_id: str | None = None) -> Credentials:
    """Parse the literal Arcane credential file and build the default TLS context."""
    values = _assignment_values(path)
    parsed = _endpoint(values["ARCANE_URL"])
    selected_environment = environment_id if environment_id is not None else values.get(
        "ARCANE_ENV_ID", DEFAULT_ENVIRONMENT_ID
    )
    if not isinstance(selected_environment, str) or not _ENVIRONMENT.fullmatch(selected_environment):
        raise VerificationError("invalid Arcane environment id", 3)
    auth_header = values.get("ARCANE_AUTH_HEADER", "X-API-Key")
    # The current Arcane API contract uses this header. Keep the file extensible enough to carry
    # the established declaration, but do not permit an arbitrary header name to be selected by a
    # credential file that could have been accidentally copied from another service.
    if auth_header != "X-API-Key":
        raise VerificationError("invalid Arcane auth header", 3)
    try:
        context = ssl.create_default_context()
    except (OSError, ssl.SSLError, ValueError):
        raise VerificationError("TLS context unavailable", 3) from None
    return Credentials(
        parsed.geturl().rstrip("/"), values["ARCANE_TOKEN"], auth_header, selected_environment, context
    )


def _quoted_part(value: Any, reason: str) -> str:
    """Require a safe URL path segment from an Arcane observation."""
    if not isinstance(value, str) or not value or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value):
        raise VerificationError(reason, 3)
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Keep an API token on the configured endpoint only."""

    def redirect_request(
        self,
        request: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: http.client.HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        return None


def _api_get(client: "ArcaneClient", path: str) -> Any:
    """Fetch and validate one Arcane JSON envelope without exposing transport details."""
    try:
        request = urllib.request.Request(
            client.url + "/api" + path,
            headers={client.auth_header: client.token, "Accept": "application/json"},
            method="GET",
        )
        with client.opener.open(request, timeout=client.timeout) as response:
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            if status != 200:
                raise VerificationError("Arcane API unavailable", 3)
            raw = response.read(_MAX_RESPONSE + 1)
    except VerificationError:
        raise
    except (
        OSError,
        urllib.error.URLError,
        urllib.error.HTTPError,
        http.client.HTTPException,
        TimeoutError,
        UnicodeError,
    ):
        raise VerificationError("Arcane API unavailable", 3) from None
    if len(raw) > _MAX_RESPONSE:
        raise VerificationError("Arcane API response unavailable", 3)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise VerificationError("malformed Arcane API response", 3) from None
    if not isinstance(payload, dict) or "success" not in payload or "data" not in payload:
        raise VerificationError("malformed Arcane API response", 3)
    if payload["success"] is not True:
        raise VerificationError("Arcane API unavailable", 3)
    return payload["data"]


@dataclass
class ArcaneClient:
    """Read-only Arcane API client with a bounded request timeout."""

    url: str
    token: str = field(repr=False)
    auth_header: str
    environment_id: str
    tls_context: ssl.SSLContext
    timeout: float = DEFAULT_TIMEOUT
    opener: urllib.request.OpenerDirector = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # HTTPSHandler carries the validated default context.  HTTP remains available only when
        # the operator explicitly configures an http:// endpoint (useful for a local test fixture).
        self.opener = urllib.request.build_opener(
            _NoRedirect(), urllib.request.HTTPSHandler(context=self.tls_context)
        )

    def get(self, path: str) -> Any:
        return _api_get(self, path)


def _sync_observation(client: ArcaneClient, service: str) -> dict[str, Any]:
    """Resolve exactly one complete service GitOps sync and its project id."""
    data = client.get(f"/environments/{client.environment_id}/gitops-syncs")
    if not isinstance(data, list) or not data:
        raise VerificationError("GitOps sync observation unavailable", 3)
    if any(not isinstance(item, dict) for item in data):
        raise VerificationError("malformed GitOps sync observation", 3)
    candidates = [
        item for item in data if item.get("name") == service or item.get("projectName") == service
    ]
    if len(candidates) != 1:
        raise VerificationError("GitOps sync identity missing or ambiguous", 1)
    sync = candidates[0]
    required = {
        "id",
        "name",
        "projectName",
        "branch",
        "composePath",
        "projectId",
        "lastSyncStatus",
        "lastSyncCommit",
    }
    if not required <= sync.keys():
        raise VerificationError("malformed GitOps sync observation", 3)
    if any(
        not isinstance(sync[key], str)
        for key in required
    ):
        raise VerificationError("malformed GitOps sync observation", 3)
    if sync["name"] != service or sync["projectName"] != service:
        raise VerificationError("GitOps sync identity mismatch", 1)
    sync_id = _quoted_part(sync["id"], "malformed GitOps sync observation")
    project_id = _quoted_part(sync["projectId"], "malformed GitOps sync observation")
    if not sync["branch"]:
        raise VerificationError("malformed GitOps sync observation", 3)
    if sync["composePath"] != f"compose/{service}/compose.yaml":
        raise VerificationError("GitOps compose identity mismatch", 1)
    if sync["lastSyncStatus"] != "success":
        raise VerificationError("GitOps sync status is not successful", 1)
    revision = sync["lastSyncCommit"]
    if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
        raise VerificationError("malformed GitOps sync revision", 3)
    return {"id": sync_id, "project_id": project_id, "revision": revision}


def _project_observation(
    client: ArcaneClient,
    sync: Mapping[str, str],
    expected_revision: str,
) -> dict[str, int | str]:
    """Require a running, GitOps-managed project at the requested revision."""
    data = client.get(
        f"/environments/{client.environment_id}/projects/{urllib.parse.quote(sync['project_id'], safe='') }"
    )
    if not isinstance(data, dict):
        raise VerificationError("malformed Arcane project observation", 3)
    required = {"status", "serviceCount", "runningCount", "lastSyncCommit", "gitOpsManagedBy"}
    if not required <= data.keys():
        raise VerificationError("malformed Arcane project observation", 3)
    if not isinstance(data["status"], str):
        raise VerificationError("malformed Arcane project observation", 3)
    if data["status"] != "running":
        raise VerificationError("Arcane project is not running", 1)
    service_count, running_count = data["serviceCount"], data["runningCount"]
    if (
        type(service_count) is not int
        or type(running_count) is not int
    ):
        raise VerificationError("malformed Arcane project observation", 3)
    if service_count <= 0 or running_count <= 0 or service_count != running_count:
        raise VerificationError("Arcane project service counts are incomplete", 1)
    if not isinstance(data["gitOpsManagedBy"], str) or not isinstance(data["lastSyncCommit"], str):
        raise VerificationError("malformed Arcane project observation", 3)
    if data["gitOpsManagedBy"] != sync["id"]:
        raise VerificationError("Arcane project GitOps identity mismatch", 1)
    revision = data["lastSyncCommit"]
    if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
        raise VerificationError("malformed Arcane project revision", 3)
    if revision != expected_revision:
        raise VerificationError("Arcane project revision mismatch", 1)
    return {"service_count": service_count, "running_count": running_count, "revision": revision}


def _run_command(args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    """Run a fixed Docker observation argv command with no shell and bounded capture."""
    try:
        result = subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise VerificationError("Docker command unavailable", 3) from None
    if result.returncode != 0:
        raise VerificationError("Docker command unavailable", 3)
    if not isinstance(result.stdout, str) or len(result.stdout) > _MAX_COMMAND_OUTPUT:
        raise VerificationError("malformed Docker command output", 3)
    return result


def _run_route_command(args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    """Run the ephemeral curl probe, preserving curl's route-failure classification."""
    try:
        result = subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            # Docker must have time to let curl hit --max-time and then remove the --rm container.
            timeout=timeout + 5.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise VerificationError("route probe unavailable", 3) from None
    if not isinstance(result.stdout, str) or len(result.stdout) > _MAX_COMMAND_OUTPUT:
        raise VerificationError("malformed route probe result", 3)
    return result


def _project_label(value: Any, expected: str) -> str:
    """Extract only the Compose-project label from Docker's flattened label rendering.

    Docker renders ``.Labels`` as comma-separated ``key=value`` pairs, but label values are free
    to contain commas.  Splitting every pair therefore turns legitimate OCI descriptions and
    Compose metadata into false malformed observations.  The project label's value is a safe
    Compose name, so an exact comma-boundary token is sufficient and leaves unrelated values
    opaque.  Mapping-shaped values are accepted for direct Docker API/test fixtures.
    """
    if isinstance(value, dict):
        project = value.get("com.docker.compose.project")
        if not isinstance(project, str):
            raise VerificationError("malformed Docker container observation", 3)
        if project != expected:
            raise VerificationError("Docker project identity mismatch", 1)
        return project
    if not isinstance(value, str):
        raise VerificationError("malformed Docker container observation", 3)
    token: re.Pattern[str] = re.compile(r"(?:^|,)com\.docker\.compose\.project=([^,]*)(?=,|$)")
    matches = token.findall(value)
    if len(matches) != 1:
        raise VerificationError("malformed Docker container observation", 3)
    if matches[0] != expected:
        raise VerificationError("Docker project identity mismatch", 1)
    return cast(str, matches[0])


def _containers(context: str, service: str, expected_count: int, timeout: float) -> list[dict[str, Any]]:
    """Read all containers for a Compose project and require complete healthy observations."""
    inspect = _run_command(["docker", "context", "inspect", context], timeout)
    if not inspect.stdout.strip():
        raise VerificationError("Docker context unavailable", 3)
    result = _run_command(
        [
            "docker",
            "--context",
            context,
            "ps",
            "--all",
            "--filter",
            f"label=com.docker.compose.project={service}",
            "--format",
            "{{json .}}",
        ],
        timeout,
    )
    if not result.stdout.strip():
        raise VerificationError("Docker container observation is empty", 1)
    rows: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        try:
            value = json.loads(line)
        except (ValueError, UnicodeError):
            raise VerificationError("malformed Docker container observation", 3) from None
        if not isinstance(value, dict):
            raise VerificationError("malformed Docker container observation", 3)
        required = {"Names", "State", "HealthStatus", "Status", "Labels"}
        if not required <= value.keys() or any(not isinstance(value[key], str) for key in required if key != "Labels"):
            raise VerificationError("malformed Docker container observation", 3)
        _project_label(value["Labels"], service)
        if not value["Names"] or not value["Status"]:
            raise VerificationError("malformed Docker container observation", 3)
        if value["State"] != "running" or value["Status"].lower().startswith("restarting"):
            raise VerificationError("Docker container is not running", 1)
        if value["HealthStatus"] != "healthy":
            if value["HealthStatus"] in {"", "none"}:
                raise VerificationError("Docker container has no healthcheck", 1)
            raise VerificationError("Docker container is unhealthy", 1)
        rows.append(value)
    if len(rows) != expected_count:
        raise VerificationError("Docker container observation is partial", 1)
    return rows


def _route_vhosts(repo: Path, service: str) -> list[str]:
    """Parse the committed route map and return all vhosts targeting this service."""
    try:
        data = routes.snapshot(repo)
    except Exception:
        raise VerificationError("route observation unavailable", 3) from None
    if not isinstance(data, dict) or not isinstance(data.get("routes"), list) or not data["routes"]:
        raise VerificationError("malformed route observation", 3)
    route_rows = data["routes"]
    counts = data.get("counts")
    if not isinstance(counts, dict):
        raise VerificationError("malformed route observation", 3)
    route_count = counts.get("routes")
    if type(route_count) is not int:
        raise VerificationError("malformed route observation", 3)
    if route_count <= 0 or route_count != len(route_rows):
        raise VerificationError("partial route observation", 3)
    vhosts: list[str] = []
    seen_vhosts: set[str] = set()
    for route in route_rows:
        if not isinstance(route, dict):
            raise VerificationError("malformed route observation", 3)
        vhost, backend, entity = (
            route.get("vhost"), route.get("backend"), route.get("backend_entity")
        )
        if (
            not isinstance(vhost, str)
            or not _HOST.fullmatch(vhost)
            or not isinstance(backend, str)
            or not routes.ADDR.fullmatch(backend)
            or not isinstance(entity, str)
            or not _ENTITY.fullmatch(entity)
            or not entity
            or "front_door" not in route
            or "front_door_alias" not in route
            or route["front_door_alias"] != routes.FRONT_DOOR_ALIAS
            or not isinstance(route.get("auth"), str)
            or route["auth"] not in _AUTH_VALUES
        ):
            raise VerificationError("malformed route observation", 3)
        if route["front_door"] != routes.FRONT_DOOR:
            raise VerificationError("route front door mismatch", 1)
        if vhost in seen_vhosts:
            raise VerificationError("duplicate route vhost", 1)
        seen_vhosts.add(vhost)
        if entity == f"svc/{service}":
            vhosts.append(vhost)
    return vhosts


def _probe_route(context: str, vhost: str, timeout: float) -> tuple[int, int]:
    """Probe one HTTPS vhost from the DMZ network using curl's verified TLS stack."""
    seconds = max(1, int(timeout))
    result = _run_route_command(
        [
            "docker",
            "--context",
            context,
            "run",
            "--rm",
            "--network",
            INGRESS_NETWORK,
            CURL_IMAGE,
            "--silent",
            "--show-error",
            "--output",
            "/dev/null",
            "--write-out",
            "%{http_code} %{ssl_verify_result}",
            "--connect-timeout",
            str(seconds),
            "--max-time",
            str(seconds),
            "--resolve",
            f"{vhost}:443:{INGRESS_IP}",
            f"https://{vhost}/",
        ],
        timeout,
    )
    if result.returncode in {125, 126, 127}:
        raise VerificationError("route probe unavailable", 3)
    match = re.fullmatch(r"\s*(\d{3})\s+(\d+)\s*", result.stdout)
    if match is None:
        if result.returncode != 0:
            raise VerificationError("declared route is unreachable", 1)
        raise VerificationError("malformed route probe result", 3)
    status, tls_result = int(match[1]), int(match[2])
    if tls_result != 0:
        raise VerificationError("declared route TLS verification failed", 1)
    if status < 100 or status >= 500 or result.returncode != 0:
        raise VerificationError("declared route is unreachable", 1)
    return status, tls_result


def snapshot(
    service: str,
    expected_revision: str,
    credentials_file: Path = DEFAULT_CREDENTIALS,
    context: str = DEFAULT_CONTEXT,
    repo: Path | None = None,
    *,
    environment_id: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Return complete verification evidence or raise a safe :class:`VerificationError`."""
    if not isinstance(service, str) or not _SERVICE.fullmatch(service):
        raise VerificationError("invalid service name", 2)
    if not isinstance(expected_revision, str) or not _REVISION.fullmatch(expected_revision):
        raise VerificationError("expected revision must be a full 40-hex commit", 2)
    if not isinstance(context, str) or not _CONTEXT.fullmatch(context):
        raise VerificationError("invalid Docker context", 2)
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 300:
        raise VerificationError("invalid verification timeout", 2)
    checkout = repo if repo is not None else Path.cwd()
    if not isinstance(checkout, Path):
        raise VerificationError("invalid repository path", 2)
    creds = credentials(credentials_file, environment_id=environment_id)
    client = ArcaneClient(
        creds.url, creds.token, creds.auth_header, creds.environment_id, creds.tls_context, float(timeout)
    )
    sync = _sync_observation(client, service)
    if sync["revision"] != expected_revision:
        raise VerificationError("GitOps sync revision mismatch", 1)
    project = _project_observation(client, sync, expected_revision)
    containers = _containers(context, service, int(project["service_count"]), float(timeout))
    vhosts = _route_vhosts(checkout, service)
    route_results: list[dict[str, int | str]] = []
    for vhost in vhosts:
        status, tls_result = _probe_route(context, vhost, float(timeout))
        route_results.append({"vhost": vhost, "http_code": status, "ssl_verify_result": tls_result})
    route_probe = {
        "vantage": f"docker context {context} / network {INGRESS_NETWORK}",
        "image": CURL_IMAGE,
        "side_effect": (
            "ephemeral probe container is created/removed; pinned image may be pulled/cached"
            if route_results else "not run (no declared route)"
        ),
    }
    return {
        "service": service,
        "expected_revision": expected_revision,
        "sync_revision": sync["revision"],
        "project_revision": project["revision"],
        "container_count": len(containers),
        "service_count": int(project["service_count"]),
        "running_count": int(project["running_count"]),
        "routes": route_results,
        "route_status": "verified" if route_results else "skipped",
        "route_probe": route_probe,
    }


def verify(
    service: str,
    expected_revision: str,
    credentials_file: Path = DEFAULT_CREDENTIALS,
    context: str = DEFAULT_CONTEXT,
    repo: Path | None = None,
    *,
    environment_id: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Return a JSON-ready report, converting internal failures to safe outcome fields."""
    report: dict[str, Any] = {
        "target": "deployment",
        "service": service,
        "expected_revision": expected_revision,
    }
    try:
        evidence = snapshot(
            service,
            expected_revision,
            credentials_file,
            context,
            repo,
            environment_id=environment_id,
            timeout=timeout,
        )
    except VerificationError as error:
        report.update(
            outcome="unavailable" if error.code == 3 else "failure",
            reason=error.reason,
            exit_code=error.code,
        )
        return report
    report.update(outcome="success", status="verified", exit_code=0)
    report.update(evidence)
    return report


def run(
    service: str,
    expected_revision: str,
    credentials_file: Path = DEFAULT_CREDENTIALS,
    context: str = DEFAULT_CONTEXT,
    repo: Path | None = None,
    *,
    environment_id: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    json_output: bool = False,
    stdout: TextIO,
) -> int:
    """Run one report-only verification and render either human or JSON output."""
    report = verify(
        service,
        expected_revision,
        credentials_file,
        context,
        repo,
        environment_id=environment_id,
        timeout=timeout,
    )
    if json_output:
        print(json.dumps(report, sort_keys=True), file=stdout)
    elif report["outcome"] == "success":
        route_note = report["route_status"]
        if report["route_status"] == "verified":
            route_note += "; ephemeral pinned curl probe may pull/cache its image"
        print(
            f"deployment: {service} verified at {expected_revision} "
            f"({report['container_count']} container(s); routes {route_note})",
            file=stdout,
        )
    else:
        print(f"deployment: {report['outcome']}: {report['reason']}", file=stdout)
    return int(report["exit_code"])


# ``check`` is a small discoverability alias for callers migrating from shell gate terminology.
check = verify
