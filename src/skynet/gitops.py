"""Bounded Arcane GitOps deployment and local rollback preparation."""

from __future__ import annotations

import http.client
import io
import json
import os
import re
import shlex
import signal
import ssl
import stat
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, TextIO

from skynet import deployment

DEFAULT_AGE_KEY = Path("/opt/skynet-ops/secrets/age.key")
DEFAULT_BRANCH = "main"
DEFAULT_TIMEOUT = 15.0
MAX_OUTPUT = 64 * 1024
MAX_RESPONSE = 1024 * 1024
ENV_WRITER_IMAGE = "busybox@sha256:dc2d74b28e4cf8984fa52af1f39bc7c3d9c73760b41a74d629f5d11b1ab28616"
_SERVICE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*")
_REVISION = re.compile(r"[0-9a-f]{40}")
_MAX_CHANGED_PATHS = 512
_PROTECTED_ROLLBACK_PATHS = frozenset(
    {
        "AGENTS.md",
        "docs/system-design.md",
        "invariants.json",
        "nix/home/aliammar.nix",
        "scripts/check-invariants.sh",
        "scripts/deploy-gate.sh",
        "scripts/secret-scan.sh",
        "scripts/tofu-apply.sh",
        "src/skynet/deployment.py",
        "src/skynet/gitops.py",
    }
)


class GitOpsError(Exception):
    """A safe, operator-facing outcome."""

    def __init__(self, reason: str, code: int = 1, *, ambiguous: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.code = code
        self.ambiguous = ambiguous


@dataclass
class Outcome:
    """Structured deployment or rollback evidence without secret-bearing details."""

    operation: str
    target: str
    source: dict[str, str]
    completed_steps: list[str] = field(default_factory=list)
    verification: str = "not-run"
    recovery: str = "not-needed"
    status: str = "failed"
    reason: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def value(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "operation": self.operation,
            "target": self.target,
            "source": self.source,
            "completed_steps": self.completed_steps,
            "verification": self.verification,
            "recovery": self.recovery,
            "status": self.status,
        }
        if self.reason is not None:
            result["reason"] = self.reason
        if self.detail:
            result["detail"] = self.detail
        return result


def _emit(outcome: Outcome, *, json_output: bool, stdout: TextIO) -> None:
    if json_output:
        print(json.dumps(outcome.value(), sort_keys=True), file=stdout)
        return
    prefix = f"{outcome.operation}: {outcome.target}: {outcome.status}"
    if outcome.reason:
        prefix += f": {outcome.reason}"
    print(prefix, file=stdout)
    source = ", ".join(f"{key}={value}" for key, value in outcome.source.items())
    if source:
        print(f"source: {source}", file=stdout)
    print(f"completed: {', '.join(outcome.completed_steps) or 'none'}", file=stdout)
    print(f"verification: {outcome.verification}; recovery: {outcome.recovery}", file=stdout)
    for key, value in outcome.detail.items():
        print(f"{key}: {value}", file=stdout)


def _validate_service(service: str) -> str:
    if not _SERVICE.fullmatch(service) or service in {".", ".."}:
        raise GitOpsError("invalid service identity", 2)
    return service


def _validate_timeout(timeout: float) -> float:
    if not 1.0 <= timeout <= 300.0:
        raise GitOpsError("timeout must be between 1 and 300 seconds", 2)
    return timeout


def _run(
    args: list[str],
    timeout: float,
    *,
    input_bytes: bytes | None = None,
    reason: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    deadline = time.monotonic() + timeout
    try:
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            start_new_session=True,
        )
    except OSError:
        raise GitOpsError(reason, 3, ambiguous=input_bytes is not None) from None
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    oversized = [False, False]
    stream_errors: list[BaseException] = []

    def drain(stream: Any, chunks: list[bytes], index: int) -> None:
        retained = 0
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
                room = MAX_OUTPUT + 1 - retained
                if room > 0:
                    chunks.append(chunk[:room])
                    retained += min(len(chunk), room)
                if retained > MAX_OUTPUT or len(chunk) > room:
                    oversized[index] = True
        except (OSError, ValueError) as error:
            stream_errors.append(error)

    assert process.stdout is not None and process.stderr is not None
    readers = [
        threading.Thread(target=drain, args=(process.stdout, stdout_chunks, 0), daemon=True),
        threading.Thread(target=drain, args=(process.stderr, stderr_chunks, 1), daemon=True),
    ]
    for reader in readers:
        reader.start()
    write_errors: list[BaseException] = []

    def feed() -> None:
        assert process.stdin is not None and input_bytes is not None
        try:
            process.stdin.write(input_bytes)
        except BrokenPipeError:
            pass
        except (OSError, ValueError) as error:
            write_errors.append(error)
        finally:
            try:
                process.stdin.close()
            except (OSError, ValueError):
                pass

    writer = threading.Thread(target=feed, daemon=True) if input_bytes is not None else None
    if writer is not None:
        writer.start()

    def terminate_group() -> None:
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
            process.wait()

    timed_out = False
    try:
        process.wait(timeout=max(0.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        timed_out = True
        terminate_group()
    workers = [*readers, *([writer] if writer is not None else [])]
    remaining = max(0.0, deadline - time.monotonic())
    for worker in workers:
        worker.join(remaining)
        remaining = max(0.0, deadline - time.monotonic())
    inherited_pipe = any(worker.is_alive() for worker in workers)
    if inherited_pipe:
        terminate_group()
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except (OSError, ValueError):
                pass
    for worker in workers:
        worker.join(1.0)
    if any(worker.is_alive() for worker in workers):
        raise GitOpsError(reason, 3, ambiguous=input_bytes is not None) from None
    if timed_out or inherited_pipe:
        raise GitOpsError(reason, 3, ambiguous=input_bytes is not None) from None
    if write_errors:
        raise GitOpsError(reason, 3, ambiguous=True)
    if stream_errors:
        raise GitOpsError(reason, 3, ambiguous=input_bytes is not None)
    result = subprocess.CompletedProcess(
        args, process.returncode, b"".join(stdout_chunks), b"".join(stderr_chunks)
    )
    if any(oversized):
        raise GitOpsError(f"{reason}: output exceeded bound", 3)
    if result.returncode != 0:
        raise GitOpsError(reason, 3)
    return result


def _text(result: subprocess.CompletedProcess[bytes], reason: str) -> str:
    try:
        return result.stdout.decode("utf-8").strip()
    except UnicodeError:
        raise GitOpsError(reason, 3) from None


def _git(repo: Path, args: list[str], timeout: float, reason: str) -> str:
    return _text(_run(["git", "-C", str(repo), *args], timeout, reason=reason), reason)


def _local_source(repo: Path, branch: str, timeout: float) -> tuple[str, str]:
    if not branch or any(ord(char) < 33 or ord(char) == 127 for char in branch):
        raise GitOpsError("invalid branch identity", 2)
    _run(["git", "check-ref-format", "--branch", branch], timeout, reason="invalid branch identity")
    revision = _git(
        repo,
        ["rev-parse", "--verify", "--end-of-options", f"refs/heads/{branch}^{{commit}}"],
        timeout,
        "selected local branch head is unavailable",
    ).lower()
    if not _REVISION.fullmatch(revision):
        raise GitOpsError("selected local branch head is malformed", 2)
    origin = _git(repo, ["config", "--get", "remote.origin.url"], timeout, "git origin unavailable")
    if not origin or any(ord(char) < 33 or ord(char) == 127 for char in origin):
        raise GitOpsError("invalid git origin", 2)
    return revision, _normalize_repository(origin)


def _revision_blob(
    repo: Path, revision: str, relative: str, timeout: float
) -> tuple[bytes, bool] | None:
    listing = _run(
        ["git", "-C", str(repo), "ls-tree", "-z", revision, "--", relative],
        timeout,
        reason="selected revision service inputs unavailable",
    ).stdout
    if not listing:
        return None
    if not listing.endswith(b"\0") or listing.count(b"\0") != 1:
        raise GitOpsError("malformed selected revision service input", 3)
    try:
        metadata, observed = listing[:-1].split(b"\t", 1)
        mode, kind, object_id = metadata.decode("ascii").split()
        observed_path = observed.decode("utf-8")
    except (UnicodeError, ValueError):
        raise GitOpsError("malformed selected revision service input", 3) from None
    if (
        observed_path != relative
        or kind != "blob"
        or mode not in {"100644", "100755"}
        or not re.fullmatch(r"[0-9a-f]{40,64}", object_id)
    ):
        raise GitOpsError("selected revision service input is not a regular file", 2)
    content = _run(
        ["git", "-C", str(repo), "cat-file", "blob", object_id],
        timeout,
        reason="selected revision service input unavailable",
    ).stdout
    return content, mode == "100755"


def _bind_service_inputs(
    repo: Path, service_dir: Path, service: str, revision: str, timeout: float
) -> dict[str, bytes]:
    """Bind deploy bytes to the selected revision before any Arcane mutation."""
    bound: dict[str, bytes] = {}
    for name, required in (("compose.yaml", True), (".env.git", False), (".env.sops", False)):
        relative = f"compose/{service}/{name}"
        selected = _revision_blob(repo, revision, relative, timeout)
        local = service_dir / name
        present = _regular_source(local, required=required or selected is not None)
        if selected is None:
            if present:
                raise GitOpsError("untracked service input is absent from selected revision", 2)
            continue
        if not present:
            raise GitOpsError("selected revision service input is absent from worktree", 2)
        local_bytes, local_executable = _read_regular_source(local)
        selected_bytes, selected_executable = selected
        if local_bytes != selected_bytes or local_executable != selected_executable:
            raise GitOpsError("worktree service input differs from selected revision", 2)
        bound[name] = local_bytes
    return bound


def _normalize_repository(value: str) -> str:
    value = value.removesuffix(".git").rstrip("/")
    if value.startswith("git@") and ":" in value:
        owner = value.split("@", 1)[1]
        host, path = owner.split(":", 1)
        value = f"ssh://{host}/{path}"
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        raise GitOpsError("invalid git repository identity", 2) from None
    if parsed.scheme not in {"https", "ssh"} or not parsed.hostname or not parsed.path.strip("/"):
        raise GitOpsError("invalid git repository identity", 2)
    if parsed.username not in {None, "git"} or parsed.password or parsed.query or parsed.fragment:
        raise GitOpsError("unsafe git repository identity", 2)
    host = parsed.hostname.lower()
    port = f":{parsed.port}" if parsed.port else ""
    return f"{host}{port}/{parsed.path.strip('/')}"


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


@dataclass
class ArcaneWriter:
    """A bounded Arcane client that classifies failed writes as ambiguous."""

    url: str
    token: str = field(repr=False)
    auth_header: str
    environment_id: str
    timeout: float
    tls_context: ssl.SSLContext
    opener: urllib.request.OpenerDirector = field(init=False, repr=False)

    def __post_init__(self) -> None:
        parsed = urllib.parse.urlsplit(self.url)
        if parsed.scheme not in {"http", "https"}:
            raise GitOpsError("invalid Arcane write endpoint", 3)
        self.opener = urllib.request.build_opener(
            _NoRedirect(), urllib.request.HTTPSHandler(context=self.tls_context)
        )

    def request(self, method: str, path: str, data: dict[str, Any] | None = None) -> Any:
        body = None if data is None else json.dumps(data, separators=(",", ":")).encode()
        headers = {self.auth_header: self.token, "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.url + "/api" + path, body, headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE + 1)
                status = getattr(response, "status", response.getcode())
        except (
            OSError,
            urllib.error.URLError,
            urllib.error.HTTPError,
            http.client.HTTPException,
            TimeoutError,
        ):
            raise GitOpsError(
                "Arcane API write outcome is ambiguous"
                if method != "GET"
                else "Arcane API unavailable",
                3,
                ambiguous=method != "GET",
            ) from None
        if status < 200 or status >= 300 or len(raw) > MAX_RESPONSE:
            raise GitOpsError("Arcane API unavailable", 3, ambiguous=method != "GET")
        try:
            payload = json.loads(raw.decode())
        except (UnicodeError, ValueError):
            raise GitOpsError(
                "malformed Arcane API response", 3, ambiguous=method != "GET"
            ) from None
        if (
            not isinstance(payload, dict)
            or payload.get("success") is not True
            or "data" not in payload
        ):
            raise GitOpsError("malformed Arcane API response", 3, ambiguous=method != "GET")
        return payload["data"]

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def redeploy(self, path: str) -> None:
        """Consume Arcane v2's bounded NDJSON redeploy stream without exposing its body."""
        parsed = urllib.parse.urlsplit(self.url)
        if parsed.hostname is None:
            raise GitOpsError("invalid Arcane write endpoint", 3)
        if parsed.scheme == "https":
            connection: http.client.HTTPConnection = http.client.HTTPSConnection(
                parsed.hostname, parsed.port, timeout=self.timeout, context=self.tls_context
            )
        else:
            connection = http.client.HTTPConnection(
                parsed.hostname, parsed.port, timeout=self.timeout
            )
        base_path = parsed.path.rstrip("/")
        target = f"{base_path}/api{path}"
        deadline = time.monotonic() + self.timeout
        raw = bytearray()
        try:
            connection.request(
                "POST",
                target,
                headers={
                    self.auth_header: self.token,
                    "Accept": "application/x-ndjson",
                },
            )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            response = connection.getresponse()
            if response.status < 200 or response.status >= 300:
                raise GitOpsError("Arcane redeploy outcome is ambiguous", 3, ambiguous=True)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                if connection.sock is not None:
                    connection.sock.settimeout(remaining)
                chunk = response.read(min(8192, MAX_RESPONSE + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > MAX_RESPONSE:
                    raise GitOpsError("Arcane redeploy response exceeded bound", 3, ambiguous=True)
        except GitOpsError:
            raise
        except (OSError, http.client.HTTPException, TimeoutError, ValueError):
            raise GitOpsError("Arcane redeploy outcome is ambiguous", 3, ambiguous=True) from None
        finally:
            connection.close()
        try:
            text = bytes(raw).decode("utf-8")
            lines = text.splitlines()
            if not lines or any(not line for line in lines):
                raise ValueError
            frames = [json.loads(line) for line in lines]
        except (UnicodeError, ValueError):
            raise GitOpsError("malformed Arcane redeploy stream", 3, ambiguous=True) from None
        if any(not isinstance(frame, dict) for frame in frames):
            raise GitOpsError("malformed Arcane redeploy stream", 3, ambiguous=True)
        if any("error" in frame for frame in frames):
            raise GitOpsError("Arcane redeploy stream reported an error", 1, ambiguous=True)
        terminals = [index for index, frame in enumerate(frames) if frame.get("done") is True]
        if terminals != [len(frames) - 1]:
            raise GitOpsError("Arcane redeploy stream missing terminal success", 3, ambiguous=True)


def _identifier(value: Any, reason: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise GitOpsError(reason, 3)
    return value


def _list(client: ArcaneWriter, path: str, reason: str) -> list[dict[str, Any]]:
    value = client.get(path)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise GitOpsError(reason, 3)
    return value


def _repository_id(client: ArcaneWriter, origin: str) -> str:
    rows = _list(client, "/customize/git-repositories", "malformed Arcane repository observation")
    matches: list[dict[str, Any]] = []
    for row in rows:
        url = row.get("url")
        if isinstance(url, str):
            try:
                if _normalize_repository(url) == origin:
                    matches.append(row)
            except GitOpsError:
                continue
    if len(matches) != 1:
        raise GitOpsError("Arcane repository identity missing or ambiguous", 1)
    return _identifier(matches[0].get("id"), "malformed Arcane repository identity")


def _sync_candidates(client: ArcaneWriter, service: str) -> list[dict[str, Any]]:
    rows = _list(
        client,
        f"/environments/{client.environment_id}/gitops-syncs",
        "malformed Arcane sync observation",
    )
    return [row for row in rows if row.get("name") == service or row.get("projectName") == service]


def _validate_sync_identity(
    sync: dict[str, Any], service: str, repository_id: str, compose_path: str
) -> tuple[str, str]:
    expected = {
        "name": service,
        "projectName": service,
        "repositoryId": repository_id,
        "composePath": compose_path,
    }
    for key, value in expected.items():
        if sync.get(key) != value:
            raise GitOpsError("Arcane sync identity mismatch", 1)
    if "syncDirectory" not in sync or "autoSync" not in sync:
        raise GitOpsError("malformed Arcane sync controls", 3)
    if sync["syncDirectory"] is not True or type(sync["autoSync"]) is not bool:
        raise GitOpsError("Arcane sync controls mismatch", 1)
    if sync["autoSync"] is not False:
        raise GitOpsError("Arcane automatic source activation must already be disabled", 1)
    sync_id = _identifier(sync.get("id"), "malformed Arcane sync identity")
    raw_project = sync.get("projectId")
    if raw_project in {None, ""}:
        raise GitOpsError("Arcane project identity unavailable", 1)
    project_id = _identifier(raw_project, "malformed Arcane project identity")
    return sync_id, project_id


def _existing_sync(
    client: ArcaneWriter, service: str, repository_id: str, compose_path: str
) -> tuple[dict[str, Any], str, str]:
    candidates = _sync_candidates(client, service)
    if not candidates:
        raise GitOpsError(
            "Arcane sync identity missing; initial sync is not safe for this command", 1
        )
    if len(candidates) != 1:
        raise GitOpsError("Arcane sync identity ambiguous", 1)
    sync_id = _identifier(candidates[0].get("id"), "malformed Arcane sync identity")
    detail = _sync_detail(client, sync_id)
    _, project_id = _validate_sync_identity(detail, service, repository_id, compose_path)
    return detail, sync_id, project_id


def _await_sync_branch(
    client: ArcaneWriter,
    service: str,
    repository_id: str,
    branch: str,
    compose_path: str,
) -> tuple[dict[str, Any], str, str]:
    """Bound reconciliation after a branch-repoint write."""
    deadline = time.monotonic() + client.timeout
    last_error: GitOpsError | None = None
    while True:
        try:
            detail, sync_id, project_id = _existing_sync(
                client, service, repository_id, compose_path
            )
            if detail.get("branch") != branch:
                raise GitOpsError("Arcane sync branch mismatch", 1)
            return detail, sync_id, project_id
        except GitOpsError as error:
            if error.reason not in {
                "Arcane sync branch mismatch",
                "Arcane API unavailable",
            }:
                raise
            last_error = error
        if time.monotonic() >= deadline:
            assert last_error is not None
            raise last_error
        time.sleep(min(0.5, client.timeout / 5))


def _repoint_sync(
    client: ArcaneWriter,
    service: str,
    repository_id: str,
    branch: str,
    compose_path: str,
    outcome: Outcome,
    sync_id: str,
    current: dict[str, Any],
) -> dict[str, Any]:
    """Select the requested branch after env install while auto-sync remains disabled."""
    if current.get("branch") == branch:
        return current
    for attempt in range(3):
        try:
            client.request(
                "PUT",
                f"/environments/{client.environment_id}/gitops-syncs/{sync_id}",
                {"branch": branch},
            )
        except GitOpsError as error:
            if not error.ambiguous:
                raise
            outcome.recovery = "repoint-reconciliation-required-after-ambiguous-write"
        try:
            detail, _, _ = _await_sync_branch(
                client, service, repository_id, branch, compose_path
            )
            if outcome.recovery != "not-needed":
                outcome.recovery = "repoint-reconciled-after-ambiguous-write"
            outcome.completed_steps.append("sync-repointed")
            return detail
        except GitOpsError as error:
            if error.reason not in {
                "Arcane sync branch mismatch",
                "Arcane API unavailable",
            } or attempt == 2:
                outcome.recovery = (
                    "sync repoint unresolved; inspect the exact service sync before retry"
                )
                raise
            outcome.recovery = "repoint-retried-after-reconciliation"
    raise AssertionError("unreachable")


def _sync_detail(client: ArcaneWriter, sync_id: str) -> dict[str, Any]:
    value = client.get(f"/environments/{client.environment_id}/gitops-syncs/{sync_id}")
    if not isinstance(value, dict):
        raise GitOpsError("malformed Arcane sync observation", 3)
    return value


def _pull(
    client: ArcaneWriter, sync_id: str, revision: str, timeout: float, outcome: Outcome
) -> dict[str, Any]:
    """Activate source, reconciling a bounded ambiguous write from observed state."""
    path = f"/environments/{client.environment_id}/gitops-syncs/{sync_id}/sync"
    prior_recovery = outcome.recovery
    for attempt in range(3):
        outcome.recovery = "source pull requested; outcome not yet reconciled"
        try:
            result = client.request("POST", path)
        except GitOpsError as error:
            detail = _sync_detail(client, sync_id)
            if (
                detail.get("lastSyncStatus") == "success"
                and detail.get("lastSyncCommit") == revision
            ):
                outcome.recovery = "pull-reconciled-after-ambiguous-write"
                outcome.completed_steps.append("source-synced")
                return detail
            if not error.ambiguous or attempt == 2:
                outcome.recovery = (
                    "source activation unresolved; inspect its commit/status before retry"
                )
                raise
            outcome.recovery = "pull-retried-after-reconciliation"
            continue
        if not isinstance(result, dict) or result.get("success") is not True:
            detail = _sync_detail(client, sync_id)
            if (
                detail.get("lastSyncStatus") == "success"
                and detail.get("lastSyncCommit") == revision
            ):
                outcome.recovery = "pull-reconciled-after-ambiguous-write"
                outcome.completed_steps.append("source-synced")
                return detail
            if attempt == 2:
                outcome.recovery = (
                    "source activation response unresolved; inspect its commit/status before retry"
                )
                raise GitOpsError("malformed Arcane source sync result", 3, ambiguous=True)
            outcome.recovery = "pull-retried-after-reconciliation"
            continue
        deadline = time.monotonic() + timeout
        while True:
            detail = _sync_detail(client, sync_id)
            status = detail.get("lastSyncStatus")
            if status == "success" and detail.get("lastSyncCommit") == revision:
                outcome.completed_steps.append("source-synced")
                if attempt == 0:
                    outcome.recovery = prior_recovery
                else:
                    outcome.recovery = "source pull reconciled after retry"
                return detail
            if status in {"failed", "error"}:
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(min(1.0, timeout / 5))
        if attempt == 2:
            outcome.recovery = "source activation failed; inspect its commit/status before retry"
            raise GitOpsError("Arcane source sync did not reach selected branch head", 1)
        outcome.recovery = "pull-retried-after-reconciliation"
    raise AssertionError("unreachable")


def _project(client: ArcaneWriter, project_id: str) -> dict[str, Any]:
    value = client.get(f"/environments/{client.environment_id}/projects/{project_id}")
    if not isinstance(value, dict):
        raise GitOpsError("malformed Arcane project observation", 3)
    return value


def _project_identity(
    detail: dict[str, Any], sync_id: str, revision: str | None, service: str
) -> tuple[str, int]:
    if detail.get("gitOpsManagedBy") != sync_id or (
        revision is not None and detail.get("lastSyncCommit") != revision
    ):
        raise GitOpsError("Arcane project source identity mismatch", 1)
    path = detail.get("path")
    if (
        not isinstance(path, str)
        or not path.startswith("/")
        or len(path) > 4096
        or any(ord(char) < 33 or ord(char) == 127 for char in path)
    ):
        raise GitOpsError("invalid Arcane project path", 3)
    pure = PurePosixPath(path)
    expected_path = PurePosixPath("/opt/docker/arcane-projects") / service
    if pure != expected_path or str(pure) != path:
        raise GitOpsError("unsafe Arcane project path", 3)
    service_count = detail.get("serviceCount")
    if type(service_count) is not int or service_count <= 0:
        raise GitOpsError("malformed Arcane project service count", 3)
    return path, service_count


def _environment_bytes(
    inputs: dict[str, bytes], age_key: Path, timeout: float
) -> tuple[bytes, int]:
    chunks: list[bytes] = []
    value = inputs.get(".env.git")
    if value is not None:
        chunks.append(value.rstrip(b"\n") + b"\n")
    encrypted = inputs.get(".env.sops")
    if encrypted is not None:
        env = os.environ.copy()
        env["SOPS_AGE_KEY_FILE"] = str(age_key)
        result = _run(
            ["sops", "-d", "--input-type", "dotenv", "--output-type", "dotenv", "/dev/stdin"],
            timeout,
            input_bytes=encrypted,
            reason="service secrets could not be decrypted",
            env=env,
        )
        chunks.append(result.stdout.rstrip(b"\n") + b"\n")
    content = b"".join(chunks)
    if len(content) > MAX_OUTPUT:
        raise GitOpsError("effective environment exceeded bound", 3)
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeError:
        raise GitOpsError("effective environment is not UTF-8", 3) from None
    count = sum(bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", line)) for line in lines)
    return content, count


def _regular_source(path: Path, *, required: bool = False) -> bool:
    """Require repository inputs to be regular files without following symlinks."""
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        if required:
            raise GitOpsError("required service source unavailable", 2) from None
        return False
    except OSError:
        raise GitOpsError("service source unavailable", 3) from None
    if not stat.S_ISREG(mode):
        raise GitOpsError("service source must be a non-symlink regular file", 2)
    return True


def _read_regular_source(path: Path) -> tuple[bytes, bool]:
    """Read one bounded regular file through a no-follow descriptor."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise GitOpsError("worktree service input unavailable", 3) from None
    try:
        source_stat = os.fstat(descriptor)
        if not stat.S_ISREG(source_stat.st_mode):
            raise GitOpsError("service source must be a non-symlink regular file", 2)
        if source_stat.st_size > MAX_OUTPUT:
            raise GitOpsError("worktree service input exceeded bound", 3)
        chunks: list[bytes] = []
        retained = 0
        while True:
            chunk = os.read(descriptor, min(8192, MAX_OUTPUT + 1 - retained))
            if not chunk:
                break
            chunks.append(chunk)
            retained += len(chunk)
            if retained > MAX_OUTPUT:
                raise GitOpsError("worktree service input exceeded bound", 3)
        return b"".join(chunks), bool(source_stat.st_mode & 0o111)
    except OSError:
        raise GitOpsError("worktree service input unavailable", 3) from None
    finally:
        os.close(descriptor)


def _regular_directory(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError:
        raise GitOpsError("service directory unavailable", 2) from None
    if not stat.S_ISDIR(mode):
        raise GitOpsError("service directory must not be a symlink", 2)


def _ssh_host(url: str) -> str:
    hostname = urllib.parse.urlsplit(url).hostname
    if not hostname or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", hostname):
        raise GitOpsError("invalid Arcane SSH host identity", 3)
    return f"svc-ops@{hostname}"


def _write_environment(host: str, path: str, content: bytes, timeout: float) -> str:
    mount = shlex.quote(f"{path}:/mnt")
    image = shlex.quote(ENV_WRITER_IMAGE)
    remote = (
        "set -eu; owner=$(stat -c '%u:%g' -- " + shlex.quote(path) + "); "
        "case $owner in *[!0-9:]*|:*|*:) exit 41;; esac; "
        f"docker run --rm -i -v {mount} {image} sh -c "
        + shlex.quote(
            "set -eu; tmp=$(mktemp /mnt/.env.skynet.XXXXXX); trap 'rm -f \"$tmp\"' EXIT; "
            'cat >"$tmp"; chown "$1" "$tmp"; chmod 0600 "$tmp"; '
            'mv -f "$tmp" /mnt/.env; trap - EXIT'
        )
        + ' sh "$owner"; printf \'%s\' "$owner"'
    )
    try:
        result = _run(
            _ssh_command(host, timeout, remote),
            timeout + 5,
            input_bytes=content,
            reason="remote environment replacement failed",
        )
    except GitOpsError as error:
        raise GitOpsError(error.reason, error.code, ambiguous=True) from None
    try:
        owner = _text(result, "malformed remote owner observation")
    except GitOpsError as error:
        raise GitOpsError(error.reason, error.code, ambiguous=True) from None
    if not re.fullmatch(r"[0-9]+:[0-9]+", owner):
        raise GitOpsError("malformed remote owner observation", 3, ambiguous=True)
    return owner


def _remote_container_ids(host: str, service: str, timeout: float) -> list[str]:
    remote = "docker ps -q --filter " + shlex.quote(f"label=com.docker.compose.project={service}")
    value = _text(
        _run(
            _ssh_command(host, timeout, remote),
            timeout + 5,
            reason="remote container observation failed",
        ),
        "malformed remote container observation",
    )
    ids = value.splitlines() if value else []
    if any(not re.fullmatch(r"[0-9a-f]{12,64}", item) for item in ids) or len(ids) != len(set(ids)):
        raise GitOpsError("malformed remote container observation", 3)
    return ids


def _remote_containers(host: str, service: str, expected_count: int, timeout: float) -> list[str]:
    ids = _remote_container_ids(host, service, timeout)
    if len(ids) != expected_count or not ids:
        raise GitOpsError("remote running container set is partial or mismatched", 1)
    remote = "docker inspect --format '{{json .State}}' -- " + " ".join(
        shlex.quote(item) for item in ids
    )
    raw = _text(
        _run(
            _ssh_command(host, timeout, remote),
            timeout + 5,
            reason="remote container state observation failed",
        ),
        "malformed remote container state observation",
    )
    lines = raw.splitlines() if raw else []
    if len(lines) != len(ids):
        raise GitOpsError("remote container state observation is partial", 1)
    for line in lines:
        try:
            state = json.loads(line)
        except (UnicodeError, ValueError):
            raise GitOpsError("malformed remote container state observation", 3) from None
        if not isinstance(state, dict):
            raise GitOpsError("malformed remote container state observation", 3)
        health = state.get("Health")
        if (
            state.get("Running") is not True
            or state.get("Restarting") is not False
            or not isinstance(health, dict)
            or health.get("Status") != "healthy"
        ):
            raise GitOpsError("remote container is not running and healthy", 1)
    return ids


def _ssh_command(host: str, timeout: float, remote: str) -> list[str]:
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={max(1, int(timeout))}",
        host,
        remote,
    ]


def _wait_running(
    client: ArcaneWriter,
    project_id: str,
    sync_id: str,
    revision: str,
    service: str,
    timeout: float,
) -> tuple[dict[str, Any], int]:
    deadline = time.monotonic() + timeout
    while True:
        detail = _project(client, project_id)
        path, count = _project_identity(detail, sync_id, revision, service)
        del path
        if detail.get("status") == "running" and detail.get("runningCount") == count:
            return detail, count
        if time.monotonic() >= deadline:
            raise GitOpsError("Arcane project did not reach complete running state", 1)
        time.sleep(min(1.0, timeout / 5))


def _deploy_failure_recovery(outcome: Outcome) -> str:
    steps = set(outcome.completed_steps)
    if "runtime-reconciled" in steps:
        return "runtime reconciled; report-only gate failed; no automatic rollback performed"
    if "cloudflared-restarted" in steps:
        return "cloudflared restart completed; post-restart verification failed; inspect runtime"
    if "redeploy-requested" in steps:
        return "redeploy requested; runtime verification incomplete; inspect exact project before retry"
    if "source-synced" in steps:
        return "source activated; runtime verification incomplete; inspect exact project before retry"
    if "environment-replaced" in steps:
        return "environment prepared; source activation not confirmed; inspect exact project before retry"
    if "sync-repointed" in steps:
        return "Arcane source branch changed; environment replacement not confirmed; inspect before retry"
    return "no write attempted"


def _finalize_deploy_recovery(outcome: Outcome) -> None:
    """Prefer the latest failed stage over an earlier successfully reconciled write."""
    steps = set(outcome.completed_steps)
    if "runtime-reconciled" in steps or "redeploy-requested" in steps:
        outcome.recovery = _deploy_failure_recovery(outcome)
    elif "environment-replaced" in steps and not (
        outcome.recovery.startswith("redeploy-outcome-ambiguous")
        or outcome.recovery.startswith("source activation")
        or outcome.recovery.startswith("sync repoint")
    ):
        outcome.recovery = _deploy_failure_recovery(outcome)
    elif "source-synced" in steps and (
        outcome.recovery == "not-needed"
        or "reconciled" in outcome.recovery
        or "retried" in outcome.recovery
    ):
        outcome.recovery = _deploy_failure_recovery(outcome)
    elif "sync-repointed" in steps and (
        outcome.recovery == "not-needed" or "reconciled" in outcome.recovery
    ):
        outcome.recovery = _deploy_failure_recovery(outcome)
    elif outcome.recovery == "not-needed":
        outcome.recovery = _deploy_failure_recovery(outcome)


def _changed_paths(raw: bytes, service: str) -> list[str]:
    """Validate and classify the whole inverse scope before preparing a rollback."""
    if not raw or not raw.endswith(b"\0"):
        raise GitOpsError("deploy revision changed-path observation is malformed", 3)
    try:
        paths = [item.decode("utf-8") for item in raw[:-1].split(b"\0")]
    except UnicodeError:
        raise GitOpsError("deploy revision changed-path observation is malformed", 3) from None
    if not paths or len(paths) > _MAX_CHANGED_PATHS or len(paths) != len(set(paths)):
        raise GitOpsError("deploy revision changed-path observation is malformed", 3)
    for path in paths:
        if path in {"", "."}:
            raise GitOpsError("deploy revision contains an unsafe changed path", 2)
        pure = PurePosixPath(path)
        if (
            not path
            or len(path) > 512
            or path.startswith("/")
            or str(pure) != path
            or ".." in pure.parts
            or any(ord(char) < 33 or ord(char) == 127 for char in path)
            or "\\" in path
        ):
            raise GitOpsError("deploy revision contains an unsafe changed path", 2)
        basename = pure.name
        named_gate = pure.parts[0] == "scripts" and (
            "gate" in basename or basename.startswith("check-")
        )
        if path in _PROTECTED_ROLLBACK_PATHS or named_gate:
            raise GitOpsError("deploy revision touches a protected constitutional or gate path", 2)
        if len(pure.parts) >= 3 and pure.parts[0] == "compose":
            project = pure.parts[1]
            selected_project = project == service
            publication_route = (
                service != "caddy-apps"
                and project == "caddy-apps"
                and pure.parts == ("compose", "caddy-apps", "Caddyfile")
            )
            if not selected_project and not publication_route:
                raise GitOpsError("deploy revision touches another Compose project", 2)
    prefix = f"compose/{service}/"
    if not any(path.startswith(prefix) for path in paths):
        raise GitOpsError("deploy revision does not touch the selected service", 2)
    return paths


def deploy_service(
    service: str,
    *,
    repo: Path,
    branch: str = DEFAULT_BRANCH,
    credentials_file: Path = deployment.DEFAULT_CREDENTIALS,
    age_key: Path = DEFAULT_AGE_KEY,
    environment_id: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    no_deploy: bool = False,
    gate: bool = False,
    json_output: bool = False,
    stdout: TextIO,
) -> int:
    """Materialize, reconcile, deploy, and optionally invoke the P10 report-only gate."""
    outcome = Outcome("deploy", service, {})
    try:
        service = _validate_service(service)
        timeout = _validate_timeout(timeout)
        repo = repo.resolve(strict=True)
        service_dir = repo / "compose" / service
        _regular_directory(repo / "compose")
        _regular_directory(service_dir)
        revision, origin = _local_source(repo, branch, timeout)
        service_inputs = _bind_service_inputs(repo, service_dir, service, revision, timeout)
        outcome.source = {"branch": branch, "revision": revision, "repository": origin}
        creds = deployment.credentials(credentials_file, environment_id=environment_id)
        client = ArcaneWriter(
            creds.url,
            creds.token,
            creds.auth_header,
            creds.environment_id,
            timeout,
            creds.tls_context,
        )
        repository_id = _repository_id(client, origin)
        outcome.completed_steps.append("repository-selected")
        compose_path = f"compose/{service}/compose.yaml"
        sync, sync_id, project_id = _existing_sync(
            client, service, repository_id, compose_path
        )
        outcome.completed_steps.append("activation-owner-verified")
        project = _project(client, project_id)
        project_path, _ = _project_identity(project, sync_id, None, service)
        content, key_count = _environment_bytes(service_inputs, age_key, timeout)
        host = _ssh_host(creds.url)
        try:
            owner = _write_environment(host, project_path, content, timeout)
        except GitOpsError as error:
            if error.ambiguous:
                outcome.recovery = "environment replacement outcome ambiguous; inspect the exact project .env before retry"
            else:
                outcome.recovery = "environment replacement failed; source activation was not requested"
            raise
        outcome.completed_steps.append("environment-replaced")
        outcome.detail.update(
            {
                "environment_keys": key_count,
                "environment_owner": owner,
                "project_id": project_id,
                "sync_id": sync_id,
            }
        )
        if no_deploy:
            outcome.status = "success"
            outcome.verification = "environment-prepared; source-not-activated (--no-deploy)"
            _emit(outcome, json_output=json_output, stdout=stdout)
            return 0
        sync = _repoint_sync(
            client,
            service,
            repository_id,
            branch,
            compose_path,
            outcome,
            sync_id,
            sync,
        )
        sync = _pull(client, sync_id, revision, timeout, outcome)
        if _identifier(sync.get("projectId"), "Arcane project identity unavailable") != project_id:
            raise GitOpsError("Arcane project identity changed during source activation", 1)
        outcome.completed_steps.append("source-sync-redeploy-accounted")
        try:
            client.redeploy(
                f"/environments/{client.environment_id}/projects/{project_id}/redeploy"
            )
        except GitOpsError as error:
            if error.ambiguous:
                outcome.recovery = "redeploy-outcome-ambiguous; inspect before retry"
            raise
        outcome.completed_steps.append("redeploy-requested")
        _, expected_count = _wait_running(client, project_id, sync_id, revision, service, timeout)
        ids = _remote_containers(host, service, expected_count, timeout)
        if service == "cloudflared":
            # Restart only IDs returned by the exact Compose project label, after count reconciliation.
            remote = "docker restart -- " + " ".join(shlex.quote(item) for item in ids)
            _run(
                _ssh_command(host, timeout, remote),
                timeout + 5,
                reason="cloudflared restart failed",
            )
            outcome.completed_steps.append("cloudflared-restarted")
            _wait_running(client, project_id, sync_id, revision, service, timeout)
            if set(_remote_containers(host, service, expected_count, timeout)) != set(ids):
                raise GitOpsError("cloudflared restart changed the bounded target set", 1)
        outcome.completed_steps.append("runtime-reconciled")
        outcome.verification = "runtime-complete"
        if gate:
            gate_output = io.StringIO()
            gate_status = deployment.run(
                service,
                revision,
                credentials_file,
                deployment.DEFAULT_CONTEXT,
                repo,
                environment_id=environment_id,
                timeout=timeout,
                json_output=True,
                stdout=gate_output,
            )
            try:
                outcome.detail["gate_report"] = json.loads(gate_output.getvalue())
            except (TypeError, ValueError):
                outcome.recovery = "runtime reconciled; report-only gate evidence malformed; no automatic rollback performed"
                raise GitOpsError(
                    "report-only deployment gate returned malformed evidence", 3
                ) from None
            if gate_status != 0:
                outcome.recovery = (
                    "runtime reconciled; report-only gate failed; no automatic rollback performed"
                )
                raise GitOpsError("report-only deployment gate failed", gate_status)
            outcome.completed_steps.append("report-only-gate-passed")
            outcome.verification = "runtime-complete-and-gate-passed"
        outcome.status = "success"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 0
    except (deployment.VerificationError, GitOpsError) as error:
        outcome.reason = error.reason
        outcome.verification = "failed-closed"
        _finalize_deploy_recovery(outcome)
        _emit(outcome, json_output=json_output, stdout=stdout)
        return error.code
    except (OSError, ValueError):
        outcome.reason = "local deployment inputs unavailable"
        outcome.verification = "failed-closed"
        _finalize_deploy_recovery(outcome)
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 3


def rollback_service(
    service: str,
    revision: str,
    *,
    repo: Path,
    prepare: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    json_output: bool = False,
    stdout: TextIO,
) -> int:
    """Report rollback advice or prepare a local isolated review branch."""
    outcome = Outcome("rollback", service, {"revision": revision})
    worktree: Path | None = None
    keep_worktree = False
    try:
        service = _validate_service(service)
        timeout = _validate_timeout(timeout)
        if not _REVISION.fullmatch(revision):
            raise GitOpsError("deploy revision must be a full lowercase 40-hex commit", 2)
        repo = repo.resolve(strict=True)
        resolved = _git(
            repo,
            ["rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}"],
            timeout,
            "deploy revision is not a commit",
        )
        if resolved != revision:
            raise GitOpsError("deploy revision identity mismatch", 2)
        base = _git(
            repo,
            ["symbolic-ref", "--short", "HEAD"],
            timeout,
            "rollback requires an attached base branch",
        )
        _run(["git", "check-ref-format", "--branch", base], timeout, reason="invalid base branch")
        ancestor = _run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", revision, base],
            timeout,
            reason="deploy revision is not in the base branch",
        )
        del ancestor
        parent_line = _git(
            repo,
            ["rev-list", "--parents", "-n", "1", revision],
            timeout,
            "deploy revision parents unavailable",
        ).split()
        if len(parent_line) == 1:
            changed_args = [
                "diff-tree",
                "--root",
                "--no-commit-id",
                "--name-only",
                "-z",
                "-r",
                revision,
            ]
        else:
            changed_args = ["diff", "--name-only", "-z", parent_line[1], revision]
        changed_result = _run(
            ["git", "-C", str(repo), *changed_args],
            timeout,
            reason="deploy revision paths unavailable",
        )
        changed = _changed_paths(changed_result.stdout, service)
        slug = f"{service}-{revision[:12]}"
        branch = f"rollback/{slug}"
        outcome.source["base_branch"] = base
        outcome.detail["review_branch"] = branch
        outcome.detail["changed_path_count"] = len(changed)
        outcome.detail["changed_paths"] = changed
        existing_ref = _git(
            repo,
            ["for-each-ref", "--format=%(refname)", f"refs/heads/{branch}"],
            timeout,
            "rollback branch identity could not be checked",
        )
        if existing_ref:
            if existing_ref != f"refs/heads/{branch}":
                raise GitOpsError("malformed rollback branch observation", 3)
            raise GitOpsError("rollback review branch already exists", 4)
        if not prepare:
            outcome.status = "report-only"
            outcome.verification = "rollback-inputs-validated"
            outcome.recovery = f"run with --prepare to create {branch}"
            _emit(outcome, json_output=json_output, stdout=stdout)
            return 3
        root = Path(tempfile.mkdtemp(prefix="skynet-rollback."))
        root.rmdir()
        worktree = root
        result = _run(
            ["git", "-C", str(repo), "worktree", "add", "-b", branch, str(worktree), base],
            timeout,
            reason="rollback worktree creation failed",
        )
        del result
        outcome.completed_steps.append("review-worktree-created")
        revert_args = ["git", "-C", str(worktree), "revert", "--no-edit"]
        if len(parent_line) > 2:
            revert_args.extend(["-m", "1"])
        revert_args.append(revision)
        try:
            _run(revert_args, timeout, reason="rollback revert conflicted")
        except GitOpsError:
            keep_worktree = True
            outcome.detail["conflict_worktree"] = str(worktree)
            outcome.recovery = "manual conflict resolution required; nothing was pushed or merged"
            raise
        outcome.completed_steps.append("revert-commit-created")
        try:
            _run(
                ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                timeout,
                reason="prepared rollback worktree cleanup failed",
            )
        except GitOpsError:
            keep_worktree = True
            outcome.detail["review_worktree"] = str(worktree)
            outcome.recovery = "rollback branch prepared but worktree cleanup failed; inspect the retained worktree"
            raise
        worktree = None
        outcome.completed_steps.append("review-worktree-cleaned")
        outcome.status = "prepared"
        outcome.verification = "local-review-branch-prepared"
        outcome.recovery = "review, push, and human-merge the branch"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 0
    except GitOpsError as error:
        outcome.reason = error.reason
        outcome.verification = "partial" if outcome.completed_steps else "failed-closed"
        if outcome.recovery == "not-needed":
            outcome.recovery = "nothing was pushed or merged"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return error.code
    except (OSError, subprocess.SubprocessError, ValueError):
        outcome.reason = "rollback preparation unavailable"
        outcome.verification = "partial" if outcome.completed_steps else "failed-closed"
        outcome.recovery = "nothing was pushed or merged"
        _emit(outcome, json_output=json_output, stdout=stdout)
        return 3
    finally:
        if worktree is not None and not keep_worktree:
            try:
                _run(
                    ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                    timeout,
                    reason="rollback worktree cleanup failed",
                )
            except GitOpsError:
                pass
