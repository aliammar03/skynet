---
summary: "The two front doors, split-horizon DNS, and the forward_auth boundary that publishes apps without holding auth's keys (SKY-003)."
tokens: 2222
---

# Spoke · Identity & proxy

> The two front doors, the split-horizon DNS behind them, and the trust boundary that lets Skynet
> publish everyday services routinely without ever holding the keys to authentication itself.
> Governed by [`../system-design.md`](../system-design.md). Landed by directive **SKY-003** —
> the constitution's "reverse proxy / ingress" growth direction, realized.

## The two-door model

Skynet has **two reverse proxies**, and the split is a trust boundary, not a load-balancing one.
Same engine (**Caddy** — one Caddyfile, no Docker socket, one mental model for both doors), two
tiers:

| Door | Address / VLAN | Tier | Fronts | Access |
|---|---|---|---|---|
| **Management Caddy** | `10.10.60.35` · VLAN 60 Admin | **T3** | sensitive infra — `opnsense.aliammar.net`, `technitium-*`, `arcane`, `pbs`, … | admin-workstation-only (rules 210/230) |
| **Apps Caddy** | `10.10.100.35` · VLAN 100 DMZ | **T2** | everyday services — `karakeep.aliammar.net`, `calibre.aliammar.net`, … | app-client VLANs (rule 200) |

The Management Caddy is **out of scope** for Skynet — it stays T3, unchanged, admin-only. This
spoke is about the **apps** door: a GitOps Caddy stack on `vm-docker-dmz` that Skynet operates at
T2, so that **publishing a new service is a routine PR** rather than a bespoke T3 ceremony.

Why one engine for both doors: Caddy's declarative `Caddyfile` is the *entire ingress in one
reviewable PR diff*. There is no per-service label scatter and no Docker socket mount (Caddy routes
by `IP:port`, not by socket discovery) — which is exactly the property the merge-gate security model
leans on (below). It is also the same engine as the door Ali already runs, so there is one mental
model to learn, not two.

## Split-horizon DNS — the rails this rides

`aliammar.net` resolves differently inside and outside the network, and the whole ingress design
depends on that being deliberate:

| Where | Resolver | `*.aliammar.net` → | Role |
|---|---|---|---|
| **Inside** | Technitium (split-horizon) | `10.10.100.35` (apps Caddy) | steers clients to the internal proxy |
| **Outside** | Cloudflare (public authoritative) | not published internally | holds the ACME challenge + public cert trust |

So `karakeep.aliammar.net` **already resolves** internally to the apps proxy — the wildcard landed
before the proxy existed. Nothing is published to the public internet by this design: internal-only
ingress, Cloudflared is a separate path.

## TLS — publicly-trusted certs with zero device-trust install

Certs are issued by **Let's Encrypt via ACME DNS-01, using Cloudflare** as the challenge writer:

- **Why not Technitium.** DNS-01 proves domain control by writing a TXT record on the domain's
  *public authoritative* nameservers. Technitium is internal split-horizon DNS — Let's Encrypt
  cannot reach it — so pointing public ACME at it fails; it would only work with a *private* ACME CA,
  which forces a root cert onto every device. Rejected.
- **Why Cloudflare.** `aliammar.net`'s public authoritative DNS is on Cloudflare (Cloudflared already
  runs here). ACME DNS-01 via Cloudflare yields **publicly-trusted `*.aliammar.net` certs with no
  device-trust install**, fully compatible with the split-horizon: the token writes the challenge on
  the *public* zone, Technitium keeps steering clients internally, and cert validity is independent
  of the internal A records.
- **The one secret.** A Cloudflare API token scoped **Zone → DNS → Edit for `aliammar.net` only**,
  stored in `.env.sops`. Caddy reaches it via the `caddy-dns/cloudflare` plugin (a prebuilt
  community image — no bespoke `xcaddy` build). The apps Caddy validates over the Cloudflare **API on
  443** (covered by egress rule 810), **not** over `:53` — so it needs no authoritative-DNS `:53`
  grant, and firewall rule 830 (`Caddy → :53`) is **not** widened for this proxy.

## One Caddy, two publish paths

A single apps Caddy site file carries both kinds of service — the fan-out the firewall was already
staged for (rule 240 → Authentik, rule 250 → origins):

- **Own-auth services** (e.g. **karakeep** — has its own login) get a plain
  `reverse_proxy 10.10.100.75:3000` site. No Authentik in the path.
- **No-auth services** (e.g. **calibre** — no gate of its own) get the **same** site plus a
  `forward_auth` directive to an Authentik outpost
  (`/outpost.goauthentik.io/auth/caddy`) → `reverse_proxy 10.10.100.53:8080`. Unauthenticated
  requests are bounced to Authentik; authenticated ones pass through.

Publishing either kind is a PR against the Caddyfile → Ali merges → Arcane reconciles. The
step-by-step for both paths lives in the `publish-service` runbook.

## The Authentik trust split — the boundary this directive moves

Authentik was **entirely T3**. SKY-003 graduates *only routine app publishing* to T2, leaving the
spine of authentication privileged. The shape is identical to the Technitium boundary the
[access-and-trust](access-and-trust.md) spoke already anticipates (zones = T2, server settings = T3):

| Capability | Tier | Mechanism |
|---|---|---|
| **Applications** + **Providers** — add / change / view | **T2** | scoped `svc-skynet` service-account token |
| **Outpost** — view / bind an existing outpost | **T2** | same scoped token |
| **Flows, Policies** (the authentication spine) | **T3** | never in the token's scope |
| **Users, Groups** | **T3** | never in the token's scope |
| **System settings, outpost tokens, signing keys** | **T3** | never in the token's scope |

The scoped token is **created by a one-time T3 ceremony Ali performs in the Authentik UI** (Skynet
cannot mint it), then stored `0600` at `/opt/skynet-ops/secrets/authentik.env` (or sops). Its scope
must be *verified real* — the token has to demonstrably fail to touch Flows, Users, settings, or
keys. After that, everyday app/provider provisioning rides the T2 token; rebuilding Authentik was
considered and rejected (it would discard enrolled users, MFA/passkey registrations, providers, and
signing keys for no benefit).

## The honest security position (recorded on purpose)

`forward_auth` at T2 is **not** protected by the SSH tier, and pretending otherwise would be the
dangerous kind of lie. On a docker host, non-root `svc-ops` is in the **docker group**, and
docker-group ≈ root (`docker run -v /:/host …` escapes to host root). So a holder of the T2 SSH key
on `vm-docker-dmz` could, in principle, edit the Caddyfile, reload, and strip auth off calibre — or
read the forward-auth shared secret from a container's env. What actually guards the auth is three
*other* controls, and the design leans on them deliberately:

1. **Network segmentation** — rule 200 lets clients reach *only the proxy*; rule 250 lets *only the
   proxy* reach origins:8080. Even if auth were stripped, an origin is exposed only to internal
   app-client VLANs, **never the internet**, and only until the next sync.
2. **Config-in-git + human merge gate** — the *sanctioned* way to change a route/auth is a PR **Ali
   merges**. Auth cannot legitimately change without a merge; any direct-host edit is out-of-band.
3. **Drift is loud and temporary** — Arcane reconciles from git; the nightly inventory diff surfaces
   tampering, which then auto-reverts.

**Net residual risk:** an insider with the ops SSH key could expose an *internal* service to other
*internal* users, visibly in git-diff, until the next sync. Contained, auditable, internal-only —
**accepted for T2.** SKY-003 Phase 4 verifies these controls actually hold and audits who can even
reach that SSH port in the first place.

## Where the parts live

| Part | Home |
|---|---|
| Apps Caddy stack + `Caddyfile` (routes in git) | `compose/caddy-apps/` |
| Firewall aliases/rules (`HOST_PROXY_APPS`, `HOST_AUTHENTIK`, rules 200/240/250/830) | [network](network.md) |
| The tier tiers themselves (T2/T3, scoped-token pattern) | [access-and-trust](access-and-trust.md) |
| How a route change deploys (PR → Arcane reconcile) | [gitops-loop](gitops-loop.md) |
| Publishing a service (both paths) | `runbooks/publish-service.md` |

## Planned expansion

- **More protected apps.** Each new no-auth service is a `forward_auth` site + a provider/application
  created through the scoped T2 token — routine, no boundary move.
- **Proxy config generated from `inventory/`.** The Caddyfile could eventually be rendered from
  inventory the way `docs/generated/` already is, closing the loop end-to-end.
- **A secrets vault beyond sops+age.** If the token/secret count outgrows file-level sops, the
  Cloudflare + Authentik tokens are candidates for an external backend — see [secrets](secrets.md).
