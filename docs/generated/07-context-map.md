---
title: Context Map
author: skynet-ops (render-context-map.sh)
tags: [skynet, generated, agent, context-map]
---

# Skynet — Context Map

**Always-loaded baseline:** `AGENTS.md` + `CLAUDE.md` ≈ **3090** tok — the contract; never in this list.
**Cold-boot read:** `docs/generated/06-agent-digest.md` ≈ 1471 tok.

Everything below is **on-demand**: nothing enters context until a trigger fires. Open a *file*, not a section.

## Procedures — `runbooks/` (trigger-driven)

| Path | Tier | Trigger | ~tok | Summary |
|---|---|---|--:|---|
| `runbooks/backup.md` | T2+ (host-level restic/PBS work needs a root grant) | How do backups work / run a backup | 1183 | How restic + PBS backups run, and how to trigger one on demand. |
| `runbooks/deploy-service.md` | T2 (PR-gated) | Deploy or update a service | 926 | Deploy or update a service through the Arcane GitOps loop: edit compose then PR then Arcane reconciles. |
| `runbooks/dr/DR-core-node.md` |  | Core node is dead | 642 | Recover when server-proxmox-core (with PBS aboard) is dead. |
| `runbooks/dr/DR-network-node.md` |  | Network node or OPNsense is dead | 350 | Recover when server-proxmox-network is dead — OPNsense and routing gone. |
| `runbooks/dr/pci-passthrough.md` |  | NIC passthrough for OPNsense | 626 | Re-establish NIC passthrough for VM 5001 (OPNsense) after a rebuild. |
| `runbooks/dr/survival-kit.md` |  |  | 337 | What lives on paper and in the password manager, outside Skynet, to bootstrap recovery. |
| `runbooks/nightly.md` | T1 read + PR | Run the nightly / nightly timer | 1107 | The report-only nightly maintenance run on both engine paths, and what it refreshes. |
| `runbooks/provision-vm.md` | T2 clone + T2+ root grant for hardening | Set up a VM for X, hardened, with restic | 525 | Clone the golden template into a hardened VM with restic, under a scoped auto-expiring root grant. |
| `runbooks/publish-service.md` | T2 (PR-gated) | Publish or expose a service | 4349 | Publish a service through the apps Caddy front door: edit the Caddyfile then PR then deploy — own-auth (plain reverse_proxy) or forward-auth via Authentik (scoped-token provider+application); optionally also expose it to the internet via the Cloudflare Tunnel (Path C). |
| `runbooks/recon.md` | **T1 read-only | Figure out why X is broken / what's going on with <host> | 970 | Start-here triage: take one T1 read-only host snapshot with scripts/recon.sh, reason over it, then branch to a diagnosis runbook. |
| `runbooks/restore-service.md` | T2 + (if VM restore) T2 PBS token | Restore a service / recover from backup | 1105 | Restore a service or VM from restic/PBS — conversational and deterministic, executable verbatim. |
| `runbooks/update-guests.md` | T2 snapshot + T2+ fleet root grant | Update all guests | 228 | Snapshot then update every guest under a fleet root grant. |

## Design spokes — `docs/design/`

| Path | ~tok | Summary |
|---|--:|---|
| `docs/design/access-and-trust.md` | 2881 | The trust tiers in full — every token, ACL, principal, and the auto-expiring SSH root grant Skynet can request but never mint. |
| `docs/design/disaster-recovery.md` | 926 | The survival kit and how each node-loss scenario is recovered; the step-by-step procedures live in runbooks/dr/. |
| `docs/design/gitops-loop.md` | 935 | How a service change becomes a running container via Arcane, with git-revert rollback and image pinning + Renovate. |
| `docs/design/identity-and-proxy.md` | 3229 | The two front doors, split-horizon DNS, the forward_auth boundary that publishes apps without holding auth's keys (SKY-003), and the sanctioned public path via a Skynet-managed Cloudflare Tunnel (SKY-014). |
| `docs/design/memory.md` | 2933 | How a stateless agent remembers: the four memory kinds, the episodic journal→digest, and the default-lean working-memory discipline. |
| `docs/design/network.md` | 1625 | Where Skynet sits, how it's addressed on VLAN 90, and the firewall rules bounding its reach to exactly what it needs. |
| `docs/design/observability.md` | 972 | How machine state becomes human-readable docs, and how the nightly run keeps the picture current. |
| `docs/design/secrets.md` | 778 | How Skynet holds secrets with sops+age so plaintext never leaves the repo, plus the .env.git/project.env layering. |

## Conventions — `docs/conventions/`

| Path | ~tok | Summary |
|---|--:|---|
| `docs/conventions/compose.md` | 1085 | The single 'skynet way' every service's compose conforms to, so the fleet is uniform and Arcane's GitOps loop can own it. |
| `docs/conventions/docs.md` | 1603 | How Skynet's prose is structured: hub-and-spoke, ADRs, runbooks, README-as-catalog, and loadable summary/trigger/tokens frontmatter. |
| `docs/conventions/git.md` | 591 | How change enters the repo: one branch per unit of work, one PR per phase, and the agent never merging its own PRs. |
| `docs/conventions/layout.md` | 1422 | Where each kind of artifact lives, and the minimum files each must have to be well-formed. |
| `docs/conventions/metadata.md` | 641 | The structured fields machines read: directive frontmatter, service-catalog entries, and the compose label/tag namespaces. |
| `docs/conventions/naming.md` | 1760 | The one naming grammar — VMIDs, IPs, hostnames, slugs, branches — so a name is predictable and machine-validatable. |
| `docs/conventions/scripts.md` | 663 | The house style for every executable in scripts/ and bin/: same shape, fails safe, and declares the tier it runs at. |

## Catalogs & templates

| Path | ~tok | Summary |
|---|--:|---|
| `compose/README.md` | 1508 | The compose/ service catalog and the Arcane GitOps deployment loop every project follows. |
| `journal/README.md` | 1029 | The episodic journal format — session/incident/decision records, the Graveyard, and the write-raw/read-summarize rule. |
| `planning/README.md` | 1398 | Where future work lives as SKY-### directives: the scratchpad→ideas→backlog→projects→archive lifecycle, bin/plan, and the roadmap. |
| `runbooks/README.md` | 1461 | Catalog of engine-neutral procedures any agent can execute, each tagged by tier and trigger — the routing menu. |
| `templates/README.md` | 395 | The golden templates (compose, script, runbook, ADR, journal) that bin/new stamps so new artifacts inherit the house style. |

## Generated views — `docs/generated/` (machine-owned; edit the renderer, not these)

| Path | ~tok | Summary |
|---|--:|---|
| `docs/generated/00-network-map.md` | 524 | Network map |
| `docs/generated/05-state-of-the-lab.md` | 1213 | State of the Lab |
| `docs/generated/06-agent-digest.md` | 1471 | Agent Digest |
| `docs/generated/10-vlans.md` | 1139 | VLANs |
| `docs/generated/20-firewall.md` | 2269 | Firewall |
| `docs/generated/90-backup-status.md` | 213 | Backup & grant status |
| `docs/generated/README.md` | 213 | Skynet — generated docs |

## Episodic memory — retrieve by topic, don't browse

- `journal/` — 28 raw episodes, ≈ 34062 tok total. Retrieve by topic: `bin/recall <topic>` (SKY-010 P4) or `grep -ri "<topic>" journal/`; recent episodes are already in `06-agent-digest.md`. **Do not load the whole store.**

---
**On-demand corpus:** ≈ **47225** tok across 39 files — but you load a *row* (≈ tens of tok) to choose, then one file.
_A cache — regenerable from git via `render-context-map.sh`; never a source of truth._

> [!note] Generated by `scripts/render-context-map.sh` from each loadable's frontmatter.
> Do not hand-edit. Content-stable (diffs only on real change). The **map of what you can
> load and what it costs** — read a ROW, then open only the one file you need. Baseline +
> this on-demand index = the default-lean discipline ([[memory]]).
