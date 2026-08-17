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
4. **Deploy.** A route-only change is just the Caddyfile, and Caddy runs with `--watch`, so once the
   PR merges Arcane's auto-sync updates the mounted Caddyfile and **Caddy reloads itself** — no
   container recreate, no manual `caddy reload`. Run `scripts/gitops-deploy.sh caddy-apps` only to
   force it immediately (or after a *compose* change, which does need the container recreated).
5. **Verify** from a peer **DMZ container** — the reliable vantage. The apps Caddy sits on a **macvlan**
   IP, so it is unreachable *from its own docker host* and from the ops VM (VLAN 90, no rule-200 path):
   ```
   ssh svc-ops@10.10.100.15 "docker exec <some-dmz-container> \
     curl -sSI --resolve <svc>.aliammar.net:443:10.10.100.35 https://<svc>.aliammar.net"
   # expect a real status (200/302/401…) and a valid public cert (ssl_verify_result=0)
   ```
   The **first** hit on a new hostname may briefly fail TLS while Caddy obtains the ACME cert
   (DNS-01, ~15–30s); retry. A `502` right after a deploy usually just means the upstream is still
   warming up.
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

### When the upstream *self-protects* (check the origin, not just the route)

A site block only moves bytes — it doesn't change how the origin treats the proxy. Two failure
shapes show up here, both fixed on the **service**, not the Caddyfile:

- **The origin allow-lists source IPs.** If it only trusts certain clients, it will `403` the proxy
  (which connects from `10.10.100.35`). Fix it *in the service's own config, in git* — e.g.
  **SillyTavern** refuses to run with no gate at all (it crash-loops on `whitelistMode=false`), so its
  gate is a whitelist: `SILLYTAVERN_WHITELIST=["::1","127.0.0.1","10.10.0.0/16"]` in
  `compose/silly/.env.git` allows the proxy + its `X-Forwarded-For` clients. Prefer an env/`.env.git`
  knob over hand-editing appdata so the gate is reproducible.
- **The origin does app-level OIDC to `auth.aliammar.net`.** That name has no dedicated DNS record, so
  the `*.aliammar.net` wildcard lands it on this proxy — it needs the `auth.aliammar.net` →
  Authentik (`10.10.80.37:9000`) site to exist, or the login redirect 404s. (Already in the Caddyfile.)

### Own-auth vs "no gate at all"

"Own-auth" means the origin has a **real login** (karakeep, aiostreams, marinara's basic-auth → `401`).
A service with *no* login is only shielded by network segmentation until Path B (forward-auth) lands —
proxy it plainly only as a deliberate, internal-only choice.
