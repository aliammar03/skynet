---
title: Context Map
author: skynet-ops (render-context-map.sh)
tags: [skynet, generated, agent, context-map]
---

# Skynet — Context Map

**Always-loaded baseline:** `AGENTS.md` + `CLAUDE.md` ≈ **3781** tok — the contract; never in this list.
**Cold-boot read:** `docs/generated/06-agent-digest.md` ≈ 1554 tok.

Everything below is **on-demand**: nothing enters context until a trigger fires. Open a *file*, not a section.

## Procedures — `runbooks/` (trigger-driven)

| Path | Tier | Trigger | ~tok | Summary |
|---|---|---|--:|---|
| `runbooks/backup.md` | T2+ (host-level restic/PBS work needs a root grant) | How do backups work / run a backup | 1183 | How restic + PBS backups run, and how to trigger one on demand. |
| `runbooks/construction-delegation.md` | **T1, build-time only | Do a substantial construction task / build X / implement or change X | 1635 | Run substantial construction as a lead — proactively find BIV chunks, route bounded helpers, verify, integrate, and PR — without gaining any production authority. |
| `runbooks/deploy-service.md` | T2 (PR-gated) | Deploy or update a service | 933 | Deploy or update a service through the Arcane GitOps loop: edit compose then PR then Arcane reconciles. |
| `runbooks/dr/DR-core-node.md` |  | Core node is dead | 689 | Recover when server-proxmox-core (with PBS aboard) is dead. |
| `runbooks/dr/DR-network-node.md` |  | Network node or OPNsense is dead | 350 | Recover when server-proxmox-network is dead — OPNsense and routing gone. |
| `runbooks/dr/pci-passthrough.md` |  | NIC passthrough for OPNsense | 626 | Re-establish NIC passthrough for VM 5001 (OPNsense) after a rebuild. |
| `runbooks/dr/survival-kit.md` |  |  | 337 | What lives on paper and in the password manager, outside Skynet, to bootstrap recovery. |
| `runbooks/nightly.md` | T1 read + PR | Run the nightly / nightly timer | 1133 | The report-only nightly maintenance run on both engine paths, and what it refreshes. |
| `runbooks/provision-lxc.md` | T2 (reviewed saved-plan apply via the operator token, API-only — no node SSH; deploy-rs over SSH) | Set up / deploy a new LXC for X | 1257 | Provision a NixOS core-managed LXC from merged source and an explicitly approved saved plan; creates are supervised T2 without automatic rollback. |
| `runbooks/provision-vm.md` | T2 saved-plan clone/apply + T2+ root grant for hardening | Set up a VM for X, hardened, with restic | 1129 | Provision a VM from merged source and an explicitly approved saved plan; creates are supervised T2 without automatic rollback. |
| `runbooks/publish-service.md` | T2 (PR-gated) | Publish or expose a service | 4910 | Publish a service through the apps Caddy front door: edit the Caddyfile then PR then deploy — own-auth (plain reverse_proxy) or forward-auth via Authentik (scoped-token provider+application); optionally also expose it to the internet via the Cloudflare Tunnel (Path C). |
| `runbooks/recon.md` | **T1 read-only | Figure out why X is broken / what's going on with <host> | 970 | Start-here triage: take one T1 read-only host snapshot with scripts/recon.sh, reason over it, then branch to a diagnosis runbook. |
| `runbooks/restore-service.md` | T2 + (if VM restore) T2 PBS token | Restore a service / recover from backup | 1116 | Restore a service or VM from restic/PBS — conversational and deterministic, executable verbatim. |
| `runbooks/update-guests.md` | T2 snapshot + T2+ fleet root grant | Update all guests | 231 | Snapshot then update every guest under a fleet root grant. |

## Design spokes — `docs/design/`

| Path | ~tok | Summary |
|---|--:|---|
| `docs/design/access-and-trust.md` | 4738 | The trust tiers in full — every token, ACL, principal, and the auto-expiring SSH root grant Skynet can request but never mint. |
| `docs/design/actuators.md` | 2078 | The L7 actuators and their rollback executors: what each write can undo, by whom, and how the rollback is decided deterministically. |
| `docs/design/disaster-recovery.md` | 926 | The survival kit and how each node-loss scenario is recovered; the step-by-step procedures live in runbooks/dr/. |
| `docs/design/gitops-loop.md` | 1034 | How a service change becomes a running container via Arcane, with git-revert rollback and image pinning + Renovate. |
| `docs/design/identity-and-proxy.md` | 3437 | The two front doors, split-horizon DNS, the forward_auth boundary that publishes apps without holding auth's keys (SKY-003), and the sanctioned public path via a Skynet-managed Cloudflare Tunnel (SKY-014). |
| `docs/design/memory.md` | 2933 | How a stateless agent remembers: the four memory kinds, the episodic journal→digest, and the default-lean working-memory discipline. |
| `docs/design/network.md` | 1713 | Where Skynet sits, how it's addressed on VLAN 90, and the firewall rules bounding its reach to exactly what it needs. |
| `docs/design/observability.md` | 985 | How machine state becomes human-readable docs, and how the nightly run keeps the picture current. |
| `docs/design/secrets.md` | 1109 | How Skynet holds secrets with sops+age and materializes GitOps service env from .env.git plus .env.sops. |

## Conventions — `docs/conventions/`

| Path | ~tok | Summary |
|---|--:|---|
| `docs/conventions/compose.md` | 1085 | The single 'skynet way' every service's compose conforms to, so the fleet is uniform and Arcane's GitOps loop can own it. |
| `docs/conventions/construction.md` | 3308 | The construction delegation contract: one accountable lead hands bounded, independent, verifiable work to at most two helpers, one level deep, native tooling first — and no helper ever gains production authority. |
| `docs/conventions/docs.md` | 1499 | How Skynet's prose is structured: hub-and-spoke, ADRs, runbooks, README-as-catalog, and loadable summary/trigger frontmatter. |
| `docs/conventions/git.md` | 591 | How change enters the repo: one branch per unit of work, one PR per phase, and the agent never merging its own PRs. |
| `docs/conventions/layout.md` | 1462 | Where each kind of artifact lives, and the minimum files each must have to be well-formed. |
| `docs/conventions/metadata.md` | 641 | The structured fields machines read: directive frontmatter, service-catalog entries, and the compose label/tag namespaces. |
| `docs/conventions/naming.md` | 1936 | The one naming grammar — VMIDs, IPs, hostnames, slugs, branches — so a name is predictable and machine-validatable. |
| `docs/conventions/scripts.md` | 663 | The house style for every executable in scripts/ and bin/: same shape, fails safe, and declares the tier it runs at. |

## Catalogs & templates

| Path | ~tok | Summary |
|---|--:|---|
| `compose/README.md` | 1519 | The compose/ service catalog and the Arcane GitOps deployment loop every project follows. |
| `journal/README.md` | 1029 | The episodic journal format — session/incident/decision records, the Graveyard, and the write-raw/read-summarize rule. |
| `planning/README.md` | 1588 | Where future work lives as SKY-### directives: the scratchpad→ideas→backlog→projects→archive lifecycle, bin/plan, and the roadmap. |
| `runbooks/README.md` | 1601 | Catalog of engine-neutral procedures any agent can execute, each tagged by tier and trigger — the routing menu. |
| `templates/README.md` | 395 | The golden templates (compose, script, runbook, ADR, journal) that bin/new stamps so new artifacts inherit the house style. |

## Generated views — `docs/generated/` (machine-owned; edit the renderer, not these)

| Path | ~tok | Summary |
|---|--:|---|
| `docs/generated/00-network-map.md` | 449 | Network map |
| `docs/generated/05-state-of-the-lab.md` | 1581 | State of the Lab |
| `docs/generated/06-agent-digest.md` | 1554 | Agent Digest |
| `docs/generated/10-vlans.md` | 794 | VLANs |
| `docs/generated/20-firewall.md` | 2206 | Firewall |
| `docs/generated/50-network-gear.md` | 507 | Network gear (Omada estate) |
| `docs/generated/90-backup-status.md` | 533 | Backup & grant status |
| `docs/generated/README.md` | 227 | Skynet — generated docs |

## Episodic memory — retrieve by topic, don't browse

- `journal/` — 58 raw episodes, ≈ 70420 tok total. Retrieve by topic: `bin/recall <topic>` (SKY-010 P4) or `grep -ri "<topic>" journal/`; recent episodes are already in `06-agent-digest.md`. **Do not load the whole store.**

---
**On-demand corpus:** ≈ **60620** tok across 44 files — but you load a *row* (≈ tens of tok) to choose, then one file.
_A cache — regenerable from git via `render-context-map.sh`; never a source of truth._

> [!note] Generated by `scripts/render-context-map.sh` from each loadable's frontmatter.
> Do not hand-edit. Content-stable (diffs only on real change). The **map of what you can
> load and what it costs** — read a ROW, then open only the one file you need. Baseline +
> this on-demand index = the default-lean discipline ([[memory]]).
