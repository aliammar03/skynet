---
summary: "The current credential, ACL, principal, and root-grant boundaries that implement Skynet's trust tiers."
---

# Spoke · Access & trust

> The current mechanisms behind the constitution's trust tiers. Governed by
> [`../system-design.md`](../system-design.md); procedures live in `runbooks/` and scripts.

## Tier mechanisms

| Tier | Current mechanism | Boundary |
|---|---|---|
| **T1 Read** | Read-only Proxmox/PBS/DNS/Docker tokens; scoped OPNsense API; Omada Viewer | No writes |
| **T2 Operate** | `svc-ops` SSH; Arcane, Technitium, Authentik, Cloudflare, and Proxmox operate tokens | PR-gated declared scope |
| **T2+ Root** | Per-host OpenSSH user certificate | Ali signs; expires automatically |
| **T3 Privileged** | Dormant `ROLE_OPS_PRIV_TARGETS` and per-session credentials | No standing route or credential |

Secret material is sops-encrypted or materialized as `0400 aliammar` below
`/opt/skynet-ops/secrets/`. The master age key is `0640 root:users`; both are readable by the agent
without sudo. Environment materialization is detailed in [secrets](secrets.md).

## Proxmox operate scope

`svc-ops@pve!operate` is the API-only identity for both imperative operations and OpenTofu. The
token is privilege-separated, so the role must be bound to both the user and token. Bootstrap is a
human out-of-band action; tofu never administers the credential it uses.

| Node | Scope | Bright lines |
|---|---|---|
| **Core** | `OpsOperator` at `/`: guest envelopes, storage, SDN, pools, and new VMIDs | No `Permissions.Modify`, `Sys.Modify`, `Sys.PowerMgmt`, or `Sys.Console`; no guest-OS root |
| **Network** | Existing `ops-managed` guests and declared storage/SDN paths | No `/vms` root or new VMIDs; VM 5001 and CTs 635/837 are unreachable |

`VM.Allocate` permits create and destroy; it cannot be narrowed to new IDs. That is why it is absent
on the network node. The core ACL can technically reach Unraid VM 2020's envelope, but automated and
OpenTofu paths never target it; its guest OS remains T3 and envelope actions are human checkpoints.
The ACL audit plus `invariants.json` enforce these exclusions and bright lines.

OpenTofu uses the saved-plan executor only. A plan has one declared scope; the wrapper rejects
mixed scope, delete/replace actions, and un-snapshotable existing-guest updates. See
[actuators](actuators.md) and the provisioning runbooks.

## Workload-host access

`svc-ops` is the standing unprivileged account (including Docker access where needed). Root requires
a certificate signed by the CA that remains on Ali's workstation. `bin/grant-root <host> [duration]`
creates a host-specific certificate and SSH configuration entry; multiple grants coexist and expire
without a cleanup action. Root session KeyIDs are collected nightly.

[`scripts/onboard-host.sh`](../../scripts/onboard-host.sh) installs CA trust and principal mapping on
a managed host. A new VM first needs its temporary bootstrap path, then this onboarding procedure;
the VM-provision runbook owns the exact steps.

## Scoped service boundaries

| System | T2 surface | T3 surface |
|---|---|---|
| Technitium | Zone view/modify | Settings, administration, DHCP |
| Authentik | Application/provider CRUD; bind an existing outpost | Flows, policies, users/groups, settings, outpost tokens, signing keys |
| Cloudflare | `aliammar.net` DNS records | Account, Access, tunnel configuration, zone settings |
| Omada | Viewer inventory, ports, PoE, VLAN/profile, firmware, adoption state | Controller/site administration |

The Authentik token is a one-time T3-created scoped service account, verified unable to touch its T3
surface. Cloudflare DNS uses a scoped `DNS:Edit` token; public hostname removal is still a hard
checkpoint because the tofu executor refuses deletion. Omada is reachable through the API-target
firewall boundary and its collector degrades safely if unavailable.

## OPNsense

OPNsense has three planes:

- **T1:** `svc-skynet-recon` reads live aliases, rules, interfaces, DHCP, neighbours, and logs, and
  runs non-mutating diagnostics. Its group grants `System: Deny config write`; privileges are granted
  through that group, never directly to the user.
- **T2 approved, not implemented:** non-self-leash firewall aliases/rules may eventually use a
  reviewed saved-plan provider path. No provider, write credential, or actuator exists today.
- **T3:** node root, account/API-key/certificate administration, reboot/halt, and every rule or alias
  that bounds Skynet's reach. The OPNsense git mirror remains rebuild-from-git truth; live API is for
  fresh observation.

The self-leash is permanently human-merged and plan-gated. The detailed policy rationale is
[ADR 0006](../decisions/0006-opnsense-read-is-t1-write-stays-t3.md).
