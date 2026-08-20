---
summary: "Publish a service through the apps Caddy front door: edit the Caddyfile then PR then deploy — own-auth (plain reverse_proxy) or forward-auth via Authentik (scoped-token provider+application)."
trigger: "Publish or expose a service"
tokens: 2659
---

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

For a service with **no gate of its own**, Authentik sits in front: an unauthenticated request is
bounced to the Authentik login, an authenticated one passes through. This is the **per-app** model
(SKY-003 P3) — each no-auth service gets its **own** proxy provider + application, so authorization
(who may reach it) and audit are per-service.

**Prerequisites (one-time, done in P3):**
- The scoped Authentik **`svc-skynet`** token lives `0600` at `/opt/skynet-ops/secrets/authentik.env`
  (`AUTHENTIK_TOKEN` + `AUTHENTIK_URL`). It can CRUD Applications/Providers and view/bind outposts —
  **nothing else** (Flows, Users, settings, keys are T3 and the token 403s on them). Creating it is a
  **T3 ceremony only Ali can do** — Skynet cannot mint it.
- The **embedded proxy outpost** exists (Applications → Outposts, `authentik Embedded Outpost`,
  type *proxy*). It is served by the Authentik server itself at **`10.10.80.37:9000`**.

**Network fact that shapes how you call the API:** only the **apps-Caddy** (`10.10.100.35`) may reach
Authentik (firewall **rule 240**) — the ops VM cannot. So Authentik API calls are driven from inside
the `caddy-apps-caddy-1` container (which has `curl`), and the token is fed on **stdin** (a curl
`-K -` config, or `read`) so it never lands in any argv. `POST /api/v3/...` bodies below are that
same call shape.

1. **Create the proxy provider** (`forward_single`). It needs an `authorization_flow` +
   `invalidation_flow`, but the scoped token **cannot list Flows** (they're T3) — so **copy the flow
   UUIDs from an existing proxy provider** you *can* read:
   ```
   GET  /api/v3/providers/proxy/          # note authorization_flow + invalidation_flow of any entry
   POST /api/v3/providers/proxy/
        {"name":"<svc>","mode":"forward_single",
         "external_host":"https://<svc>.aliammar.net",
         "authorization_flow":"<uuid>","invalidation_flow":"<uuid>"}
   ```
2. **Create the application**, bound to the new provider (`pk` from step 1):
   ```
   POST /api/v3/core/applications/
        {"name":"<Svc>","slug":"<svc>","provider":<pk>,
         "meta_launch_url":"https://<svc>.aliammar.net"}
   ```
   (Add authorization **policy bindings** to this application if the service should be limited to
   specific users/groups — that's the per-app win. Bindings are a separate T2 call.)
3. **Bind the provider to the embedded outpost** — `PATCH` its `providers` list, **keeping the
   existing entries** and appending the new `pk` (clobbering the list unbinds everything else):
   ```
   GET   /api/v3/outposts/instances/                       # find the embedded outpost pk + current providers
   PATCH /api/v3/outposts/instances/<outpost-pk>/  {"providers":[<existing…>, <pk>]}
   ```
   The outpost picks the provider up in seconds. Sanity-check before touching Caddy — from the
   `caddy-apps` container, the outpost auth endpoint should 302 to Authentik for your host:
   ```
   docker exec caddy-apps-caddy-1 curl -sI -H "Host: <svc>.aliammar.net" \
     http://10.10.80.37:9000/outpost.goauthentik.io/auth/caddy   # expect 302 -> auth.aliammar.net
   ```
4. **Add the Caddyfile site** — the standard Authentik forward-auth snippet, pointing at the embedded
   outpost. Two `reverse_proxy`: the outpost's own `/outpost.goauthentik.io/*` endpoints, then the app.
   ```
   <svc>.aliammar.net {
       reverse_proxy /outpost.goauthentik.io/* 10.10.80.37:9000
       forward_auth 10.10.80.37:9000 {
           uri /outpost.goauthentik.io/auth/caddy
           copy_headers X-Authentik-Username X-Authentik-Groups X-Authentik-Email X-Authentik-Name X-Authentik-Uid
           trusted_proxies private_ranges
       }
       reverse_proxy <origin-ip>:<origin-port>
   }
   ```
   Validate (Path A, step 2), **PR**, Ali merges, Caddy reloads on sync.
5. **Verify** from a peer DMZ container: an unauthenticated hit is **302'd to Authentik**, not served:
   ```
   ssh svc-ops@10.10.100.15 "docker exec <some-dmz-container> \
     curl -sI --resolve <svc>.aliammar.net:443:10.10.100.35 https://<svc>.aliammar.net"
   # expect 302 with Location: https://auth.aliammar.net/... — never the app's own page
   ```
   Then in a browser: unauthenticated → Authentik login → after login → the service.

**Rollback:** `git revert` the Caddyfile block (Arcane reconciles). The Authentik provider/application
delete via the scoped token (`DELETE /api/v3/core/applications/<slug>/`, then the provider) or the UI.

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
