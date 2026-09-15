"""T1 route inventory: a static parse of the committed Caddyfile, no live access.

Provenance is static: the vhost→front-door→backend→auth chain is read from `compose/caddy-apps/
Caddyfile` and resolved with the compose macvlan address map plus the packaged entity derivation.
Nothing is probed; the timestamp records when the parse ran on this checkout. A parse or publication failure
leaves the requested destination untouched.
"""

import json
import os
import re
import signal
import socket
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, TextIO

from skynet import entities
from skynet.proxmox import CollectionError, publish

SOURCE = "caddyfile static parse (compose/)"
CADDYFILE = Path("compose/caddy-apps/Caddyfile")
FRONT_DOOR = "svc/caddy-apps"
FRONT_DOOR_ALIAS = "HOST_PROXY_APPS"
VHOST_START = re.compile(r"^([A-Za-z0-9.*_-]+\.aliammar\.net)\s*\{")
ADDR = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]*:[0-9]+$")
IPV4 = re.compile(r"ipv4_address:\s*(10\.10\.\d{1,3}\.\d{1,3})")
_REVISION = re.compile(r"[0-9a-f]{40}", re.IGNORECASE)
_OBJECT_ID = re.compile(r"[0-9a-f]{40,64}", re.IGNORECASE)
_SERVICE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_GIT_MAX_OUTPUT = 4 * 1024 * 1024
_GIT_MAX_BLOB = 2 * 1024 * 1024
_GIT_TIMEOUT = 15.0


def _terminate_git(process: subprocess.Popen[bytes]) -> None:
    """Terminate and reap a Git process group after a bounded observation."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
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
        process.wait(timeout=5.0)
    except (OSError, subprocess.TimeoutExpired):
        raise CollectionError("route source observation cleanup failed", 3) from None


def _git(
    repo: Path,
    arguments: list[str],
    timeout: float,
    reason: str,
    *,
    max_output: int = _GIT_MAX_OUTPUT,
) -> bytes:
    """Read bounded Git object output without retaining stderr or leaking command details."""
    if not repo.is_dir() or not 1.0 <= timeout <= 300.0 or max_output <= 0:
        raise CollectionError(reason, 3)
    try:
        process = subprocess.Popen(
            ["git", "-C", str(repo), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except (OSError, ValueError):
        raise CollectionError(reason, 3) from None

    assert process.stdout is not None
    stream = process.stdout
    chunks: list[bytes] = []
    size = 0
    oversized = False

    def drain() -> None:
        nonlocal size, oversized
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    return
                if size < max_output:
                    room = max_output - size
                    chunks.append(chunk[:room])
                size += len(chunk)
                if size > max_output:
                    oversized = True
        except (OSError, ValueError):
            oversized = True

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    timed_out = False
    try:
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_git(process)
        reader.join(timeout=5.0)
        if reader.is_alive():
            _terminate_git(process)
            reader.join(timeout=5.0)
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass
    if timed_out or reader.is_alive():
        raise CollectionError(reason, 3) from None
    if oversized:
        raise CollectionError("route source observation exceeded its bound", 3)
    if process.returncode != 0:
        raise CollectionError(reason, 3)
    return b"".join(chunks)


def _git_text(repo: Path, arguments: list[str], timeout: float, reason: str) -> str:
    raw = _git(repo, arguments, timeout, reason)
    try:
        return raw.decode("utf-8").strip()
    except UnicodeError:
        raise CollectionError(reason, 3) from None


def _validate_revision(revision: str) -> str:
    if not isinstance(revision, str) or _REVISION.fullmatch(revision) is None:
        raise CollectionError("invalid route source revision", 2)
    return revision.lower()


def _validate_git_path(raw_path: bytes, prefix: str) -> str:
    try:
        path = raw_path.decode("utf-8")
    except UnicodeError:
        raise CollectionError("malformed route Git path", 3) from None
    pure = PurePosixPath(path)
    if (
        not path.startswith(prefix + "/")
        or "\\" in path
        or str(pure) != path
        or any(part in {"", ".", ".."} for part in pure.parts)
        or any(ord(char) < 33 or ord(char) == 127 for char in path)
    ):
        raise CollectionError("unsafe route Git path", 2)
    return path


def _git_entry(repo: Path, revision: str, path: str, timeout: float) -> tuple[str, str, int]:
    """Return one exact commit path as (object id, kind, mode)."""
    raw = _git(
        repo,
        ["ls-tree", "-z", revision, "--", path],
        timeout,
        "route source unavailable",
        max_output=64 * 1024,
    )
    if not raw.endswith(b"\0"):
        raise CollectionError("malformed route Git tree", 3)
    records = raw[:-1].split(b"\0")
    if len(records) != 1:
        raise CollectionError("route source path is missing or duplicated", 3)
    try:
        metadata, raw_path = records[0].split(b"\t", 1)
        mode_raw, kind_raw, object_raw = metadata.split(b" ")
        actual_path = _validate_git_path(raw_path, "compose")
        mode = int(mode_raw.decode("ascii"), 8)
        kind = kind_raw.decode("ascii")
        object_id = object_raw.decode("ascii").lower()
    except (UnicodeDecodeError, ValueError):
        raise CollectionError("malformed route Git tree", 3) from None
    if actual_path != path or kind != "blob" or mode_raw not in {b"100644", b"100755"}:
        raise CollectionError("route source path is not a regular file", 2)
    if _OBJECT_ID.fullmatch(object_id) is None:
        raise CollectionError("malformed route Git object identity", 3)
    return object_id, kind, mode


def _git_blob(repo: Path, object_id: str, timeout: float, reason: str) -> bytes:
    if _OBJECT_ID.fullmatch(object_id) is None:
        raise CollectionError("malformed route Git object identity", 3)
    return _git(repo, ["cat-file", "blob", object_id], timeout, reason, max_output=_GIT_MAX_BLOB)


def _git_revision(repo: Path, revision: str, timeout: float) -> str:
    revision = _validate_revision(revision)
    object_type = _git_text(repo, ["cat-file", "-t", revision], timeout,
                            "route source revision unavailable")
    if object_type != "commit":
        raise CollectionError("route source revision is not a commit", 2)
    return revision


def _service_ips_at_revision(repo: Path, revision: str, timeout: float) -> dict[str, str]:
    """Map exact-commit Compose macvlan addresses to service names."""
    raw = _git(
        repo,
        ["ls-tree", "--full-tree", "-r", "-z", revision, "--", "compose"],
        timeout,
        "route Compose source unavailable",
        max_output=_GIT_MAX_OUTPUT,
    )
    if not raw or not raw.endswith(b"\0"):
        raise CollectionError("route Compose source unavailable", 3)
    entries: list[tuple[str, str, int, str]] = []
    for record in raw[:-1].split(b"\0"):
        if not record:
            raise CollectionError("malformed route Git tree", 3)
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode_raw, kind_raw, object_raw = metadata.split(b" ")
            path = _validate_git_path(raw_path, "compose")
            mode = int(mode_raw.decode("ascii"), 8)
            kind = kind_raw.decode("ascii")
            object_id = object_raw.decode("ascii").lower()
        except (UnicodeDecodeError, ValueError):
            raise CollectionError("malformed route Git tree", 3) from None
        if _OBJECT_ID.fullmatch(object_id) is None:
            raise CollectionError("malformed route Git object identity", 3)
        entries.append((path, kind, mode, object_id))

    ip2svc: dict[str, str] = {}
    direct = re.compile(r"^compose/([^/]+)/compose\.yaml$")
    for path, kind, mode, object_id in sorted(entries):
        match = direct.fullmatch(path)
        if match is None:
            continue
        project = match[1]
        if _SERVICE.fullmatch(project) is None:
            raise CollectionError("malformed route Compose service name", 2)
        if kind != "blob" or mode not in {0o100644, 0o100755}:
            raise CollectionError("route Compose manifest is not a regular file", 2)
        try:
            text = _git_blob(repo, object_id, timeout, "route Compose source unavailable").decode("utf-8")
        except UnicodeDecodeError:
            raise CollectionError("route Compose source is not UTF-8", 3) from None
        match_ip = IPV4.search(text)
        if match_ip:
            ip2svc.setdefault(match_ip[1], project)
    return ip2svc


def _parse_caddy(text: str) -> list[tuple[str, str, str]]:
    """Reduce each `*.aliammar.net { … }` block to (vhost, catch-all backend, forward_auth)."""
    routes: list[tuple[str, str, str]] = []
    depth = 0
    vhost = ""
    backend = ""
    fauth = "no"
    for line in text.splitlines():
        if depth == 0:
            match = VHOST_START.match(line)
            if match:
                vhost, depth, backend, fauth = match[1], 1, "", "no"
            continue
        fields = line.split()
        # The catch-all backend is a reverse_proxy whose first argument is an address; path-scoped
        # ones (e.g. `reverse_proxy /outpost.goauthentik.io/* <authentik>`) are auth plumbing.
        if len(fields) >= 2 and fields[0] == "reverse_proxy" and ADDR.match(fields[1]):
            backend = fields[1]
        if fields and fields[0] == "forward_auth":
            fauth = "yes"
        depth += line.count("{") - line.count("}")
        if depth < 0:
            raise CollectionError("malformed Caddy route block")
        if depth == 0:
            if vhost:
                routes.append((vhost, backend, fauth))
            depth, vhost = 0, ""
    if depth != 0:
        raise CollectionError("malformed Caddy route block")
    return routes


def _service_ips(repo: Path) -> dict[str, str]:
    """Map each compose project's macvlan address to its service entity id."""
    ip2svc: dict[str, str] = {}
    compose = repo / "compose"
    if not compose.is_dir():
        return ip2svc
    for project in sorted(compose.iterdir()):
        manifest = project / "compose.yaml"
        try:
            match = IPV4.search(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            continue
        if match:
            ip2svc.setdefault(match[1], project.name)
    return ip2svc


def _guest_ips(repo: Path) -> dict[str, str]:
    """Resolve collected guests directly through the packaged entity functions."""
    guest_ip: dict[str, str] = {}
    declared: tuple[int, ...] = entities.DEFAULT_VLANS
    slugs: dict[int, str] = entities.DEFAULT_VLAN_SLUGS
    if (repo / "invariants.json").is_file() and (repo / "lab.json").is_file():
        try:
            declared, slugs, _, _ = entities.conventions(repo)
        except entities.EntityError as error:
            raise CollectionError(str(error), 2) from None
    try:
        firewall = entities.firewall_ips(repo) if (repo / "inventory" / "firewall" / "firewall.json").is_file() else set()
    except entities.EntityError as error:
        raise CollectionError(str(error), 2) from None
    for path in sorted((repo / "inventory").glob("proxmox-*.json")):
        if path.name.endswith("-acl.json"):
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError):
            raise CollectionError("guest inventory unavailable", 3) from None
        if not isinstance(raw, dict) or not isinstance(raw.get("resources"), list):
            raise CollectionError("malformed guest inventory")
        for resource in raw["resources"]:
            if not isinstance(resource, dict) or resource.get("type") not in {"qemu", "lxc"}:
                continue
            vmid, name = resource.get("vmid"), resource.get("name")
            if type(vmid) is not int or not isinstance(name, str):
                raise CollectionError("malformed guest inventory")
            try:
                ip = entities.vmid_to_ip(vmid, declared)
            except entities.EntityError as error:
                if error.code != 2:
                    continue
                candidates = [candidate for candidate in entities.candidate_ips(vmid, declared)
                              if candidate in firewall]
                if len(candidates) != 1:
                    continue
                ip = candidates[0]
            guest_ip[ip] = entities.guest_id(vmid, name, declared, slugs)
    return guest_ip


def _resolve(backend: str, ip2svc: dict[str, str], guest_ip: dict[str, str]) -> str:
    ip = backend.split(":", 1)[0]
    if ip in ip2svc:
        return f"svc/{ip2svc[ip]}"
    if ip in guest_ip:
        return guest_ip[ip]
    return f"host:{ip}"


def _render_snapshot(
    repo: Path,
    text: str,
    ip2svc: dict[str, str],
    source_revision: str | None = None,
) -> dict[str, Any]:
    parsed_routes = _parse_caddy(text)
    if not parsed_routes:
        raise CollectionError("route source contains no supported routes")
    guest_ip = _guest_ips(repo)
    routes = []
    for vhost, backend, fauth in parsed_routes:
        entity = "—"
        auth = "own-auth/plain"
        if backend:
            entity = _resolve(backend, ip2svc, guest_ip)
            if entity.startswith("guest/authentik-") and fauth == "no":
                auth = "identity (authentik)"
        if fauth == "yes":
            auth = "forward_auth (authentik)"
        routes.append({"vhost": vhost, "front_door": FRONT_DOOR,
                       "front_door_alias": FRONT_DOOR_ALIAS, "backend": backend,
                       "backend_entity": entity, "auth": auth})
    result: dict[str, Any] = {
        "collected": datetime.now(UTC).isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "source": SOURCE,
        "counts": {"routes": len(routes)},
        "routes": routes,
    }
    if source_revision is not None:
        result["source_revision"] = source_revision
    return result


def snapshot(
    repo: Path,
    revision: str | None = None,
    *,
    timeout: float = _GIT_TIMEOUT,
) -> dict[str, Any]:
    """Project routes from the checkout or one exact Git commit.

    Collection callers omit ``revision`` and retain the historical checkout-based snapshot.  The
    deployment verifier supplies the expected generation revision; that path reads the Caddyfile
    and every Compose service-address input from Git objects, so dirty checkout bytes cannot change
    which route is required for the verified release.
    """
    if revision is None:
        caddyfile = repo / CADDYFILE
        try:
            text = caddyfile.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            raise CollectionError("route source unavailable", 3) from None
        return _render_snapshot(repo, text, _service_ips(repo))

    selected_revision = _git_revision(repo, revision, timeout)
    object_id, _, _ = _git_entry(repo, selected_revision, str(CADDYFILE), timeout)
    try:
        text = _git_blob(repo, object_id, timeout, "route source unavailable").decode("utf-8")
    except UnicodeDecodeError:
        raise CollectionError("route source is not UTF-8", 3) from None
    return _render_snapshot(
        repo,
        text,
        _service_ips_at_revision(repo, selected_revision, timeout),
        selected_revision,
    )


def collect(repo: Path, output: Path, *, json_output: bool, stdout: TextIO) -> int:
    """Collect one atomic route snapshot; failure leaves the requested destination untouched."""
    report: dict[str, Any] = {"target": "routes", "output": str(output)}
    try:
        data = snapshot(repo)
        publish(output, data)
    except CollectionError as error:
        report.update(outcome="unavailable" if error.code == 3 else "failure",
                      reason=f"{error}; refresh failed; any retained snapshot is previous evidence")
        code = error.code
    else:
        report.update(outcome="success", collected=data["collected"], counts=data["counts"])
        code = 0
    if json_output:
        print(json.dumps(report), file=stdout)
    else:
        print(f"routes: {report['outcome']} → {report['output']}", file=stdout)
        if code:
            print(report["reason"], file=stdout)
    return code
