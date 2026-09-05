---
summary: "Catalog of task-shaped, engine-neutral operational procedures. Rendered from runbook frontmatter."
---

# runbooks — procedures any agent can execute

A runbook is engine-neutral markdown plus plain bash. Read the leaf whose trigger matches the task; do not load unrelated procedures.

## Catalog

| Runbook | Tier | Trigger | Summary |
|---|---|---|---|
| [`backup.md`](backup.md) | T2+ root grant | How do backups work / run a backup | How restic and PBS backups run, how to provision restic, and how to take a pre-change backup. |
| [`construction-delegation.md`](construction-delegation.md) | T1 build-time only | Do a substantial construction task / build X / implement or change X | Run substantial construction as a lead — route bounded helpers, verify their work, and open the PR without granting production authority. |
| [`deploy-service.md`](deploy-service.md) | T2 PR-gated | Deploy or update a service | Deploy or update a service through the Arcane GitOps loop: edit compose then PR then Arcane reconciles. |
| [`diagnose/arcane-stuck.md`](diagnose/arcane-stuck.md) | T1/T2 | A merged compose PR didn't deploy / Arcane isn't reconciling / git and running have drifted | Triage a merged compose PR that didn't deploy — check the Arcane Git Sync status/error, compare git vs running, distinguish sync-fail vs apply-fail vs drift. |
| [`diagnose/backup-missed.md`](diagnose/backup-missed.md) | T1/T2 | An expected backup/snapshot is missing / a restic or PBS timer failed | Triage a missed backup — check the timer, the last snapshot age, and repo reachability across restic→gdrive and PBS→gdrive, fix the timer/creds/repo declaratively. |
| [`diagnose/cert-expired.md`](diagnose/cert-expired.md) | T1 | Cert warning / TLS handshake fails / 'certificate expired' / ACME renewal failing | Triage an expired/failing TLS cert — read the served cert's dates, find why ACME isn't renewing (HTTP-01 vs DNS-01, rate limit, clock), fix in Caddy config. |
| [`diagnose/container-crashloop.md`](diagnose/container-crashloop.md) | T1 | A container is Restarting / unhealthy / keeps exiting | Triage a container that restarts, is unhealthy, or exits — read exit code + logs + healthcheck, branch to the cause, fix in compose/. |
| [`diagnose/disk-full.md`](diagnose/disk-full.md) | T1/T2+ | Disk full / write failures / df at 100% (or inodes exhausted with space free) | Triage a full disk (or exhausted inodes) — find what ate the space, distinguish data vs logs vs docker cruft, fix the cause declaratively. |
| [`diagnose/dns-failure.md`](diagnose/dns-failure.md) | T1/T2 | A name won't resolve / service unreachable by hostname / ACME DNS-01 failing | Triage internal Technitium and public Cloudflare DNS failures, then repair records through the scoped declarative path. |
| [`dr/DR-core-node.md`](dr/DR-core-node.md) | T2+ | Core node is dead | Recover when server-proxmox-core (with PBS aboard) is dead. |
| [`dr/DR-network-node.md`](dr/DR-network-node.md) | T3 | Network node or OPNsense is dead | Recover when server-proxmox-network is dead — OPNsense and routing gone. |
| [`dr/pci-passthrough.md`](dr/pci-passthrough.md) | T3 | NIC passthrough for OPNsense | Re-establish NIC passthrough for VM 5001 (OPNsense) after a rebuild. |
| [`dr/survival-kit.md`](dr/survival-kit.md) | T3 | Prepare or verify the off-site survival kit | What lives on paper and in the password manager, outside Skynet, to bootstrap recovery. |
| [`nightly.md`](nightly.md) | T1 read + generated-only PR | Run the nightly / nightly timer | The report-only nightly maintenance run on both engine paths, and what it refreshes. |
| [`provision-lxc.md`](provision-lxc.md) | Supervised T2 saved-plan create | Set up / deploy a new LXC for X | Provision a NixOS core-managed LXC from merged source and an explicitly approved saved plan; creates are supervised T2 without automatic rollback. |
| [`provision-vm.md`](provision-vm.md) | Supervised T2 saved-plan create + T2+ root grant | Set up a VM for X, hardened, with restic | Provision a VM from merged source and an explicitly approved saved plan; creates are supervised T2 without automatic rollback. |
| [`publish-service.md`](publish-service.md) | T2 PR-gated | Publish or expose a service | Choose the runbook for publishing a service through apps Caddy, Authentik, or the Cloudflare Tunnel. |
| [`publish/forward-auth.md`](publish/forward-auth.md) | T2 PR-gated | Put a no-login service behind Authentik | Publish a service with no native login behind Authentik forward-auth on apps Caddy. |
| [`publish/internal-route.md`](publish/internal-route.md) | T2 PR-gated | Give an authenticated service an internal aliammar.net URL | Publish an own-auth service on the internal apps Caddy front door. |
| [`publish/public-tunnel.md`](publish/public-tunnel.md) | T2 PR-gated | Expose an internally published service to the public internet | Add Cloudflare Tunnel and public DNS exposure to an already-working internal route. |
| [`recon.md`](recon.md) | T1 read-only | Figure out why X is broken / what's going on with <host> | Take a bounded T1 host snapshot, interpret its signals, and route to the focused diagnosis runbook. |
| [`restore-service.md`](restore-service.md) | T2; PBS token for VM restore | Restore a service / recover from backup | Restore a service or VM from restic/PBS using a selected recovery point. |
| [`update-guests.md`](update-guests.md) | T2 snapshot + T2+ fleet root grant | Update all guests | Snapshot then update every guest under a fleet root grant. |

## Runbook contract

- Use compact frontmatter: `summary`, `trigger` where natural, `tier`, `executor`, and `rollback`.
- Structure every leaf as **Preconditions → Steps → Verify → Rollback → Evidence**.
- Keep procedures current and task-shaped; doctrine belongs in its authoritative design/convention document, history in `journal/`.

_A cache — regenerate with `scripts/render-runbook-catalog.sh`; never hand-edit._
