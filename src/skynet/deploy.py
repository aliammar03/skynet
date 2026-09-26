"""`skynet deploy`: the one executor that turns a merged `compose/<svc>/` into running containers.

ADR 0008, Docker half. For one service at one merged revision:

- **render** on the ops VM from git objects (never the working tree): `.env.git` + the decrypted
  `.env.sops` become a `0600` `.env` in a tmpfs directory, and Compose itself resolves the project
  to JSON (env inlined, relative paths kept). Every service gets `skynet.revision`/`skynet.service`.
- **stage** the non-secret files as an immutable release `/opt/docker/services/<svc>/<rev>/` on the
  Docker host, written by a pinned throwaway container over the Docker context.
- **up**: `docker compose -f -` over the context with the resolved JSON on stdin and the release
  as project directory, so relative mounts see that revision's files. Secrets travel only through
  the pipe; no `.env` exists on the Docker host.
- **verify** with `deployment.verify`; on failure **roll back** to the host's `verified` revision,
  mark the failed revision, and open a revert PR that makes `main` match what runs.

Host facts live beside the releases: `verified` (the rollback target) and `failed` (a revision
`--pending` will not retry until `main` moves).
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from skynet import deployment, writepath
from skynet.writepath import FAILED, UNAVAILABLE, USAGE, Ledger, Operation, WriteError

MAIN = "origin/main"
RELEASES = "/opt/docker/services"
AGE_KEY = "/opt/skynet-ops/secrets/age.key"
# Pinned throwaway image for host-side release and fact files; nothing else runs in it.
BUSYBOX = "busybox@sha256:dc2d74b28e4cf8984fa52af1f39bc7c3d9c73760b41a74d629f5d11b1ab28616"
KEEP_RELEASES = 5
WAIT_SECONDS = 300
FACTS = ("verified", "failed")
SKIPPED_FILES = {".env.git", ".env.sops"}
_KEY = re.compile(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
_MANUAL = re.compile(r"^x-skynet:\s*\n(?:[ \t]+.*\n)*?[ \t]+deploy:\s*manual\s*$", re.MULTILINE)
_DOCKER_ENV = ("PATH", "HOME", "USER", "LANG", "SSH_AUTH_SOCK", "DOCKER_CONFIG", "XDG_RUNTIME_DIR")


# --- commands --------------------------------------------------------------------------------

def _run(args: list[str], *, stdin: bytes | None = None, timeout: float = 60.0,
         env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(args, input=stdin, capture_output=True, timeout=timeout, env=env,
                              cwd=cwd, check=False)
    except subprocess.TimeoutExpired:
        raise WriteError(f"{args[0]} timed out", UNAVAILABLE) from None
    except (OSError, subprocess.SubprocessError):
        raise WriteError(f"{args[0]} unavailable", UNAVAILABLE) from None


def _ok(args: list[str], reason: str, code: int = UNAVAILABLE, **kwargs: Any) -> bytes:
    result = _run(args, **kwargs)
    if result.returncode != 0:
        raise WriteError(reason, code)
    return result.stdout


def docker_env() -> dict[str, str]:
    """Only what Docker needs: shell variables must not shadow a service's interpolation."""
    return {key: os.environ[key] for key in _DOCKER_ENV if key in os.environ}


def _sops_env() -> dict[str, str]:
    env = {key: os.environ[key] for key in ("PATH", "HOME") if key in os.environ}
    env["SOPS_AGE_KEY_FILE"] = os.environ.get("SOPS_AGE_KEY_FILE", AGE_KEY)
    return env


# --- git -------------------------------------------------------------------------------------

def _git(repo: Path, *args: str, reason: str = "git unavailable") -> str:
    return _ok(["git", "-C", str(repo), *args], reason).decode("utf-8", "replace").strip()


def fetch(repo: Path) -> None:
    _git(repo, "fetch", "--quiet", "origin", "main", reason="git fetch of origin/main failed")


def resolve(repo: Path, ref: str) -> str:
    if ref.startswith("-"):
        raise WriteError("invalid revision", USAGE)
    revision = _git(repo, "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}",
                    reason="revision not found")
    if not deployment.REVISION.fullmatch(revision):
        raise WriteError("revision not found", USAGE)
    return revision


def merged(repo: Path, revision: str) -> bool:
    result = _run(["git", "-C", str(repo), "merge-base", "--is-ancestor", revision, MAIN])
    if result.returncode not in (0, 1):
        raise WriteError("git unavailable", UNAVAILABLE)
    return result.returncode == 0


def services(repo: Path, ref: str = MAIN) -> list[str]:
    """Every compose project on `ref`, in name order."""
    paths = _git(repo, "ls-tree", "-r", "--name-only", ref, "--", "compose").splitlines()
    return sorted(match[1] for path in paths
                  if (match := re.fullmatch(r"compose/([A-Za-z0-9][A-Za-z0-9_.-]*)/compose\.yaml", path)))


def service_revision(repo: Path, service: str, ref: str = MAIN) -> str | None:
    """The newest commit on `ref` that touched `compose/<service>/`; None if absent there."""
    if service not in services(repo, ref):
        return None
    revision = _git(repo, "log", "-1", "--format=%H", ref, "--", f"compose/{service}/")
    return revision if deployment.REVISION.fullmatch(revision) else None


def manual(repo: Path, service: str, ref: str) -> bool:
    """`x-skynet: {deploy: manual}` opts a project out of the executor (read without rendering)."""
    text = _git(repo, "show", f"{ref}:compose/{service}/compose.yaml", reason="compose.yaml unreadable")
    return bool(_MANUAL.search(text + "\n"))


def _archive(repo: Path, revision: str, path: str) -> bytes:
    return _ok(["git", "-C", str(repo), "archive", "--format=tar", revision, "--", path],
               "source archive unavailable", timeout=120.0)


@contextmanager
def checkout(repo: Path, revision: str, path: str = "compose") -> Iterator[Path]:
    """A throwaway extraction of `path` at `revision` in tmpfs (removed on exit)."""
    with tempfile.TemporaryDirectory(prefix="skynet-", dir=_runtime_dir()) as tmp:
        with tarfile.open(fileobj=io.BytesIO(_archive(repo, revision, path))) as tar:
            tar.extractall(tmp, filter="data")
        yield Path(tmp)


def _runtime_dir() -> str:
    """A memory-backed directory: rendered env never reaches persistent storage."""
    for candidate in (os.environ.get("XDG_RUNTIME_DIR"), "/dev/shm"):
        if candidate and os.path.isdir(candidate) and os.access(candidate, os.W_OK):
            return candidate
    raise WriteError("no tmpfs runtime directory for rendering", UNAVAILABLE)


# --- render ----------------------------------------------------------------------------------

@dataclass(frozen=True)
class Release:
    """One service at one revision, resolved. `model` holds secret env values: never print it."""

    service: str
    revision: str
    model: dict[str, Any] = field(repr=False)
    files: bytes = field(repr=False)

    @property
    def services(self) -> tuple[str, ...]:
        return tuple(sorted(self.model["services"]))

    @property
    def directory(self) -> str:
        return f"{RELEASES}/{self.service}/{self.revision}"

    def document(self) -> bytes:
        return json.dumps(self.model, sort_keys=True).encode()


def _keys(text: str) -> list[str]:
    return [match[1] for line in text.splitlines() if (match := _KEY.match(line))]


def merge_env(plain: str, secret: str) -> str:
    """`.env.git` then decrypted `.env.sops`; a key defined twice is ambiguous and refused."""
    keys = _keys(plain) + _keys(secret)
    if len(keys) != len(set(keys)):
        raise WriteError("an env key is defined more than once", USAGE)
    return plain.rstrip("\n") + "\n" + secret.rstrip("\n") + "\n"


def _decrypt(encrypted: bytes) -> str:
    return _ok(["sops", "--decrypt", "--input-type", "dotenv", "--output-type", "dotenv", "/dev/stdin"],
               "secret decryption failed", stdin=encrypted, env=_sops_env()).decode("utf-8")


def _release_files(archive: bytes, service: str) -> bytes:
    """The revision's non-secret files, re-rooted at the release directory, owned by root."""
    prefix = f"compose/{service}/"
    output = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(archive)) as source, tarfile.open(fileobj=output, mode="w") as target:
        for member in source.getmembers():
            name = member.name.rstrip("/")
            if not name.startswith(prefix) or Path(name).name in SKIPPED_FILES:
                continue
            if not (member.isfile() or member.isdir()):
                raise WriteError("release may hold only files and directories", USAGE)
            member.name = name[len(prefix):]
            member.uid = member.gid = 0
            member.uname = member.gname = ""
            member.mode = 0o755 if member.isdir() or member.mode & 0o100 else 0o644
            target.addfile(member, source.extractfile(member) if member.isfile() else None)
    return output.getvalue()


def render(repo: Path, service: str, revision: str) -> Release:
    """Resolve one service at one revision with Compose; secrets exist only in tmpfs and memory."""
    if not deployment.NAME.fullmatch(service):
        raise WriteError("invalid service name", USAGE)
    archive = _archive(repo, revision, f"compose/{service}")
    with tempfile.TemporaryDirectory(prefix="skynet-render-", dir=_runtime_dir()) as tmp:
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(tmp, filter="data")
        project = Path(tmp) / "compose" / service
        if not (project / "compose.yaml").is_file():
            raise WriteError("no compose.yaml at the revision", USAGE)
        plain = _read(project / ".env.git")
        secret = _decrypt((project / ".env.sops").read_bytes()) if (project / ".env.sops").is_file() else ""
        descriptor = os.open(project / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(merge_env(plain, secret))
        rendered = _ok(["docker", "compose", "-p", service, "--project-directory", str(project),
                        "-f", str(project / "compose.yaml"), "config", "--format", "json",
                        "--no-path-resolution"], "compose render failed", USAGE, env=docker_env(),
                       cwd=project)  # unresolved paths (env_file) are read relative to the cwd
    try:
        model = json.loads(rendered)
    except ValueError:
        raise WriteError("compose render failed", USAGE) from None
    if not isinstance(model, dict) or model.get("name") != service:
        raise WriteError("compose project name must match its directory", USAGE)
    if not isinstance(model.get("services"), dict) or not model["services"]:
        raise WriteError("compose project declares no services", USAGE)
    for definition in model["services"].values():
        labels = definition.setdefault("labels", {})
        if not isinstance(labels, dict):
            raise WriteError("compose render failed", USAGE)
        labels.update({deployment.REVISION_LABEL: revision, "skynet.service": service})
    return Release(service, revision, model, _release_files(archive, service))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


# --- docker host -----------------------------------------------------------------------------

def _host(context: str, script: str, *args: str, stdin: bytes | None = None,
          read_only: bool = False, reason: str = "Docker host unavailable") -> str:
    """Run a fixed script in the pinned throwaway container with the release root mounted."""
    mount = f"{RELEASES}:/srv" + (":ro" if read_only else "")
    command = ["docker", "--context", context, "run", "--rm", "--network", "none",
               *(["--interactive"] if stdin is not None else []), "--volume", mount, BUSYBOX,
               "sh", "-c", script, "sh", *args]
    return _ok(command, reason, stdin=stdin, env=docker_env(), timeout=120.0).decode("utf-8", "replace")


def stage(context: str, release: Release) -> None:
    """Write the immutable release directory once; an existing one is kept as-is."""
    _host(context, 'set -eu; d="/srv/$1/$2"; if [ -d "$d" ]; then cat >/dev/null; exit 0; fi; '
          'mkdir -p "/srv/$1"; rm -rf "$d.tmp"; mkdir "$d.tmp"; tar -x -C "$d.tmp"; mv "$d.tmp" "$d"',
          release.service, release.revision, stdin=release.files, reason="release staging failed")


@dataclass(frozen=True)
class HostFacts:
    verified: str | None = None
    failed: str | None = None
    releases: tuple[tuple[int, str], ...] = ()


def host_facts(context: str, service: str) -> HostFacts:
    output = _host(context, 'd="/srv/$1"; [ -d "$d" ] || exit 0; '
                   'for f in verified failed; do [ -f "$d/$f" ] && printf "%s=%s\\n" "$f" "$(cat "$d/$f")"; done; '
                   'for r in "$d"/*/; do [ -d "$r" ] && printf "release=%s %s\\n" '
                   '"$(stat -c %Y "$r")" "$(basename "$r")"; done; true',
                   service, read_only=True, reason="host facts unavailable")
    values: dict[str, str] = {}
    releases: list[tuple[int, str]] = []
    for line in output.splitlines():
        key, _, value = line.partition("=")
        if key in FACTS and deployment.REVISION.fullmatch(value):
            values[key] = value
        elif key == "release" and (match := re.fullmatch(r"(\d+) ([0-9a-f]{40})", value)):
            releases.append((int(match[1]), match[2]))
    return HostFacts(values.get("verified"), values.get("failed"), tuple(sorted(releases, reverse=True)))


def set_fact(context: str, service: str, name: str, revision: str | None) -> None:
    if name not in FACTS or revision is not None and not deployment.REVISION.fullmatch(revision):
        raise WriteError("invalid host fact", USAGE)
    _host(context, 'set -eu; mkdir -p "/srv/$1"; if [ -z "$3" ]; then rm -f "/srv/$1/$2"; else '
          'printf "%s\\n" "$3" > "/srv/$1/$2.tmp"; mv "/srv/$1/$2.tmp" "/srv/$1/$2"; fi',
          service, name, revision or "", reason="host fact not written")


def prune(context: str, service: str, keep: set[str]) -> list[str]:
    """Keep the newest releases plus `keep` (verified, running); remove the rest."""
    facts = host_facts(context, service)
    newest = {name for _, name in facts.releases[:KEEP_RELEASES]}
    doomed = [name for _, name in facts.releases if name not in newest | keep]
    if doomed:
        _host(context, 'set -eu; s="$1"; shift; for r in "$@"; do rm -rf "/srv/$s/$r"; done',
              service, *doomed, reason="release pruning failed")
    return doomed


def compose(context: str, release: Release, *verb: str, timeout: float = 600.0) -> None:
    _ok(["docker", "--context", context, "compose", "-p", release.service, "--project-directory",
         release.directory, "-f", "-", *verb], f"compose {verb[0]} failed", FAILED,
        stdin=release.document(), env=docker_env(), timeout=timeout)


def up(context: str, release: Release) -> None:
    compose(context, release, "up", "--detach", "--remove-orphans", "--wait",
            "--wait-timeout", str(WAIT_SECONDS), timeout=WAIT_SECONDS + 120.0)


def running(context: str, service: str) -> str | None:
    try:
        return deployment.running_revision(deployment.inspect_project(context, service, 30.0))
    except deployment.VerificationError as error:
        raise WriteError(error.reason, UNAVAILABLE) from None


def route_revision(repo: Path, context: str) -> str:
    """Routes are checked against what the front door actually serves, else what main declares."""
    try:
        return running(context, "caddy-apps") or resolve(repo, MAIN)
    except WriteError:
        return resolve(repo, MAIN)


def check(repo: Path, context: str, release: Release) -> dict[str, Any]:
    """Verify one release is what runs; a verifier failure is a WriteError for the shape."""
    with checkout(repo, route_revision(repo, context)) as routes_root:
        try:
            return deployment.verify(release.service, release.revision, release.services, routes_root,
                                     context=context)
        except deployment.VerificationError as error:
            raise WriteError(error.reason, FAILED if error.code == 1 else UNAVAILABLE) from None


# --- deploy ----------------------------------------------------------------------------------

@dataclass
class _Saved:
    release: Release | None = None
    facts: HostFacts = HostFacts()
    previous: str | None = None


def deploy(repo: Path, service: str, *, revision: str | None = None, context: str,
           ledger: Ledger, refresh: bool = True, revert_pr: bool = True) -> Operation:
    """Apply one merged revision of one service through the write-path shape."""
    if not deployment.NAME.fullmatch(service):
        return _refused(service, "invalid service name")
    try:
        if refresh:
            fetch(repo)
        target = resolve(repo, revision) if revision else service_revision(repo, service)
    except WriteError as error:
        return _refused(service, error.reason, error.code)
    if target is None:
        return _refused(service, "service is not on origin/main")
    operation = Operation("deploy", f"svc/{service}", target)
    saved = _Saved()

    def preflight() -> None:
        if not merged(repo, target):
            raise WriteError("revision is not merged to origin/main", USAGE)
        if manual(repo, service, target):
            raise WriteError("service is deployed by hand (x-skynet.deploy: manual)", USAGE)
        saved.release = render(repo, service, target)
        compose(context, saved.release, "pull", "--quiet")  # a bad image fails before any change
        stage(context, saved.release)

    def snapshot() -> _Saved:
        saved.facts = host_facts(context, service)
        saved.previous = running(context, service)
        return saved

    def execute(state: _Saved) -> None:
        assert state.release is not None
        up(context, state.release)

    def verify(state: _Saved) -> dict[str, Any]:
        assert state.release is not None
        return check(repo, context, state.release)

    def rollback(state: _Saved, error: WriteError) -> str:
        set_fact(context, service, "failed", target)
        back = state.facts.verified
        if back is None or back == target:
            operation.note("rollback", "skipped", "no earlier verified revision")
            return "no-rollback-target"
        release = render(repo, service, back)
        stage(context, release)
        up(context, release)
        check(repo, context, release)
        operation.note("rollback", "ok", f"running verified {back}")
        if revert_pr and service_revision(repo, service) == target:
            try:
                operation.note("revert-pr", "ok", open_revert_pr(repo, service, target, back, error.reason))
            except WriteError as pr_error:
                operation.note("revert-pr", "failed", pr_error.reason)
        return "rolled-back"

    def reconcile() -> dict[str, Any]:
        return {"running": running(context, service)}

    def commit(state: _Saved) -> None:
        set_fact(context, service, "verified", target)
        if state.facts.failed == target:
            set_fact(context, service, "failed", None)
        keep = {target} | {value for value in (state.facts.verified, state.previous) if value}
        prune(context, service, keep)

    return writepath.run(operation, ledger, preflight=preflight, snapshot=snapshot, execute=execute,
                         verify=verify, rollback=rollback, reconcile=reconcile, commit=commit)


def _refused(service: str, reason: str, code: int = USAGE) -> Operation:
    operation = Operation("deploy", f"svc/{service}", "")
    operation.outcome, operation.reason, operation.code = "refused", reason, code
    return operation


def open_revert_pr(repo: Path, service: str, failed: str, verified: str, reason: str) -> str:
    """Make main match what runs: restore `compose/<service>/` to the verified tree on a branch."""
    branch = f"revert/{service}-{failed[:12]}"
    title = f"revert({service}): return to verified {verified[:12]}"
    body = (f"`skynet deploy` rolled `{service}` back automatically.\n\n"
            f"- failed revision: `{failed}`\n- reason: {reason}\n- running now: `{verified}`\n\n"
            f"This restores `compose/{service}/` to the verified tree so `main` matches what runs. "
            "Merge it, or fix forward in another PR; `--pending` will not retry the failed revision.")
    with tempfile.TemporaryDirectory(prefix="skynet-revert-") as tmp:
        tree = Path(tmp) / "tree"
        _git(repo, "worktree", "add", "--quiet", "--detach", str(tree), MAIN, reason="revert worktree failed")
        try:
            _git(tree, "rm", "-r", "-q", "--ignore-unmatch", f"compose/{service}", reason="revert failed")
            _git(tree, "checkout", verified, "--", f"compose/{service}", reason="revert failed")
            if _run(["git", "-C", str(tree), "diff", "--cached", "--quiet"]).returncode == 0:
                return "main already matches the verified tree"
            _git(tree, "commit", "-q", "-m", title, "-m", body, reason="revert commit failed")
            _git(tree, "push", "-q", "origin", f"HEAD:refs/heads/{branch}", reason="revert push failed")
            url = _ok(["gh", "pr", "create", "--head", branch, "--base", "main", "--title", title,
                       "--body", body], "revert PR not opened", cwd=tree)
            return url.decode("utf-8", "replace").strip()
        finally:
            _run(["git", "-C", str(repo), "worktree", "remove", "--force", str(tree)])


def pending(repo: Path, *, context: str, ledger: Ledger) -> list[dict[str, Any]]:
    """Deploy every service whose merged revision is not the one running (the timer's job)."""
    fetch(repo)
    results: list[dict[str, Any]] = []
    for service in services(repo):
        if manual(repo, service, MAIN):
            continue
        target = service_revision(repo, service)
        try:
            if target is None or running(context, service) == target:
                continue
            if host_facts(context, service).failed == target:
                results.append({"target": f"svc/{service}", "source": target, "outcome": "held",
                                "reason": "revision failed and was rolled back; awaiting a new merge"})
                continue
        except WriteError as error:
            results.append({"target": f"svc/{service}", "outcome": "unavailable", "reason": error.reason,
                            "code": error.code})
            continue
        results.append(writepath.report(deploy(repo, service, revision=target, context=context,
                                               ledger=ledger, refresh=False)))
    return results


# --- dry run (the PR's effect) ---------------------------------------------------------------

def _ports(service: dict[str, Any]) -> list[str]:
    return sorted(f"{p.get('host_ip', '') + ':' if p.get('host_ip') else ''}{p.get('published', '')}"
                  f":{p.get('target')}/{p.get('protocol', 'tcp')}" for p in service.get("ports") or [])


def _volumes(service: dict[str, Any]) -> list[str]:
    return sorted(f"{v.get('source', '')}:{v.get('target')}{':ro' if v.get('read_only') else ''}"
                  for v in service.get("volumes") or [])


def _networks(service: dict[str, Any]) -> list[str]:
    networks = service.get("networks") or {}
    return sorted(f"{name}{'=' + (value or {}).get('ipv4_address', '') if (value or {}).get('ipv4_address') else ''}"
                  for name, value in networks.items())


_SHOWN = {"image", "ports", "volumes", "networks", "environment", "labels"}


def effect(old: dict[str, Any] | None, new: dict[str, Any]) -> list[tuple[str, str]]:
    """What changes per Compose service. Env values are compared, never shown: only key names."""
    rows: list[tuple[str, str]] = []
    before = (old or {}).get("services", {})
    after = new["services"]
    for name in sorted(set(before) | set(after)):
        if name not in after:
            rows.append((name, "removed"))
            continue
        if name not in before:
            rows.append((name, f"added: `{after[name].get('image')}`"))
        a, b = before.get(name, {}), after[name]
        if name in before and a.get("image") != b.get("image"):
            rows.append((name, f"image: `{a.get('image')}` → `{b.get('image')}`"))
        for label, read in (("ports", _ports), ("volumes", _volumes), ("networks", _networks)):
            if name in before and read(a) != read(b):
                added = sorted(set(read(b)) - set(read(a)))
                removed = sorted(set(read(a)) - set(read(b)))
                rows.append((name, f"{label}: +{added or '[]'} −{removed or '[]'}"))
        env_a, env_b = a.get("environment") or {}, b.get("environment") or {}
        for verb, keys in (("added", set(env_b) - set(env_a)), ("removed", set(env_a) - set(env_b)),
                           ("changed", {k for k in set(env_a) & set(env_b) if env_a[k] != env_b[k]})):
            if keys and name in before:
                rows.append((name, f"env {verb}: {', '.join(sorted(keys))}"))
        labels_a = {k: v for k, v in (a.get("labels") or {}).items() if not k.startswith("skynet.")}
        labels_b = {k: v for k, v in (b.get("labels") or {}).items() if not k.startswith("skynet.")}
        if name in before and labels_a != labels_b:
            rows.append((name, "labels changed: " + ", ".join(sorted(
                k for k in set(labels_a) | set(labels_b) if labels_a.get(k) != labels_b.get(k)))))
        other = sorted(k for k in (set(a) | set(b)) - _SHOWN if a.get(k) != b.get(k))
        if name in before and other:
            rows.append((name, "settings changed: " + ", ".join(other)))
    return rows


def dry_run(repo: Path, service: str, ref: str, *, context: str) -> str:
    """The Markdown effect table a PR carries: base (what runs) → candidate (the PR's commit)."""
    candidate = resolve(repo, ref)
    try:
        fetch(repo)
    except WriteError:
        pass  # a stale origin/main only affects the fallback base, which the table names
    base, base_source = None, "running label"
    try:
        base = running(context, service)
    except WriteError:
        base_source = "Docker host unavailable"
    if base is None:
        base, base_source = service_revision(repo, service), "origin/main"
    new = render(repo, service, candidate)
    old = render(repo, service, base) if base else None
    rows = effect(old.model if old else None, new.model)
    lines = [f"### Deploy effect: `{service}`",
             f"base `{base[:12] if base else 'none'}` ({base_source}) → candidate `{candidate[:12]}`", ""]
    if rows:
        lines += ["| service | change |", "|---|---|"] + [f"| {name} | {change} |" for name, change in rows]
    else:
        lines.append("No configuration change.")
    lines += ["", "Every container of the project is recreated with the new `skynet.revision` label. "
              "Env values are compared but never shown."]
    return "\n".join(lines)


# --- CLI glue --------------------------------------------------------------------------------

def run_deploy(repo: Path, service: str | None, *, revision: str | None, dry_run_ref: str | None,
               pending_all: bool, context: str, state_dir: Path, json_output: bool,
               stdout: TextIO) -> int:
    ledger = Ledger(state_dir)
    try:
        if dry_run_ref is not None:
            assert service is not None
            print(dry_run(repo, service, dry_run_ref, context=context), file=stdout)
            return 0
        if pending_all:
            results = pending(repo, context=context, ledger=ledger)
            for result in results:
                _print(result, json_output, stdout)
            return max((int(r.get("code", 0)) for r in results), default=0)
    except WriteError as error:
        _print({"target": "deploy", "outcome": "unavailable" if error.code == UNAVAILABLE else "refused",
                "reason": error.reason, "code": error.code}, json_output, stdout)
        return error.code
    assert service is not None
    result = writepath.report(deploy(repo, service, revision=revision, context=context, ledger=ledger))
    _print(result, json_output, stdout)
    return int(result["code"])


def run_verify(repo: Path, service: str, revision: str | None, *, context: str, json_output: bool,
               stdout: TextIO) -> int:
    """Report-only: is `revision` (default: the running label) what runs, healthy and routed?"""
    try:
        target = resolve(repo, revision) if revision else running(context, service)
        if target is None:
            raise WriteError("no single skynet.revision label is running", FAILED)
        evidence = check(repo, context, render(repo, service, target))
    except WriteError as error:
        _print({"target": f"svc/{service}", "outcome": "failure" if error.code == FAILED else
                "unavailable", "reason": error.reason, "code": error.code}, json_output, stdout)
        return error.code
    _print({"target": f"svc/{service}", "outcome": "verified", "code": 0, **evidence}, json_output, stdout)
    return 0


def _print(result: dict[str, Any], json_output: bool, stdout: TextIO) -> None:
    if json_output:
        print(json.dumps(result, sort_keys=True), file=stdout)
        return
    source = f"@{str(result['source'])[:12]}" if result.get("source") else ""
    line = f"{result.get('target')}{source}: {result.get('outcome')}"
    if result.get("reason"):
        line += f" — {result['reason']}"
    if result.get("recovery") not in (None, "not-needed"):
        line += f" (recovery: {result['recovery']})"
    print(line, file=stdout)
    for step in result.get("steps", []):
        if step.get("detail"):
            print(f"  {step['step']}: {step['outcome']} — {step['detail']}", file=stdout)
