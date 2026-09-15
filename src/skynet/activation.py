"""Direct Compose activation and filesystem-backed deployment state.

This module is the runtime half of the P11 deployment owner.  Generation preparation and
independent deployment verification live in their own packages; this module only admits one
immutable generation to a Docker host, reconciles what Docker actually runs, and records the
result in the host's protected state directory.

The host is reached as the standing ``svc-ops`` user.  All remote mutations are one bounded SSH
invocation and are protected by a host ``flock``.  Compose output is discarded remotely, and the
only data returned to this process is a small, validated set of identities and states.  In
particular, this module never reads, hashes, serializes, or forwards the effective environment.
"""

from __future__ import annotations

import http.client
import json
import os
import queue
import re
import shlex
import signal
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

DEFAULT_HOST = "svc-ops@10.10.100.15"
DEFAULT_STATE_ROOT = "/home/svc-ops/.local/state/skynet-deploy"
DEFAULT_ARCANE_CREDENTIALS = Path("/opt/skynet-ops/secrets/arcane.env")
DEFAULT_ENVIRONMENT_ID = "0"
DEFAULT_TIMEOUT = 30.0
MAX_OUTPUT = 64 * 1024
MAX_ARCANE_RESPONSE = 1024 * 1024

_SERVICE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_OPERATION = re.compile(r"[0-9a-f]{32}\Z")
_HOST = re.compile(r"(?:svc-ops@)?[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\Z")
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*\Z")
_STATE = re.compile(r"[a-z][a-z0-9-]*\Z")
_RUNTIME_CLASS = frozenset(
    {
        "none",
        "complete",
        "partial",
        "mixed",
        "legacy",
        "legacy-unknown",
        "orphan",
        "unavailable",
        "stopped",
    }
)
_MAX_SERVICES = 128
_MAX_GENERATIONS = 1024


class ActivationError(Exception):
    """A safe, operator-facing activation outcome.

    ``ambiguous`` is true when transport or a remote mutation prevents the caller from claiming
    that no write happened.  ``operation_id`` is safe to include in reports and is retained when
    the remote script emitted it before the failure.
    """

    def __init__(
        self,
        reason: str,
        code: int = 1,
        *,
        ambiguous: bool = False,
        operation_id: str | None = None,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.code = code
        self.ambiguous = ambiguous
        self.operation_id = operation_id


@dataclass(frozen=True)
class RuntimeObservation:
    """Validated Docker Compose identity evidence.

    ``generation`` is only populated for a single generation whose working-directory and
    config-file labels both identify a full revision below the protected state root.  A partial or
    mixed observation intentionally retains no path and cannot establish deployment health.
    """

    classification: str
    generation: str | None = None
    containers: int = 0
    detail: str | None = None

    def value(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "classification": self.classification,
            "containers": self.containers,
        }
        if self.generation is not None:
            value["generation"] = self.generation
        if self.detail is not None:
            value["detail"] = self.detail
        return value


@dataclass(frozen=True)
class ActivationResult:
    """JSON-ready result returned after a known remote activation/reconciliation."""

    operation_id: str
    service: str
    generation: str
    status: str
    active: str | None
    stable: str | None
    previous: str | None
    runtime: RuntimeObservation
    recovery: str = "not-needed"
    reason: str | None = None

    def value(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "operation_id": self.operation_id,
            "service": self.service,
            "generation": self.generation,
            "status": self.status,
            "active": self.active,
            "stable": self.stable,
            "previous": self.previous,
            "runtime": self.runtime.value(),
            "recovery": self.recovery,
        }
        if self.reason is not None:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True)
class ArcaneObservation:
    """Read-only Arcane Git Sync observation used by the migration guard."""

    service: str
    present: bool
    auto_sync: bool = False
    sync_id: str | None = None
    project_id: str | None = None
    last_revision: str | None = None
    project_revision: str | None = None
    project_status: str | None = None

    def value(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "service": self.service,
            "present": self.present,
            "auto_sync": self.auto_sync,
        }
        for key, value in (
            ("sync_id", self.sync_id),
            ("project_id", self.project_id),
            ("last_revision", self.last_revision),
            ("project_revision", self.project_revision),
            ("project_status", self.project_status),
        ):
            if value is not None:
                result[key] = value
        return result


@dataclass(frozen=True)
class ArcaneCredentials:
    """Validated Arcane endpoint data.  The token is deliberately excluded from repr."""

    url: str
    token: str = field(repr=False)
    environment_id: str


MigrationEvidence = Mapping[str, Any]
ArcaneSource = ArcaneObservation | Mapping[str, Any] | Callable[[], ArcaneObservation | Mapping[str, Any]]


def _validate_service(service: str) -> str:
    if not isinstance(service, str) or not _SERVICE.fullmatch(service) or service in {".", ".."}:
        raise ActivationError("invalid service identity", 2)
    return service


def _validate_service_set(value: Any, *, label: str = "Compose service set") -> tuple[str, ...]:
    """Validate a complete non-secret Compose service identity set."""

    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or not value:
        raise ActivationError(f"{label} must be a non-empty list", 2)
    if len(value) > _MAX_SERVICES:
        raise ActivationError(f"{label} is too large", 2)
    services: list[str] = []
    for item in value:
        try:
            services.append(_validate_service(item))
        except ActivationError:
            raise ActivationError(f"{label} contains an invalid service", 2) from None
    if len(services) != len(set(services)):
        raise ActivationError(f"{label} contains duplicate services", 2)
    return tuple(sorted(services))


def _validate_revision(revision: str) -> str:
    if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
        raise ActivationError("generation identity must be a full 40-hex Git revision", 2)
    return revision.lower()


def _validate_operation(operation_id: str) -> str:
    if not isinstance(operation_id, str) or not _OPERATION.fullmatch(operation_id):
        raise ActivationError("operation identity is malformed", 2)
    return operation_id.lower()


def _validate_timeout(timeout: float) -> float:
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 1 <= timeout <= 300:
        raise ActivationError("timeout must be between 1 and 300 seconds", 2)
    return float(timeout)


def _validate_host(host: str) -> str:
    if not isinstance(host, str) or not _HOST.fullmatch(host):
        raise ActivationError("invalid Docker host identity", 2)
    if "@" in host and not host.startswith("svc-ops@"):
        raise ActivationError("Docker activation requires the svc-ops SSH user", 2)
    return host if "@" in host else f"svc-ops@{host}"


def _validate_state_root(state_root: str | Path) -> str:
    value = os.fspath(state_root)
    if not isinstance(value, str) or not value.startswith("/") or len(value) > 4096:
        raise ActivationError("invalid deployment state root", 2)
    if any(ord(char) < 33 or ord(char) == 127 for char in value):
        raise ActivationError("invalid deployment state root", 2)
    pure = PurePosixPath(value)
    if ".." in pure.parts or str(pure) != value.rstrip("/"):
        raise ActivationError("unsafe deployment state root", 2)
    return value.rstrip("/")


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except OSError:
        pass
    try:
        process.wait(timeout=0.25)
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        pass
    if process.poll() is None:
        try:
            process.wait(timeout=1.0)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _run(
    args: list[str],
    timeout: float,
    *,
    input_bytes: bytes | None = None,
    mutating: bool = False,
    allow_nonzero: bool = False,
) -> bytes:
    """Run one bounded argv command while retaining only bounded stdout.

    Stderr is sent directly to ``/dev/null``.  Remote Compose commands also discard both streams
    before they reach SSH.  This makes accidental environment values in tool diagnostics
    unretained by Skynet.
    """

    stdout_pipe = subprocess.PIPE
    try:
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
            stdout=stdout_pipe,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        raise ActivationError("bounded subprocess unavailable", 3, ambiguous=mutating) from None

    chunks: list[bytes] = []
    retained = 0
    oversized = False
    stream_error: BaseException | None = None

    def drain() -> None:
        nonlocal retained, oversized, stream_error
        assert process.stdout is not None
        try:
            while True:
                chunk = process.stdout.read(8192)
                if not chunk:
                    break
                room = MAX_OUTPUT + 1 - retained
                if room > 0:
                    chunks.append(chunk[:room])
                    retained += min(len(chunk), room)
                if retained > MAX_OUTPUT or len(chunk) > room:
                    oversized = True
        except (OSError, ValueError) as error:
            stream_error = error

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    write_error: BaseException | None = None

    def feed() -> None:
        nonlocal write_error
        if input_bytes is None:
            return
        assert process.stdin is not None
        try:
            process.stdin.write(input_bytes)
        except BrokenPipeError:
            pass
        except (OSError, ValueError) as error:
            write_error = error
        finally:
            try:
                process.stdin.close()
            except (OSError, ValueError):
                pass

    writer = threading.Thread(target=feed, daemon=True) if input_bytes is not None else None
    if writer is not None:
        writer.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_process_group(process)
    reader.join(max(0.0, timeout))
    if writer is not None:
        writer.join(max(0.0, timeout))
    if reader.is_alive() or writer is not None and writer.is_alive():
        _kill_process_group(process)
        reader.join(1.0)
        if writer is not None:
            writer.join(1.0)
    try:
        if process.stdin is not None:
            process.stdin.close()
        if process.stdout is not None:
            process.stdout.close()
    except (OSError, ValueError):
        pass
    if timed_out or reader.is_alive() or writer is not None and writer.is_alive():
        raise ActivationError("subprocess timed out; activation outcome is unresolved", 3, ambiguous=mutating)
    if write_error is not None or stream_error is not None:
        raise ActivationError("subprocess stream failed", 3, ambiguous=mutating)
    if oversized:
        raise ActivationError("subprocess output exceeded bound", 3, ambiguous=mutating)
    if process.returncode != 0 and not allow_nonzero:
        raise ActivationError("remote Docker operation failed", 1, ambiguous=mutating)
    return b"".join(chunks)


def _ssh_args(host: str, timeout: float) -> list[str]:
    seconds = max(1, int(timeout))
    return [
        "ssh",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={seconds}",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=1",
        host,
        "bash",
        "-s",
    ]


def _remote(
    host: str,
    script: str,
    timeout: float,
    *,
    mutating: bool = False,
    operation_id: str | None = None,
) -> list[str]:
    try:
        raw = _run(
            _ssh_args(host, timeout),
            timeout + 5.0,
            input_bytes=script.encode("utf-8"),
            mutating=mutating,
            allow_nonzero=True,
        )
    except ActivationError as error:
        # The operation id is generated before a mutating SSH call.  Preserve it even when the
        # transport dies before the remote structured result can be returned; callers can then
        # inspect the corresponding lock and operation record without guessing which attempt ran.
        if mutating and operation_id is not None and error.operation_id is None:
            error.operation_id = operation_id
        raise
    try:
        return raw.decode("utf-8").splitlines()
    except UnicodeError:
        raise ActivationError("remote identity observation is malformed", 3, ambiguous=mutating) from None


def _interactive_remote(
    host: str,
    script: str,
    timeout: float,
    operation_id: str,
    gate: Callable[[], None],
) -> list[str]:
    """Hold the remote deployment lock while a local Arcane recheck gates Compose.

    The pre-lock script is sent first and waits after emitting ``READY``.  The local callback then
    performs the second read-only Arcane observation and sends only the fixed ``GO`` or ``ABORT``
    token followed by the post-gate mutation script.  No credential or observation body crosses
    this SSH stdin boundary.  The process group remains bounded and is killed on every transport/
    timeout path so an abandoned lock cannot overlap a later operation.
    """

    marker = "\n# P11_INTERACTIVE_POST\n"
    if script.count(marker) != 1:
        raise ActivationError("remote activation lock handshake is unavailable", 3, ambiguous=True, operation_id=operation_id)
    pre_script, post_script = script.split(marker, 1)
    pre_script += "\n"
    pre_bytes = pre_script.encode("utf-8")
    post_bytes = post_script.encode("utf-8")
    if len(pre_bytes) > MAX_OUTPUT or len(post_bytes) > MAX_OUTPUT or len(pre_bytes) + len(post_bytes) > MAX_OUTPUT:
        raise ActivationError("remote activation script exceeded its bound", 3, ambiguous=True, operation_id=operation_id)
    process: subprocess.Popen[bytes] | None = None
    output: list[str] = []
    output_bytes = 0
    output_overflow = False
    events: queue.Queue[tuple[str, str | None]] = queue.Queue()
    writer: threading.Thread | None = None
    writer_error: BaseException | None = None
    writer_done = threading.Event()

    try:
        process = subprocess.Popen(
            _ssh_args(host, timeout),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        raise ActivationError("bounded subprocess unavailable", 3, ambiguous=True, operation_id=operation_id) from None

    assert process.stdin is not None and process.stdout is not None
    stream = process.stdout

    def drain() -> None:
        nonlocal output_bytes, output_overflow
        pending = b""
        try:
            while True:
                # Buffered ``read(8192)`` can wait for a full buffer while the remote shell is
                # deliberately blocked after its short READY marker.  Read the pipe directly so
                # the lock handshake is liveness bounded by the marker, not EOF.
                chunk = os.read(stream.fileno(), 8192)
                if not chunk:
                    break
                pending += chunk
                if len(pending) > MAX_OUTPUT:
                    output_overflow = True
                    events.put(("overflow", None))
                    return
                while b"\n" in pending:
                    raw_line, pending = pending.split(b"\n", 1)
                    output_bytes += len(raw_line) + 1
                    if output_bytes > MAX_OUTPUT:
                        output_overflow = True
                        events.put(("overflow", None))
                        return
                    try:
                        line = raw_line.decode("utf-8")
                    except UnicodeDecodeError:
                        events.put(("malformed", None))
                        return
                    output.append(line.rstrip("\r"))
                    events.put(("line", line.rstrip("\r")))
            if pending:
                output_bytes += len(pending)
                if output_bytes > MAX_OUTPUT:
                    output_overflow = True
                    events.put(("overflow", None))
                else:
                    try:
                        line = pending.decode("utf-8")
                    except UnicodeDecodeError:
                        events.put(("malformed", None))
                    else:
                        output.append(line)
                        events.put(("line", line))
        except (OSError, ValueError):
            events.put(("stream-error", None))
        finally:
            events.put(("eof", None))

    def feed() -> None:
        nonlocal writer_error
        assert process is not None and process.stdin is not None
        try:
            process.stdin.write(pre_bytes)
            process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as error:
            writer_error = error
            events.put(("write-error", None))
        finally:
            writer_done.set()

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    writer = threading.Thread(target=feed, daemon=True)
    writer.start()
    try:
        deadline = time.monotonic() + timeout + 5.0
        ready = False
        while not ready:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_process_group(process)
                raise ActivationError("activation lock handshake timed out", 3, ambiguous=True, operation_id=operation_id)
            try:
                event, value = events.get(timeout=remaining)
            except queue.Empty:
                _kill_process_group(process)
                raise ActivationError("activation lock handshake timed out", 3, ambiguous=True, operation_id=operation_id) from None
            if event == "line" and value is not None:
                if value.startswith("READY|"):
                    parts = _safe_line(value.split("|"), minimum=3)
                    if len(parts) != 3 or parts[1] != operation_id:
                        _kill_process_group(process)
                        raise ActivationError("remote activation READY marker is malformed", 3, ambiguous=True, operation_id=operation_id)
                    ready = True
                    break
                if value.startswith(("FAILED|", "UNRESOLVED|", "LOCKED|", "SUCCESS|", "RECONCILED|")):
                    if process.stdin is not None:
                        process.stdin.close()
                    process.wait(timeout=max(0.1, remaining))
                    return list(output)
                _kill_process_group(process)
                raise ActivationError("remote activation lock handshake is malformed", 3, ambiguous=True, operation_id=operation_id)
            if event in {"overflow", "malformed", "stream-error", "write-error"}:
                _kill_process_group(process)
                raise ActivationError("remote activation lock handshake is malformed", 3, ambiguous=True, operation_id=operation_id)
            if event == "eof":
                raise ActivationError("remote activation lock handshake ended early", 3, ambiguous=True, operation_id=operation_id)

        if writer is not None and not writer_done.wait(timeout=1.0):
            _kill_process_group(process)
            raise ActivationError("activation lock handshake transport failed", 3, ambiguous=True, operation_id=operation_id)
        if writer_error is not None:
            _kill_process_group(process)
            raise ActivationError("activation lock handshake transport failed", 3, ambiguous=True, operation_id=operation_id)

        gate_error: ActivationError | None = None
        try:
            gate()
        except ActivationError as error:
            gate_error = error
        token = b"ABORT\n" if gate_error is not None else b"GO\n"
        try:
            # The remote shell has only received the prelude through its blocking ``read``.  Send
            # the fixed postlude for both GO and ABORT so the holder records the refusal and exits
            # while still owning the flock; returning the local guard reason before that marker is
            # observed would make lock release itself ambiguous.
            process.stdin.write(token + post_bytes)
            process.stdin.flush()
            process.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            _kill_process_group(process)
            if gate_error is not None:
                raise gate_error
            raise ActivationError("post-lock activation transport failed", 3, ambiguous=True, operation_id=operation_id) from None

        remaining = timeout + 5.0
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            _kill_process_group(process)
            raise ActivationError("post-GO activation outcome is unresolved", 3, ambiguous=True, operation_id=operation_id) from None
        reader.join(timeout=1.0)
        if reader.is_alive() or output_overflow:
            _kill_process_group(process)
            raise ActivationError("post-GO activation output is malformed", 3, ambiguous=True, operation_id=operation_id)
        if gate_error is not None:
            abort_markers = [
                line
                for line in output
                if line == f"FAILED|{operation_id}|post-lock-guard-refused"
            ]
            if len(abort_markers) != 1:
                raise ActivationError("post-lock guard outcome is unresolved", 3, ambiguous=True, operation_id=operation_id)
            if gate_error.operation_id is None:
                gate_error.operation_id = operation_id
            raise gate_error
        return list(output)
    finally:
        if process is not None and process.poll() is None:
            _kill_process_group(process)
        try:
            if process is not None and process.stdin is not None:
                process.stdin.close()
            if process is not None and process.stdout is not None:
                process.stdout.close()
        except (OSError, ValueError):
            pass
        reader.join(timeout=1.0)
        if writer is not None:
            writer.join(timeout=1.0)


def _safe_line(parts: list[str], *, minimum: int = 1) -> list[str]:
    if len(parts) < minimum or any(any(ord(c) < 32 or ord(c) == 127 for c in p) for p in parts):
        raise ActivationError("remote identity observation is malformed", 3)
    return parts


def _q(value: str) -> str:
    return shlex.quote(value)


def _common_script(service: str, state_root: str) -> str:
    """Return the fixed shell prelude shared by read and mutation operations."""

    return f"""set -u
umask 077
service={_q(service)}
state_root={_q(state_root)}
state="$state_root/{service}"
generations="$state/generations"
operations="$state/operations"
lock="$state/deploy.lock"
active_file="$state/active"
# stable/previous are one atomic metadata record.  The individual pointer names from the logical
# layout are deliberately not authoritative; keeping this pair together prevents status from
# observing a half-promoted stable transition.
stability_file="$state/stable-state.json"
latest_file="$state/latest-operation"
legacy_workdir=''
# A first-takeover caller may provide an independently derived old Compose service set.  It is
# comma-delimited only after strict validation by the Python boundary and is never treated as a
# count; runtime labels are still compared member-for-member below.
legacy_services=''

valid_revision() {{ [[ "$1" =~ ^[0-9a-f]{{40}}$ ]]; }}
valid_service() {{ [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; }}

ensure_state() {{
  if [ -L "$state_root" ] || [ -L "$state" ] || [ -L "$generations" ] || [ -L "$operations" ]; then
    return 64
  fi
  mkdir -p -- "$generations" "$operations" || return 64
  chmod 0700 "$state_root" "$state" "$generations" "$operations" || return 64
  if [ -e "$lock" ] && [ -L "$lock" ]; then return 64; fi
  if [ ! -e "$lock" ]; then : >"$lock" || return 64; fi
  chmod 0600 "$lock" || return 64
}}

read_pointer() {{
  local path="$1" value
  if [ ! -e "$path" ]; then printf ''; return 0; fi
  [ -f "$path" ] && [ ! -L "$path" ] || return 64
  value=$(<"$path") || return 64
  if [ -n "$value" ] && ! valid_revision "$value"; then return 64; fi
  printf '%s' "$value"
}}

read_stability() {{
  local raw fields stable_value previous_value extra
  stable=''
  previous=''
  if [ ! -e "$stability_file" ]; then return 0; fi
  [ -f "$stability_file" ] && [ ! -L "$stability_file" ] || return 64
  raw=$(<"$stability_file") || return 64
  fields=$(printf '%s\\n' "$raw" | sed -n 's/^{{"schema":1,"stable":\\([^,]*\\),"previous":\\([^}}]*\\)}}$/\\1|\\2/p') || return 64
  [ -n "$fields" ] || return 64
  IFS='|' read -r stable_value previous_value extra <<< "$fields"
  [ -z "$extra" ] || return 64
  stable=$(decode_pointer "$stable_value") || return 64
  previous=$(decode_pointer "$previous_value") || return 64
}}

decode_pointer() {{
  local raw="$1" value
  if [ "$raw" = null ]; then printf ''; return 0; fi
  value=$(printf '%s\\n' "$raw" | sed -n 's/^"\\([0-9a-f]*\\)"$/\\1/p') || return 64
  [ -n "$value" ] && valid_revision "$value" || return 64
  printf '%s' "$value"
}}

read_operation_pointer() {{
  local path="$1" value
  if [ ! -e "$path" ]; then printf ''; return 0; fi
  [ -f "$path" ] && [ ! -L "$path" ] || return 64
  value=$(<"$path") || return 64
  [[ "$value" =~ ^[0-9a-f]{{32}}$ ]] || return 64
  printf '%s' "$value"
}}

write_atomic() {{
  local path="$1" value="$2" tmp
  tmp=$(mktemp "$path.tmp.XXXXXX") || return 64
  trap 'rm -f -- "$tmp"' RETURN
  printf '%s\\n' "$value" >"$tmp" || return 64
  chmod 0600 "$tmp" || return 64
  mv -f -- "$tmp" "$path" || return 64
  trap - RETURN
}}

write_stability() {{
  local next_stable="$1" next_previous="$2" tmp
  if [ -n "$next_stable" ] && ! valid_revision "$next_stable"; then return 64; fi
  if [ -n "$next_previous" ] && ! valid_revision "$next_previous"; then return 64; fi
  tmp=$(mktemp "$stability_file.tmp.XXXXXX") || return 64
  trap 'rm -f -- "$tmp"' RETURN
  printf '{{"schema":1,"stable":%s,"previous":%s}}\\n' \\
    "$(json_nullable "$next_stable")" "$(json_nullable "$next_previous")" >"$tmp" || return 64
  chmod 0600 "$tmp" || return 64
  mv -f -- "$tmp" "$stability_file" || return 64
  trap - RETURN
}}

json_field() {{
  local path="$1" key="$2"
  [ -f "$path" ] && [ ! -L "$path" ] || return 64
  sed -n "s/.*\\\"$key\\\":\\\"\\([A-Za-z0-9_.:-]*\\)\\\".*/\\1/p" "$path" | head -n 1
}}

json_nullable() {{
  if [ -n "$1" ]; then printf '\"%s\"' "$1"; else printf 'null'; fi
}}

list_generations() {{
  local entry name
  local -a names=()
  [ -d "$generations" ] && [ ! -L "$generations" ] || return 64
  # Include dot entries so a malformed or abandoned hidden generation cannot be silently ignored.
  shopt -s nullglob dotglob
  for entry in "$generations"/*; do
    [ -L "$entry" ] && return 64
    [ -d "$entry" ] || return 64
    name="${{entry##*/}}"
    valid_revision "$name" || return 64
    names+=("$name")
    [ "${{#names[@]}}" -le {_MAX_GENERATIONS} ] || return 64
  done
  shopt -u nullglob dotglob
  if [ "${{#names[@]}}" -eq 0 ]; then
    printf ''
    return 0
  fi
  printf '%s\n' "${{names[@]}}" | LC_ALL=C sort | paste -sd, -
}}

runtime_probe() {{
  local ids rows line cid project work config compose_service state_value
  local first_rev='' first_work='' first_kind='' count=0 same=1 bad=0 stopped=0 duplicate=0
  local expected_services expected_service expected_count=0
  declare -A observed_services=()
  ids=$(docker ps -aq --filter "label=com.docker.compose.project=$service" 2>/dev/null) || {{
    printf 'RUNTIME|unavailable||0'
    return 0
  }}
  if [ -z "$ids" ]; then printf 'RUNTIME|none||0'; return 0; fi
  for cid in $ids; do
    [[ "$cid" =~ ^[0-9a-f]{{12,64}}$ ]] || {{ printf 'RUNTIME|unavailable||0'; return 0; }}
  done
  # Go templates emit a literal backslash-t for \\t here on the target Docker CLI.  A fixed
  # non-whitespace delimiter keeps the parser deterministic; a delimiter inside a label leaves
  # an invalid final field and therefore fails closed as partial runtime evidence.
  rows=$(docker inspect --format '{{{{.Id}}}}|{{{{index .Config.Labels "com.docker.compose.project"}}}}|{{{{index .Config.Labels "com.docker.compose.project.working_dir"}}}}|{{{{index .Config.Labels "com.docker.compose.project.config_files"}}}}|{{{{index .Config.Labels "com.docker.compose.service"}}}}|{{{{.State.Status}}}}' $ids 2>/dev/null) || {{
    printf 'RUNTIME|unavailable||0'
    return 0
  }}
  while IFS='|' read -r cid project work config compose_service state_value; do
    [ -n "$cid" ] || {{ bad=1; continue; }}
    count=$((count + 1))
    if ! [[ "$cid" =~ ^[0-9a-f]{{12,64}}$ ]] || [ "$project" != "$service" ] ||
       [ -z "$work" ] || [ "$config" != "$work/compose.yaml" ] ||
       ! valid_service "$compose_service" || [ "$state_value" != 'running' ]; then
      bad=1
      [ "$state_value" != 'running' ] && stopped=1
      continue
    fi
    if [ -n "${{observed_services[$compose_service]+x}}" ]; then duplicate=1; fi
    observed_services[$compose_service]=1
    case "$work" in
      "$generations"/*)
        rev="${{work#"$generations"/}}"
        if ! valid_revision "$rev"; then bad=1; continue; fi
        if [ -z "$first_kind" ]; then first_kind=gen; first_rev="$rev"; first_work="$work";
        elif [ "$first_kind" != gen ] || [ "$first_rev" != "$rev" ]; then same=0; fi
        ;;
      /*)
        if [[ "$work" == *'..'* ]] || [ -n "$legacy_workdir" ] && [ "$work" != "$legacy_workdir" ]; then
          bad=1; continue
        fi
        if [ -z "$first_kind" ]; then first_kind=legacy; first_work="$work";
        elif [ "$first_kind" != legacy ] || [ "$first_work" != "$work" ]; then same=0; fi
        ;;
      *) bad=1; continue;;
    esac
  done <<< "$rows"
  if [ "$count" -eq 0 ]; then printf 'RUNTIME|none||0'; return 0; fi
  if [ "$same" -ne 1 ]; then printf 'RUNTIME|mixed||%s' "$count"; return 0; fi
  if [ "$first_kind" = legacy ]; then
    if [ "$bad" -ne 0 ] || [ "$stopped" -ne 0 ] || [ "$duplicate" -ne 0 ]; then
      printf 'RUNTIME|partial||%s' "$count"
      return 0
    fi
    if [ -n "$legacy_services" ]; then
      expected_services=$(printf '%s' "$legacy_services" | tr ',' '\\n') || {{ printf 'RUNTIME|legacy-unknown||%s' "$count"; return 0; }}
    else
      expected_services=$(cd "$first_work" && docker compose -p "$service" -f compose.yaml config --services 2>/dev/null) || {{ printf 'RUNTIME|legacy-unknown||%s' "$count"; return 0; }}
    fi
    expected_count=0
    declare -A expected_legacy_seen=()
    while IFS= read -r expected_service; do
      valid_service "$expected_service" || {{ printf 'RUNTIME|partial||%s' "$count"; return 0; }}
      [ -z "${{expected_legacy_seen[$expected_service]+x}}" ] || {{ printf 'RUNTIME|partial||%s' "$count"; return 0; }}
      expected_legacy_seen[$expected_service]=1
      expected_count=$((expected_count + 1))
      [ "$expected_count" -le {_MAX_SERVICES} ] || {{ printf 'RUNTIME|partial||%s' "$count"; return 0; }}
    done <<< "$expected_services"
    if [ "$expected_count" -eq 0 ] || [ "$expected_count" -ne "$count" ]; then
      printf 'RUNTIME|partial||%s' "$count"
      return 0
    fi
    for expected_service in "${{!expected_legacy_seen[@]}}"; do
      [ -n "${{observed_services[$expected_service]+x}}" ] || {{ printf 'RUNTIME|partial||%s' "$count"; return 0; }}
    done
    printf 'RUNTIME|legacy||%s' "$count"
    return 0
  fi
  if [ "$bad" -ne 0 ]; then
    if [ "$stopped" -ne 0 ]; then printf 'RUNTIME|stopped|%s|%s' "$first_rev" "$count";
    else printf 'RUNTIME|partial|%s|%s' "$first_rev" "$count"; fi
    return 0
  fi
  if [ ! -d "$generations/$first_rev" ] || [ -L "$generations/$first_rev" ]; then
    printf 'RUNTIME|orphan|%s|%s' "$first_rev" "$count"
    return 0
  fi
  expected_services=$(cd "$generations/$first_rev" && docker compose -p "$service" -f compose.yaml config --services 2>/dev/null) || {{ printf 'RUNTIME|partial|%s|%s' "$first_rev" "$count"; return 0; }}
  expected_count=0
  declare -A expected_services_seen=()
  while IFS= read -r expected_service; do
    valid_service "$expected_service" || {{ printf 'RUNTIME|partial|%s|%s' "$first_rev" "$count"; return 0; }}
    [ -z "${{expected_services_seen[$expected_service]+x}}" ] || {{ printf 'RUNTIME|partial|%s|%s' "$first_rev" "$count"; return 0; }}
    expected_services_seen[$expected_service]=1
    expected_count=$((expected_count + 1))
    [ "$expected_count" -le {_MAX_SERVICES} ] || {{ printf 'RUNTIME|partial|%s|%s' "$first_rev" "$count"; return 0; }}
  done <<< "$expected_services"
  if [ "$expected_count" -eq 0 ] || [ "$expected_count" -ne "$count" ] || [ "$duplicate" -ne 0 ]; then
    printf 'RUNTIME|partial|%s|%s' "$first_rev" "$count"
    return 0
  fi
  for expected_service in "${{!expected_services_seen[@]}}"; do
    [ -n "${{observed_services[$expected_service]+x}}" ] || {{ printf 'RUNTIME|partial|%s|%s' "$first_rev" "$count"; return 0; }}
  done
  printf 'RUNTIME|complete|%s|%s' "$first_rev" "$count"
}}
"""


def _parse_runtime(line: str) -> RuntimeObservation:
    parts = _safe_line(line.split("|"), minimum=4)
    if parts[0] != "RUNTIME" or parts[1] not in _RUNTIME_CLASS:
        raise ActivationError("remote runtime observation is malformed", 3)
    classification = parts[1]
    generation = parts[2] or None
    count = parts[3]
    if generation is not None and not _REVISION.fullmatch(generation):
        raise ActivationError("remote runtime generation identity is malformed", 3)
    if not count.isdigit() or int(count) < 0 or int(count) > _MAX_SERVICES:
        raise ActivationError("remote runtime count is malformed", 3)
    if classification == "none" and (generation is not None or count != "0"):
        raise ActivationError("remote runtime observation is malformed", 3)
    return RuntimeObservation(classification, generation, int(count))


def _runtime_from_lines(lines: list[str]) -> RuntimeObservation:
    observations = [_parse_runtime(line) for line in lines if line.startswith("RUNTIME|")]
    if len(observations) != 1:
        raise ActivationError("remote runtime observation is missing or ambiguous", 3)
    return observations[0]


def _new_operation() -> str:
    return uuid.uuid4().hex


def _state_script(service: str, state_root: str) -> str:
    return (
        _common_script(service, state_root)
        + r'''
if [ ! -d "$state" ] || [ -L "$state" ]; then
  printf 'STATE|no-state||||free||||\n'
  runtime_probe
  exit 0
fi
if [ -e "$lock" ] && [ -L "$lock" ]; then exit 64; fi
lock_state=free
if [ -e "$lock" ]; then
  exec 9<"$lock" || exit 64
  if ! flock -n 9; then lock_state=held; fi
  exec 9>&-
fi
active=$(read_pointer "$active_file") || exit 64
read_stability || exit 64
op_id=''
op_state=''
requested=''
if [ -e "$latest_file" ]; then
  op_id=$(read_operation_pointer "$latest_file") || exit 64
  if ! [[ "$op_id" =~ ^[0-9a-f]{32}$ ]]; then exit 64; fi
  op_path="$operations/$op_id.json"
  op_state=$(json_field "$op_path" state) || exit 64
  requested=$(json_field "$op_path" requested_generation) || true
fi
printf 'STATE|%s|%s|%s|%s|%s|%s|%s|%s|\n' "$service" "${active:-}" "${stable:-}" "${previous:-}" "$lock_state" "$op_id" "$op_state" "$requested"
prepared=$(list_generations) || exit 64
printf 'GENERATIONS|%s\n' "$prepared"
runtime_probe
'''
    )


def _status_snapshot(
    service: str,
    *,
    host: str,
    state_root: str,
    timeout: float,
) -> dict[str, Any]:
    lines = _remote(host, _state_script(service, state_root), timeout)
    state_lines = [line for line in lines if line.startswith("STATE|")]
    if len(state_lines) != 1:
        raise ActivationError("remote deployment state observation is missing or ambiguous", 3)
    parts = _safe_line(state_lines[0].split("|"), minimum=10)
    if parts[0] != "STATE" or parts[1] not in {"no-state", service}:
        raise ActivationError("remote deployment state observation is malformed", 3)
    runtime = _runtime_from_lines(lines)
    if parts[1] == "no-state":
        return {
            "schema": 1,
            "service": service,
            "host": host,
            "state_root": state_root,
            "initialized": False,
            "active": None,
            "stable": None,
            "previous": None,
            "prepared": [],
            "lock": "free",
            "operation": None,
            "runtime": runtime.value(),
        }
    fields = parts[2:10]
    active, stable, previous, lock_state, op_id, op_state, requested, _ = fields
    for value in (active, stable, previous, requested):
        if value and not _REVISION.fullmatch(value):
            raise ActivationError("remote deployment pointer is malformed", 3)
    if lock_state not in {"free", "held"} or (op_id and not _OPERATION.fullmatch(op_id)):
        raise ActivationError("remote deployment operation identity is malformed", 3)
    if op_state and not _STATE.fullmatch(op_state):
        raise ActivationError("remote deployment operation state is malformed", 3)
    generation_lines = [line for line in lines if line.startswith("GENERATIONS|")]
    if len(generation_lines) != 1:
        raise ActivationError("remote generation inventory is missing or ambiguous", 3)
    generation_parts = _safe_line(generation_lines[0].split("|"), minimum=2)
    if len(generation_parts) != 2:
        raise ActivationError("remote generation inventory is malformed", 3)
    prepared = [] if not generation_parts[1] else generation_parts[1].split(",")
    if len(prepared) > _MAX_GENERATIONS or any(not _REVISION.fullmatch(value) for value in prepared):
        raise ActivationError("remote generation inventory is malformed", 3)
    if prepared != sorted(set(prepared)):
        raise ActivationError("remote generation inventory is malformed", 3)
    return {
        "schema": 1,
        "service": service,
        "host": host,
        "state_root": state_root,
        "initialized": True,
        "active": active or None,
        "stable": stable or None,
        "previous": previous or None,
        "prepared": prepared,
        "lock": lock_state,
        "operation": (
            {"id": op_id, "state": op_state or None, "requested_generation": requested or None}
            if op_id
            else None
        ),
        "runtime": runtime.value(),
    }


def status(
    service: str,
    *,
    host: str = DEFAULT_HOST,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Return report-only filesystem and Docker state for one service."""

    service = _validate_service(service)
    host = _validate_host(host)
    state = _validate_state_root(state_root)
    timeout = _validate_timeout(timeout)
    return _status_snapshot(service, host=host, state_root=state, timeout=timeout)


def _credentials(path: Path, environment_id: str | None) -> ArcaneCredentials:
    assignment = re.compile(
        r"\s*(ARCANE_URL|ARCANE_TOKEN|ARCANE_ENV_ID|ARCANE_AUTH_HEADER)=(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"]+))\s*(?:#.*)?\Z"
    )
    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        raise ActivationError("Arcane credentials unavailable", 3) from None
    values: dict[str, str] = {}
    for line in contents.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = assignment.fullmatch(line)
        if match is None:
            raise ActivationError("invalid Arcane credential assignments", 3)
        key = match[1]
        value = next(part for part in match.groups()[1:] if part is not None)
        if key in values or not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ActivationError("invalid Arcane credential assignments", 3)
        values[key] = value
    if not {"ARCANE_URL", "ARCANE_TOKEN"} <= values.keys():
        raise ActivationError("required Arcane credentials missing", 3)
    if values.get("ARCANE_AUTH_HEADER", "X-API-Key") != "X-API-Key":
        raise ActivationError("invalid Arcane auth header", 3)
    try:
        parsed = urllib.parse.urlsplit(values["ARCANE_URL"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError
        if parsed.username is not None or parsed.password is not None or not parsed.hostname:
            raise ValueError
    except ValueError:
        raise ActivationError("invalid Arcane URL", 3) from None
    selected = environment_id if environment_id is not None else values.get("ARCANE_ENV_ID", DEFAULT_ENVIRONMENT_ID)
    if not isinstance(selected, str) or not _SAFE_ID.fullmatch(selected):
        raise ActivationError("invalid Arcane environment id", 3)
    try:
        parsed_url = parsed.geturl().rstrip("/")
    except ValueError:
        raise ActivationError("invalid Arcane URL", 3) from None
    return ArcaneCredentials(parsed_url, values["ARCANE_TOKEN"], selected)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
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


def _arcane_get(credentials: ArcaneCredentials, path: str, timeout: float) -> Any:
    try:
        context = ssl.create_default_context()
        opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=context))
        request = urllib.request.Request(
            credentials.url + "/api" + path,
            headers={"X-API-Key": credentials.token, "Accept": "application/json"},
            method="GET",
        )
        with opener.open(request, timeout=timeout) as response:
            status_code = getattr(response, "status", response.getcode())
            raw = response.read(MAX_ARCANE_RESPONSE + 1)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, http.client.HTTPException,
            TimeoutError, ssl.SSLError, UnicodeError, ValueError):
        raise ActivationError("Arcane read-only observation unavailable", 3) from None
    if status_code != 200 or len(raw) > MAX_ARCANE_RESPONSE:
        raise ActivationError("Arcane read-only observation unavailable", 3)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise ActivationError("malformed Arcane read-only observation", 3) from None
    if not isinstance(payload, dict) or payload.get("success") is not True or "data" not in payload:
        raise ActivationError("malformed Arcane read-only observation", 3)
    return payload["data"]


def observe_arcane(
    service: str,
    *,
    credentials_file: Path = DEFAULT_ARCANE_CREDENTIALS,
    environment_id: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> ArcaneObservation:
    """Inspect Arcane Git Sync metadata with GET requests only.

    The function intentionally has no write/redeploy method.  A missing sync is represented as
    an explicit observation and is accepted only when a caller supplies matching migration
    evidence to :func:`guard_arcane`.
    """

    service = _validate_service(service)
    timeout = _validate_timeout(timeout)
    credentials = _credentials(credentials_file, environment_id)
    path = f"/environments/{urllib.parse.quote(credentials.environment_id, safe='')}/gitops-syncs"
    data = _arcane_get(credentials, path, timeout)
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise ActivationError("malformed Arcane Git Sync observation", 3)
    candidates = [item for item in data if item.get("name") == service or item.get("projectName") == service]
    if len(candidates) > 1:
        raise ActivationError("Arcane Git Sync identity is ambiguous", 1)
    if not candidates:
        return ArcaneObservation(service, False)
    sync = candidates[0]
    auto_sync = sync.get("autoSync")
    if type(auto_sync) is not bool:
        raise ActivationError("malformed Arcane Git Sync controls", 3)
    sync_id = sync.get("id")
    project_id = sync.get("projectId")
    if not isinstance(sync_id, str) or not _SAFE_ID.fullmatch(sync_id):
        raise ActivationError("malformed Arcane Git Sync identity", 3)
    if project_id is not None and (not isinstance(project_id, str) or not _SAFE_ID.fullmatch(project_id)):
        raise ActivationError("malformed Arcane project identity", 3)
    last_revision = sync.get("lastSyncCommit")
    if last_revision is not None and (not isinstance(last_revision, str) or not _REVISION.fullmatch(last_revision)):
        raise ActivationError("malformed Arcane Git Sync revision", 3)
    project_revision: str | None = None
    project_status: str | None = None
    if project_id is not None:
        project_path = (
            f"/environments/{urllib.parse.quote(credentials.environment_id, safe='')}/projects/"
            f"{urllib.parse.quote(project_id, safe='')}"
        )
        project = _arcane_get(credentials, project_path, timeout)
        if not isinstance(project, dict):
            raise ActivationError("malformed Arcane project observation", 3)
        raw_revision = project.get("lastSyncCommit")
        if raw_revision is not None and (not isinstance(raw_revision, str) or not _REVISION.fullmatch(raw_revision)):
            raise ActivationError("malformed Arcane project revision", 3)
        project_revision = raw_revision
        raw_status = project.get("status")
        if raw_status is not None and not isinstance(raw_status, str):
            raise ActivationError("malformed Arcane project status", 3)
        project_status = raw_status
    return ArcaneObservation(
        service,
        True,
        auto_sync,
        sync_id,
        project_id,
        last_revision.lower() if last_revision else None,
        project_revision.lower() if project_revision else None,
        project_status,
    )


def _normalize_arcane(source: ArcaneSource, service: str) -> ArcaneObservation:
    value: ArcaneObservation | Mapping[str, Any]
    if callable(source):
        value = source()
    else:
        value = source
    if isinstance(value, ArcaneObservation):
        observation = value
    elif isinstance(value, Mapping):
        raw_present = value.get("present", value.get("sync_present", True))
        raw_auto = value.get("auto_sync", value.get("autoSync"))
        if type(raw_present) is not bool or type(raw_auto) is not bool:
            raise ActivationError("Arcane migration evidence is malformed", 3)
        def optional_id(name: str) -> str | None:
            raw = value.get(name)
            if raw is None:
                return None
            if not isinstance(raw, str) or not _SAFE_ID.fullmatch(raw):
                raise ActivationError("Arcane migration evidence is malformed", 3)
            return raw
        def optional_revision(*names: str) -> str | None:
            for name in names:
                raw = value.get(name)
                if raw is not None:
                    if not isinstance(raw, str) or not _REVISION.fullmatch(raw):
                        raise ActivationError("Arcane migration evidence is malformed", 3)
                    return raw.lower()
            return None
        raw_status = value.get("project_status")
        if raw_status is not None and not isinstance(raw_status, str):
            raise ActivationError("Arcane migration evidence is malformed", 3)
        observation = ArcaneObservation(
            service,
            raw_present,
            raw_auto,
            optional_id("sync_id"),
            optional_id("project_id"),
            optional_revision("last_revision", "lastSyncCommit"),
            optional_revision("project_revision", "projectRevision"),
            raw_status,
        )
    else:
        raise ActivationError("Arcane migration evidence is malformed", 3)
    if observation.service != service:
        raise ActivationError("Arcane service identity mismatch", 2)
    return observation


def _evidence_bool(evidence: MigrationEvidence, *names: str) -> bool:
    values = [evidence[name] for name in names if name in evidence]
    return bool(values) and all(type(value) is bool and value for value in values)


def guard_arcane(
    service: str,
    source: ArcaneSource,
    *,
    first_takeover: bool,
    migration_evidence: MigrationEvidence | None = None,
) -> ArcaneObservation:
    """Fail closed on an Arcane auto-sync writer and enforce takeover evidence.

    ``migration_evidence`` is deliberately caller supplied.  Arcane's read API exposes the
    control and last completed revision, but not a proof that a disabled scheduled sync has been
    drained for the deployed interval.  First takeover therefore requires explicit evidence of
    disabled scheduling, drain completion, and the old running revision.
    """

    service = _validate_service(service)
    observation = _normalize_arcane(source, service)
    # An enabled auto-sync flag is a dual-writer signal even if a caller's observation omitted or
    # lost the corresponding sync object.  Treat that combination as unsafe rather than allowing
    # a malformed ``present=false, auto_sync=true`` snapshot through the write gate.
    if observation.auto_sync:
        raise ActivationError("Arcane automatic sync is enabled; direct activation refused", 1)
    if not first_takeover:
        return observation
    # A brand-new service with no Arcane sync and no existing project has nothing to drain.  Keep
    # that path usable; if an operator supplies evidence anyway, validate its optional facts but do
    # not manufacture an old-runtime requirement.  Any legacy project discovered under the lock
    # is still refused because it has no expected takeover path/evidence.
    if not observation.present and migration_evidence is None:
        return observation
    if migration_evidence is None or not isinstance(migration_evidence, Mapping):
        raise ActivationError("first takeover requires Arcane disable-and-drain evidence", 1)
    evidence_present = migration_evidence.get("sync_present", migration_evidence.get("present", observation.present))
    if type(evidence_present) is not bool or evidence_present != observation.present:
        raise ActivationError("Arcane takeover evidence does not match observed sync presence", 1)
    if not observation.present:
        for names, reason in (
            (("auto_sync_disabled", "autoSyncDisabled"), "auto-sync-disabled"),
            (("drained", "sync_drained"), "sync-drained"),
        ):
            if any(name in migration_evidence for name in names) and not _evidence_bool(migration_evidence, *names):
                raise ActivationError(f"first takeover evidence contradicts {reason}", 1)
        if "old_services" in migration_evidence:
            _validate_service_set(migration_evidence.get("old_services"), label="old Compose service set")
        for name in ("old_revision", "running_revision"):
            if name in migration_evidence:
                value = migration_evidence[name]
                if not isinstance(value, str) or not _REVISION.fullmatch(value):
                    raise ActivationError("malformed first-takeover revision evidence", 2)
        return observation
    if not _evidence_bool(migration_evidence, "auto_sync_disabled", "autoSyncDisabled"):
        raise ActivationError("first takeover lacks proof that Arcane auto-sync is disabled", 1)
    if not _evidence_bool(migration_evidence, "drained", "sync_drained"):
        raise ActivationError("first takeover lacks proof that Arcane sync is drained", 1)
    # A legacy Compose directory may be unreadable to svc-ops even though Docker exposes its
    # labels.  The migration proof must therefore carry the complete old service set derived by
    # the caller from the exact old revision.  Runtime labels are compared against every member
    # under the deployment lock; a count alone is never sufficient.
    _validate_service_set(migration_evidence.get("old_services"), label="old Compose service set")
    old_revision = migration_evidence.get("old_revision", migration_evidence.get("running_revision"))
    if observation.present:
        if not isinstance(old_revision, str) or not _REVISION.fullmatch(old_revision):
            raise ActivationError("first takeover lacks the old running revision", 1)
        old_revision = old_revision.lower()
        if not _evidence_bool(migration_evidence, "old_runtime_verified", "runtime_verified"):
            raise ActivationError("first takeover lacks independent old-runtime verification", 1)
        legacy_workdir = migration_evidence.get("legacy_working_dir")
        expected_legacy = f"/opt/docker/arcane-projects/{service}"
        if not isinstance(legacy_workdir, str) or legacy_workdir != expected_legacy:
            raise ActivationError("first takeover lacks the expected legacy Compose path", 1)
        for observed in (observation.last_revision, observation.project_revision):
            if observed is not None and observed.lower() != old_revision:
                raise ActivationError("Arcane takeover revision evidence does not match", 1)
    elif old_revision is not None and (not isinstance(old_revision, str) or not _REVISION.fullmatch(old_revision)):
        raise ActivationError("malformed first-takeover revision evidence", 2)
    return observation


def _generation_script(
    service: str,
    state_root: str,
    operation_id: str,
    generation: str,
    *,
    legacy_workdir: str | None = None,
    legacy_services: Sequence[str] | None = None,
    await_gate: bool = False,
) -> str:
    legacy_assignment = _q(legacy_workdir) if legacy_workdir is not None else "''"
    legacy_service_values = _validate_service_set(legacy_services) if legacy_services is not None else ()
    legacy_services_assignment = _q(",".join(legacy_service_values)) if legacy_service_values else "''"
    gate_block = ""
    if await_gate:
        gate_block = """
	printf 'READY|%s|%s\\n' "$operation_id" "$requested_generation"
IFS= read -r gate
# P11_INTERACTIVE_POST
if [ "$gate" != GO ]; then
  write_record 'activation-refused' '["lock-acquired","generation-validated","runtime-inspected","ready-emitted","post-lock-guard-refused"]' 'not-run' 'post-lock-guard-refused' 'post-lock-guard-aborted' || true
  printf 'FAILED|%s|post-lock-guard-refused' "$operation_id"
  exit 1
fi
"""
    return (
        _common_script(service, state_root)
        + f"""
operation_id={_q(operation_id)}
requested_generation={_q(generation)}
generation_path="$generations/{generation}"
legacy_workdir={legacy_assignment}
legacy_services={legacy_services_assignment}
started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

write_record() {{
  local record_state="$1" steps="$2" verification="$3" recovery="$4" reason="$5" now tmp
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ) || return 64
  tmp=$(mktemp "$operations/.$operation_id.XXXXXX") || return 64
  printf '{{"schema":1,"operation_id":"%s","service":"%s","requested_generation":"%s","requested_revision":"%s","previous_active":%s,"previous_stable":%s,"state":"%s","completed_steps":%s,"verification":"%s","recovery":"%s","reason":"%s","started_at":"%s","updated_at":"%s"}}\\n' \\
    "$operation_id" "$service" "$requested_generation" "$requested_generation" \\
    "$(json_nullable "$prior_active")" "$(json_nullable "$prior_stable")" \\
    "$record_state" "$steps" "$verification" "$recovery" "$reason" "$started_at" "$now" >"$tmp" || return 64
  chmod 0600 "$tmp" || return 64
  mv -f -- "$tmp" "$operations/$operation_id.json" || return 64
  write_atomic "$latest_file" "$operation_id" || return 64
}}

validate_generation() {{
  local mode services line count=0
  [ -d "$generation_path" ] && [ ! -L "$generation_path" ] || return 65
  [ -f "$generation_path/compose.yaml" ] && [ ! -L "$generation_path/compose.yaml" ] || return 65
  [ -f "$generation_path/.env" ] && [ ! -L "$generation_path/.env" ] || return 65
  [ -f "$generation_path/release.json" ] && [ ! -L "$generation_path/release.json" ] || return 65
  mode=$(stat -c %a -- "$generation_path/.env" 2>/dev/null) || return 65
  [ "$mode" = 600 ] || return 65
  services=$(cd "$generation_path" && docker compose -p "$service" -f compose.yaml config --services 2>/dev/null) || return 66
  [ -n "$services" ] || return 66
  declare -A seen=()
  while IFS= read -r line; do
    valid_service "$line" || return 66
    [ -z "${{seen[$line]+x}}" ] || return 66
    seen[$line]=1
    count=$((count + 1))
    [ "$count" -le {_MAX_SERVICES} ] || return 66
  done <<< "$services"
  [ "$count" -gt 0 ] || return 66
  printf 'COMPOSE|%s' "$count"
}}

if ! ensure_state; then printf 'FAILED|%s|state-path-unavailable' "$operation_id"; exit 1; fi
exec 9>"$lock" || {{ printf 'FAILED|%s|lock-unavailable' "$operation_id"; exit 1; }}
if ! flock -n 9; then printf 'LOCKED|%s' "$operation_id"; exit 75; fi

prior_active=$(read_pointer "$active_file") || {{ printf 'FAILED|%s|state-pointer-malformed' "$operation_id"; exit 1; }}
read_stability || {{ printf 'FAILED|%s|state-pointer-malformed' "$operation_id"; exit 1; }}
prior_stable="$stable"
prior_previous="$previous"
prior_operation=''
prior_state=''
prior_requested=''
if [ -e "$latest_file" ]; then
  prior_operation=$(read_operation_pointer "$latest_file") || {{ printf 'FAILED|%s|operation-pointer-malformed' "$operation_id"; exit 1; }}
  if ! [[ "$prior_operation" =~ ^[0-9a-f]{{32}}$ ]]; then printf 'FAILED|%s|operation-pointer-malformed' "$operation_id"; exit 1; fi
  prior_path="$operations/$prior_operation.json"
  prior_state=$(json_field "$prior_path" state) || {{ printf 'FAILED|%s|operation-record-malformed' "$operation_id"; exit 1; }}
  prior_requested=$(json_field "$prior_path" requested_generation) || true
fi
prior_unresolved=0
case "$prior_state" in activation-in-progress|unresolved|recovery-required) prior_unresolved=1;; esac

# A known but unverified candidate owns the project until the verifier records a result.  Do not
# silently replace it with a different candidate and lose the only explicit rollback identity.
if [ -n "$prior_active" ] && [ "$prior_active" != "$prior_stable" ] &&
   [ "$prior_state" = activated-unverified ] && [ "$prior_active" != "$requested_generation" ]; then
  write_record 'recovery-required' '["lock-acquired","runtime-inspected"]' 'not-run' 'different-generation-refused' 'candidate-verification-pending' || true
  printf 'UNRESOLVED|%s|candidate-verification-pending' "$operation_id"
  exit 3
fi

if ! validate_generation >/dev/null; then
  write_record 'validation-failed' '[]' 'not-run' 'no-runtime-mutation' 'generation-invalid' || true
  printf 'FAILED|%s|generation-invalid' "$operation_id"
  exit 1
fi
write_record 'activation-in-progress' '["lock-acquired","generation-validated","runtime-inspected"]' 'not-run' 'not-needed' 'none' || {{ printf 'FAILED|%s|operation-record-failed' "$operation_id"; exit 1; }}
runtime_line=$(runtime_probe)
IFS='|' read -r runtime_tag runtime_class runtime_generation runtime_count <<< "$runtime_line"
if [ "$runtime_tag" != RUNTIME ]; then
  write_record 'recovery-required' '["lock-acquired","generation-validated"]' 'not-run' 'runtime-observation-failed' 'runtime-observation-invalid' || true
  printf 'UNRESOLVED|%s|runtime-observation-invalid' "$operation_id"
  exit 3
fi

# A first takeover is allowed to replace the old Arcane project only while the independently
# observed legacy project is still one complete, running Compose application at the expected path.
# If the drained old project disappeared or became mixed after evidence was collected, refuse the
# write and require fresh migration/reconciliation evidence.
if [ -n "$legacy_workdir" ] && [ "$runtime_class" != legacy ]; then
  write_record 'recovery-required' '["lock-acquired","generation-validated","runtime-inspected"]' 'not-run' 'legacy-takeover-required' 'legacy-runtime-not-coherent' || true
  printf 'UNRESOLVED|%s|legacy-runtime-not-coherent' "$operation_id"
  exit 3
fi

if [ "$prior_unresolved" -eq 1 ]; then
  if [ "$prior_requested" != "$requested_generation" ]; then
    if [ "$runtime_class" != complete ] || [ -z "$prior_stable" ] ||
       [ "$runtime_generation" != "$prior_stable" ]; then
      write_record 'recovery-required' '["lock-acquired","runtime-inspected"]' 'not-run' 'different-generation-refused' 'prior-operation-unresolved' || true
      printf 'UNRESOLVED|%s|prior-operation-unresolved' "$operation_id"
      exit 3
    fi
    # Docker proves that the old stable generation remained untouched, but this invocation must
    # still stop.  Mark the ambiguity reconciled and require a later invocation before admitting a
    # different candidate; replacing it in this same shell would erase the timeout boundary.
    write_atomic "$active_file" "$prior_stable" || {{ printf 'FAILED|%s|active-pointer-write-failed' "$operation_id"; exit 1; }}
    write_record 'prior-reconciled' '["lock-acquired","runtime-inspected","prior-stable-reconciled"]' 'not-run' 'prior-stable-untouched' 'prior-operation-reconciled' || true
    printf 'UNRESOLVED|%s|prior-operation-reconciled' "$operation_id"
    exit 3
  fi
fi

case "$runtime_class" in
  legacy)
    if [ -z "$legacy_workdir" ]; then
      write_record 'recovery-required' '["lock-acquired","generation-validated","runtime-inspected"]' 'not-run' 'legacy-takeover-evidence-required' 'legacy-runtime-not-adopted' || true
      printf 'UNRESOLVED|%s|legacy-runtime-not-adopted' "$operation_id"
      exit 3
    fi
    ;;
  legacy-unknown)
    write_record 'recovery-required' '["lock-acquired","generation-validated","runtime-inspected"]' 'not-run' 'legacy-service-set-unavailable' 'legacy-runtime-service-set-unavailable' || true
    printf 'UNRESOLVED|%s|legacy-runtime-service-set-unavailable' "$operation_id"
    exit 3
    ;;
  mixed|partial|stopped|orphan)
    if [ "$prior_requested" != "$requested_generation" ] && [ "$prior_active" != "$requested_generation" ]; then
      write_record 'recovery-required' '["lock-acquired","runtime-inspected"]' 'not-run' 'runtime-recovery-required' 'mixed-or-partial-runtime' || true
      printf 'UNRESOLVED|%s|mixed-or-partial-runtime' "$operation_id"
      exit 3
    fi
    ;;
  unavailable)
    write_record 'recovery-required' '["lock-acquired"]' 'not-run' 'runtime-observation-unavailable' 'docker-observation-unavailable' || true
    printf 'UNRESOLVED|%s|docker-observation-unavailable' "$operation_id"
    exit 3
    ;;
esac

# A candidate that can return success, including a same-generation reconciliation, must pass the
# second Arcane observation while this lock is still held.  The interactive caller places this
# marker immediately after the blocking read; the no-handshake helper used by disposable shell
# probes leaves it empty.
{gate_block}

if [ "$prior_unresolved" -eq 1 ] && [ "$prior_requested" = "$requested_generation" ] &&
   [ "$runtime_class" = complete ] && [ "$runtime_generation" = "$requested_generation" ]; then
  write_atomic "$active_file" "$requested_generation" || {{ printf 'FAILED|%s|active-pointer-write-failed' "$operation_id"; exit 1; }}
  write_record 'activated-unverified' '["lock-acquired","runtime-reconciled","same-generation-converged"]' 'not-run' 'same-generation-reconciled' 'none' || true
  printf 'RECONCILED|%s|%s|%s|%s|%s' "$operation_id" "$requested_generation" "$requested_generation" "${{prior_stable:-}}" "${{prior_previous:-}}"
  exit 0
fi

if [ "$runtime_class" = complete ] && [ "$runtime_generation" = "$requested_generation" ]; then
  write_atomic "$active_file" "$requested_generation" || {{ printf 'FAILED|%s|active-pointer-write-failed' "$operation_id"; exit 1; }}
  write_record 'activated-unverified' '["lock-acquired","generation-validated","runtime-reconciled","same-generation-idempotent"]' 'not-run' 'not-needed' 'none' || true
  printf 'RECONCILED|%s|%s|%s|%s|%s' "$operation_id" "$requested_generation" "$requested_generation" "${{prior_stable:-}}" "${{prior_previous:-}}"
  exit 0
fi

set +e
(cd "$generation_path" && docker compose -p "$service" -f compose.yaml up -d --force-recreate --remove-orphans) >/dev/null 2>&1
compose_rc=$?
set -e
if [ "$compose_rc" -ne 0 ]; then
  write_record 'activation-failed' '["lock-acquired","generation-validated","runtime-inspected","compose-attempted"]' 'not-run' 'inspect-runtime-before-retry' 'compose-failed' || true
  printf 'FAILED|%s|compose-failed' "$operation_id"
  exit 1
fi
runtime_line=$(runtime_probe)
IFS='|' read -r runtime_tag runtime_class runtime_generation runtime_count <<< "$runtime_line"
if [ "$runtime_class" = complete ] && [ "$runtime_generation" = "$requested_generation" ]; then
  write_atomic "$active_file" "$requested_generation" || {{ printf 'FAILED|%s|active-pointer-write-failed' "$operation_id"; exit 1; }}
  write_record 'activated-unverified' '["lock-acquired","generation-validated","runtime-inspected","compose-applied","runtime-reconciled"]' 'not-run' 'verification-pending' 'none' || true
  printf 'SUCCESS|%s|%s|%s|%s|%s' "$operation_id" "$requested_generation" "$requested_generation" "${{prior_stable:-}}" "${{prior_previous:-}}"
  exit 0
fi
write_record 'unresolved' '["lock-acquired","generation-validated","runtime-inspected","compose-applied"]' 'not-run' 'runtime-reconciliation-required' 'compose-outcome-ambiguous' || true
printf 'UNRESOLVED|%s|compose-outcome-ambiguous' "$operation_id"
exit 3
"""
    )


def _parse_activation_result(
    service: str,
    generation: str,
    lines: list[str],
    *,
    default_operation: str,
) -> ActivationResult:
    result_lines = [line for line in lines if any(line.startswith(prefix) for prefix in ("SUCCESS|", "RECONCILED|"))]
    if len(result_lines) != 1:
        for line in lines:
            if line.startswith("LOCKED|"):
                raise ActivationError("deployment activation is already in progress", 1, operation_id=default_operation)
            if line.startswith("UNRESOLVED|"):
                parts = _safe_line(line.split("|"), minimum=3)
                operation = parts[1] if _OPERATION.fullmatch(parts[1]) else default_operation
                raise ActivationError(
                    f"activation unresolved: {parts[2]}", 3, ambiguous=True, operation_id=operation
                )
            if line.startswith("FAILED|"):
                parts = _safe_line(line.split("|"), minimum=3)
                operation = parts[1] if _OPERATION.fullmatch(parts[1]) else default_operation
                raise ActivationError(f"activation failed: {parts[2]}", 1, operation_id=operation)
        raise ActivationError("remote activation result is missing or ambiguous", 3, ambiguous=True, operation_id=default_operation)
    parts = _safe_line(result_lines[0].split("|"), minimum=6)
    if parts[0] not in {"SUCCESS", "RECONCILED"} or not _OPERATION.fullmatch(parts[1]):
        raise ActivationError("remote activation result is malformed", 3, ambiguous=True, operation_id=default_operation)
    if not _REVISION.fullmatch(parts[2]) or parts[2] != generation:
        raise ActivationError("remote activation generation identity mismatch", 3, ambiguous=True, operation_id=parts[1])
    def pointer(value: str) -> str | None:
        if value and not _REVISION.fullmatch(value):
            raise ActivationError("remote activation pointer is malformed", 3, ambiguous=True, operation_id=parts[1])
        return value or None
    active, stable, previous = pointer(parts[3]), pointer(parts[4]), pointer(parts[5])
    runtime = RuntimeObservation("complete", generation)
    return ActivationResult(
        parts[1], service, generation, "success" if parts[0] == "SUCCESS" else "reconciled",
        active, stable, previous, runtime,
        "same-generation-reconciled" if parts[0] == "RECONCILED" else "verification-pending",
    )


def _state_exists(snapshot: Mapping[str, Any]) -> bool:
    return bool(snapshot.get("initialized")) and any(snapshot.get(key) for key in ("active", "stable", "previous"))


def _guard_source(
    service: str,
    source: ArcaneSource | None,
    *,
    credentials_file: Path,
    environment_id: str | None,
    timeout: float,
) -> ArcaneObservation:
    if source is None:
        return observe_arcane(service, credentials_file=credentials_file, environment_id=environment_id, timeout=timeout)
    if callable(source) or isinstance(source, ArcaneObservation) or isinstance(source, Mapping):
        return _normalize_arcane(source, service)
    raise ActivationError("Arcane migration evidence is malformed", 3)


def activate_generation(
    service: str,
    generation: str,
    *,
    host: str = DEFAULT_HOST,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    timeout: float = DEFAULT_TIMEOUT,
    arcane: ArcaneSource | None = None,
    arcane_credentials: Path = DEFAULT_ARCANE_CREDENTIALS,
    environment_id: str | None = None,
    migration_evidence: MigrationEvidence | None = None,
) -> ActivationResult:
    """Activate one prepared immutable generation with direct Docker Compose.

    The generation directory and its release manifest must already exist on the Docker host.  A
    successful return means Docker labels identify the requested generation and metadata records
    it as ``active``; independent P10 verification and :func:`promote` are still required before
    the generation becomes ``stable``.
    """

    service = _validate_service(service)
    generation = _validate_revision(generation)
    host = _validate_host(host)
    state = _validate_state_root(state_root)
    timeout = _validate_timeout(timeout)
    # Read state before the Arcane guard to decide whether disable-and-drain evidence is required;
    # this read does not create directories or lock files.
    snapshot = _status_snapshot(service, host=host, state_root=state, timeout=timeout)
    first_takeover = not _state_exists(snapshot)
    observation = _guard_source(
        service,
        arcane,
        credentials_file=arcane_credentials,
        environment_id=environment_id,
        timeout=timeout,
    )
    guard_arcane(service, observation, first_takeover=first_takeover, migration_evidence=migration_evidence)
    legacy_workdir: str | None = None
    legacy_services: tuple[str, ...] | None = None
    if first_takeover and observation.present and migration_evidence is not None:
        legacy_services = _validate_service_set(
            migration_evidence.get("old_services"), label="old Compose service set"
        )
    if first_takeover and observation.present and migration_evidence is not None:
        raw_legacy = migration_evidence.get("legacy_working_dir")
        if isinstance(raw_legacy, str):
            legacy_workdir = raw_legacy
    operation_id = _new_operation()
    def locked_arcane_recheck() -> None:
        refreshed = _guard_source(
            service,
            arcane,
            credentials_file=arcane_credentials,
            environment_id=environment_id,
            timeout=timeout,
        )
        guard_arcane(
            service,
            refreshed,
            first_takeover=first_takeover,
            migration_evidence=migration_evidence,
        )

    lines = _interactive_remote(
        host,
        _generation_script(
            service,
            state,
            operation_id,
            generation,
            legacy_workdir=legacy_workdir,
            legacy_services=legacy_services,
            await_gate=True,
        ),
        timeout,
        operation_id,
        locked_arcane_recheck,
    )
    return _parse_activation_result(service, generation, lines, default_operation=operation_id)


activate = activate_generation


def _reconcile_script(service: str, state_root: str, operation_id: str) -> str:
    return (
        _common_script(service, state_root)
        + f"""
operation_id={_q(operation_id)}
started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
write_record() {{
  local record_state="$1" steps="$2" verification="$3" recovery="$4" reason="$5" now tmp requested
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ) || return 64
  requested="$1"
  tmp=$(mktemp "$operations/.$operation_id.XXXXXX") || return 64
  printf '{{"schema":1,"operation_id":"%s","service":"%s","requested_generation":null,"requested_revision":null,"previous_active":%s,"previous_stable":%s,"state":"%s","completed_steps":%s,"verification":"%s","recovery":"%s","reason":"%s","started_at":"%s","updated_at":"%s"}}\\n' \\
    "$operation_id" "$service" "$(json_nullable "$old_active")" "$(json_nullable "$old_stable")" \\
    "$record_state" "$steps" "$verification" "$recovery" "$reason" "$started_at" "$now" >"$tmp" || return 64
  chmod 0600 "$tmp" || return 64
  mv -f -- "$tmp" "$operations/$operation_id.json" || return 64
  write_atomic "$latest_file" "$operation_id" || return 64
}}
if [ ! -d "$state" ] || [ -L "$state" ]; then printf 'STATE|no-state'; exit 0; fi
if ! ensure_state; then printf 'FAILED|%s|state-path-unavailable' "$operation_id"; exit 1; fi
exec 9>"$lock" || {{ printf 'FAILED|%s|lock-unavailable' "$operation_id"; exit 1; }}
if ! flock -n 9; then printf 'LOCKED|%s' "$operation_id"; exit 75; fi
old_active=$(read_pointer "$active_file") || {{ printf 'FAILED|%s|state-pointer-malformed' "$operation_id"; exit 1; }}
read_stability || {{ printf 'FAILED|%s|state-pointer-malformed' "$operation_id"; exit 1; }}
old_stable="$stable"
old_previous="$previous"
runtime_line=$(runtime_probe)
IFS='|' read -r runtime_tag runtime_class runtime_generation runtime_count <<< "$runtime_line"
if [ "$runtime_tag" != RUNTIME ]; then printf 'UNRESOLVED|%s|runtime-observation-invalid' "$operation_id"; exit 3; fi
if [ "$runtime_class" = complete ] && [ -n "$runtime_generation" ]; then
  if [ ! -d "$generations/$runtime_generation" ] || [ -L "$generations/$runtime_generation" ]; then
    write_record 'recovery-required' '["lock-acquired","runtime-inspected"]' 'not-run' 'orphan-generation' 'runtime-generation-not-retained' || true
    printf 'UNRESOLVED|%s|orphan-generation' "$operation_id"; exit 3
  fi
  write_atomic "$active_file" "$runtime_generation" || {{ printf 'FAILED|%s|active-pointer-write-failed' "$operation_id"; exit 1; }}
  write_record 'reconciled' '["lock-acquired","runtime-inspected","active-reconciled"]' 'not-run' 'not-needed' 'none' || true
  printf 'RECONCILED|%s|%s|%s|%s|%s|%s' "$operation_id" "$runtime_generation" "$runtime_generation" "${{old_stable:-}}" "${{old_previous:-}}" "$runtime_class"
  exit 0
fi
if [ "$runtime_class" = none ] && [ -n "$old_stable" ]; then
  write_record 'recovery-required' '["lock-acquired","runtime-inspected"]' 'not-run' 'project-absent' 'no-project' || true
  printf 'UNRESOLVED|%s|no-project'; exit 3
fi
write_record 'recovery-required' '["lock-acquired","runtime-inspected"]' 'not-run' 'runtime-recovery-required' 'mixed-or-partial-runtime' || true
printf 'UNRESOLVED|%s|runtime-recovery-required' "$operation_id"
exit 3
"""
    )


def reconcile(
    service: str,
    *,
    host: str = DEFAULT_HOST,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Reconcile the active pointer to one complete Docker generation after interruption."""

    service = _validate_service(service)
    host = _validate_host(host)
    state = _validate_state_root(state_root)
    timeout = _validate_timeout(timeout)
    operation_id = _new_operation()
    lines = _remote(
        host,
        _reconcile_script(service, state, operation_id),
        timeout,
        mutating=True,
        operation_id=operation_id,
    )
    for line in lines:
        if line.startswith("LOCKED|"):
            raise ActivationError("deployment activation is still in progress", 1, operation_id=operation_id)
        if line.startswith("UNRESOLVED|"):
            parts = _safe_line(line.split("|"), minimum=3)
            raise ActivationError(f"runtime reconciliation required: {parts[2]}", 3, ambiguous=True, operation_id=operation_id)
        if line.startswith("RECONCILED|"):
            parts = _safe_line(line.split("|"), minimum=7)
            if not _OPERATION.fullmatch(parts[1]) or not _REVISION.fullmatch(parts[2]):
                raise ActivationError("remote reconciliation result is malformed", 3, operation_id=operation_id)
            runtime = RuntimeObservation(parts[6], parts[2])
            def pointer(value: str) -> str | None:
                if value and not _REVISION.fullmatch(value):
                    raise ActivationError("remote reconciliation pointer is malformed", 3, operation_id=parts[1])
                return value or None
            return {
                "operation_id": parts[1],
                "service": service,
                "status": "reconciled",
                "active": pointer(parts[3]),
                "stable": pointer(parts[4]),
                "previous": pointer(parts[5]),
                "runtime": runtime.value(),
            }
    raise ActivationError("remote reconciliation result is missing or ambiguous", 3, ambiguous=True, operation_id=operation_id)


def _verification_summary(verification: Mapping[str, Any], generation: str) -> tuple[bool, int, str]:
    if not isinstance(verification, Mapping):
        raise ActivationError("verification evidence is malformed", 2)
    # deployment.verify exposes both identities separately: ``generation`` is the selected
    # directory path, while ``expected_revision`` and ``active_revision`` carry the authored
    # release identity and Docker's observed active pointer.  Promotion requires both exact
    # revision fields so a path or stale report cannot stand in for runtime evidence.
    expected_revision = verification.get("expected_revision")
    active_revision = verification.get("active_revision")
    if (
        not isinstance(expected_revision, str)
        or not _REVISION.fullmatch(expected_revision)
        or expected_revision != generation
    ):
        raise ActivationError("verification expected revision is missing or mismatched", 1)
    if not isinstance(active_revision, str) or not _REVISION.fullmatch(active_revision) or active_revision != generation:
        raise ActivationError("verification active revision is missing or mismatched", 1)
    selected_path = verification.get("generation")
    if selected_path is not None and (
        not isinstance(selected_path, str)
        or any(ord(char) < 33 or ord(char) == 127 for char in selected_path)
    ):
        raise ActivationError("verification generation path is malformed", 2)
    outcome = verification.get("outcome", verification.get("status"))
    passed = outcome in {"success", "verified", "passed"} or verification.get("verified") is True
    if (
        verification.get("verified") is False
        or outcome in {"failure", "failed", "unavailable"}
        or verification.get("route_status") == "failed"
    ):
        passed = False
    count = verification.get("container_count", verification.get("containers", 0))
    if type(count) is not int or count < 0 or count > _MAX_SERVICES:
        raise ActivationError("verification container count is malformed", 2)
    route_status = verification.get("route_status", "not-run")
    if not isinstance(route_status, str) or route_status not in {"verified", "skipped", "not-run", "failed"}:
        raise ActivationError("verification route status is malformed", 2)
    return passed, count, route_status


def _promotion_script(
    service: str,
    state_root: str,
    operation_id: str,
    generation: str,
    passed: bool,
    container_count: int,
    route_status: str,
) -> str:
    verification = "passed" if passed else "failed"
    return (
        _common_script(service, state_root)
        + f"""
operation_id={_q(operation_id)}
requested_generation={_q(generation)}
verification_status={_q(verification)}
verification_count={_q(str(container_count))}
verification_routes={_q(route_status)}
started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
write_record() {{
  local record_state="$1" steps="$2" verify="$3" recovery="$4" reason="$5" now tmp
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ) || return 64
  tmp=$(mktemp "$operations/.$operation_id.XXXXXX") || return 64
  printf '{{"schema":1,"operation_id":"%s","service":"%s","requested_generation":"%s","requested_revision":"%s","previous_active":%s,"previous_stable":%s,"state":"%s","completed_steps":%s,"verification":"%s","verification_containers":%s,"verification_routes":"%s","recovery":"%s","reason":"%s","started_at":"%s","updated_at":"%s"}}\\n' \\
    "$operation_id" "$service" "$requested_generation" "$requested_generation" \\
    "$(json_nullable "$old_active")" "$(json_nullable "$old_stable")" \\
    "$record_state" "$steps" "$verify" "$verification_count" "$verification_routes" "$recovery" "$reason" "$started_at" "$now" >"$tmp" || return 64
  chmod 0600 "$tmp" || return 64
  mv -f -- "$tmp" "$operations/$operation_id.json" || return 64
  write_atomic "$latest_file" "$operation_id" || return 64
}}
if ! ensure_state; then printf 'FAILED|%s|state-path-unavailable' "$operation_id"; exit 1; fi
exec 9>"$lock" || {{ printf 'FAILED|%s|lock-unavailable' "$operation_id"; exit 1; }}
if ! flock -n 9; then printf 'LOCKED|%s' "$operation_id"; exit 75; fi
old_active=$(read_pointer "$active_file") || {{ printf 'FAILED|%s|state-pointer-malformed' "$operation_id"; exit 1; }}
read_stability || {{ printf 'FAILED|%s|state-pointer-malformed' "$operation_id"; exit 1; }}
old_stable="$stable"
old_previous="$previous"
operation_path="$operations/$operation_id.json"
recorded_generation=$(json_field "$operation_path" requested_generation) || {{ printf 'FAILED|%s|operation-record-missing' "$operation_id"; exit 1; }}
[ "$recorded_generation" = "$requested_generation" ] || {{ printf 'FAILED|%s|operation-generation-mismatch' "$operation_id"; exit 1; }}
write_record 'promotion-in-progress' '["lock-acquired","verification-recorded"]' "$verification_status" 'promotion-pending' 'none' || {{ printf 'FAILED|%s|operation-record-failed' "$operation_id"; exit 1; }}
if [ "$verification_status" != passed ]; then
  write_record 'verification-failed' '["lock-acquired","verification-recorded"]' 'failed' 'rollback-candidate-retained' 'independent-verification-failed' || true
  printf 'FAILED|%s|verification-failed' "$operation_id"; exit 1
fi
[ -d "$generations/$requested_generation" ] && [ ! -L "$generations/$requested_generation" ] || {{ printf 'FAILED|%s|generation-not-retained' "$operation_id"; exit 1; }}
[ "$old_active" = "$requested_generation" ] || {{ printf 'FAILED|%s|active-generation-mismatch' "$operation_id"; exit 1; }}
runtime_line=$(runtime_probe)
IFS='|' read -r runtime_tag runtime_class runtime_generation runtime_count <<< "$runtime_line"
if [ "$runtime_tag" != RUNTIME ] || [ "$runtime_class" != complete ] || [ "$runtime_generation" != "$requested_generation" ]; then
  write_record 'recovery-required' '["lock-acquired","runtime-inspected"]' 'not-run' 'promotion-refused' 'runtime-generation-mismatch' || true
  printf 'UNRESOLVED|%s|runtime-generation-mismatch' "$operation_id"; exit 3
fi
if [ "$old_stable" != "$requested_generation" ]; then
  write_stability "$requested_generation" "$old_stable" || {{ printf 'FAILED|%s|stability-transition-failed' "$operation_id"; exit 1; }}
fi
write_record 'promoted' '["lock-acquired","runtime-reconciled","verification-recorded","stable-promoted"]' 'passed' 'not-needed' 'none' || true
result_previous="$old_stable"
[ "$old_stable" = "$requested_generation" ] && result_previous="$old_previous"
printf 'PROMOTED|%s|%s|%s|%s|%s' "$operation_id" "$requested_generation" "$requested_generation" "$requested_generation" "$result_previous"
exit 0
"""
    )


def promote(
    service: str,
    generation: str,
    operation_id: str,
    verification: Mapping[str, Any],
    *,
    host: str = DEFAULT_HOST,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    timeout: float = DEFAULT_TIMEOUT,
) -> ActivationResult:
    """Atomically promote a verified active generation to stable."""

    service = _validate_service(service)
    generation = _validate_revision(generation)
    operation_id = _validate_operation(operation_id)
    host = _validate_host(host)
    state = _validate_state_root(state_root)
    timeout = _validate_timeout(timeout)
    passed, count, route_status = _verification_summary(verification, generation)
    if not passed:
        raise ActivationError("independent verification did not pass; stable was not promoted", 1, operation_id=operation_id)
    lines = _remote(
        host,
        _promotion_script(service, state, operation_id, generation, passed, count, route_status),
        timeout,
        mutating=True,
        operation_id=operation_id,
    )
    for line in lines:
        if line.startswith("LOCKED|"):
            raise ActivationError("deployment activation is still in progress", 1, operation_id=operation_id)
        if line.startswith("UNRESOLVED|"):
            parts = _safe_line(line.split("|"), minimum=3)
            raise ActivationError(f"promotion unresolved: {parts[2]}", 3, ambiguous=True, operation_id=operation_id)
        if line.startswith("FAILED|"):
            parts = _safe_line(line.split("|"), minimum=3)
            raise ActivationError(f"promotion failed: {parts[2]}", 1, operation_id=operation_id)
        if line.startswith("PROMOTED|"):
            parts = _safe_line(line.split("|"), minimum=6)
            if parts[1] != operation_id or parts[2] != generation:
                raise ActivationError("promotion identity mismatch", 3, operation_id=operation_id)
            def pointer(value: str) -> str | None:
                if value and not _REVISION.fullmatch(value):
                    raise ActivationError("promotion pointer is malformed", 3, operation_id=operation_id)
                return value or None
            active = pointer(parts[3])
            stable = pointer(parts[4])
            previous = pointer(parts[5])
            if active != generation or stable != generation:
                raise ActivationError("promotion state identity mismatch", 3, operation_id=operation_id)
            return ActivationResult(
                operation_id, service, generation, "promoted", active, stable,
                previous, RuntimeObservation("complete", generation, count),
            )
    raise ActivationError("remote promotion result is missing or ambiguous", 3, ambiguous=True, operation_id=operation_id)


def mark_verification(
    service: str,
    generation: str,
    operation_id: str,
    *,
    passed: bool,
    container_count: int = 0,
    route_status: str = "not-run",
    host: str = DEFAULT_HOST,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Record a failed independent verification without changing stable or rolling back.

    Successful verification should call :func:`promote`, which rechecks Docker identity while
    holding the same service lock before changing stable metadata.
    """

    service = _validate_service(service)
    generation = _validate_revision(generation)
    operation_id = _validate_operation(operation_id)
    if type(passed) is not bool or type(container_count) is not int or container_count < 0 or container_count > _MAX_SERVICES:
        raise ActivationError("verification result is malformed", 2)
    if route_status not in {"verified", "skipped", "not-run", "failed"}:
        raise ActivationError("verification route status is malformed", 2)
    if passed:
        raise ActivationError("successful verification must use promotion", 2, operation_id=operation_id)
    # Reuse promotion's metadata path with a failed result.  It deliberately writes no pointer.
    script = _promotion_script(service, _validate_state_root(state_root), operation_id, generation, False, container_count, route_status)
    lines = _remote(
        _validate_host(host),
        script,
        _validate_timeout(timeout),
        mutating=True,
        operation_id=operation_id,
    )
    for line in lines:
        if line.startswith("LOCKED|"):
            raise ActivationError("deployment activation is still in progress", 1, operation_id=operation_id)
        if line.startswith("FAILED|"):
            parts = _safe_line(line.split("|"), minimum=3)
            if parts[1] == operation_id and parts[2] == "verification-failed":
                return {
                    "operation_id": operation_id,
                    "service": service,
                    "generation": generation,
                    "status": "verification-failed",
                    "stable": "unchanged",
                    "recovery": "rollback-candidate-retained",
                }
            raise ActivationError(f"verification record failed: {parts[2]}", 1, operation_id=operation_id)
    raise ActivationError("remote verification record result is missing", 3, ambiguous=True, operation_id=operation_id)


record_verification = mark_verification


__all__ = [
    "ActivationError",
    "ActivationResult",
    "ArcaneCredentials",
    "ArcaneObservation",
    "DEFAULT_ARCANE_CREDENTIALS",
    "DEFAULT_ENVIRONMENT_ID",
    "DEFAULT_HOST",
    "DEFAULT_STATE_ROOT",
    "DEFAULT_TIMEOUT",
    "MigrationEvidence",
    "RuntimeObservation",
    "activate",
    "activate_generation",
    "guard_arcane",
    "mark_verification",
    "observe_arcane",
    "promote",
    "reconcile",
    "record_verification",
    "status",
]
