# Skynet — System Design

> The constitution: authority, hard laws, versioned dials, the autonomy ladder, and the contract
> every operator follows. Domain mechanics live in the linked design spokes.

## 0. Authority and scope

This file is the constitution. When it conflicts with another repository document, this file wins;
correct the other document rather than creating a second rule. [`AGENTS.md`](../AGENTS.md) is the
always-loaded, cross-vendor operating contract distilled from this design and must agree with it.

The repository is the rebuildable source of system truth. Generated views report current state;
runbooks execute procedures; ADRs record decisions; directives in [`planning/`](../planning/README.md)
own future work; and the [`journal/`](../journal/README.md) owns evidence and incidents.

## 1. System and terminal goal

`vm-skynet-ops` is a replaceable agent runtime: NixOS VMID 9090, static `10.10.90.90` on VLAN 90.
Git is operational truth; Arcane reconciles GitOps services; encrypted secrets, inventory, docs,
and policy rebuild from git; backups restore payload only after the system stands up. Details are in
[network](design/network.md), [gitops loop](design/gitops-loop.md),
[secrets](design/secrets.md), and [disaster recovery](design/disaster-recovery.md).

The terminal goal is full agent control: a human states intent and Skynet safely provisions,
publishes, backs up, monitors, documents, repairs, and reverts the lab. The current leash reflects
missing evidence, not a different goal. Autonomy is earned per capability, never granted wholesale.

| Level | Capability | Required evidence |
|---|---|---|
| **A0** Observe | Read, render, report | — |
| **A1** Propose | Open a reviewable PR | Human review |
| **A2** Rehearse | Run in a proving ground | Rehearsal assertions |
| **A3** Supervised act | Act in production with easy undo | Gates and verification |
| **A4** Auto act | Act unattended in declared scope | Gates, verification, and automatic failure-tested rollback by a dumb executor |
| **A5** Self-direct | Decide when to act | The above plus drift attribution and a budget |

No irreversible action (`destroy`, data deletion, credential rotation, or T3 work) becomes
unattended. The rationale and reversibility test are in
[ADR 0005](decisions/0005-full-agent-control-as-terminal-goal.md); future promotions belong to
[SKY-017](../planning/ideas/SKY-017-the-road-to-full-agent-control-verification-proving-ground-and-an-evidence-earned-ratchet.md).

## 2. Hard laws

- **No standing T3 write path.** Management Caddy, Authentik administration, Proxmox node root,
  Unraid root, Technitium settings, and Cloudflare account/Access/tunnel/zone settings require a
  dormant route and per-session credentials. OPNsense node root, account/cert administration,
  reboot, and self-leash rules are also T3.
- **Never widen the agent's own leash.** This includes `ROLE_OPS_*`, `ROLE_OPS_PRIV_TARGETS`, the
  block-other-DNS rules, and the agent's OPNsense accounts. Changes to this section, this ladder,
  the dials below, `AGENTS.md` §3/§6, `invariants.json`, or enforcing gates are human-merged forever.
- **Root is grant-only.** The SSH CA private key stays on Ali's workstation; each host certificate
  expires by itself and its KeyID is harvested nightly.
- **Secrets are encrypted in git or agent-readable restrictive local files under
  `/opt/skynet-ops/secrets/`.** Materialized files are `0400 aliammar`; the lab age key is
  `0640 root:users`, so the agent decrypts sops without sudo. Plaintext never enters commits, logs,
  transcripts, or chat.
- **System rebuilds from git; payload restores from backup.** A system-class item recoverable only
  from backup is a bug.
- **Generated state is machine-owned.** The agent does not hand-edit `inventory/` or
  `docs/generated/`.

Deterministic parts of these laws are enforced by `invariants.json` and its gates; prose remains the
authority where judgment is required. The enforcement principle is
[ADR 0003](decisions/0003-ambiguity-layering-and-format-follows-enforcement.md).

## 3. Versioned dials

These are current settings, changed only by a PR here.

- **Write blast radius:** the `ops-managed` pool set, `ROLE_OPS_SSH_TARGETS`, and Technitium zones.
  The network node is pool-scoped; VM 5001 and CTs 635/837 never enter a pool. The core operate
  token is deliberately root-`/` for managed guest envelopes, storage, SDN, and pools, but lacks
  `Permissions.Modify` and node-root privileges. It can technically reach Unraid VM 2020's envelope;
  automated/OpenTofu paths must never target it, and its guest OS remains T3. Exact ACLs and
  exclusions: [access and trust](design/access-and-trust.md).
- **Merge gate:** human merge for authored changes. The nightly may auto-merge only its own
  generated-only, CI-green PRs (off switch `OPS_NIGHTLY_AUTOMERGE=0`); see
  [ADR 0004](decisions/0004-auto-merge-generated-only-nightly-prs.md).
- **Autonomy:** report-only outside the version-controlled auto-approve list. The nightly's
  generated-only merge is the sole A4 capability; all other promotions require recorded evidence.
- **Survival:** verify the survival kit quarterly and drill `disable tokens + qm stop 9090` before
  autonomy day one and on demand.

## 4. Trust spine

The detailed token, ACL, and principal design is [access and trust](design/access-and-trust.md).

| Tier | Scope | Standing? |
|---|---|---|
| **T1 Read** | Proxmox, PBS, Docker, DNS, Omada, and OPNsense diagnostics | Yes, read-only |
| **T2 Operate** | Managed envelopes, Docker through Arcane/unprivileged SSH, Technitium zones, scoped Authentik app/provider CRUD, `aliammar.net` DNS records, backup/snapshot, saved-plan guest changes | Yes where implemented; PR-gated |
| **T2+ Root** | Workload-host root shell | Only a time-limited grant |
| **T3 Privileged** | Management planes and all self-leash changes | Never standing |

OPNsense has a T1 live-read path and an approved but not yet implemented T2 firewall-config path;
the self-leash remains T3. Cloudflare DNS records and Technitium zones are T2; their accounts and
server settings are T3. Saved-plan OpenTofu actions use `scripts/tofu-apply.sh` with one scope and
never a bare apply; create is supervised and destroy is refused. See
[actuators](design/actuators.md) and the provisioning runbooks.

## 5. Operator contract and extension index

Skynet is agent-agnostic: any operator that can read markdown and run bash follows `AGENTS.md`,
uses scripts as capabilities, and runbooks as procedures. The runtime engine is replaceable.

| Change | Authoritative home |
|---|---|
| Service deploy or publish | [GitOps loop](design/gitops-loop.md), `runbooks/` |
| Host onboarding, Proxmox scope, or root grant | [access and trust](design/access-and-trust.md) |
| Network, DNS, or firewall reachability | [network](design/network.md) |
| Identity, proxy, or public exposure | [identity and proxy](design/identity-and-proxy.md) |
| Secrets or recovery | [secrets](design/secrets.md), [disaster recovery](design/disaster-recovery.md) |
| New capability, tier, dial, or blast-radius change | This constitution plus a directive in `planning/` |

## 6. Design spokes

| Spoke | Current domain |
|---|---|
| [access-and-trust](design/access-and-trust.md) | Credentials, ACLs, grants, and tier boundaries |
| [actuators](design/actuators.md) | Write paths and rollback eligibility |
| [disaster-recovery](design/disaster-recovery.md) | Recovery architecture and survival kit |
| [gitops-loop](design/gitops-loop.md) | Service reconciliation and rollback |
| [identity-and-proxy](design/identity-and-proxy.md) | DNS, proxy, Authentik, and public path |
| [memory](design/memory.md) | Portable memory and default-lean retrieval |
| [network](design/network.md) | Placement and reachability boundary |
| [observability](design/observability.md) | Inventory, generated state, and nightly reporting |
| [secrets](design/secrets.md) | sops/age and environment materialization |

Past build history is in [`history/`](history/); future expansion is in
[`planning/`](../planning/README.md), not this constitution.
