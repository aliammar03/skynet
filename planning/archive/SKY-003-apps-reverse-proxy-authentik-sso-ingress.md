---
id: SKY-003
title: Apps reverse proxy + Authentik SSO ingress
status: done
horizon: short
created: 2026-08-16
updated: 2026-08-20
phases: 5
current_phase: 5
tier_touched: [T1, T2, T2+, T3]   # T2 apps proxy; T2-scoped Authentik provisioning; Authentik server-admin
                                  # + OPNsense stay T3 → this directive PRs docs/system-design.md by rule.
related:
  - docs/system-design.md
  - docs/design/network.md
  - docs/design/access-and-trust.md
  - docs/design/identity-and-proxy.md   # NEW — authored in Phase 1
  - compose/karakeep/compose.yaml
  - compose/calibre/compose.yaml
  - "[[arcane-api-reference]]"
  - "[[skynet-service-standard]]"
---

# SKY-003 · Apps reverse proxy + Authentik SSO ingress

> Give everyday services a real front door. Stand up a **T2 apps Caddy** at `karakeep.aliammar.net`
> (and friends) — the everyday-services twin of the T3 Management Caddy — and wire **Authentik**
> forward-auth in front of services that have no login of their own (calibre). Do it on the
> skynet way (GitOps, config-in-git), onto firewall + split-DNS rails that are **already staged**.

## 1. Problem / motivation

Today there are two front doors' worth of *intent* and only one that exists:

- **Management Caddy** (`10.10.60.35`, VLAN 60 Admin) is real and **T3** — admin-workstation-only
  access to sensitive services (`opnsense.aliammar.net`, `technitium-*`, `arcane`, `pbs`, …). Good.
- **The apps side is scaffolded but empty.** The firewall config mirror already defines
  `HOST_PROXY_APPS` (`10.10.100.35`, VLAN 100 DMZ), `HOST_AUTHENTIK` (`10.10.80.37`, VLAN 80
  Identity), and rules **200** (app clients → apps proxy), **240** (apps proxy → Authentik), **250**
  (apps proxy → app origins:8080), plus **830** (Caddy → authoritative DNS for ACME). Split-DNS is
  live: `*.aliammar.net` → `10.10.100.35`, so `karakeep.aliammar.net` **already resolves** to a
  proxy that doesn't exist yet. Authentik is installed and running in an LXC. **But there is zero
  proxy/auth config in this repo** — nothing rides the rails.

Consequences of the gap: everyday services are reached by raw `IP:port` (or not at all); services
with no built-in auth (calibre) have no gate in front of them; and the constitution's named
growth direction "reverse proxy / ingress" plus its "likely-next" spoke `identity-and-proxy.md`
are still on paper. This directive builds the apps front door and, in doing so, makes **publishing
a new service a routine T2 PR** rather than a bespoke task.

## 2. Brainstorm — options considered

**Proxy engine** — evaluated against the one axis that matters most here: *config-in-git as a
single reviewable artifact is the actual security control* (the merge gate, not the SSH tier, is
what protects `forward_auth` — see the honest security position below).
- **A — Nginx Proxy Manager:** friendly GUI, but its state is a database, not git — it fights the
  GitOps loop and can't be reviewed in a PR. Rejected.
- **B — Traefik (genuinely evaluated):** docker-native and powerful. Its idiomatic mode (Docker
  provider) discovers backends via **labels on each service's compose** and wants the **Docker
  socket** mounted into the proxy (≈ root — needs a socket-proxy to be safe). That scatters ingress
  across every compose (no single reviewable diff) and widens the attack surface — both against our
  model. Its **file provider** (central dynamic YAML) avoids the socket and keeps config-in-git, but
  then you've dropped Traefik's headline feature and taken on a more verbose router→service→
  middleware object graph. Traefik's real wins are **built-in DNS-ACME providers (no custom image)**
  and a **turnkey dashboard + Prometheus** — but at this scale (one instance, a handful of static
  backends) they're mostly unused, and the DNS-ACME edge is neutralized once we pick Cloudflare
  (below), where prebuilt Caddy images are ubiquitous. Viable, but a second engine to run and teach
  for advantages we don't need. Rejected for this system.
- **C — Caddy (CHOSEN):** one declarative `Caddyfile` in git — the whole ingress in one PR diff —
  first-class `forward_auth`, no Docker socket (routes by IP:port). **Same engine as the Management
  Caddy → one mental model for both doors**, legible for a learning operator. Config-as-code is the
  cleanest possible fit for GitOps + human-merge review. Ali's call: "ol' reliable."

**TLS / ACME — Cloudflare vs Technitium DNS-01 (DNS-01 chosen; Cloudflare, decisively)**
- DNS-01 proves domain control by writing a TXT record on the domain's **public authoritative**
  nameservers — it needs no inbound reachability, so it issues certs for internal-only services.
- **Technitium** is the *internal, split-horizon* DNS (`*.aliammar.net` → 10.10.100.35). Let's
  Encrypt **can't reach it**, so pointing public ACME there fails; it only works with a **private
  ACME CA**, which forces a root cert onto every device. Rejected.
- **Cloudflare (CHOSEN)** is `aliammar.net`'s public authoritative DNS (confirmed — the domain is on
  Cloudflare; Cloudflared already runs here). ACME DNS-01 via Cloudflare yields **publicly-trusted
  `*.aliammar.net` certs with zero device-trust install**, fully compatible with the split-horizon
  (the token writes the challenge on the *public* zone; Technitium keeps steering clients internally;
  cert validity is independent of the internal A records). Token scoped to **Zone → DNS → Edit for
  `aliammar.net` only**, stored in `.env.sops`. Caddy reaches it via the `caddy-dns/cloudflare`
  plugin (a prebuilt cloudflare-enabled image — the most common Caddy plugin, not a bespoke build).

**Number of proxies**
- **Two proxies** (a plain one + a separate auth-enforcing one): more parts, two things to keep in
  sync, and the firewall was staged for one (`HOST_PROXY_APPS` fans out to both Authentik *and*
  origins).
- **One apps Caddy (CHOSEN):** own-auth services (karakeep) get a plain `reverse_proxy` site;
  no-auth services (calibre) get the **same** site plus a `forward_auth` directive to an Authentik
  outpost. One config, one host, matches the staged rules 240 + 250.

**Authentik trust boundary**
- **Keep everything T3:** every new protected app becomes a T3 dormant-alias ceremony. Safe, but
  kills the "Skynet provisions apps easily" goal Ali asked for.
- **Scoped T2 provisioning (CHOSEN):** a dedicated `svc-skynet` Authentik service account whose
  role can CRUD **Applications + Providers** and **bind to an existing outpost** — and *nothing*
  else. Users, groups, **Flows/Policies** (the spine of authentication itself), System settings,
  outpost tokens, and signing keys stay **T3**. This is the exact shape of the Technitium boundary
  (zones = T2, server settings = T3) the access-and-trust spoke already anticipates.

**Decision:** one **Caddy** apps proxy at **T2** (GitOps docker stack on `vm-docker-dmz`) with
**publicly-trusted certs via Cloudflare DNS-01**, keep the existing Authentik LXC, and graduate
*only routine app/provider provisioning* to a **scoped T2 token**. Rebuilding Authentik was
considered and rejected — it would throw away enrolled users, MFA/passkey registrations, providers,
and signing keys for no benefit.

### The honest security position (recorded here on purpose)

`forward_auth` at T2 is **not** protected by the SSH tier. On a docker host, non-root `svc-ops` is
in the **docker group**, and docker-group ≈ root (`docker run -v /:/host …` escapes to host root).
So a holder of the T2 SSH key on `vm-docker-dmz` could, in principle, edit the Caddyfile, reload,
and strip auth off calibre — or read the forward-auth shared secret from a container's env. What
actually guards the auth is three *other* controls, and the design leans on them deliberately:

1. **Network segmentation** — rule 200 lets clients reach *only the proxy*; rule 250 lets *only the
   proxy* reach origins:8080. Even if auth were stripped, an origin is exposed only to internal
   app-client VLANs, **never the internet**, and only until the next sync.
2. **Config-in-git + human merge gate** — the *sanctioned* way to change a route/auth is a PR **Ali
   merges**. Auth can't legitimately change without a merge; any direct-host edit is out-of-band.
3. **Drift is loud and temporary** — Arcane reconciles from git; the nightly inventory diff surfaces
   tampering, which then auto-reverts.

Net residual risk: *an insider with the ops SSH key could expose an internal service to other
internal users, visibly in git-diff, until the next sync.* Contained, auditable, internal-only —
accepted for T2. Phase 4 verifies these controls actually hold (and audits who can even reach that
SSH port in the first place).

## 3. The plan

- **Scope.** Build the apps Caddy stack; publish karakeep (own-auth) and calibre (forward-auth) as
  the two pilots; create the scoped Authentik `svc-skynet` token + a "publish a service" runbook;
  author the `identity-and-proxy` spoke + the mandatory constitution PR; finish with a firewall
  hardening pass **and** a DMZ-docker SSH-exposure audit.
- **Non-goals.** Not touching the **Management Caddy** (stays T3, unchanged). **No internet
  exposure** — this is internal ingress only (Cloudflared is a separate path). No migration of
  existing LXC services onto docker. No secrets-vault work. The agent never merges its own PRs.
- **Hosts & tiers touched.** `vm-docker-dmz` (`10.10.100.15`, T2 svc-ops SSH — the apps Caddy runs
  here) · Authentik LXC (`10.10.80.37`, T3 server-admin for the one-time scoped-account setup, then
  T2 via the scoped token) · OPNsense (`T3`, human-applied firewall changes in Phase 4) ·
  `docs/system-design.md` (constitution PR, by the boundary-change rule).
- **Rollback posture.** Every phase is a PR → `git revert`. Caddy routes revert via git + Arcane
  reconcile. Authentik app/provider objects delete via the scoped token or the UI. Firewall changes
  revert via the OPNsense config mirror.
- **Grants / human actions (narrowest per phase).** P1: none (docs). P2: none expected — GitOps +
  svc-ops T2; a one-time `gr vm-docker-dmz 1h` **only if** host-level networking needs a touch. P3:
  a **T3 Authentik ceremony** — Ali creates the `svc-skynet` account + scoped role + token in the
  Authentik UI (one-time; not a Skynet-mintable grant). P4: **T3 OPNsense** — agent proposes the
  ruleset delta, Ali applies it on OPNsense. P5: none.

---

### Phase 1 — The trust-boundary decision, in writing  (~1–2h)   `[x]` done — 2026-08-17

Docs only — write the decision down *before* building it, because it moves a trust boundary.

Steps:
1. Author **`docs/design/identity-and-proxy.md`** (the spoke the constitution names as likely-next):
   the two-door model (admin Caddy T3 / apps Caddy T2), the split-DNS map, one-Caddy `forward_auth`,
   the Authentik **scoped-token** boundary (Applications+Providers CRUD + outpost bind = T2;
   flows/users/settings/keys = T3), and **the honest docker-group≈root position + the three controls**
   from §2 above, verbatim in spirit.
2. **PR `docs/system-design.md`:** move `identity-and-proxy` from "likely-next" into the live spoke
   index (§7); update §6 growth direction ("reverse proxy / ingress" → landing via SKY-003); adjust
   the trust-model note so Authentik reads "server admin T3; app/provider provisioning T2 (scoped)".
3. Update the **Planned expansion** sections of `network.md` (reverse proxy → realized, cross-link
   the new spoke) and `access-and-trust.md` (Authentik-out-of-T3 → realized, scoped-token pattern).

Exit criteria: new spoke exists and is self-consistent; the constitution indexes it and records the
Authentik tier split; every internal link resolves; no infra touched. → PR.
Grants / human actions: none beyond Ali merging the P1 PR.

### Phase 2 — Apps Caddy stack + karakeep pilot (own-auth reverse proxy)  (~1–2h)   `[x]` done — 2026-08-17

Steps:
1. Create `compose/caddy-apps/` on the skynet way: digest-pinned **cloudflare-enabled Caddy image**
   (`caddy-dns/cloudflare` — a prebuilt community image, no bespoke xcaddy build), `env_file: .env`,
   a healthcheck, `x-arcane` role tag (`proxy`, pick a stable colour), attached to the external `dmz`
   network at **`10.10.100.35`**. Mount the `Caddyfile` as a repo-tracked `./Caddyfile:/etc/caddy/Caddyfile:ro`
   (GitOps-synced) so routes live in git. **TLS: ACME DNS-01 via Cloudflare** for publicly-trusted
   `*.aliammar.net` certs (no device-trust install; works for internal-only services). The Cloudflare
   API token (scoped **Zone→DNS→Edit, `aliammar.net` only**) is the sole secret → `.env.sops`. The
   proxy reaches the Cloudflare API over **outbound 443** (already covered by `NET_WEB_EGRESS` rule
   810 — no new firewall rule needed; see the Phase-4 note on rule 830).
2. First site: **`karakeep.aliammar.net`** → `reverse_proxy 10.10.100.75:3000` (karakeep has its own
   login — no forward-auth). Confirm the `*.aliammar.net` wildcard already lands on `.35`.
3. Deploy with `scripts/gitops-deploy.sh caddy-apps`; confirm `(healthy)` and a working HTTPS hit.
4. Start the **`runbooks/publish-service.md`** runbook (T2) — the reverse-proxy case: "add a site to
   the Caddyfile → PR → deploy". Catalogue it in `runbooks/README.md`.

Exit criteria: `https://karakeep.aliammar.net` serves karakeep through the apps proxy, healthy, all
config in git; publish-service runbook covers the own-auth path. → PR.
Grants / human actions: none expected (GitOps + svc-ops T2). Checkpoint & request `gr vm-docker-dmz 1h`
**only if** host-level macvlan/network setup turns out to be needed.

### Phase 3 — Authentik scoped token + calibre pilot (forward_auth)  (~1–2h)   `[x]` done — 2026-08-20

Steps:
1. **T3 ceremony (Ali, one-time, in the Authentik UI):** create service account `svc-skynet` + a role
   scoped to `Application` and `Provider` **add/change/view** and outpost **view/bind** only; issue an
   API token. Store it `0600` at `/opt/skynet-ops/secrets/authentik.env` (or sops). **Verify the
   scope is real** — the token must fail to touch Flows, Users, System settings, or keys.
2. Using the **scoped token** (proving the T2 path), create a proxy/forward-auth Provider + Application
   for calibre and bind it to the existing outpost.
3. Add **`calibre.aliammar.net`** to the Caddyfile: `forward_auth` to the outpost's Caddy endpoint
   (`/outpost.goauthentik.io/auth/caddy`) → `reverse_proxy 10.10.100.53:8080`. PR + `gitops-deploy.sh`.
4. Verify: unauthenticated → redirected to Authentik; after login → calibre. Extend
   `runbooks/publish-service.md` with the **forward-auth** case (the T2 provisioning-via-token steps).

Exit criteria: calibre is reachable only after Authentik login; the scoped token demonstrably CRUDs
apps/providers but nothing privileged; the runbook documents both publish paths. → PR.
Grants / human actions: the Phase-3 step 1 Authentik account/role/token creation is a **T3 human
action** — hard checkpoint, Ali does it in the UI. Everything after uses the scoped T2 token.

### Phase 4 — Firewall hardening + DMZ-docker SSH-exposure audit  (~1–2h)   `[x]` done — 2026-08-20

The "prove the controls actually hold" phase Ali asked for. Firewall changes are **T3** — the agent
proposes the delta; Ali applies it on OPNsense.

Steps:
1. **Least-privilege pass on the ingress rules now that the proxy is live:** reconcile
   `ROLE_APP_ORIGINS` to *exactly* the origins actually proxied (prune stale, add missing); check
   `PORT_APP_BACKENDS` (currently `8080`) against reality — karakeep-web listens on **3000**, so
   either front it on 8080 internally or add 3000 as the **narrowest** fix; confirm rule 240 targets
   the right `PORT_AUTHENTIK` for the outpost forward-auth endpoint; confirm **no direct
   client→origin path** exists (clients hit only the proxy). **Rule 830 check:** it permits
   `Caddy → authoritative DNS :53` — but with **Cloudflare DNS-01** the apps Caddy validates over the
   Cloudflare **API on 443** (already covered by rule 810), *not* :53. So the apps Caddy needs no
   `:53` grant; confirm rule 830 is still justified only by whatever actually uses it (Management
   Caddy / resolvers) and don't widen it for this proxy.
2. **DMZ-docker SSH-exposure audit** (the docker-group≈root surface): enumerate *what can reach
   `10.10.100.15:22`* at the **network** layer (expect only `HOST_ADMIN_WORKSTATION` via rule 220
   breakglass + `HOST_SKYNET_OPS` via rule 370 — flag anything else) **and** *who can authenticate*
   at the **host** layer (svc-ops `authorized_keys`, root CA principals via `AuthorizedPrincipalsFile`,
   `PermitRootLogin prohibit-password`, docker-group membership). Confirm the T3 dormant alias
   `ROLE_OPS_PRIV_TARGETS` is still **empty**. Record the finding in `inventory/`.
3. Write the resulting firewall/host delta as a reviewable change set (config-mirror diff + notes);
   **Ali applies** any OPNsense change. Re-collect the firewall mirror; confirm the docs regenerate
   clean and drift-check is green.

Exit criteria: ingress rules match the live topology at least-privilege; the exact SSH-reach +
SSH-auth surface of `vm-docker-dmz` is documented and minimal; any change is applied by Ali and
re-mirrored. → PR.
Grants / human actions: **T3 OPNsense** changes are human-applied (hard checkpoint). Reads use T1.

### Phase 5 — Close-out  (~30m)   `[x]` done — 2026-08-20

Steps:
1. `bin/plan archive SKY-003` (status → done) + `bin/plan list` (regenerate roadmap).
2. Catalogue caddy-apps + the publish-service capability in `planning/services/` if useful.
3. Memory: write `SKY-003-progress` (what shipped, the tier split, the docker-group caveat, the
   publish-a-service one-liner) + a `MEMORY.md` pointer.

Exit criteria: roadmap shows SKY-003 done; memory reflects the new apps front door + provisioning
path. → PR (may fold into P4's close-out).

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-003-apps-reverse-proxy-authentik-sso-ingress.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-003-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-003-apps-reverse-proxy-authentik-sso-ingress.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-003-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-16 — created (approved, not yet started). Born from Ali's ask for an everyday-services
  front door (twin of the T3 Management Caddy) + Authentik-protected apps for services without their
  own login. Research found the firewall + split-DNS **already staged** for this exact topology
  (`HOST_PROXY_APPS`, `HOST_AUTHENTIK`, rules 200/240/250/830; `*.aliammar.net` → 10.10.100.35) with
  **no proxy/auth config in the repo yet**. Decided: one **Caddy** apps proxy at **T2** (GitOps
  stack on vm-docker-dmz), keep the existing Authentik LXC, graduate only app/provider provisioning
  to a **scoped T2 token** (flows/users/settings/keys stay T3). Accepted the honest docker-group≈root
  position, guarded by network segmentation + human merge gate + drift-revert. Phase 4 adds the
  firewall hardening pass **and** a DMZ-docker SSH-exposure audit (both at Ali's request).
- 2026-08-16 — **engine + TLS decided.** Evaluated Traefik vs Caddy properly (Traefik's Docker/label
  provider wants the Docker socket + scatters config → against the config-in-git/merge-gate model;
  its file-provider gives that up; its DNS-ACME/dashboard wins are unused at this scale). **Caddy
  chosen** ("ol' reliable" — one Caddyfile, no socket, one engine across both doors). TLS: **ACME
  DNS-01 via Cloudflare** (confirmed `aliammar.net` public DNS is on Cloudflare) → publicly-trusted
  `*.aliammar.net` certs, no device-trust install, split-horizon-compatible; token scoped
  Zone→DNS→Edit for the one zone, in `.env.sops`. Knock-on: rule 830 (`:53`) isn't needed for this
  proxy (Cloudflare API rides 443 / rule 810) — noted for the Phase-4 hardening pass.
- 2026-08-17 — **Phase 1 done (docs only).** Authored the `identity-and-proxy` spoke (two-door model,
  split-horizon DNS, Cloudflare DNS-01, one-Caddy `forward_auth`, Authentik T2/T3 split, the honest
  docker-group≈root position + three controls). Constitution PR'd: §6 growth directions
  (reverse-proxy + SSO now "landing via SKY-003"), §7 spoke index (identity-and-proxy promoted out of
  "likely-next"), §3 trust note (Authentik server-admin T3 / app+provider provisioning T2 scoped).
  `network.md` + `access-and-trust.md` "Planned expansion" → realized; `gitops-loop.md` cross-linked.
  All internal links verified; no infra touched. → PR (agent does not merge its own).
- 2026-08-17 — **Phase 2 done (apps Caddy live).** PR #40 merged: `compose/caddy-apps/` — prebuilt
  `caddybuilds/caddy-cloudflare:2.11.4-alpine` (digest-pinned, cloudflare plugin baked in, no xcaddy);
  role tag `proxy`/red; DMZ macvlan `10.10.100.35`; `Caddyfile` ro-mounted from git; ACME certs
  persisted; healthcheck on Caddy admin `:2019`. First site `karakeep.aliammar.net → reverse_proxy
  10.10.100.75:3000` (own-auth). **Let's Encrypt cert issued via Cloudflare DNS-01** (token scoped
  Zone→DNS→Edit, in `.env.sops`; decrypt round-trip verified). `runbooks/publish-service.md` shipped
  (own-auth reverse-proxy path; forward-auth path stubbed for P3) + catalogued. Deployed via
  `scripts/gitops-deploy.sh caddy-apps`; container `(healthy)`; verified end-to-end from a peer DMZ
  container — HTTP 200, valid public cert, redirect to karakeep `/signin`. Two deploy notes for
  later: `gitops-deploy.sh` writes the project `.env` as `root@vm-docker-dmz` → needs a **T2+ root
  grant** (`gr vm-docker-dmz 1h`, auto-expiring — used once here); and a **macvlan** container is
  unreachable from its own host, so HTTPS must be verified from a *peer* DMZ container, not the host
  or the ops VM.
- 2026-08-20 — **Phase 3 agent-work done (PR open; awaiting merge + live verify).** Ali ran the **T3
  ceremony**: `svc-skynet` service account + scoped role + API token (`0600` at
  `/opt/skynet-ops/secrets/authentik.env`). **Scope verified real** — the token views
  Applications/Providers/Outposts (200) and **403s** on Flows, Users, Groups, signing keys, and system
  settings, exactly as designed. **Auth-model decision: Option A — per-app forward-auth** (chosen over
  reusing the pre-existing domain-level provider pk 2), for per-service authorization + audit +
  contained blast radius, matching the directive/spoke. Via the scoped token: created proxy provider
  **pk 14** `calibre` (`forward_single`, `external_host=https://calibre.aliammar.net`, flows reused
  from the un-listable-by-token domain provider), Application **`calibre`** → provider 14, and bound 14
  to the **embedded proxy outpost** (`providers:[2,14]`). Pre-merge sanity from the `caddy-apps`
  container: the outpost auth endpoint **302s to Authentik with provider 14's own client_id + a calibre
  callback** for `Host: calibre.aliammar.net` (an unmatched host falls through to domain provider 2).
  Caddyfile: `calibre.aliammar.net` converted to the standard Authentik forward-auth snippet (outpost
  endpoints + `forward_auth` → `10.10.80.37:9000` rule 240, then `reverse_proxy 10.10.100.53:8080`);
  `caddy validate` clean. `runbooks/publish-service.md` **Path B** filled in (per-app provider+app via
  scoped token, the flow-reuse gotcha, outpost-bind-don't-clobber, verify). **Token hygiene:** the API
  is driven from inside `caddy-apps-caddy-1` (the only container rule 240 lets reach Authentik), token
  fed on stdin so it never hits argv. → PR (agent does not merge its own). **Next:** Ali merges → agent
  live-verifies unauth→302→login→calibre from a peer DMZ container → flips P3 `[x]` + close-out.
- 2026-08-20 — **Phase 3 DONE (verified live).** PR #77 merged (forward-auth + runbook Path B; a
  follow-on commit also added runbook **Path C** — optional public exposure via the Cloudflare Tunnel).
  Triggered the Arcane sync (`gitops-deploy.sh caddy-apps`); Caddy hot-reloaded the merged Caddyfile.
  **Live check from a peer DMZ container:** `calibre.aliammar.net` → **HTTP 302 → auth.aliammar.net**
  with provider-14's client_id + a calibre callback — unauthenticated requests are bounced to Authentik,
  not served. All P3 exit criteria met: gate live, scoped token proven (CRUDs apps/providers, 403s on
  flows/users/keys/settings), both publish paths documented. **Next: P4** (firewall least-privilege +
  DMZ-docker SSH-exposure audit). Note for P4: Ali amended rule 240 to add `HOST_SKYNET_OPS` as a source
  (ops VM → Authentik) — it's saved in config.xml but was not passing live at close-out (needs OPNsense
  Apply); the agent drove the Authentik API via the caddy-apps container instead. Also: a **public
  calibre** exposure is under discussion (goal: publicly reachable; low-friction/no-dashboard gating) —
  that's SKY-014-adjacent, tracked separately, not part of SKY-003.
- 2026-08-20 — **Phase 4 DONE (audit + least-privilege delta applied).** Read-only audit (T1) →
  findings journaled. **Ingress:** core segmentation confirmed (no client→origin rule; clients reach
  only the proxy). Discovered app origins are all **intra-DMZ** (same VLAN 100 as Caddy) → L2, never
  firewalled, so rule 250/`PORT_APP_BACKENDS` governed nothing real (corrects the P3 "karakeep :3000"
  note — no fix needed). Ali **deleted rule 250 + `ROLE_APP_ORIGINS` + `PORT_APP_BACKENDS`** entirely
  (dead config; a stale cross-VLAN `10.10.20.63` was its only enforced member). **Rule 830** trimmed —
  `HOST_PROXY_APPS` removed (apps Caddy validates ACME on the CF API 443, needs no `:53`). **SSH
  exposure of `vm-docker-dmz`:** rules 270 & 370 both granted ops→`.15:22`, with 270 over-broad
  (superseded 260/270 family); Ali **deleted rule 270 + orphaned `ROLE_SKYNET_OPS_TARGETS`**, leaving
  the narrow rule 370 as the sole ops-SSH rule. **Host sshd** (agent, under a `gr vm-docker-dmz`
  grant): `PasswordAuthentication no` + removed the stray `PermitRootLogin yes`/`PasswordAuthentication
  yes` footguns; `sshd -T` confirms `passwordauthentication no` / `permitrootlogin without-password`;
  no lockout. `ROLE_OPS_PRIV_TARGETS` **confirmed empty**. Re-collected the mirror (via a fresh `gh`
  clone — the root mirror lags, no https creds in-context), regenerated firewall docs, `check-invariants`
  green. **Next: P5** close-out. → PR (agent does not merge its own).
- 2026-08-20 — **Phase 5 DONE — SKY-003 complete.** PRs #77/#78/#79/#80/#81 merged. The apps front
  door is live: T2 apps Caddy (`compose/caddy-apps/`, Cloudflare DNS-01 certs), own-auth services
  (karakeep, aiostreams, aiometadata, marinara, obsidian) and forward-auth (calibre) via the scoped
  `svc-skynet` Authentik token (per-app providers; CRUD apps/providers, 403 on flows/users/keys). The
  publish-service runbook covers all three paths (A own-auth, B forward-auth, C public via the
  Cloudflare Tunnel). calibre is live **internally and publicly** (`calibre.aliammar.net`, behind
  Authentik passkey login; `auth.aliammar.net` published with its admin UI locked to the LAN). P4
  firewall least-privilege pass + `vm-docker-dmz` sshd hardening applied. Directive archived. → PR.
