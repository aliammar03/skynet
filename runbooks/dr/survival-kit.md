# Survival kit — paper + password manager, OUTSIDE Skynet

Assembled and printed by Ali from the agent's manifest (A2 row 9). Verified quarterly.
Without these, encrypted history is confetti — store them off Skynet entirely.

## Contents

- [ ] **age private key** (`/opt/skynet-ops/secrets/age.key`) — decrypts every `.env.sops`.
- [ ] **restic password(s)** — per docker host repo.
- [ ] **PBS encryption key** — exported at A2 row 8; must never transit the agent.
- [ ] **SSH CA private key** (`~/.skynet-ca/ops_ca`) — the whole root-grant model. Custody = Ali only.
- [ ] **GitHub fine-grained PAT(s)** — repo access for a from-scratch clone.
- [ ] **rclone Google OAuth config** (`rclone.conf`) — off-site restore access.
- [ ] **Proxmox + OPNsense install ISOs on USB.**
- [ ] **NIC passthrough PCI IDs + BIOS notes** (also versioned in `runbooks/dr/pci-passthrough.md`).
- [ ] **One printed page:** "Clone both repos, open `runbooks/dr/`, follow it."

## Verify (quarterly)

- age key decrypts a known `.env.sops`.
- restic/PBS keys open their repos.
- CA key signs a throwaway 10-minute cert (`grant-root docker-dmz 10m`) that then lapses.
- The kill switch is drilled: disable tokens + `qm stop 9090`, then restart.
