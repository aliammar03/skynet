# Runbook — publish a service through the apps Caddy (the front door)

**Tier:** T2 (PR-gated). **Executor:** edit the Caddyfile → PR → Ali merges → `scripts/gitops-deploy.sh caddy-apps`.
**Rollback:** `git revert` (Arcane reconciles the old routes back).

This is how a service gets a real URL (`https://<svc>.aliammar.net`) instead of a raw `IP:port`.
The whole apps ingress is **one file in git** — `compose/caddy-apps/Caddyfile` — so publishing is a
reviewable PR, not a bespoke task. Background + the trust model: [`../docs/design/identity-and-proxy.md`](../docs/design/identity-and-proxy.md).

## Which path? Two kinds of service

| The service… | Path | What you add |
|---|---|---|
| **has its own login** (karakeep, most apps) | **own-auth reverse proxy** | one `reverse_proxy` site block |
| **has no gate of its own** (calibre) | **forward-auth** | the same site **plus** `forward_auth` to an Authentik outpost, **plus** a scoped-token-created Authentik provider/application |

Pick the own-auth path unless the service genuinely has no authentication of its own.

## Prerequisites (true for every publish)

- The origin runs on the **DMZ** network with a known `IP:port` (see its `compose/<svc>/compose.yaml`).
- `*.aliammar.net` already resolves internally to the apps Caddy (`10.10.100.35`) via Technitium
  split-DNS — so `<svc>.aliammar.net` resolves the moment the route exists. (Public DNS is Cloudflare;
  nothing is exposed to the internet — this is internal ingress only.)
- TLS is automatic: Caddy issues a publicly-trusted cert via ACME **DNS-01 over Cloudflare**. No
  per-service cert work, no device-trust install.

---

## Path A — own-auth reverse proxy (the common case)

1. **Branch** `deploy/caddy-apps`. Edit `compose/caddy-apps/Caddyfile`, add a site block:
   ```
   <svc>.aliammar.net {
       reverse_proxy <origin-ip>:<origin-port>
   }
   ```
   Use the origin's **actual** listen port (e.g. karakeep-web is `10.10.100.75:3000`, not 8080).
2. **Validate** the Caddyfile before you PR (catches typos without touching the running proxy):
   ```
   cd compose/caddy-apps
   docker run --rm -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" \
     ghcr.io/caddybuilds/caddy-cloudflare:2.11.4-alpine \
     caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   ```
   (`caddy fmt --overwrite /etc/caddy/Caddyfile` normalizes formatting.)
3. **PR** with a teaching description (what the service is, its origin `IP:port`, the URL it gets,
   own-auth vs forward-auth). **Ali merges** — the merge gate is what actually protects the routes
   (see the honest security position in the spoke). The agent never merges its own PR.
4. **Deploy:** `scripts/gitops-deploy.sh caddy-apps` — pulls the merged Caddyfile, redeploys, health-checks.
5. **Verify** from an app-client vantage (a host on the DMZ / app-client VLANs, where split-DNS
   resolves `*.aliammar.net` → `10.10.100.35`):
   ```
   curl -sSI https://<svc>.aliammar.net        # expect 200/302 from the service, valid public cert
   ```
   From the ops host (`vm-skynet-ops`, VLAN 90) the name resolves to **public** Cloudflare IPs, not
   `.35`, so verify against the proxy directly instead:
   ```
   curl -sSI --resolve <svc>.aliammar.net:443:10.10.100.35 https://<svc>.aliammar.net
   ```
6. If red → `git revert`, re-run `scripts/gitops-deploy.sh caddy-apps`.

---

## Path B — forward-auth (no-login services, via Authentik)

> Added in SKY-003 Phase 3. Requires the scoped Authentik `svc-skynet` token (a T3 one-time
> ceremony Ali performs — Skynet cannot mint it). Provisioning the Authentik provider/application
> through that token, plus the `forward_auth` Caddyfile block, is documented here once P3 lands.

<!-- P3 fills this in: create Provider+Application via the scoped token → bind the outpost →
     add the forward_auth directive to the Caddyfile site → verify unauth→Authentik→service. -->

---

## Notes

- **Certs persist** across restarts (bind-mounted `/opt/docker/appdata/caddy-apps/data`) — Caddy does
  not re-issue on redeploy, so Let's Encrypt rate limits are not a concern for routine route changes.
- **One role tag** (`proxy`, red) and **one healthcheck** (Caddy admin API on `:2019`) already ship in
  `compose/caddy-apps/compose.yaml`; a new *site* changes only the Caddyfile, never the compose.
- **The apps Caddy is T2, the Management Caddy is T3** and out of scope — never publish sensitive infra
  (`opnsense`, `technitium`, `arcane`, `pbs`, …) through this door.
