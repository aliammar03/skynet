---
id: SKY-014
title: Adopt cloudflared as a Skynet-managed tunnel (public path via apps-Caddy)
status: in-progress
horizon: short
created: 2026-08-19
updated: 2026-08-19
phases: 2
current_phase: 1
tier_touched: [T2, T3]
related:
  - compose/cloudflared/
  - compose/caddy-apps/Caddyfile
  - docs/system-design.md
  - docs/design/identity-and-proxy.md
  - docs/design/network.md
  - runbooks/deploy-service.md
  - "[[SKY-013-progress]]"
  - "[[SKY-014-progress]]"
---

# SKY-014 · Adopt cloudflared as a Skynet-managed tunnel (public path via apps-Caddy)

> Bring the Cloudflare Tunnel under Skynet's management — a GitOps `cloudflared` service that
> replaces the hand-run `lxc-cloudflared` (CT 1033) — and use it to open Skynet's **first
> deliberate public path**: the tunnel points at the apps-Caddy as its single origin, so
> publishing any app to the internet becomes one reviewed ingress line, not a new moving part.

## 1. Problem / motivation

Two gaps, one directive:

1. **The tunnel is off the rails.** A Cloudflare Tunnel connector already runs as
   `lxc-cloudflared` (CT 1033, `10.10.100.33`, mid-migration off VLAN 40), but it's a **hand-managed
   Proxmox LXC** — Skynet sees it (T1) and can't touch it. Its config (which hostname routes where)
   lives in the Cloudflare dashboard / on the box, not in reviewed git. It's exactly the kind of
   snowflake the GitOps loop exists to erase.
2. **There is no sanctioned public path.** Everything Skynet publishes is **internal-ingress only**
   (`identity-and-proxy` spoke: *"Nothing is published to the public internet by this design …
   Cloudflared is a separate path."*). Ali wants real off-network access — sync Obsidian from a phone
   on cellular, no VPN — which today means either poking OPNsense (a boundary we deliberately don't
   move) or leaning on that unmanaged LXC.

The fix is to **adopt** cloudflared the skynet way and, in the same move, **define** the public path
as a first-class, PR-gated boundary: a tunnel that fronts the apps-Caddy, exposing one hostname at a
time, each an explicit git change.

## 2. Decisions (settled)

*(What we're building — the calls already made. Not a debate; just the record so nobody reopens them.)*

- **Replace, don't wrap.** cloudflared becomes a **Skynet-managed GitOps docker service**
  (`compose/cloudflared/` on `vm-docker-dmz`), and CT 1033 is **retired** once the new connector
  proves out. Config as reviewed git, same loop as every other service. **(CHOSEN)**
- **Origin = the apps-Caddy, not per-service.** The tunnel's single origin is
  `https://10.10.100.35` (apps-Caddy), forwarding by SNI. Caddy already terminates the real
  Let's Encrypt cert and routes to the backend, so TLS stays end-to-end (edge → cloudflared → Caddy →
  service) and **publishing a new app publicly = add one `ingress` line + one public DNS record**,
  reusing the internal Caddy route verbatim. **(CHOSEN)**
- **The connector reuses CT 1033's IP, `10.10.100.33`.** The docker service takes the DMZ static IP
  the LXC holds today. Two payoffs: it **inherits the existing `HOST_CLOUDFLARED` egress** (firewall
  rule 800 already permits `.33 → 443, 7844`), so **no OPNsense change is needed**; and it makes the
  cutover clean. The catch — one IP can't be in two places — sets the sequencing: the container can
  only bind `.33` **after** CT 1033 is stopped, so **bring-up *is* the cutover** (no parallel run). We
  trade the parallel-fallback for a symmetric, seconds-fast rollback: CT 1033 is **stopped, not
  destroyed**, during a soak, so backing out is `docker compose down` + `pct start 1033`. **(CHOSEN)**
- **Pilot = one app, own-auth.** First public hostname is **`obsidian.aliammar.net`** (SKY-013):
  it self-gates (CouchDB → `401` without creds), its contents are **E2E-encrypted** on the client, and
  remote sync is the motivating use case. Edge guard = **the service's own login** (no Cloudflare
  Access / Authentik in front for the pilot). Blast radius stays one hostname; more apps are added
  later, per-PR. **(CHOSEN)**
- **Ingress config lives in git.** Locally-managed `config.yml` (the `ingress:` rules) is
  repo-tracked and mounted `:ro`, mirroring SKY-013's `local.ini`. The tunnel **credential** is a
  secret (sops). *One implementation detail to confirm in Phase 1, don't assume:* whether we deliver
  the credential as `TUNNEL_TOKEN` in `.env.sops` (simplest) or a sops-encrypted `credentials.json`
  file — and whether a token-run tunnel still honors a local `config.yml` ingress, or forces
  dashboard-managed config. Pick the one that keeps **ingress rules in git**; fall back to
  dashboard-managed only if the file path proves brittle. (Same "confirm the mechanism, then run"
  discipline as SKY-013's healthcheck-tool check.)

## 3. The plan

- **Scope / non-goals:**
  - **In:** a Skynet-managed `cloudflared` connector; a git-tracked tunnel `ingress` fronting the
    apps-Caddy; the pilot hostname `obsidian.aliammar.net` reachable from the **public** internet;
    retirement of CT 1033; the constitution amendment that sanctions the public path.
  - **Out (non-goals):** no Cloudflare Access / Zero-Trust policy for the pilot (own-auth only —
    revisited before any app *without* its own strong login goes public); no per-service tunnel
    origins (always via Caddy); no change to the **internal** path (Technitium keeps steering internal
    clients straight to apps-Caddy — internal traffic never transits Cloudflare); no exposure of any
    hostname beyond the pilot in this directive; no OPNsense inbound rules (the tunnel is
    **outbound-only** by design — that's the whole point).
- **Hosts & tiers touched:**
  - **T2** — `vm-docker-dmz` (the cloudflared compose service, via Arcane GitOps + `svc-ops`);
    `compose/caddy-apps` unchanged but is the origin.
  - **T3 / human** — **Cloudflare account** (create/attach the tunnel, mint its token, add the public
    DNS record); **Proxmox** (stop, then later destroy, CT 1033). Each is a **⚠ checkpoint** — Ali
    acts. **No OPNsense change** — reusing `.33` keeps the connector inside the existing rule-800
    egress (confirm `7844` is in that alias before cutover; cloudflared falls back to `443` if not).
  - **Blast-radius boundary moves** (internal-only → a sanctioned public path) ⇒ **this plan PRs
    `docs/system-design.md`** + the `identity-and-proxy` spoke. Done in Phase 1.
- **Rollback posture:** because the container and CT 1033 **share `.33`**, the two never run at once —
  so the break-glass path is the LXC, kept **stopped-not-destroyed** through a soak: `docker compose
  down` the connector + `pct start 1033` restores the old tunnel in seconds. `git revert` the
  compose / `config.yml` PR reconciles the connector away; pulling the public DNS record stops the
  hostname resolving to the tunnel immediately. CT 1033 is destroyed only **after** the soak proves
  the new path.
- **Grants / human actions:** no standing-tier expansion. The T3 touches are all **Ali-applied,
  one-shot** (Cloudflare dashboard, one OPNsense rule, one `pct stop`), not new standing routes.

### Phase 1 — Sanction the path + build the connector (validated, not yet deployed)  (~1–2h)   `[~]` agent-work done; awaiting Ali (CF checkpoint + merge)

*(No deploy here: `.33` is still CT 1033's, so standing the container up = the cutover, which is
Phase 2. Phase 1 lands everything that can land without touching the live tunnel.)*

Steps:
1. **Amend the constitution (PR).** `docs/system-design.md` + `docs/design/identity-and-proxy.md`:
   define **the public path** — cloudflared is now a **T2 Skynet-managed** service; its origin is the
   apps-Caddy; **only hostnames with an explicit `ingress` entry are public**, each added by PR;
   own-auth (or stronger) is required at the edge; the tunnel credential is sops. State the invariant:
   *the internal path is unchanged and never transits Cloudflare.* Note that `HOST_CLOUDFLARED` /
   `.33` is **retained** — its runtime moves from the LXC to the docker-dmz service, so rule 800
   carries over unchanged.
2. **Cloudflare side (⚠ checkpoint — Ali).** Create/attach the tunnel, mint its **token/credential**,
   hand it to Skynet to store in `.env.sops` (never in a commit/transcript). Confirm the
   credential-delivery mechanism per §2's open detail. Confirm `7844` is inside the rule-800 alias
   (else the connector will fall back to `443`, which is fine).
3. **Build `compose/cloudflared/` the skynet way:** `cloudflare/cloudflared` **digest-pinned**,
   `restart: unless-stopped`, `env_file: [.env]`, `x-arcane` tag (reuse a fitting role or add one),
   on the `dmz` network at the **static IP `10.10.100.33`** (inherits rule-800 egress). Command runs
   the tunnel against a **git-tracked `config.yml`** whose single `ingress` origin is
   `https://10.10.100.35` with `originServerName` set so Caddy's cert verifies — plus the mandatory
   catch-all `http_status:404`. **No public hostname yet.** Stateless service → **no named volume**.
   **Healthcheck** against cloudflared's `/ready` metrics endpoint (expose `--metrics 0.0.0.0:<port>`;
   confirm the in-container probe tool — the image is distroless-ish, so a bash `/dev/tcp` open on the
   metrics port may be the move, don't assume curl exists).
4. **Validate + PR** (teaching description: what a tunnel is, outbound-only, why origin=Caddy, why the
   public path is now a reviewed boundary). Validation is offline (`docker compose config -q`) — the
   service is **not deployed** while CT 1033 still holds `.33`. **⚠ Ali merges.**

Exit criteria: `docs/system-design.md` + spoke sanction the public path (merged); `compose/cloudflared/`
is built, validated, and merged, pinned to `.33` with a git-tracked ingress that routes nothing public
yet; the Cloudflare tunnel + token exist (token in `.env.sops`). CT 1033 still serving untouched —
nothing has cut over.
Grants / human actions: **⚠ Ali creates the CF tunnel + supplies the token** (credential handling);
**⚠ Ali merges the PRs**. No OPNsense, no Proxmox action yet.

### Phase 2 — Cut over to `.33`, publish the pilot, verify from outside, retire CT 1033  (~1–2h)   `[ ]` not started

Steps:
1. **Free the IP (⚠ checkpoint — Ali).** `pct stop 1033` — releases `10.10.100.33`. CT 1033 is
   **stopped, not destroyed**: it's the rollback.
2. **Cut over.** `scripts/gitops-deploy.sh cloudflared` → the container binds `.33` and **registers
   with Cloudflare** (4 edge connections / `Registered tunnel connection` in logs; `/ready` healthy).
   Still nothing public — this just proves the managed connector runs on the inherited IP + egress.
   *Rollback if it doesn't: `docker compose down` + `pct start 1033`.*
3. **Route the pilot (PR).** Add `obsidian.aliammar.net` to `config.yml`'s `ingress` (→ the Caddy
   origin). **⚠ Ali adds the public DNS record** on Cloudflare (`obsidian.aliammar.net` CNAME →
   `<tunnel-id>.cfargotunnel.com`, proxied) — a specific record that overrides the public wildcard for
   this host only. **⚠ Ali merges**, then `gitops-deploy.sh cloudflared`.
4. **Verify from the public internet** (not just a DMZ peer — the whole point is off-network):
   from a device **off** the LAN (Ali's phone on cellular, or an external checker),
   `https://obsidian.aliammar.net/_up` → `200` with a valid cert, and root without creds → `401`.
   Confirm the **internal** path is unchanged (internal client still resolves via Technitium straight
   to apps-Caddy, not through Cloudflare).
5. **Prove the use case:** LiveSync round-trips from the off-network device through the tunnel
   (an edit made on cellular lands on a LAN device and back).
6. **Soak, then retire (⚠ checkpoint — Ali).** After the new path soaks, **Ali destroys CT 1033**.
   Skynet updates `inventory/` + the firewall docs to record that `HOST_CLOUDFLARED` / `.33` now =
   the docker-dmz service (rule 800 unchanged, the LXC row retired).

Exit criteria: `obsidian.aliammar.net` is reachable and syncing **from the public internet** through
the Skynet-managed tunnel on `.33`; own-auth gates it (`401` without creds); the internal path is
unchanged; CT 1033 is stopped (destroyed after soak) and inventory + firewall docs reflect the new
runtime behind `.33`. Adding the *next* public app is now a one-line `ingress` + one DNS-record PR.
Grants / human actions: **⚠ Ali `pct stop 1033`** (frees the IP; the rollback); **⚠ Ali adds the
public DNS record**; **⚠ Ali merges the PR**; **⚠ Ali destroys CT 1033** after the soak. No standing
grant, no OPNsense change.

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-014-adopt-cloudflared-as-a-skynet-managed-tunnel-public-path-via-apps-caddy.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-014-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-014-adopt-cloudflared-as-a-skynet-managed-tunnel-public-path-via-apps-caddy.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-014-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
*(One dated line per milestone — cite PR numbers; convert relative dates to absolute. Newest last.)*
- 2026-08-19 — created; promoted straight to projects/. Decisions settled with Ali: replace CT 1033
  with a Skynet-managed cloudflared; tunnel origin = apps-Caddy (SNI forward, TLS end-to-end); pilot =
  `obsidian.aliammar.net` own-auth; ingress config in git. Moves the internal-only→public boundary, so
  Phase 1 PRs `docs/system-design.md` + the identity-and-proxy spoke.
- 2026-08-19 — revised: the container **reuses CT 1033's IP `10.10.100.33`** (inherits rule-800 egress
  → no OPNsense change). Shared IP ⇒ bring-up IS the cutover: Phase 1 now builds+validates only (no
  deploy), Phase 2 does `pct stop 1033` → deploy on `.33` → publish → verify → destroy after soak.
  Rollback = `compose down` + `pct start 1033` (LXC kept stopped-not-destroyed through the soak).
- 2026-08-19 — **Phase 1 agent-work done → PR #67** (branch `phase/sky-014-p1`). Constitution +
  `identity-and-proxy` spoke sanction the public path; `compose/cloudflared/` built + validated offline
  (`docker compose config -q` ✓), pinned to `.33`, ingress routes nothing public (404 catch-all only).
  The §2 open detail is **resolved**: ingress-in-git forces a **locally-managed** tunnel — a `--token`
  run is remotely-managed and ignores local `config.yml` (cloudflared #1029) — so the credential is a
  **sops `credentials.json` file**, not `TUNNEL_TOKEN`. Healthcheck = distroless-safe
  `cloudflared tunnel ready`. Rule 800 already carries 443+7844 (no OPNsense change). **Not fully
  closed:** awaiting **⚠ Ali** to create the CF tunnel + supply the credential (→ `credentials.json.sops`
  + fill `config.yml` id) and to **merge PR #67**.
