---
title: Context Map
author: skynet-ops (render-context-map.sh)
tags: [skynet, generated, agent, context-map]
---

# Skynet — Context Map

**Always-loaded baseline:** `AGENTS.md` + `CLAUDE.md` ≈ **3839** tok — the contract; never in this list.
**Cold-boot read:** `docs/generated/06-agent-digest.md` ≈ 1496 tok.

Everything below is **on-demand**: nothing enters context until a trigger fires. Open a *file*, not a section.

## Procedures — `runbooks/` (trigger-driven)

| Path | Tier | Trigger | ~tok | Summary |
|---|---|---|--:|---|
| `runbooks/backup.md` | T2+ root grant | How do backups work / run a backup | 1312 | How restic + PBS backups run, and how to trigger one on demand. |
| `runbooks/construction-delegation.md` | T1 build-time only | Do a substantial construction task / build X / implement or change X | 1465 | Run substantial construction as a lead — proactively find BIV chunks, route bounded helpers, verify, integrate, and PR — without gaining any production authority. |
| `runbooks/deploy-service.md` | T2 PR-gated | Deploy or update a service | 1100 | Deploy or update a service through the Arcane GitOps loop: edit compose then PR then Arcane reconciles. |
| `runbooks/diagnose/arcane-stuck.md` | T1/T2 | A merged compose PR didn't deploy / Arcane isn't reconciling / git and running have drifted | 899 | Triage a merged compose PR that didn't deploy — check the Arcane Git Sync status/error, compare git vs running, distinguish sync-fail vs apply-fail vs drift. |
| `runbooks/diagnose/backup-missed.md` | T1/T2 | An expected backup/snapshot is missing / a restic or PBS timer failed | 866 | Triage a missed backup — check the timer, the last snapshot age, and repo reachability across restic→gdrive and PBS→gdrive, fix the timer/creds/repo declaratively. |
| `runbooks/diagnose/cert-expired.md` | T1 | Cert warning / TLS handshake fails / 'certificate expired' / ACME renewal failing | 879 | Triage an expired/failing TLS cert — read the served cert's dates, find why ACME isn't renewing (HTTP-01 vs DNS-01, rate limit, clock), fix in Caddy config. |
| `runbooks/diagnose/container-crashloop.md` | T1 | A container is Restarting / unhealthy / keeps exiting | 936 | Triage a container that restarts, is unhealthy, or exits — read exit code + logs + healthcheck, branch to the cause, fix in compose/. |
| `runbooks/diagnose/disk-full.md` | T1/T2+ | Disk full / write failures / df at 100% (or inodes exhausted with space free) | 899 | Triage a full disk (or exhausted inodes) — find what ate the space, distinguish data vs logs vs docker cruft, fix the cause declaratively. |
| `runbooks/diagnose/dns-failure.md` | T1/T2 | A name won't resolve / service unreachable by hostname / ACME DNS-01 failing | 1438 | Triage DNS failures — split internal (Technitium) vs public (Cloudflare), read NXDOMAIN/SERVFAIL, fix the record through the sanctioned T2 path. |
| `runbooks/dr/DR-core-node.md` | T2+ | Core node is dead | 807 | Recover when server-proxmox-core (with PBS aboard) is dead. |
| `runbooks/dr/DR-network-node.md` | T3 | Network node or OPNsense is dead | 554 | Recover when server-proxmox-network is dead — OPNsense and routing gone. |
| `runbooks/dr/pci-passthrough.md` | T3 | NIC passthrough for OPNsense | 789 | Re-establish NIC passthrough for VM 5001 (OPNsense) after a rebuild. |
| `runbooks/dr/survival-kit.md` | T3 | Prepare or verify the off-site survival kit | 564 | What lives on paper and in the password manager, outside Skynet, to bootstrap recovery. |
| `runbooks/nightly.md` | T1 read + generated-only PR | Run the nightly / nightly timer | 1325 | The report-only nightly maintenance run on both engine paths, and what it refreshes. |
| `runbooks/provision-lxc.md` | Supervised T2 saved-plan create | Set up / deploy a new LXC for X | 1393 | Provision a NixOS core-managed LXC from merged source and an explicitly approved saved plan; creates are supervised T2 without automatic rollback. |
| `runbooks/provision-vm.md` | Supervised T2 saved-plan create + T2+ root grant | Set up a VM for X, hardened, with restic | 1340 | Provision a VM from merged source and an explicitly approved saved plan; creates are supervised T2 without automatic rollback. |
| `runbooks/publish-service.md` | T2 PR-gated | Publish or expose a service | 471 | Choose the runbook for publishing a service through apps Caddy, Authentik, or the Cloudflare Tunnel. |
| `runbooks/publish/forward-auth.md` | T2 PR-gated | Put a no-login service behind Authentik | 1502 | Publish a service with no native login behind Authentik forward-auth on apps Caddy. |
| `runbooks/publish/internal-route.md` | T2 PR-gated | Give an authenticated service an internal aliammar.net URL | 1258 | Publish an own-auth service on the internal apps Caddy front door. |
| `runbooks/publish/public-tunnel.md` | T2 PR-gated | Expose an internally published service to the public internet | 1495 | Add Cloudflare Tunnel and public DNS exposure to an already-working internal route. |
| `runbooks/recon.md` | T1 read-only | Figure out why X is broken / what's going on with <host> | 1061 | Start-here triage: take one T1 read-only host snapshot with scripts/recon.sh, reason over it, then branch to a diagnosis runbook. |
| `runbooks/restore-service.md` | T2; PBS token for VM restore | Restore a service / recover from backup | 1310 | Restore a service or VM from restic/PBS — conversational and deterministic, executable verbatim. |
| `runbooks/update-guests.md` | T2 snapshot + T2+ fleet root grant | Update all guests | 389 | Snapshot then update every guest under a fleet root grant. |

## Design spokes — `docs/design/`

| Path | ~tok | Summary |
|---|--:|---|
| `docs/design/access-and-trust.md` | 1192 | The current credential, ACL, principal, and root-grant boundaries that implement Skynet's trust tiers. |
| `docs/design/actuators.md` | 585 | The current write actuators, deterministic rollback paths, and A4 eligibility of each capability. |
| `docs/design/disaster-recovery.md` | 601 | The survival kit and how each node-loss scenario is recovered; the step-by-step procedures live in runbooks/dr/. |
| `docs/design/gitops-loop.md` | 682 | How a service change becomes a running container via Arcane, with git-revert rollback and image pinning + Renovate. |
| `docs/design/identity-and-proxy.md` | 882 | The current two-door proxy, split-DNS, Authentik boundary, and Cloudflare Tunnel public path. |
| `docs/design/memory.md` | 511 | How Skynet keeps portable semantic, procedural, episodic, and working memory without overloading a fresh agent. |
| `docs/design/network.md` | 1559 | Where Skynet sits, how it's addressed on VLAN 90, and the firewall rules bounding its reach to exactly what it needs. |
| `docs/design/observability.md` | 737 | How machine state becomes human-readable docs, and how the nightly run keeps the picture current. |
| `docs/design/secrets.md` | 964 | How Skynet holds secrets with sops+age and materializes GitOps service env from .env.git plus .env.sops. |

## Conventions — `docs/conventions/`

| Path | ~tok | Summary |
|---|--:|---|
| `docs/conventions/compose.md` | 1085 | The single 'skynet way' every service's compose conforms to, so the fleet is uniform and Arcane's GitOps loop can own it. |
| `docs/conventions/construction.md` | 3176 | The construction delegation contract: one accountable lead hands bounded, independent, verifiable work to at most two helpers, one level deep, native tooling first — and no helper ever gains production authority. |
| `docs/conventions/docs.md` | 1538 | How Skynet's prose is structured: hub-and-spoke, ADRs, runbooks, README-as-catalog, and loadable summary/trigger frontmatter. |
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
| `runbooks/README.md` | 1514 | Catalog of task-shaped, engine-neutral operational procedures. Rendered from runbook frontmatter. |
| `templates/README.md` | 395 | The golden templates (compose, script, runbook, ADR, journal) that bin/new stamps so new artifacts inherit the house style. |

## Generated views — `docs/generated/` (machine-owned; edit the renderer, not these)

| Path | ~tok | Summary |
|---|--:|---|
| `docs/generated/00-network-map.md` | 449 | Network map |
| `docs/generated/05-state-of-the-lab.md` | 1581 | State of the Lab |
| `docs/generated/06-agent-digest.md` | 1496 | Agent Digest |
| `docs/generated/10-vlans.md` | 794 | VLANs |
| `docs/generated/20-firewall.md` | 2206 | Firewall |
| `docs/generated/50-network-gear.md` | 507 | Network gear (Omada estate) |
| `docs/generated/90-backup-status.md` | 533 | Backup & grant status |
| `docs/generated/README.md` | 227 | Skynet — generated docs |

## Episodic memory — retrieve by topic, don't browse

- `journal/` — 64 raw episodes, ≈ 74332 tok total. Retrieve by topic: `bin/recall <topic>` (SKY-010 P4) or `grep -ri "<topic>" journal/`; recent episodes are already in `06-agent-digest.md`. **Do not load the whole store.**

---
**On-demand corpus:** ≈ **56695** tok across 53 files — but you load a *row* (≈ tens of tok) to choose, then one file.
_A cache — regenerable from git via `render-context-map.sh`; never a source of truth._

> [!note] Generated by `scripts/render-context-map.sh` from each loadable's frontmatter.
> Do not hand-edit. Content-stable (diffs only on real change). The **map of what you can
> load and what it costs** — read a ROW, then open only the one file you need. Baseline +
> this on-demand index = the default-lean discipline ([[memory]]).
