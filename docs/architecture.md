# Skynet-ops architecture

The full, authoritative design is [`system-design.md`](system-design.md) (the constitution) +
its [`design/`](design/) spokes. This page is the fast orientation map; when the two disagree,
the design wins.

## One-paragraph model

One VM (`vm-skynet-ops`, 10.10.90.90, VLAN 90) hosts a **replaceable** agentic AI runtime.
The GitHub repo `skynet` is machine-readable truth; **Arcane GitOps** is the deployment
executor; secrets are **sops+age**-encrypted in git; **restic → Google Drive** backs up app
data and **PBS → Google Drive** backs up guests. Hands-on host work uses **auto-expiring,
certificate-based root grants**. A disaster runbook can rebuild the network node — OPNsense
included — from a laptop and a phone hotspot.

## Components

| Component | Role | Tier |
|---|---|---|
| GitHub `skynet` | Operational truth (compose, runbooks, inventory, docs) | — |
| GitHub `skynet-opnsense` | Auto-pushed `config.xml` — firewall/router truth that survives the router | — |
| Arcane | GitOps reconciler for docker compose projects (host 10.10.100.15) | T2 |
| Proxmox core / network | Hypervisors; `ops-managed` pools plus the core-node managed guest-envelope exception are the write boundary | T1 read / T2 managed envelope |
| PBS (10.10.20.40) | Guest backups, client-side encrypted | T1 / T2 |
| Technitium (10.10.70.50/.51) | Split-horizon DNS; zones editable at T2 | T2 zones |
| OPNsense | Router/firewall/DHCP — read/diagnostics live at T1; non-leash aliases/rules approved for T2 but SKY-020 implementation is pending; node/admin/reboot/self-leash T3 | T1 live / T2 config pending / T3 privileged |
| Authentik | Identity provider; scoped app/provider publishing at T2, administration at T3 | T2 slice / T3 admin |
| age key | Master secret at `/opt/skynet-ops/secrets/age.key` | — |
| SSH user-CA | On Ali's workstation only; signs auto-expiring root certs | — |

## Data flows

- **Deploy:** edit `compose/<svc>/` → PR → merge → `gitops-deploy.sh` materializes `.env`
  from `.env.git` + decrypted `.env.sops` → Arcane reconciles → health check.
- **Legacy env import:** `envsync.sh` encrypts a host `project.env` when one exists; GitOps projects
  use committed `.env.git` + `.env.sops` and do not depend on `project.env`.
- **OpenTofu:** authored source PR → human merge → reviewed saved plan →
  `TOFU_APPLY_SCOPE=proxmox-core scripts/tofu-apply.sh <planfile>`; no production bare apply.
  New-guest creates run as supervised T2 actions with explicit approval; they have no automatic
  rollback and are not A4-eligible. The wrapper refuses delete/replace plans.
- **App-data backup:** nightly restic of `/opt/docker/appdata` → rclone → Google Drive.
- **Guest backup:** vzdump → PBS → nightly `rclone sync` of the datastore → Google Drive.
- **Docs:** `render-docs.sh` turns `inventory/*.json` + firewall config into `docs/generated/` (Obsidian).

See the per-topic detail in `runbooks/` and the plan sections referenced throughout.
