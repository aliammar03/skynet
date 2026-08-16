# Skynet-ops architecture

The full, authoritative design is [`deployment-plan.md`](deployment-plan.md). This page is
the fast orientation map; when the two disagree, the plan wins.

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
| Proxmox core / network | Hypervisors; `ops-managed` pools are the write blast radius | T1 read / T2 pool |
| PBS (10.10.20.40) | Guest backups, client-side encrypted | T1 / T2 |
| Technitium (10.10.70.50/.51) | Split-horizon DNS; zones editable at T2 | T2 zones |
| OPNsense | Router/firewall/DHCP — **T3, never standing access** | T3 |
| age key | Master secret at `/opt/skynet-ops/secrets/age.key` | — |
| SSH user-CA | On Ali's workstation only; signs auto-expiring root certs | — |

## Data flows

- **Deploy:** edit `compose/<svc>/` → PR → merge → Arcane syncs → agent health-checks → inventory commit.
- **Secrets backup:** nightly `envsync.sh` pulls each project's `project.env`, `sops`-encrypts to `compose/<svc>/.env.sops`.
- **App-data backup:** nightly restic of `/opt/docker/appdata` → rclone → Google Drive.
- **Guest backup:** vzdump → PBS → nightly `rclone sync` of the datastore → Google Drive.
- **Docs:** `render-docs.sh` turns `inventory/*.json` + firewall config into `docs/generated/` (Obsidian).

See the per-topic detail in `runbooks/` and the plan sections referenced throughout.
