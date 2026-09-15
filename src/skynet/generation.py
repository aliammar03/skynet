"""Prepare immutable Compose generations from exact Git revisions.

This module owns the preparation half of the P11 deployment path.  It reads only Git
objects for the selected local branch head, decrypts the optional encrypted environment
in memory, and sends one bounded payload to the existing ``svc-ops`` SSH capability.  The
remote script validates the generation with Docker Compose before atomically publishing it
under the revision named directory.

Preparation has no runtime activation side effect.  A failed or ambiguous remote write is
reported without retaining remote command output; repeating the same preparation reconciles
an already published generation through its public release manifest.
"""

from __future__ import annotations

import io
import json
import os
import re
import shlex
import signal
import subprocess
import tarfile
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Final, Mapping


DEFAULT_AGE_KEY = Path("/opt/skynet-ops/secrets/age.key")
DEFAULT_BRANCH = "main"
DEFAULT_HOST = "10.10.100.15"
DEFAULT_STATE_ROOT = "/home/svc-ops/.local/state/skynet-deploy"
DEFAULT_TIMEOUT = 30.0

MAX_COMMAND_OUTPUT = 64 * 1024
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 1024
MAX_ENV_BYTES = 256 * 1024
SSH_GRACE = 5.0

_SERVICE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_REVISION = re.compile(r"[0-9a-f]{40}")
_OBJECT_ID = re.compile(r"[0-9a-f]{40,64}")
_HOST = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?")
_PREPARED_AT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_RELEASE_KEYS = frozenset(
    {
        "schema",
        "service",
        "revision",
        "source_tree",
        "compose_input",
        "env_git_input",
        "env_sops_input",
        "prepared_at",
    }
)
MAX_RELEASE_BYTES = 4096


class GenerationError(Exception):
    """A safe preparation outcome with no command or secret text attached."""

    def __init__(self, reason: str, code: int = 1, *, ambiguous: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.code = code
        self.ambiguous = ambiguous


@dataclass(frozen=True)
class SourceIdentity:
    """Public Git identities bound to one exact service revision."""

    service: str
    revision: str
    source_tree: str
    compose_input: str
    env_git_input: str
    env_sops_input: str | None

    @property
    def tree(self) -> str:
        """Compatibility spelling for callers that call the source tree ``tree``."""
        return self.source_tree

    @property
    def compose_blob(self) -> str:
        """Compatibility spelling for the Compose input blob identity."""
        return self.compose_input


@dataclass(frozen=True)
class PreparedGeneration:
    """The non-secret result of a published or reused immutable generation."""

    service: str
    revision: str
    path: str
    release: Mapping[str, object]
    reused: bool
    source: SourceIdentity

    @property
    def generation_path(self) -> str:
        """The remote generation directory."""
        return self.path


@dataclass(frozen=True)
class _SourceBundle:
    identity: SourceIdentity
    runtime_files: Mapping[str, tuple[bytes, int]]
    env_git: bytes
    env_sops: bytes | None


def _validate_service(service: str) -> str:
    if not isinstance(service, str) or _SERVICE.fullmatch(service) is None:
        raise GenerationError("invalid service identity", 2)
    return service


def _validate_revision(revision: str) -> str:
    if not isinstance(revision, str) or _REVISION.fullmatch(revision.lower()) is None:
        raise GenerationError("selected Git revision is malformed", 2)
    return revision.lower()


def _validate_branch(branch: str) -> str:
    if not isinstance(branch, str) or not branch:
        raise GenerationError("invalid branch identity", 2)
    if any(ord(char) < 33 or ord(char) == 127 for char in branch):
        raise GenerationError("invalid branch identity", 2)
    return branch


def _validate_timeout(timeout: float) -> float:
    if not isinstance(timeout, (int, float)) or not 1.0 <= float(timeout) <= 300.0:
        raise GenerationError("timeout must be between 1 and 300 seconds", 2)
    return float(timeout)


def _validate_host(host: str) -> str:
    if not isinstance(host, str) or _HOST.fullmatch(host) is None or "@" in host:
        raise GenerationError("invalid Docker host identity", 2)
    return host


def _validate_state_root(state_root: str) -> str:
    if not isinstance(state_root, str) or not state_root.startswith("/"):
        raise GenerationError("invalid deployment state root", 2)
    if re.fullmatch(r"/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", state_root) is None:
        raise GenerationError("invalid deployment state root", 2)
    pure = PurePosixPath(state_root)
    if str(pure) != state_root or ".." in pure.parts:
        raise GenerationError("invalid deployment state root", 2)
    return state_root


def _terminate(process: subprocess.Popen[bytes]) -> None:
    """Terminate and reap one process group without retaining child output."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except OSError:
        pass
    try:
        process.wait(timeout=0.5)
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        pass
    try:
        process.wait(timeout=1.0)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _run(
    args: list[str],
    timeout: float,
    *,
    input_bytes: bytes | None = None,
    reason: str,
    env: Mapping[str, str] | None = None,
    max_output: int = MAX_COMMAND_OUTPUT,
    ambiguous_on_failure: bool = False,
) -> bytes:
    """Run a bounded command and discard all stderr, including on failure.

    The process has its own session so timeout cleanup cannot leave an SSH or sops child
    running.  Stdout is drained concurrently and capped; stderr is sent directly to the
    null device so a failing command can never retain secret-bearing diagnostics.
    """
    if timeout <= 0 or max_output <= 0:
        raise GenerationError(reason, 3, ambiguous=ambiguous_on_failure)
    try:
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=dict(env) if env is not None else None,
            start_new_session=True,
        )
    except OSError:
        raise GenerationError(reason, 3, ambiguous=ambiguous_on_failure) from None

    assert process.stdout is not None
    stdout = process.stdout
    chunks: list[bytes] = []
    output_size = 0
    output_oversized = False
    stream_error: list[BaseException] = []

    def drain() -> None:
        nonlocal output_size, output_oversized
        try:
            while True:
                chunk = stdout.read(8192)
                if not chunk:
                    return
                if output_size < max_output:
                    room = max_output - output_size
                    chunks.append(chunk[:room])
                output_size += len(chunk)
                if output_size > max_output:
                    output_oversized = True
        except (OSError, ValueError) as error:
            stream_error.append(error)

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()

    write_error: list[BaseException] = []
    writer: threading.Thread | None = None
    if input_bytes is not None:

        def feed() -> None:
            assert process.stdin is not None
            try:
                process.stdin.write(input_bytes)
            except (BrokenPipeError, OSError, ValueError) as error:
                write_error.append(error)
            finally:
                try:
                    process.stdin.close()
                except (OSError, ValueError):
                    pass

        writer = threading.Thread(target=feed, daemon=True)
        writer.start()

    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate(process)

    workers = [reader] + ([writer] if writer is not None else [])
    for worker in workers:
        worker.join(timeout=1.0)
    if any(worker.is_alive() for worker in workers):
        _terminate(process)
        for worker in workers:
            worker.join(timeout=1.0)

    try:
        if process.stdin is not None:
            process.stdin.close()
        stdout.close()
    except (OSError, ValueError):
        pass

    ambiguous = ambiguous_on_failure or input_bytes is not None and (timed_out or bool(write_error))
    if timed_out or any(worker.is_alive() for worker in workers):
        raise GenerationError(reason, 3, ambiguous=ambiguous) from None
    if stream_error or write_error:
        raise GenerationError(reason, 3, ambiguous=ambiguous) from None
    if output_oversized:
        raise GenerationError(f"{reason}: output exceeded bound", 3, ambiguous=ambiguous) from None
    if process.returncode != 0:
        raise GenerationError(reason, 3, ambiguous=ambiguous) from None
    return b"".join(chunks)


def _git(
    repo: Path,
    arguments: list[str],
    timeout: float,
    reason: str,
    *,
    max_output: int = MAX_COMMAND_OUTPUT,
) -> bytes:
    return _run(
        ["git", "-C", str(repo), *arguments],
        timeout,
        reason=reason,
        max_output=max_output,
    )


def _git_text(
    repo: Path,
    arguments: list[str],
    timeout: float,
    reason: str,
    *,
    max_output: int = MAX_COMMAND_OUTPUT,
) -> str:
    raw = _git(repo, arguments, timeout, reason, max_output=max_output)
    try:
        return raw.decode("utf-8").strip()
    except UnicodeError:
        raise GenerationError(reason, 3) from None


def resolve_revision(
    repo: Path, branch: str = DEFAULT_BRANCH, timeout: float = DEFAULT_TIMEOUT
) -> str:
    """Resolve one local branch head to a lowercase full commit identity."""
    branch = _validate_branch(branch)
    timeout = _validate_timeout(timeout)
    if not repo.is_dir():
        raise GenerationError("Git checkout is unavailable", 3)
    _git(repo, ["check-ref-format", "--branch", branch], timeout, "invalid branch identity")
    revision = _git_text(
        repo,
        [
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"refs/heads/{branch}",
        ],
        timeout,
        "selected local branch head is unavailable",
    ).lower()
    revision = _validate_revision(revision)
    _ensure_commit(repo, revision, timeout)
    return revision


def _validate_object_id(value: str, reason: str) -> str:
    if _OBJECT_ID.fullmatch(value.lower()) is None:
        raise GenerationError(reason, 3)
    return value.lower()


def _ensure_commit(repo: Path, revision: str, timeout: float) -> None:
    """Require the selected object itself to be a commit object."""
    object_type = _git_text(
        repo,
        ["cat-file", "-t", revision],
        timeout,
        "selected Git revision is unavailable",
    )
    if object_type != "commit":
        raise GenerationError("selected Git revision is not a commit", 2)


def _tree_identity(repo: Path, revision: str, service: str, timeout: float) -> str:
    tree_id = _git_text(
        repo,
        ["rev-parse", "--verify", f"{revision}:compose/{service}"],
        timeout,
        "selected service tree is unavailable",
    )
    tree_id = _validate_object_id(tree_id, "selected service tree is malformed")
    object_type = _git_text(
        repo,
        ["cat-file", "-t", tree_id],
        timeout,
        "selected service tree is unavailable",
    )
    if object_type != "tree":
        raise GenerationError("selected service tree is malformed", 3)
    return tree_id


def _blob(repo: Path, object_id: str, timeout: float) -> bytes:
    return _git(
        repo,
        ["cat-file", "blob", object_id],
        timeout,
        "selected service input is unavailable",
        max_output=MAX_FILE_BYTES,
    )


def _tree_path(raw_path: bytes, prefix: str) -> str:
    """Decode and validate one raw ``ls-tree -z`` path below the service tree."""
    try:
        path = raw_path.decode("utf-8")
    except UnicodeDecodeError:
        raise GenerationError("malformed Git service path", 3) from None
    if (
        not path.startswith(prefix + "/")
        or "\\" in path
        or any(ord(char) < 33 or ord(char) == 127 for char in path)
    ):
        raise GenerationError("unsafe Git service path", 2)
    relative = path[len(prefix) + 1 :]
    pure = PurePosixPath(relative)
    if (
        not relative
        or relative.startswith("/")
        or str(pure) != relative
        or any(part in {"", ".", ".."} for part in pure.parts)
        or len(relative) > 512
    ):
        raise GenerationError("unsafe Git service path", 2)
    return relative


def _tree_files(
    repo: Path, revision: str, service: str, timeout: float
) -> dict[str, tuple[str, int]]:
    """Return every regular file in the exact Git service tree.

    ``git archive`` is deliberately not used here: its export-ignore attributes can omit
    committed runtime files.  Raw recursive tree entries are validated before any blob is
    materialized, so symlinks, submodules, malformed modes, and path escapes fail closed.
    """
    prefix = f"compose/{service}"
    raw = _git(
        repo,
        ["ls-tree", "--full-tree", "-r", "-z", revision, "--", prefix],
        timeout,
        "selected service tree is unavailable",
        max_output=MAX_ARCHIVE_BYTES,
    )
    if not raw or not raw.endswith(b"\0"):
        raise GenerationError("selected service Compose inputs are incomplete", 2)
    entries: dict[str, tuple[str, int]] = {}
    records = raw[:-1].split(b"\0")
    if len(records) > MAX_ARCHIVE_MEMBERS:
        raise GenerationError("selected service tree contained too many entries", 3)
    for record in records:
        if not record:
            raise GenerationError("malformed Git service tree", 3)
        try:
            metadata, raw_path = record.split(b"\t", 1)
            fields = metadata.split(b" ")
            if len(fields) != 3:
                raise ValueError
            raw_mode, raw_kind, raw_object = fields
            mode = raw_mode.decode("ascii")
            kind = raw_kind.decode("ascii")
            object_id = _validate_object_id(
                raw_object.decode("ascii"), "malformed Git service object identity"
            )
            mode_int = int(mode, 8)
        except (UnicodeDecodeError, ValueError):
            raise GenerationError("malformed Git service tree", 3) from None
        relative = _tree_path(raw_path, prefix)
        if relative in entries:
            raise GenerationError("duplicate Git service path", 3)
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise GenerationError("selected service tree contains an unsafe file type", 2)
        if relative in {".env", "project.env"}:
            raise GenerationError("plaintext environment input is not allowed", 2)
        entries[relative] = (object_id, mode_int)
    if "compose.yaml" not in entries or ".env.git" not in entries:
        raise GenerationError("selected service Compose inputs are incomplete", 2)
    return entries


def _source_bundle(repo: Path, service: str, revision: str, timeout: float) -> _SourceBundle:
    tree_id = _tree_identity(repo, revision, service, timeout)
    entries = _tree_files(repo, revision, service, timeout)
    compose_id, _ = entries["compose.yaml"]
    env_git_id, _ = entries[".env.git"]
    runtime: dict[str, tuple[bytes, int]] = {}
    env_git: bytes | None = None
    env_sops: bytes | None = None
    env_sops_id: str | None = None
    for relative, (object_id, mode) in entries.items():
        content = _blob(repo, object_id, timeout)
        if relative == ".env.git":
            env_git = content
        elif relative == ".env.sops":
            env_sops_id = object_id
            env_sops = content
        else:
            runtime[relative] = (content, mode)
    if env_git is None:
        raise GenerationError("selected service Compose inputs are incomplete", 2)
    identity = SourceIdentity(
        service=service,
        revision=revision,
        source_tree=tree_id,
        compose_input=compose_id,
        env_git_input=env_git_id,
        env_sops_input=env_sops_id,
    )
    return _SourceBundle(identity, runtime, env_git, env_sops)


def _environment(env_git: bytes, env_sops: bytes | None, age_key: Path, timeout: float) -> bytes:
    """Layer dotenv bytes while keeping decrypted output in memory only."""
    chunks: list[bytes] = []
    if len(env_git) > MAX_ENV_BYTES:
        raise GenerationError("effective environment exceeded bound", 3)
    try:
        decoded = env_git.decode("utf-8")
    except UnicodeError:
        raise GenerationError("effective environment is not UTF-8", 2) from None
    if "\x00" in decoded:
        raise GenerationError("effective environment contains an unsafe value", 2)
    chunks.append(env_git.rstrip(b"\n") + b"\n")
    if env_sops is not None:
        if len(env_sops) > MAX_FILE_BYTES:
            raise GenerationError("encrypted environment exceeded bound", 3)
        environment = os.environ.copy()
        environment["SOPS_AGE_KEY_FILE"] = str(age_key)
        decrypted = _run(
            ["sops", "-d", "--input-type", "dotenv", "--output-type", "dotenv", "/dev/stdin"],
            timeout,
            input_bytes=env_sops,
            reason="service secrets could not be decrypted",
            env=environment,
            max_output=MAX_ENV_BYTES,
        )
        try:
            decoded = decrypted.decode("utf-8")
        except UnicodeError:
            raise GenerationError("decrypted environment is not UTF-8", 2) from None
        if "\x00" in decoded:
            raise GenerationError("decrypted environment contains an unsafe value", 2) from None
        chunks.append(decrypted.rstrip(b"\n") + b"\n")
    result = b"".join(chunks)
    if len(result) > MAX_ENV_BYTES:
        raise GenerationError("effective environment exceeded bound", 3)
    return result


def _payload(runtime_files: Mapping[str, tuple[bytes, int]], environment: bytes) -> bytes:
    """Build a safe, in-memory tar stream for the remote staging directory."""
    all_files: dict[str, tuple[bytes, int]] = dict(runtime_files)
    all_files[".env"] = (environment, 0o600)
    for path in all_files:
        pure = PurePosixPath(path)
        if (
            not path
            or path.startswith("/")
            or "\\" in path
            or str(pure) != path
            or ".." in pure.parts
            or any(ord(char) < 33 or ord(char) == 127 for char in path)
        ):
            raise GenerationError("unsafe service runtime path", 2)
    if len(all_files) > MAX_ARCHIVE_MEMBERS:
        raise GenerationError("service runtime contained too many files", 3)
    total = sum(len(content) for content, _ in all_files.values())
    if total > MAX_ARCHIVE_BYTES:
        raise GenerationError("service runtime exceeded bound", 3)
    directories: set[str] = set()
    for path in all_files:
        parent = PurePosixPath(path).parent
        while parent != PurePosixPath("."):
            directories.add(str(parent))
            parent = parent.parent
    destination = io.BytesIO()
    try:
        with tarfile.open(fileobj=destination, mode="w", format=tarfile.GNU_FORMAT) as stream:
            for directory in sorted(directories, key=lambda item: (item.count("/"), item)):
                info = tarfile.TarInfo(directory + "/")
                info.type = tarfile.DIRTYPE
                info.mode = 0o700
                info.mtime = 0
                stream.addfile(info)
            for path in sorted(all_files):
                content, mode = all_files[path]
                info = tarfile.TarInfo(path)
                info.size = len(content)
                info.mode = mode & 0o777 or 0o600
                info.mtime = 0
                stream.addfile(info, io.BytesIO(content))
    except (OSError, tarfile.TarError, ValueError):
        raise GenerationError("service runtime archive could not be built", 3) from None
    payload = destination.getvalue()
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise GenerationError("service runtime archive exceeded bound", 3)
    return payload


def _release(identity: SourceIdentity) -> tuple[dict[str, object], str]:
    """Create the small public release manifest and its canonical JSON form."""
    manifest: dict[str, object] = {
        "schema": 1,
        "service": identity.service,
        "revision": identity.revision,
        "source_tree": identity.source_tree,
        "compose_input": identity.compose_input,
        "env_git_input": identity.env_git_input,
        "env_sops_input": identity.env_sops_input,
        "prepared_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    try:
        encoded = json.dumps(manifest, ensure_ascii=True, separators=(",", ":")) + "\n"
    except (TypeError, ValueError):
        raise GenerationError("release manifest could not be encoded", 3) from None
    return manifest, encoded


def _unique_release_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON keys before validating the public release schema."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if not isinstance(key, str) or key in result:
            raise ValueError
        result[key] = value
    return result


def _validated_remote_release(
    output: bytes, marker: str, expected: Mapping[str, object]
) -> dict[str, object]:
    """Decode only the bounded, non-secret release manifest returned by the host."""
    if len(output) > MAX_RELEASE_BYTES:
        raise GenerationError("remote generation result exceeded bound", 3, ambiguous=True)
    try:
        text = output.decode("utf-8")
        marker_line, separator, encoded = text.partition("\n")
        if marker_line != marker or not separator or not encoded:
            raise ValueError
        value = json.loads(encoded, object_pairs_hook=_unique_release_pairs)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        raise GenerationError("remote generation result is malformed", 3, ambiguous=True) from None
    if not isinstance(value, dict) or set(value) != _RELEASE_KEYS:
        raise GenerationError("remote release manifest is malformed", 3, ambiguous=True)
    if value.get("schema") != 1 or isinstance(value.get("schema"), bool):
        raise GenerationError("remote release manifest is malformed", 3, ambiguous=True)
    if any(value.get(key) != expected.get(key) for key in _RELEASE_KEYS - {"prepared_at"}):
        raise GenerationError("remote release identity does not match prepared input", 3, ambiguous=True)
    prepared_at = value.get("prepared_at")
    if not isinstance(prepared_at, str) or _PREPARED_AT.fullmatch(prepared_at) is None:
        raise GenerationError("remote release manifest is malformed", 3, ambiguous=True)
    try:
        datetime.fromisoformat(prepared_at.removesuffix("Z") + "+00:00")
    except ValueError:
        raise GenerationError("remote release manifest is malformed", 3, ambiguous=True) from None
    return value


def _ssh_command(host: str, timeout: float, command: str) -> list[str]:
    return [
        "ssh",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={max(1, int(timeout))}",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=1",
        f"svc-ops@{host}",
        command,
    ]


def _remote_prepare_script(
    service: str, revision: str, state_root: str, release_json: str
) -> str:
    """Return a fixed shell transaction; all dynamic values are shell-quoted."""
    root = shlex.quote(state_root)
    service_arg = shlex.quote(service)
    revision_arg = shlex.quote(revision)
    release_arg = shlex.quote(release_json.rstrip("\n"))
    return f"""set -eu
root={root}
service={service_arg}
revision={revision_arg}
expected_release={release_arg}
uid=$(id -u) || exit 44
gid=$(id -g) || exit 44
state_parent="$root"
while [ ! -e "$state_parent" ] && [ ! -L "$state_parent" ]; do
  next_parent=$(dirname -- "$state_parent") || exit 41
  [ "$next_parent" != "$state_parent" ] || exit 42
  state_parent="$next_parent"
done
[ -d "$state_parent" ] && [ ! -L "$state_parent" ] || exit 43
resolved_parent=$(readlink -f -- "$state_parent") || exit 44
[ "$resolved_parent" = "$state_parent" ] || exit 45
parent_owner=$(stat -c '%u:%g' -- "$state_parent") || exit 46
[ "$parent_owner" = "$uid:$gid" ] || exit 47
parent_mode=$(stat -c '%a' -- "$state_parent") || exit 48
parent_restricted=${{parent_mode#?}}
case "$parent_restricted" in *[2367]*) exit 49;; esac
if [ "$state_parent" = "$root" ]; then
  relative_root=
else
  relative_root=${{root#"$state_parent"/}}
fi
path="$state_parent"
old_ifs="$IFS"
IFS=/
set -- $relative_root
IFS="$old_ifs"
for component in "$@"; do
  path="$path/$component"
  if [ -e "$path" ] || [ -L "$path" ]; then
    [ -d "$path" ] && [ ! -L "$path" ] || exit 50
    component_owner=$(stat -c '%u:%g' -- "$path") || exit 51
    [ "$component_owner" = "$uid:$gid" ] || exit 52
    component_mode=$(stat -c '%a' -- "$path") || exit 53
    component_restricted=${{component_mode#?}}
    case "$component_restricted" in *[2367]*) exit 54;; esac
  else
    mkdir -- "$path" || exit 55
    chmod 700 -- "$path" || exit 56
  fi
done
[ "$path" = "$root" ] || exit 57
root_mode=$(stat -c '%a' -- "$root") || exit 58
[ "$root_mode" = 700 ] || exit 59
owner=$(stat -c '%u:%g' -- "$root") || exit 60
[ "$owner" = "$uid:$gid" ] || exit 61
base="$root/$service"
if [ -e "$base" ] || [ -L "$base" ]; then
  [ -d "$base" ] && [ ! -L "$base" ] || exit 62
  base_owner=$(stat -c '%u:%g' -- "$base") || exit 63
  [ "$base_owner" = "$uid:$gid" ] || exit 64
  chmod 700 -- "$base" || exit 65
else
  mkdir -- "$base" || exit 66
  chmod 700 -- "$base" || exit 67
fi
generations="$base/generations"
if [ -e "$generations" ] || [ -L "$generations" ]; then
  [ -d "$generations" ] && [ ! -L "$generations" ] || exit 68
else
  mkdir -- "$generations" || exit 69
fi
chmod 700 -- "$generations" || exit 70
stage=$(mktemp -d "$base/.generation-stage.XXXXXX") || exit 71
cleanup() {{ rm -rf -- "$stage"; }}
trap cleanup 0 1 2 3 15
tar -xf - -C "$stage" --no-same-owner --no-same-permissions --no-overwrite-dir || exit 72
if [ -n "$(find "$stage" -type l -print -quit)" ]; then exit 73; fi
[ -f "$stage/compose.yaml" ] && [ ! -L "$stage/compose.yaml" ] || exit 74
[ -f "$stage/.env" ] && [ ! -L "$stage/.env" ] || exit 75
docker compose --project-name "$service" --project-directory "$stage" --env-file "$stage/.env" -f "$stage/compose.yaml" config --quiet >/dev/null 2>&1 || exit 78
find "$stage" -type d -exec chmod 700 {{}} + || exit 76
find "$stage" -type f -exec chmod 600 {{}} + || exit 77
printf '%s\\n' "$expected_release" > "$stage/release.json" || exit 79
chmod 600 -- "$stage/release.json" || exit 80
target="$generations/$revision"
same_release() {{
  [ -d "$target" ] && [ ! -L "$target" ] || return 1
  [ -f "$target/release.json" ] && [ ! -L "$target/release.json" ] || return 1
  target_owner=$(stat -c '%u:%g' -- "$target") || return 1
  [ "$target_owner" = "$uid:$gid" ] || return 1
  target_mode=$(stat -c '%a' -- "$target") || return 1
  [ "$target_mode" = 700 ] || return 1
  for required_file in compose.yaml .env release.json; do
    required_path="$target/$required_file"
    [ -f "$required_path" ] && [ ! -L "$required_path" ] || return 1
    required_owner=$(stat -c '%u:%g' -- "$required_path") || return 1
    [ "$required_owner" = "$uid:$gid" ] || return 1
    required_mode=$(stat -c '%a' -- "$required_path") || return 1
    [ "$required_mode" = 600 ] || return 1
  done
  if [ -n "$(find "$target" -mindepth 1 ! \\( -type d -o -type f \\) -print -quit)" ]; then return 1; fi
  if [ -n "$(find "$target" ! -uid "$uid" -print -quit)" ]; then return 1; fi
  if [ -n "$(find "$target" -type d ! -perm 700 -print -quit)" ]; then return 1; fi
  if [ -n "$(find "$target" -type f ! -perm 600 -print -quit)" ]; then return 1; fi
  if ! diff -qr --exclude=release.json -- "$stage" "$target" >/dev/null 2>&1; then return 1; fi
  docker compose --project-name "$service" --project-directory "$target" --env-file "$target/.env" -f "$target/compose.yaml" config --quiet >/dev/null 2>&1 || return 1
  expected_identity=$(sed -E 's/,"prepared_at":"[^\"]+"}}$//' "$stage/release.json") || return 1
  actual_identity=$(sed -E 's/,"prepared_at":"[^\"]+"}}$//' "$target/release.json") || return 1
  [ "$expected_identity" = "$actual_identity" ]
}}
if [ -e "$target" ] || [ -L "$target" ]; then
  if same_release; then
    cleanup
    trap - 0 1 2 3 15
    printf '%s\\n' GENERATION_REUSED
    cat -- "$target/release.json" || exit 81
    exit 0
  fi
  exit 66
fi
if mv -T -- "$stage" "$target"; then
  trap - 0 1 2 3 15
  printf '%s\\n' GENERATION_PUBLISHED
  cat -- "$target/release.json" || exit 82
  exit 0
fi
if same_release; then
  cleanup
  trap - 0 1 2 3 15
  printf '%s\\n' GENERATION_REUSED
  cat -- "$target/release.json" || exit 83
  exit 0
fi
exit 67
"""


def _publish(
    payload: bytes,
    service: str,
    revision: str,
    state_root: str,
    host: str,
    release_json: str,
    expected_release: Mapping[str, object],
    timeout: float,
) -> tuple[bool, dict[str, object]]:
    script = _remote_prepare_script(service, revision, state_root, release_json)
    try:
        output = _run(
            _ssh_command(host, timeout, script),
            timeout + SSH_GRACE,
            input_bytes=payload,
            reason="remote generation preparation failed",
            max_output=4096,
            ambiguous_on_failure=True,
        )
    except GenerationError as error:
        raise GenerationError(error.reason, error.code, ambiguous=True) from None
    try:
        marker_line = output.split(b"\n", 1)[0].decode("ascii")
    except (IndexError, UnicodeDecodeError):
        raise GenerationError("remote generation result is malformed", 3, ambiguous=True) from None
    if marker_line not in {"GENERATION_PUBLISHED", "GENERATION_REUSED"}:
        raise GenerationError("remote generation result is malformed", 3, ambiguous=True)
    release = _validated_remote_release(output, marker_line, expected_release)
    return marker_line == "GENERATION_REUSED", release


def prepare_generation(
    service: str,
    repo: Path,
    *,
    branch: str = DEFAULT_BRANCH,
    host: str = DEFAULT_HOST,
    state_root: str = DEFAULT_STATE_ROOT,
    age_key: Path = DEFAULT_AGE_KEY,
    timeout: float = DEFAULT_TIMEOUT,
    revision: str | None = None,
) -> PreparedGeneration:
    """Prepare and atomically publish one exact Git service generation.

    ``revision`` is an optional already-resolved full commit.  When omitted, the local
    ``refs/heads/<branch>`` head is resolved at the beginning of this call.  The function
    returns only public identities and the remote generation path; the effective environment
    is never serialized into the result.
    """
    service = _validate_service(service)
    branch = _validate_branch(branch)
    host = _validate_host(host)
    state_root = _validate_state_root(state_root)
    timeout = _validate_timeout(timeout)
    selected_revision = (
        resolve_revision(repo, branch, timeout)
        if revision is None
        else _validate_revision(revision)
    )
    _ensure_commit(repo, selected_revision, timeout)
    if revision is not None:
        branch_head = resolve_revision(repo, branch, timeout)
        if selected_revision != branch_head:
            raise GenerationError("requested Git revision is not the current local branch head", 2)
    bundle = _source_bundle(repo, service, selected_revision, timeout)
    environment = _environment(bundle.env_git, bundle.env_sops, age_key, timeout)
    payload = _payload(bundle.runtime_files, environment)
    manifest, release_json = _release(bundle.identity)
    reused, retained_release = _publish(
        payload,
        service,
        selected_revision,
        state_root,
        host,
        release_json,
        manifest,
        timeout,
    )
    path = f"{state_root}/{service}/generations/{selected_revision}"
    return PreparedGeneration(service, selected_revision, path, retained_release, reused, bundle.identity)


def prepare_revision(
    service: str,
    revision: str,
    repo: Path,
    *,
    branch: str = DEFAULT_BRANCH,
    host: str = DEFAULT_HOST,
    state_root: str = DEFAULT_STATE_ROOT,
    age_key: Path = DEFAULT_AGE_KEY,
    timeout: float = DEFAULT_TIMEOUT,
) -> PreparedGeneration:
    """Prepare a caller-supplied full revision bound to the selected branch head."""
    return prepare_generation(
        service,
        repo,
        branch=branch,
        host=host,
        state_root=state_root,
        age_key=age_key,
        timeout=timeout,
        revision=revision,
    )


prepare = prepare_generation


__all__: Final = [
    "DEFAULT_AGE_KEY",
    "DEFAULT_BRANCH",
    "DEFAULT_HOST",
    "DEFAULT_STATE_ROOT",
    "DEFAULT_TIMEOUT",
    "GenerationError",
    "PreparedGeneration",
    "SourceIdentity",
    "prepare",
    "prepare_generation",
    "prepare_revision",
    "resolve_revision",
]
