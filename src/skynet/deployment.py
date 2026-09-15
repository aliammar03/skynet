"""Report-only verification for immutable Compose generations.

The deployment owner prepares and activates a generation.  This module is the independent
observer used after activation: it reads the selected generation's non-secret release manifest,
observes the active pointer and the Docker daemon, and then probes declared routes from the DMZ.
It never activates a project, changes persistent state, or relies on a UI's deployment record.

The Docker observations deliberately use only narrow inspect templates.  A full ``docker inspect``
would include container environment variables and could put secret material in a retained process
output buffer.  Error text and command stderr are discarded; callers receive fixed, safe outcome
reasons only.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import signal
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence, TextIO

from skynet import routes


DEFAULT_CONTEXT = "docker-dmz"
DEFAULT_HOST = "svc-ops@10.10.100.15"
DEFAULT_STATE_ROOT = PurePosixPath("/home/svc-ops/.local/state/skynet-deploy")
DEFAULT_TIMEOUT = 15.0

# This compatibility value is not read.  The previous UI-backed verifier's credential contract
# has intentionally disappeared, but a short transition keeps stale importers loadable while the
# packaged CLI is reworked.
DEFAULT_CREDENTIALS: Path | None = None

# This is a reviewed, immutable probe image.  It is supplied as an argv item to Docker; no shell
# is involved and no unpinned image can be selected by route data.
CURL_IMAGE = "curlimages/curl:8.16.0@sha256:463eaf6072688fe96ac64fa623fe73e1dbe25d8ad6c34404a669ad3ce1f104b6"
INGRESS_NETWORK = "dmz"
INGRESS_IP = "10.10.100.35"

_REVISION = re.compile(r"[0-9a-f]{40}", re.IGNORECASE)
_SERVICE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_CONTEXT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_CONTAINER_ID = re.compile(r"[0-9a-f]{12,64}")
_OBJECT_ID = re.compile(r"[0-9a-f]{40,64}")
_SSH_HOST = re.compile(
    r"(?:[A-Za-z0-9][A-Za-z0-9_.-]*@)?[A-Za-z0-9][A-Za-z0-9_.-]*"
)
_HOST = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+aliammar\.net")
_ENTITY = re.compile(
    r"(?:svc|guest)/[A-Za-z0-9][A-Za-z0-9_.:-]*|host:[A-Za-z0-9][A-Za-z0-9_.:-]*"
)
_AUTH_VALUES = frozenset({"own-auth/plain", "forward_auth (authentik)", "identity (authentik)"})
_MAX_RESPONSE = 1024 * 1024
_MAX_COMMAND_OUTPUT = 256 * 1024
_CLEANUP_TIMEOUT = 5.0
_RELEASE_FIELDS = frozenset(
    {
        "schema",
        "service",
        "revision",
        "source_tree",
        "compose_input",
        "env_git_input",
        "env_sops_input",
        "prepared_at",
        # Optional service metadata is checked against Compose, never trusted as its authority.
        "compose_services",
        "services",
    }
)
_SECRET_HASH_FIELDS = frozenset(
    {"env_hash", "effective_env_hash", "plaintext_env_hash", "secret_hash"}
)


class VerificationError(Exception):
    """A safe verification outcome with a stable process exit code."""

    def __init__(self, reason: str, code: int = 1):
        super().__init__(reason)
        self.reason = reason
        self.code = code


@dataclass(frozen=True)
class _ProcessOutput:
    """A bounded command result with stderr intentionally unavailable to callers."""

    args: list[str]
    returncode: int
    stdout: str


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate and reap a command's process group, including descendants."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError:
        pass
    try:
        process.wait(timeout=0.25)
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass
    try:
        process.wait(timeout=_CLEANUP_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        raise VerificationError("verification command cleanup was not confirmed", 3) from None


def _run_process(args: list[str], timeout: float, reason: str) -> _ProcessOutput:
    """Run one fixed argv command with bounded stdout and process-tree cleanup.

    ``stderr`` is redirected to the OS sink rather than captured.  This is a deliberate custody
    boundary: a remote tool must not be able to place an environment value in retained evidence by
    printing it on failure.
    """
    process: subprocess.Popen[bytes] | None = None
    chunks: list[bytes] = []
    retained = 0
    oversized = False

    try:
        process = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except (OSError, ValueError):
        raise VerificationError(reason, 3) from None

    assert process.stdout is not None
    stream = process.stdout

    def drain() -> None:
        nonlocal retained, oversized
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    return
                room = _MAX_COMMAND_OUTPUT + 1 - retained
                if room > 0:
                    chunks.append(chunk[:room])
                    retained += min(len(chunk), room)
                if retained > _MAX_COMMAND_OUTPUT or len(chunk) > room:
                    oversized = True
        except (OSError, ValueError):
            oversized = True

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    try:
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _terminate_group(process)
            raise VerificationError(reason, 3) from None
        reader.join(timeout=_CLEANUP_TIMEOUT)
        if reader.is_alive():
            _terminate_group(process)
            reader.join(timeout=_CLEANUP_TIMEOUT)
            raise VerificationError(reason, 3)
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass

    if oversized:
        raise VerificationError("verification command output exceeded its bound", 3)
    try:
        stdout = b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError:
        raise VerificationError("malformed verification command output", 3) from None
    return _ProcessOutput(args, int(process.returncode or 0), stdout)


def _run_command(args: list[str], timeout: float, *, reason: str) -> _ProcessOutput:
    """Run a command and classify a non-zero result without retaining its error output."""
    result = _run_process(args, timeout, reason)
    if result.returncode != 0:
        raise VerificationError(reason, 3)
    return result


def _run_route_command(args: list[str], timeout: float) -> _ProcessOutput:
    """Run a route probe while preserving curl's non-zero reachability result."""
    return _run_process(args, timeout, "route probe unavailable")


def _validate_service(value: Any, *, label: str = "service") -> str:
    if not isinstance(value, str) or not _SERVICE.fullmatch(value) or value in {".", ".."}:
        raise VerificationError(f"invalid {label} name", 2)
    return value


def _validate_revision(value: Any, *, label: str = "revision") -> str:
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise VerificationError(f"{label} must be a full 40-hex commit", 2)
    return value


def _validate_context(value: Any) -> str:
    if not isinstance(value, str) or not _CONTEXT.fullmatch(value):
        raise VerificationError("invalid Docker context", 2)
    return value


def _validate_timeout(value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value <= 300:
        raise VerificationError("invalid verification timeout", 2)
    return float(value)


def _validate_host(value: Any) -> str:
    if not isinstance(value, str) or not _SSH_HOST.fullmatch(value):
        raise VerificationError("invalid Docker SSH host", 2)
    return value


def _safe_absolute_path(value: str | Path | PurePosixPath, label: str) -> PurePosixPath:
    """Validate a host path used only as a generation/state observation target."""
    try:
        raw = str(value)
    except (TypeError, ValueError):
        raise VerificationError(f"invalid {label} path", 2) from None
    if (
        not raw
        or any(ord(char) < 33 or ord(char) == 127 for char in raw)
        or "\\" in raw
    ):
        raise VerificationError(f"invalid {label} path", 2)
    path = PurePosixPath(raw)
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        raise VerificationError(f"unsafe {label} path", 2)
    return path


def _join_path(root: PurePosixPath, *parts: str) -> PurePosixPath:
    try:
        result = root.joinpath(*parts)
    except (TypeError, ValueError):
        raise VerificationError("unsafe generation path", 2) from None
    if any(part in {".", ".."} for part in result.parts):
        raise VerificationError("unsafe generation path", 2)
    return result


def _generation_paths(
    state_root: str | Path | PurePosixPath,
    service: str,
    revision: str,
    generation_dir: str | Path | PurePosixPath | None,
) -> tuple[PurePosixPath, PurePosixPath, PurePosixPath]:
    root = _safe_absolute_path(state_root, "state root")
    service_dir = _join_path(root, service)
    if generation_dir is None:
        selected = _join_path(service_dir, "generations", revision)
    else:
        selected = _safe_absolute_path(generation_dir, "generation")
        if (
            selected.name != revision
            or selected.parent.name != "generations"
            or selected.parent.parent != service_dir
        ):
            raise VerificationError("generation path does not match service and revision", 2)
    return selected, _join_path(service_dir, "active"), _join_path(selected, "release.json")


def _ssh_command(host: str, remote_command: str, timeout: float) -> list[str]:
    """Build one bounded, non-interactive command for the standing Docker-host identity."""
    _validate_host(host)
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={max(1, int(timeout))}",
        host,
        remote_command,
    ]


def _remote_text(
    path: PurePosixPath,
    host: str | None,
    timeout: float,
    reason: str,
) -> str:
    """Read one bounded text observation from the target, never echoing its body on failure."""
    if host is None:
        try:
            raw = Path(str(path)).read_bytes()
        except (OSError, ValueError):
            raise VerificationError(reason, 3) from None
        if len(raw) > _MAX_RESPONSE:
            raise VerificationError("remote observation exceeded its bound", 3)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raise VerificationError("malformed remote observation", 3) from None
    result = _run_command(
        _ssh_command(host, f"cat -- {shlex.quote(str(path))}", timeout),
        timeout + 5.0,
        reason=reason,
    )
    if len(result.stdout.encode("utf-8")) > _MAX_RESPONSE:
        raise VerificationError("remote observation exceeded its bound", 3)
    return result.stdout


def _active_revision(path: PurePosixPath, expected: str, host: str | None, timeout: float) -> str:
    raw = _remote_text(path, host, timeout, "active generation observation unavailable")
    value = raw.strip()
    if not _REVISION.fullmatch(value):
        raise VerificationError("malformed active generation observation", 3)
    if value != expected:
        raise VerificationError("active generation revision mismatch", 1)
    return value


def _manifest_identity(
    raw: str,
    service: str,
    expected_revision: str,
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    try:
        manifest = json.loads(raw)
    except (UnicodeError, ValueError):
        raise VerificationError("malformed generation release manifest", 3) from None
    if not isinstance(manifest, dict):
        raise VerificationError("malformed generation release manifest", 3)
    if _SECRET_HASH_FIELDS.intersection(manifest):
        raise VerificationError("generation release manifest contains secret hash material", 3)
    unknown = set(manifest).difference(_RELEASE_FIELDS)
    if unknown:
        raise VerificationError("generation release manifest has unknown fields", 3)

    # Preparation currently emits this exact public schema.  Requiring every field prevents a
    # partial manifest from becoming an identity assertion, especially when a secret input is
    # absent and must therefore be represented explicitly as JSON null.
    required = {
        "schema",
        "service",
        "revision",
        "source_tree",
        "compose_input",
        "env_git_input",
        "env_sops_input",
        "prepared_at",
    }
    if not required <= manifest.keys():
        raise VerificationError("generation release manifest is incomplete", 3)
    if manifest["schema"] != 1:
        raise VerificationError("unsupported generation release schema", 3)
    manifest_service = manifest["service"]
    if not isinstance(manifest_service, str) or not _SERVICE.fullmatch(manifest_service):
        raise VerificationError("malformed generation release service", 3)
    if manifest_service != service:
        raise VerificationError("generation release service mismatch", 1)
    revision = manifest["revision"]
    if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
        raise VerificationError("malformed generation release revision", 3)
    if revision != expected_revision:
        raise VerificationError("generation release revision mismatch", 1)

    identity: dict[str, Any] = {
        "schema": 1,
        "service": service,
        "revision": revision,
    }
    for key in ("source_tree", "compose_input", "env_git_input"):
        value = manifest[key]
        if not isinstance(value, str) or not _OBJECT_ID.fullmatch(value):
            raise VerificationError("malformed generation release identity", 3)
        identity[key] = value
    env_sops_input = manifest["env_sops_input"]
    if env_sops_input is not None and (
        not isinstance(env_sops_input, str) or not _OBJECT_ID.fullmatch(env_sops_input)
    ):
        raise VerificationError("malformed generation release encrypted-input identity", 3)
    identity["env_sops_input"] = env_sops_input

    prepared_at = manifest["prepared_at"]
    if not isinstance(prepared_at, str) or not 0 < len(prepared_at) <= 128:
        raise VerificationError("malformed generation release timestamp", 3)
    if any(ord(char) < 32 or ord(char) == 127 for char in prepared_at):
        raise VerificationError("malformed generation release timestamp", 3)
    # generation.py emits UTC RFC3339 seconds with a literal Z.  Parse it as well as checking the
    # character boundary so impossible calendar values cannot be accepted as public identity.
    try:
        datetime.strptime(prepared_at, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        raise VerificationError("malformed generation release timestamp", 3) from None
    identity["prepared_at"] = prepared_at
    return identity, manifest


def _manifest_services(manifest: Mapping[str, Any]) -> list[str] | None:
    """Read optional service metadata; Compose remains the independent authority."""
    observed: list[list[str]] = []
    for key in ("compose_services", "services"):
        if key not in manifest:
            continue
        candidate = manifest[key]
        if not isinstance(candidate, list) or not candidate:
            raise VerificationError("malformed generation Compose service metadata", 3)
        values = [_validate_service(item, label="Compose service") for item in candidate]
        if len(values) != len(set(values)):
            raise VerificationError("duplicate generation Compose service metadata", 3)
        observed.append(sorted(values))
    if not observed:
        return None
    if any(values != observed[0] for values in observed[1:]):
        raise VerificationError("generation Compose service metadata disagrees", 1)
    return observed[0]


def _compose_services(
    generation: PurePosixPath,
    project: str,
    host: str | None,
    timeout: float,
) -> list[str]:
    """Resolve the Compose service set without asking Compose to print its expanded environment."""
    command = [
        "docker",
        "compose",
        "--project-name",
        project,
        "--project-directory",
        str(generation),
        "--env-file",
        str(_join_path(generation, ".env")),
        "--file",
        str(_join_path(generation, "compose.yaml")),
        "config",
        "--services",
    ]
    if host is None:
        result = _run_command(command, timeout, reason="generation Compose observation unavailable")
    else:
        result = _run_command(
            _ssh_command(host, shlex.join(command), timeout),
            timeout + 5.0,
            reason="generation Compose observation unavailable",
        )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise VerificationError("generation Compose service set is empty", 1)
    values = [_validate_service(item, label="Compose service") for item in lines]
    if len(values) != len(set(values)):
        raise VerificationError("duplicate generation Compose service", 3)
    return sorted(values)


def _json_field(values: str, label: str) -> list[Any]:
    rows = values.splitlines()
    if not rows:
        raise VerificationError(f"empty Docker {label} observation", 3)
    decoded: list[Any] = []
    for row in rows:
        try:
            decoded.append(json.loads(row))
        except (UnicodeError, ValueError):
            raise VerificationError(f"malformed Docker {label} observation", 3) from None
    return decoded


def _inspect_values(
    context: str,
    ids: Sequence[str],
    template: str,
    label: str,
    timeout: float,
) -> list[Any]:
    result = _run_command(
        ["docker", "--context", context, "inspect", "--format", template, *ids],
        timeout,
        reason=f"Docker {label} observation unavailable",
    )
    values = _json_field(result.stdout, label)
    if len(values) != len(ids):
        raise VerificationError(f"partial Docker {label} observation", 3)
    return values


def _containers(
    context: str,
    project: str,
    expected_services: Sequence[str] | int,
    timeout: float = DEFAULT_TIMEOUT,
    *,
    generation_dir: str | PurePosixPath | None = None,
) -> list[dict[str, str]]:
    """Require one complete, healthy container per expected service and exact generation labels."""
    result = _run_command(
        [
            "docker",
            "--context",
            context,
            "ps",
            "--all",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.ID}}",
        ],
        timeout,
        reason="Docker container observation unavailable",
    )
    raw_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not raw_ids:
        raise VerificationError("Docker project has no containers", 1)
    if any(not _CONTAINER_ID.fullmatch(value) for value in raw_ids) or len(raw_ids) != len(set(raw_ids)):
        raise VerificationError("malformed Docker container identity observation", 3)

    expected_count = expected_services if isinstance(expected_services, int) else len(expected_services)
    if expected_count <= 0:
        raise VerificationError("expected Compose service set is empty", 3)
    expected_set = (
        None
        if isinstance(expected_services, int)
        else set(_validate_service(item, label="Compose service") for item in expected_services)
    )
    if expected_set is not None and len(expected_set) != expected_count:
        raise VerificationError("duplicate expected Compose service", 3)
    if len(raw_ids) != expected_count:
        raise VerificationError("Docker container observation is partial", 1)

    label_templates = {
        "project": '{{json (index .Config.Labels "com.docker.compose.project")}}',
        "service": '{{json (index .Config.Labels "com.docker.compose.service")}}',
        "working_dir": '{{json (index .Config.Labels "com.docker.compose.project.working_dir")}}',
        "config_files": '{{json (index .Config.Labels "com.docker.compose.project.config_files")}}',
        "oneoff": '{{json (index .Config.Labels "com.docker.compose.oneoff")}}',
    }
    field_rows: dict[str, list[Any]] = {
        key: _inspect_values(context, raw_ids, template, f"container {key}", timeout)
        for key, template in label_templates.items()
    }
    state_rows = _inspect_values(
        context,
        raw_ids,
        '{{json .State.Status}}',
        "container state",
        timeout,
    )
    running_rows = _inspect_values(
        context,
        raw_ids,
        '{{json .State.Running}}',
        "container running state",
        timeout,
    )
    restarting_rows = _inspect_values(
        context,
        raw_ids,
        '{{json .State.Restarting}}',
        "container restart state",
        timeout,
    )
    health_rows = _inspect_values(
        context,
        raw_ids,
        '{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}}',
        "container health state",
        timeout,
    )
    healthcheck_rows = _inspect_values(
        context,
        raw_ids,
        '{{if .Config.Healthcheck}}true{{else}}false{{end}}',
        "container healthcheck presence",
        timeout,
    )

    expected_working = str(generation_dir) if generation_dir is not None else None
    expected_config = (
        str(_join_path(PurePosixPath(expected_working), "compose.yaml"))
        if expected_working is not None
        else None
    )
    observations: list[dict[str, str]] = []
    seen_services: set[str] = set()
    for index, container_id in enumerate(raw_ids):
        row: dict[str, Any] = {key: field_rows[key][index] for key in label_templates}
        project_value = row["project"]
        service_value = row["service"]
        working_value = row["working_dir"]
        config_value = row["config_files"]
        oneoff_value = row["oneoff"]
        if any(not isinstance(row[key], str) or not row[key] for key in label_templates):
            raise VerificationError("malformed Docker Compose label observation", 3)
        if project_value != project:
            raise VerificationError("Docker Compose project identity mismatch", 1)
        service_name = _validate_service(service_value, label="observed Compose service")
        if service_name in seen_services:
            raise VerificationError("duplicate Docker Compose service container", 1)
        seen_services.add(service_name)
        if expected_set is not None and service_name not in expected_set:
            raise VerificationError("Docker Compose service set contains an extra service", 1)
        if expected_working is not None and working_value != expected_working:
            raise VerificationError("Docker container generation working directory mismatch", 1)
        if expected_config is not None:
            config_paths = config_value.split(",")
            if config_paths != [expected_config]:
                raise VerificationError("Docker container Compose input mismatch", 1)
        if oneoff_value.lower() != "false":
            raise VerificationError("Docker project contains a one-off container", 1)

        state_value, running_value, restarting_value = (
            state_rows[index], running_rows[index], restarting_rows[index]
        )
        health_value = health_rows[index]
        healthcheck_value = healthcheck_rows[index]
        if state_value != "running" or running_value is not True or restarting_value is not False:
            raise VerificationError("Docker container is not running", 1)
        if healthcheck_value is not True:
            raise VerificationError("Docker container has no healthcheck", 1)
        if health_value != "healthy":
            if health_value in {None, "", "none"}:
                raise VerificationError("Docker container has no healthcheck", 1)
            raise VerificationError("Docker container is unhealthy", 1)
        observations.append({"id": container_id, "service": service_name, "health": "healthy"})

    if expected_set is not None and seen_services != expected_set:
        raise VerificationError("Docker Compose service set is missing a required service", 1)
    return observations


def _route_vhosts(
    repo: Path,
    service: str,
    expected_revision: str,
    timeout: float,
) -> list[str]:
    """Parse the exact release route map and return vhosts targeting this service."""
    try:
        data = routes.snapshot(repo, revision=expected_revision, timeout=timeout)
    except Exception:
        raise VerificationError("route observation unavailable", 3) from None
    if not isinstance(data, dict) or not isinstance(data.get("routes"), list) or not data["routes"]:
        raise VerificationError("malformed route observation", 3)
    if data.get("source_revision") != expected_revision:
        raise VerificationError("route observation revision mismatch", 1)
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
        vhost, backend, entity = route.get("vhost"), route.get("backend"), route.get("backend_entity")
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
        timeout + 5.0,
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
    context: str = DEFAULT_CONTEXT,
    repo: Path | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    state_root: str | Path | PurePosixPath = DEFAULT_STATE_ROOT,
    host: str | None = DEFAULT_HOST,
    project_name: str | None = None,
    generation_dir: str | Path | PurePosixPath | None = None,
    expected_services: Sequence[str] | None = None,
    release_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return complete generation verification evidence or raise ``VerificationError``."""
    service = _validate_service(service)
    expected_revision = _validate_revision(expected_revision, label="expected revision")
    context = _validate_context(context)
    timeout = _validate_timeout(timeout)
    project = service if project_name is None else _validate_service(project_name, label="Compose project")
    if host is not None:
        host = _validate_host(host)
    checkout = repo if repo is not None else Path.cwd()
    if not isinstance(checkout, Path):
        raise VerificationError("invalid repository path", 2)
    selected_generation, active_path, manifest_path = _generation_paths(
        state_root, service, expected_revision, generation_dir
    )

    active = _active_revision(active_path, expected_revision, host, timeout)
    if release_manifest is None:
        manifest_raw = _remote_text(
            manifest_path,
            host,
            timeout,
            "generation release manifest unavailable",
        )
        release, manifest = _manifest_identity(manifest_raw, service, expected_revision)
    else:
        try:
            manifest_raw = json.dumps(dict(release_manifest), separators=(",", ":"))
        except (TypeError, ValueError):
            raise VerificationError("malformed generation release manifest", 3) from None
        release, manifest = _manifest_identity(manifest_raw, service, expected_revision)

    # Always resolve the selected generation with Compose.  A release manifest's optional service
    # list is a consistency hint only; trusting it would let stale metadata hide missing or extra
    # runtime services.
    service_set = _compose_services(selected_generation, project, host, timeout)
    manifest_services = _manifest_services(manifest)
    if manifest_services is not None and manifest_services != service_set:
        raise VerificationError("generation Compose service metadata mismatch", 1)
    if expected_services is not None:
        if isinstance(expected_services, (str, bytes)):
            raise VerificationError("malformed expected Compose service set", 3)
        expected_set = [_validate_service(item, label="expected Compose service") for item in expected_services]
        if not expected_set or len(expected_set) != len(set(expected_set)):
            raise VerificationError("malformed expected Compose service set", 3)
        if sorted(expected_set) != service_set:
            raise VerificationError("expected Compose service set mismatch", 1)

    context_observation = _run_command(
        ["docker", "context", "inspect", context],
        timeout,
        reason="Docker context unavailable",
    )
    if not context_observation.stdout.strip():
        raise VerificationError("Docker context unavailable", 3)
    containers = _containers(
        context,
        project,
        service_set,
        timeout,
        generation_dir=selected_generation,
    )
    vhosts = _route_vhosts(checkout, service, expected_revision, timeout)
    route_results: list[dict[str, int | str]] = []
    for vhost in vhosts:
        status, tls_result = _probe_route(context, vhost, timeout)
        route_results.append({"vhost": vhost, "http_code": status, "ssl_verify_result": tls_result})
    route_probe = {
        "vantage": f"docker context {context} / network {INGRESS_NETWORK}",
        "image": CURL_IMAGE,
        "side_effect": (
            "ephemeral probe container is created/removed; pinned image may be pulled/cached"
            if route_results
            else "not run (no declared route)"
        ),
    }
    return {
        "service": service,
        "expected_revision": expected_revision,
        "active_revision": active,
        "generation": str(selected_generation),
        "release": release,
        "project_name": project,
        "expected_services": service_set,
        "observed_services": sorted(row["service"] for row in containers),
        "container_count": len(containers),
        "containers": containers,
        "routes": route_results,
        "route_status": "verified" if route_results else "skipped",
        "route_probe": route_probe,
    }


def verify(
    service: str,
    expected_revision: str,
    context: str = DEFAULT_CONTEXT,
    repo: Path | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    state_root: str | Path | PurePosixPath = DEFAULT_STATE_ROOT,
    host: str | None = DEFAULT_HOST,
    project_name: str | None = None,
    generation_dir: str | Path | PurePosixPath | None = None,
    expected_services: Sequence[str] | None = None,
    release_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return non-secret verification evidence or raise a safe :class:`VerificationError`.

    Promotion uses this raising form so a failed candidate cannot be mistaken for a report-only
    success.  The human/JSON rendering wrapper below converts the same fixed errors to outcome
    fields.
    """
    return snapshot(
        service,
        expected_revision,
        context,
        repo,
        timeout=timeout,
        state_root=state_root,
        host=host,
        project_name=project_name,
        generation_dir=generation_dir,
        expected_services=expected_services,
        release_manifest=release_manifest,
    )


def run(
    service: str,
    expected_revision: str,
    docker_context: str = DEFAULT_CONTEXT,
    repo: Path | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    state_root: str | Path | PurePosixPath = DEFAULT_STATE_ROOT,
    host: str | None = DEFAULT_HOST,
    project_name: str | None = None,
    generation_dir: str | Path | PurePosixPath | None = None,
    expected_services: Sequence[str] | None = None,
    release_manifest: Mapping[str, Any] | None = None,
    json_output: bool = False,
    stdout: TextIO,
) -> int:
    """Run one report-only verification and render human or JSON output."""
    safe_service = service if isinstance(service, str) and _SERVICE.fullmatch(service) else "<invalid>"
    safe_revision = (
        expected_revision
        if isinstance(expected_revision, str) and _REVISION.fullmatch(expected_revision)
        else "<invalid>"
    )
    report: dict[str, Any] = {
        "target": "deployment",
        "service": safe_service,
        "expected_revision": safe_revision,
    }
    try:
        evidence = verify(
            service,
            expected_revision,
            docker_context,
            repo,
            timeout=timeout,
            state_root=state_root,
            host=host,
            project_name=project_name,
            generation_dir=generation_dir,
            expected_services=expected_services,
            release_manifest=release_manifest,
        )
    except VerificationError as error:
        report.update(
            outcome="unavailable" if error.code == 3 else "failure",
            reason=error.reason,
            exit_code=error.code,
        )
    else:
        report.update(outcome="success", status="verified", exit_code=0)
        report.update(evidence)
    if json_output:
        print(json.dumps(report, sort_keys=True), file=stdout)
    elif report["outcome"] == "success":
        route_note = report["route_status"]
        if route_note == "verified":
            route_note += "; ephemeral pinned curl probe may pull/cache its image"
        print(
            f"deployment: {report['service']} verified at {report['expected_revision']} "
            f"({report['container_count']} container(s); routes {route_note})",
            file=stdout,
        )
    else:
        print(f"deployment: {report['outcome']}: {report['reason']}", file=stdout)
    return int(report["exit_code"])


# ``check`` remains a discoverability alias for callers migrating from shell gate terminology.
check = verify
