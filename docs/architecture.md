# Skynet-ops architecture

The full, authoritative design is [`system-design.md`](system-design.md) (the constitution) +
its [`design/`](design/) spokes. This page is the fast orientation map; when the two disagree,
the design wins.

## One-paragraph model

One VM (`vm-skynet-ops`, 10.10.90.90, VLAN 90) hosts a **replaceable** agentic AI runtime.
The GitHub repo `skynet` is machine-readable truth; **`skynet deploy`** is the deployment
executor; secrets are **sops+age**-encrypted in git; **restic → Google Drive** backs up app
data and **PBS → Google Drive** backs up guests. Hands-on host work uses **auto-expiring,
certificate-based root grants**. A disaster runbook can rebuild the network node — OPNsense
included — from a laptop and a phone hotspot.

## Components

| Component | Role | Tier |
|---|---|---|
| GitHub `skynet` | Operational truth (compose, runbooks, inventory, docs) | — |
| GitHub `skynet-opnsense` | Auto-pushed `config.xml` — firewall/router truth that survives the router | — |
| Arcane | Read-only dashboard for the docker-dmz compose projects (host 10.10.100.15); Git Sync off | T1 |
| Proxmox core / network | Hypervisors; `ops-managed` pools plus the core-node managed guest-envelope exception are the write boundary | T1 read / T2 managed envelope |
| PBS (10.10.20.40) | Guest backups, client-side encrypted | T1 / T2 |
| Technitium (10.10.70.50/.51) | Split-horizon DNS; zones editable at T2 | T2 zones |
| OPNsense | Router/firewall/DHCP — read/diagnostics live at T1; non-leash aliases/rules are an approved T2 boundary, but no write actuator is available; node/admin/reboot/self-leash T3 | T1 live / T2 config unavailable / T3 privileged |
| Authentik | Identity provider; scoped app/provider publishing at T2, administration at T3 | T2 slice / T3 admin |
| age key | Master secret at `/opt/skynet-ops/secrets/age.key` | — |
| SSH user-CA | On Ali's workstation only; signs auto-expiring root certs | — |

## Data flows

- **Deploy:** edit `compose/<svc>/` → PR (with the `--dry-run` effect) → merge → the
  `skynet-deploy` timer runs `skynet deploy --pending`: compose and env rendered at the merged
  revision, applied together, verified (labels, health, routes). A failure returns to the last
  verified revision and opens a revert PR.
- **OpenTofu:** edit `tofu/<stack>/` (or a DNS stack's derived input) → PR with
  `approved-plan.json` from `skynet tofu plan <stack> --approve` → merge → `skynet tofu apply --pending`, run supervised until its drills enable the `skynet-tofu` timer
  (`skynet tofu apply --pending`, each minute, its own unit): re-plan at the merged revision, require the approved hash,
  snapshot existing-guest updates, apply, require a clean re-plan, commit encrypted state to the
  `tofu-state` branch. Delete/replace is refused; creates and DNS writes have no automatic inverse.
- **App-data backup:** nightly restic of `/opt/docker/appdata` → rclone → Google Drive.
- **Guest backup:** vzdump → PBS → nightly `rclone sync` of the datastore → Google Drive.
- **Docs:** `skynet render docs` turns validated inventory into `docs/generated/` (Obsidian).

See the per-topic detail in `runbooks/`.
