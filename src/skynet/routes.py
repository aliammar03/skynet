"""T1 route inventory: a static parse of the committed Caddyfile, no live access.

Provenance is static: the vhost→front-door→backend→auth chain is read from `compose/caddy-apps/
Caddyfile` and resolved with the compose macvlan address map plus the packaged entity derivation.
Nothing is probed; the timestamp records when the parse ran on this checkout. A parse or publication failure
leaves the requested destination untouched.
"""

import json
import re
import socket
from datetime import UTC, datetime
from pathlib import Path
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


def snapshot(repo: Path) -> dict[str, Any]:
    """Project the static route chain from one readable, structurally complete Caddyfile."""
    caddyfile = repo / CADDYFILE
    try:
        text = caddyfile.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise CollectionError("route source unavailable", 3) from None
    parsed_routes = _parse_caddy(text)
    if not parsed_routes:
        raise CollectionError("route source contains no supported routes")
    ip2svc = _service_ips(repo)
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
    return {"collected": datetime.now(UTC).isoformat(timespec="seconds"),
            "host": socket.gethostname(), "source": SOURCE,
            "counts": {"routes": len(routes)}, "routes": routes}


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
