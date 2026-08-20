---
id: SKY-015
title: Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory
status: draft
horizon: long
created: 2026-08-20
updated: 2026-08-20
phases: 3
current_phase: 0
tier_touched: [T1]     # all read + render. No new access, no blast-radius move → no system-design PR.
related:
  - scripts/render-docs.sh
  - docs/generated/30-services/README.md
  - docs/generated/10-vlans.md
  - "[[SKY-005-progress]]"
  - "[[lab-addressing-static-first]]"
  - "[[SKY-015-progress]]"
---

# SKY-015 · Inventory renderer overhaul: proxy-aware service annotation, canonical host map, reverse-proxy route inventory

> Make `docs/generated/` tell the truth about the **proxy layer**, so no reader — agent or human —
> ever mistakes a reverse-proxy front-door record for a host's real address.

> **Status: idea.** Sketched, not scheduled. Promote with `bin/plan start SKY-015` when it's picked up.

## 1. Problem / motivation

The generated inventory has a blind spot that already caused a wrong IP to ship:

- **`30-services/README.md` renders DNS A/CNAME records flat**, with no signal that a target IP is a
  *shared reverse-proxy front door*. A whole swath of admin vanity names — `arcane`, `opnsense`,
  `pbs`, `proxmox-core`, `proxmox-network`, `technitium-core`, `technitium-network` — all A-record to
  **`10.10.60.35` = `HOST_PROXY_ADMIN`** (Management Caddy). Grep a service name, take its A record,
  and you've got the *proxy* IP, not the host.
- This is not hypothetical: SKY-005 P2 shipped a DNS-diagnosis runbook telling the reader to
  `dig @10.10.60.35` (Management Caddy, T3) — the actual resolver is **`tdns-core` `10.10.70.51`**,
  which lives under `ROLE_DNS_RESOLVERS` in `20-firewall.md`, a different file. Two rows, two meanings,
  no signal telling them apart.
- **The renderer already knows** which IPs are shared proxy targets — the host-map logic in
  `render-docs.sh` deliberately *drops* them ("a shared target = a reverse-proxy vhost → one IP") so
  `10-vlans.md` stays clean. That knowledge simply isn't surfaced in the services view.
- **No single canonical "where does host X live" view.** Truth is scattered — `10-vlans` (IP→alias),
  `20-firewall` (roles), `30-services` (DNS), `40-hosts` (guests) — and you must *know* that `10-vlans`
  is authoritative for a host's IP while `30-services` is a front-door map, not a host map.
- **The reverse-proxy route layer isn't in inventory at all.** hostname → which Caddy → real backend
  `host:port` lives only in the Caddyfiles under `compose/`, so the docs can never resolve a vanity
  name all the way to its real backend.

## 2. Approach

Reuse what the renderer already computes (shared-target detection); collect exactly **one** new
dataset (the Caddy route table) rather than duplicating source-of-truth. Phase it cheapest-first: the
annotation that kills the specific trap lands in Phase 1; the new dataset that enables full
backend-resolution comes last. The raw collectors (OPNsense / Technitium / Proxmox) stay the
authoritative sources — this overhaul is about **rendering the truth legibly**, not re-collecting it.

## 3. The plan

- **Scope:** proxy-aware annotation + a legend in the service/IP views; a canonical host map; a
  reverse-proxy route inventory (collect + render); split-horizon (internal/public) DNS labeling.
- **Non-goals:** changing the raw collectors' source-of-truth; any new T2+/T3 access; touching the
  live proxies. Read-only over data already in git (`inventory/`, `compose/` Caddyfiles).
- **Hosts & tiers touched:** T1 render only. No blast-radius move → **no `docs/system-design.md` PR**.
- **Rollback posture:** every artifact is generated/doc — `git revert`; `docs/generated/` is
  machine-owned and re-rendered idempotently.
- **Grants / human actions:** none (pure T1 rendering).

### Phase 1 — proxy-aware services + legend  (~1–2h)   `[ ]` not started
Steps:
1. In `render-docs.sh`, when a DNS record's target IP is a known shared proxy alias
   (`HOST_PROXY_ADMIN`, `HOST_PROXY_APPS`, …), annotate the `30-services` row — e.g.
   `⚠ front door (HOST_PROXY_ADMIN) — not the host`. Reuse the shared-target set the host-map logic
   already builds.
2. Add a one-line legend to `30-services` and `10-vlans`: *vanity admin names A-record to the
   reverse proxies; the name is a front door, for a host's own IP use the canonical host map.*

Exit criteria: no flat DNS record can be read as a host address; the `technitium-core` row explicitly
says it's the Management-Caddy front door, not the DNS server.

### Phase 2 — canonical host map  (~1–2h)   `[ ]` not started
Steps:
1. New generated view (e.g. `docs/generated/45-host-map.md`): **one row per real host** — name,
   management IP, VLAN, role, tier, and *fronted-by* (the vanity names that proxy to it).
2. Join data that already exists: Proxmox guests (`40-hosts`) + firewall host aliases + unique-target
   DNS. Link it from the `docs/generated/README.md` index as the authoritative "where does X live."

Exit criteria: "where does host X actually live, and what fronts it" is answered in **one** table.

### Phase 3 — reverse-proxy route inventory + split-horizon  (~1–2h)   `[ ]` not started
Steps:
1. Collect the Caddy route table (admin + apps Caddyfiles under `compose/`) into `inventory/` —
   hostname → proxy → backend `host:port`.
2. Render it, and wire it into Phase 1's annotations so a vanity name resolves all the way
   (`technitium-core → Mgmt Caddy → tdns-core 10.10.70.51:<port>`).
3. Label DNS records **internal (Technitium)** vs **public (Cloudflare)** so the two-door model is
   visible in the data.

Exit criteria: a vanity hostname in the docs resolves to its real backend + horizon in one hop.

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive (after `bin/plan start SKY-015`). Swap `<N>`.
```
Read planning/projects/SKY-015-inventory-renderer-overhaul-proxy-aware-service-annotation-canonical-host-map-reverse-proxy-route-inventory.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-015-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-015-inventory-renderer-overhaul-proxy-aware-service-annotation-canonical-host-map-reverse-proxy-route-inventory.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-015-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-20 — created (idea) out of the SKY-005 P2 DNS-IP incident: a runbook shipped Management
  Caddy's `10.10.60.35` as the resolver because `30-services` presents a proxy front-door A record
  indistinguishably from a host address. Scoped a renderer overhaul to make the proxy layer legible.
  Left as an idea for later pickup.
