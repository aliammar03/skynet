"""`skynet publish` / `skynet withdraw`: make a service's declared routes real, or clean up after one.

Git declares publication: a vhost block in `compose/caddy-apps/Caddyfile` (deployed by
`skynet deploy caddy-apps`), a `hostname:` in `compose/cloudflared/config.yml` for public reach,
and DNS records derived from both by OpenTofu. What git cannot hold is Authentik's per-vhost
forward-auth objects; `publish` creates them (provider → application → embedded-outpost binding,
additive only) and proves the route. `withdraw` is the one gated delete: after a PR has removed a
vhost's declarations, it deletes the leftover application, provider, and public CNAME.

Authentik is reachable only from the apps front door (firewall rule 240), so its API is called
with `curl -K -` inside the Caddy container; the bearer header and body travel on stdin.
"""

from __future__ import annotations

import copy
import http.client
import json
import re
import ssl
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from skynet import common, deploy, deployment, routes, writepath
from skynet.writepath import FAILED, UNAVAILABLE, USAGE, Ledger, Operation, WriteError

AUTHENTIK_CREDENTIALS = Path("/opt/skynet-ops/secrets/authentik.env")
CLOUDFLARE_CREDENTIALS = Path("/opt/skynet-ops/secrets/cloudflare-dns.env")
FRONT_DOOR_CONTAINER = "caddy-apps-caddy-1"
LOGIN = "https://auth.aliammar.net/"
EMBEDDED_OUTPOST = "goauthentik.io/outposts/embedded"
FORWARD_AUTH = "forward_auth (authentik)"
_INGRESS = re.compile(r"(?m)^\s*-\s*hostname:\s*(\S+)")
_VHOST = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+aliammar\.net")
PROBE_ATTEMPTS = 6
PROBE_PAUSE = 5.0


# --- credentials -----------------------------------------------------------------------------

def authentik_credentials(path: Path = AUTHENTIK_CREDENTIALS) -> dict[str, str]:
    values = common.read_assignments(path, ("AUTHENTIK_URL", "AUTHENTIK_TOKEN"),
                                     ("AUTHENTIK_URL", "AUTHENTIK_TOKEN"), error=WriteError,
                                     service="Authentik")
    parsed = urllib.parse.urlsplit(values["AUTHENTIK_URL"])
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.query or parsed.username:
        raise WriteError("invalid Authentik URL", UNAVAILABLE)
    if not common.printable(values["AUTHENTIK_TOKEN"]):
        raise WriteError("invalid Authentik credential assignments", UNAVAILABLE)
    return values


def cloudflare_credentials(path: Path = CLOUDFLARE_CREDENTIALS) -> dict[str, str]:
    values = common.read_assignments(path, ("CF_DNS_TOKEN", "CF_ZONE", "TUNNEL_ID"),
                                     ("CF_DNS_TOKEN", "CF_ZONE"), error=WriteError,
                                     service="Cloudflare")
    if not common.printable(values["CF_DNS_TOKEN"]) or not common.valid_host(values["CF_ZONE"]):
        raise WriteError("invalid Cloudflare credential assignments", UNAVAILABLE)
    return values


# --- Authentik (through the front door) ------------------------------------------------------

def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def curl_config(method: str, url: str, token: str, body: Any = None) -> bytes:
    """A curl config for stdin: the token and body never reach an argv or a file."""
    lines = [f"url = {_quote(url)}", f"request = {_quote(method)}",
             f"header = {_quote('Authorization: Bearer ' + token)}",
             'header = "Accept: application/json"', "silent", "show-error", "max-time = 20",
             'write-out = "\\n%{http_code}"']
    if body is not None:
        lines += ['header = "Content-Type: application/json"',
                  f"data = {_quote(json.dumps(body, sort_keys=True))}"]
    return ("\n".join(lines) + "\n").encode()


@dataclass
class Authentik:
    context: str
    url: str
    token: str = field(repr=False)

    def call(self, method: str, path: str, body: Any = None) -> Any:
        config = curl_config(method, self.url.rstrip("/") + "/api/v3" + path, self.token, body)
        result = deploy._run(["docker", "--context", self.context, "exec", "--interactive",
                              FRONT_DOOR_CONTAINER, "curl", "--config", "-"],
                             stdin=config, env=deploy.docker_env(), timeout=40.0)
        text, _, status = result.stdout.decode("utf-8", "replace").rpartition("\n")
        if result.returncode != 0 or not status.strip().isdigit():
            raise WriteError("Authentik unavailable", UNAVAILABLE)
        if not 200 <= int(status) < 300:
            raise WriteError(f"Authentik refused {method} {path.split('?')[0]}", FAILED)
        if not text.strip():
            return None
        try:
            return json.loads(text)
        except ValueError:
            raise WriteError("malformed Authentik response", UNAVAILABLE) from None

    def list(self, path: str) -> list[dict[str, Any]]:
        data = self.call("GET", f"{path}?page_size=1000")
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise WriteError("malformed Authentik response", UNAVAILABLE)
        if (data.get("pagination") or {}).get("next"):
            raise WriteError("Authentik list exceeds one page", UNAVAILABLE)
        return [row for row in data["results"] if isinstance(row, dict)]


@dataclass
class AuthentikState:
    providers: list[dict[str, Any]]
    applications: list[dict[str, Any]]
    outpost: dict[str, Any]

    def provider(self, vhost: str) -> dict[str, Any] | None:
        found = [p for p in self.providers if p.get("external_host", "").rstrip("/") == f"https://{vhost}"]
        if len(found) > 1:
            raise WriteError("more than one Authentik provider serves the vhost", FAILED)
        return found[0] if found else None

    def application(self, provider_pk: Any) -> dict[str, Any] | None:
        found = [a for a in self.applications if a.get("provider") == provider_pk]
        return found[0] if found else None


def read_authentik(client: Authentik) -> AuthentikState:
    outposts = [o for o in client.list("/outposts/instances/") if o.get("managed") == EMBEDDED_OUTPOST]
    if len(outposts) != 1 or not isinstance(outposts[0].get("providers"), list):
        raise WriteError("embedded Authentik outpost not found", UNAVAILABLE)
    # A snapshot is a copy: later writes must not reach back into what rollback restores.
    return copy.deepcopy(AuthentikState(client.list("/providers/proxy/"),
                                        client.list("/core/applications/"), outposts[0]))


# --- Cloudflare DNS records ------------------------------------------------------------------

@dataclass
class Cloudflare:
    token: str = field(repr=False)
    zone: str = ""
    zone_id: str = ""

    def call(self, method: str, path: str, body: Any = None) -> Any:
        connection = http.client.HTTPSConnection("api.cloudflare.com", 443, timeout=20,
                                                 context=ssl.create_default_context())
        try:
            raw, _ = common.request(connection, method, "/client/v4/" + path, headers={
                "Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                body=None if body is None else json.dumps(body).encode())
            payload = common.json_object(raw)
        except common.CollectionError:
            raise WriteError(f"Cloudflare refused {method}", UNAVAILABLE) from None
        if payload.get("success") is not True:
            raise WriteError(f"Cloudflare refused {method}", FAILED)
        return payload.get("result")

    def records(self, name: str) -> list[dict[str, Any]]:
        if not self.zone_id:
            zones = self.call("GET", f"zones?name={urllib.parse.quote(self.zone)}")
            if not isinstance(zones, list) or len(zones) != 1:
                raise WriteError("Cloudflare zone not visible to the token", UNAVAILABLE)
            self.zone_id = str(zones[0].get("id"))
        found = self.call("GET", f"zones/{self.zone_id}/dns_records?name={urllib.parse.quote(name)}")
        if not isinstance(found, list):
            raise WriteError("malformed Cloudflare response", UNAVAILABLE)
        return [record for record in found if isinstance(record, dict)]


def _cloudflare() -> Cloudflare:
    values = cloudflare_credentials()
    return Cloudflare(values["CF_DNS_TOKEN"], values["CF_ZONE"])


# --- declarations ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Route:
    vhost: str
    auth: str
    public: bool


def declared(root: Path) -> tuple[list[dict[str, Any]], set[str]]:
    """Routes from a checkout's Caddyfile, and the hostnames its tunnel ingress publishes."""
    try:
        data = routes.snapshot(root)
    except common.CollectionError as error:
        raise WriteError(error.reason, UNAVAILABLE) from None
    ingress = root / "compose" / "cloudflared" / "config.yml"
    public = set(_INGRESS.findall(ingress.read_text(encoding="utf-8"))) if ingress.is_file() else set()
    return list(data["routes"]), public


def service_routes(repo: Path, service: str) -> list[Route]:
    with deploy.checkout(repo, deploy.resolve(repo, deploy.MAIN)) as root:
        rows, public = declared(root)
    return [Route(row["vhost"], row["auth"], row["vhost"] in public)
            for row in rows if row.get("backend_entity") == f"svc/{service}"]


def _converged(repo: Path, context: str, service: str) -> None:
    """Publication rides on the front door and tunnel: they must run what main declares."""
    wanted = deploy.service_revision(repo, service)
    if wanted is None or deploy.running(context, service) != wanted:
        raise WriteError(f"{service} is not running origin/main; deploy it first", FAILED)


# --- publish ---------------------------------------------------------------------------------

@dataclass
class _Published:
    before: AuthentikState | None = None
    created: list[tuple[str, str]] = field(default_factory=list)
    outpost_changed: bool = False


def publish(repo: Path, service: str, *, context: str, ledger: Ledger,
            dry_run: bool = False, stdout: TextIO | None = None) -> Operation:
    try:
        deploy.fetch(repo)
        revision = deploy.resolve(repo, deploy.MAIN)
        declared_routes = service_routes(repo, service)
    except WriteError as error:
        return _refused("publish", service, error.reason, error.code)
    if not declared_routes:
        return _refused("publish", service, "no route for the service in the Caddyfile on origin/main")
    forward = [route for route in declared_routes if route.auth == FORWARD_AUTH]
    operation = Operation("publish", f"svc/{service}", revision)
    state = _Published()
    client: Authentik | None = None

    def preflight() -> None:
        nonlocal client
        _converged(repo, context, "caddy-apps")
        if any(route.public for route in declared_routes):
            _converged(repo, context, "cloudflared")
        if forward:
            values = authentik_credentials()
            client = Authentik(context, values["AUTHENTIK_URL"], values["AUTHENTIK_TOKEN"])

    def snapshot() -> _Published:
        if client is not None:
            state.before = read_authentik(client)
        return state

    def execute(saved: _Published) -> None:
        if client is None or saved.before is None:
            return
        before = saved.before
        template = next((p for p in before.providers if p.get("mode") == "forward_single"), None)
        providers = list(before.outpost["providers"])
        for route in forward:
            provider = before.provider(route.vhost)
            if provider is None:
                if template is None:
                    raise WriteError("no forward_single provider to copy flows from", FAILED)
                provider = client.call("POST", "/providers/proxy/", {
                    "name": route.vhost.split(".")[0], "mode": "forward_single",
                    "external_host": f"https://{route.vhost}",
                    "authorization_flow": template["authorization_flow"],
                    "invalidation_flow": template["invalidation_flow"]})
                saved.created.append(("provider", str(provider["pk"])))
            if before.application(provider["pk"]) is None:
                slug = route.vhost.split(".")[0]
                if any(app.get("slug") == slug for app in before.applications):
                    raise WriteError("application slug already used by another provider", FAILED)
                client.call("POST", "/core/applications/", {
                    "name": slug.capitalize(), "slug": slug, "provider": provider["pk"],
                    "meta_launch_url": f"https://{route.vhost}"})
                saved.created.append(("application", slug))
            if provider["pk"] not in providers:
                providers.append(provider["pk"])
        if providers != before.outpost["providers"]:
            client.call("PATCH", f"/outposts/instances/{before.outpost['pk']}/", {"providers": providers})
            saved.outpost_changed = True

    def verify(saved: _Published) -> dict[str, Any]:
        probes = [_probe(context, route) for route in declared_routes]
        public = [route.vhost for route in declared_routes if route.public]
        return {"routes": probes, "created": [f"{kind}:{name}" for kind, name in saved.created],
                "public_dns": _public_dns(public) if public else {}}

    def rollback(saved: _Published, error: WriteError) -> str:
        if client is None or saved.before is None:
            return "not-needed"
        if saved.outpost_changed:
            client.call("PATCH", f"/outposts/instances/{saved.before.outpost['pk']}/",
                        {"providers": saved.before.outpost["providers"]})
        for kind, name in reversed(saved.created):
            path = f"/core/applications/{name}/" if kind == "application" else f"/providers/proxy/{name}/"
            client.call("DELETE", path)
        return "rolled-back" if saved.created or saved.outpost_changed else "not-needed"

    if dry_run:
        plan = {"target": operation.target, "outcome": "dry-run",
                "routes": [route.__dict__ for route in declared_routes],
                "authentik": "reconcile forward-auth objects" if forward else "none needed"}
        print(json.dumps(plan, sort_keys=True), file=stdout)
        operation.outcome = "dry-run"
        return operation
    return writepath.run(operation, ledger, preflight=preflight, snapshot=snapshot, execute=execute,
                         verify=verify, rollback=rollback, reconcile=lambda: {"idempotent": True})


def _probe(context: str, route: Route) -> dict[str, Any]:
    """Forward-auth must redirect an anonymous request to the login; own-auth must answer < 500."""
    for attempt in range(PROBE_ATTEMPTS):
        try:
            result = deployment.probe(context, route.vhost, deployment.DEFAULT_TIMEOUT)
        except deployment.VerificationError as error:
            if error.code != 1 or attempt == PROBE_ATTEMPTS - 1:
                raise WriteError(error.reason, FAILED if error.code == 1 else UNAVAILABLE) from None
        else:
            if route.auth != FORWARD_AUTH or (result["http_code"] == 302
                                              and str(result["redirect"]).startswith(LOGIN)):
                return {**result, "auth": route.auth}
            if attempt == PROBE_ATTEMPTS - 1:
                raise WriteError("forward-auth route does not redirect to the login", FAILED)
        time.sleep(PROBE_PAUSE)
    raise WriteError("route probe exhausted", FAILED)


def _public_dns(hosts: list[str]) -> dict[str, str]:
    """Report-only: the CNAME is OpenTofu's to create (saved plan until Phase 15)."""
    try:
        cloudflare = _cloudflare()
        return {host: "present" if cloudflare.records(host) else "pending tofu apply" for host in hosts}
    except WriteError:
        return {host: "unknown (Cloudflare unavailable)" for host in hosts}


# --- withdraw --------------------------------------------------------------------------------

@dataclass
class _Withdrawn:
    authentik: AuthentikState | None = None
    records: list[dict[str, Any]] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)


def withdraw(repo: Path, vhost: str, confirm: str, *, context: str, ledger: Ledger) -> Operation:
    """Delete what a removed vhost left behind. Git must no longer declare it; Ali confirms by name."""
    if not _VHOST.fullmatch(vhost):
        return _refused("withdraw", vhost, "invalid vhost")
    if confirm != vhost:
        return _refused("withdraw", vhost, "--confirm must repeat the vhost exactly")
    try:
        deploy.fetch(repo)
        revision = deploy.resolve(repo, deploy.MAIN)
    except WriteError as error:
        return _refused("withdraw", vhost, error.reason, error.code)
    operation = Operation("withdraw", f"vhost/{vhost}", revision)
    state = _Withdrawn()
    parts: dict[str, Any] = {}

    def preflight() -> None:
        with deploy.checkout(repo, revision) as root:
            rows, public = declared(root)
        if vhost in public or any(row["vhost"] == vhost for row in rows):
            raise WriteError("vhost is still declared on origin/main; remove it by PR first", USAGE)
        values = authentik_credentials()
        parts["authentik"] = Authentik(context, values["AUTHENTIK_URL"], values["AUTHENTIK_TOKEN"])
        parts["cloudflare"] = _cloudflare()

    def snapshot() -> _Withdrawn:
        state.authentik = read_authentik(parts["authentik"])
        state.records = parts["cloudflare"].records(vhost)
        if any(record.get("type") != "CNAME" for record in state.records):
            raise WriteError("vhost has a non-CNAME public record; not withdrawn", FAILED)
        operation.note("snapshot", "ok", json.dumps({"records": [
            {k: r.get(k) for k in ("type", "name", "content", "proxied", "ttl")} for r in state.records]}))
        return state

    def execute(saved: _Withdrawn) -> None:
        client, cloudflare = parts["authentik"], parts["cloudflare"]
        assert saved.authentik is not None
        provider = saved.authentik.provider(vhost)
        if provider is not None:
            app = saved.authentik.application(provider["pk"])
            if app is not None:
                client.call("DELETE", f"/core/applications/{app['slug']}/")
                saved.deleted.append(f"application:{app['slug']}")
            client.call("DELETE", f"/providers/proxy/{provider['pk']}/")
            saved.deleted.append(f"provider:{provider['pk']}")
        for record in saved.records:
            cloudflare.call("DELETE", f"zones/{cloudflare.zone_id}/dns_records/{record['id']}")
            saved.deleted.append(f"cname:{record['name']}")

    def verify(saved: _Withdrawn) -> dict[str, Any]:
        if parts["cloudflare"].records(vhost):
            raise WriteError("public record still present", FAILED)
        if read_authentik(parts["authentik"]).provider(vhost) is not None:
            raise WriteError("Authentik provider still present", FAILED)
        return {"deleted": saved.deleted,
                "not_touched": "internal Technitium record (the zone token cannot delete)"}

    def rollback(saved: _Withdrawn, error: WriteError) -> str:
        cloudflare = parts["cloudflare"]
        restored = False
        for record in saved.records:
            if f"cname:{record['name']}" in saved.deleted:
                cloudflare.call("POST", f"zones/{cloudflare.zone_id}/dns_records", {
                    k: record[k] for k in ("type", "name", "content", "proxied", "ttl") if k in record})
                restored = True
        if any(item.startswith(("provider:", "application:")) for item in saved.deleted):
            operation.note("rollback", "partial", "Authentik objects are not recreated; re-run publish")
        return "rolled-back" if restored else "not-needed"

    return writepath.run(operation, ledger, preflight=preflight, snapshot=snapshot, execute=execute,
                         verify=verify, rollback=rollback, reconcile=lambda: {"idempotent": True})


def _refused(kind: str, target: str, reason: str, code: int = USAGE) -> Operation:
    operation = Operation(kind, target, "")
    operation.outcome, operation.reason, operation.code = "refused", reason, code
    return operation


def run(repo: Path, service: str, *, context: str, state_dir: Path, dry_run: bool,
        json_output: bool, stdout: TextIO) -> int:
    operation = publish(repo, service, context=context, ledger=Ledger(state_dir), dry_run=dry_run,
                        stdout=stdout)
    if operation.outcome != "dry-run":
        deploy._print(writepath.report(operation), json_output, stdout)
    return operation.code


def run_withdraw(repo: Path, vhost: str, confirm: str, *, context: str, state_dir: Path,
                 json_output: bool, stdout: TextIO) -> int:
    operation = withdraw(repo, vhost, confirm, context=context, ledger=Ledger(state_dir))
    deploy._print(writepath.report(operation), json_output, stdout)
    return operation.code
