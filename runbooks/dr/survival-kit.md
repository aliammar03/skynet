---
summary: "What lives on paper and in the password manager, outside Skynet, to bootstrap recovery."
trigger: "Prepare or verify the off-site survival kit"
tier: "T3"
executor: "Ali's paper kit and password manager"
rollback: "replace compromised material through a separate recovery procedure"
---

# Survival kit — paper + password manager, OUTSIDE Skynet

**Tier:** **T3** (human-held recovery materials). **Trigger:** prepare or run the quarterly survival-kit
verification. Store these materials entirely outside Skynet.

The kit is the seed for decrypting encrypted configuration and reaching the recovery systems.

## Preconditions

- Ali has custody of the paper kit, password manager, CA private key, and physical install media.
- Do not paste, commit, or send any listed secret through the agent or repository.

## Steps

### Maintain the contents

- [ ] **age private key** (`/opt/skynet-ops/secrets/age.key`) — decrypts every `.env.sops`.
- [ ] **restic password(s)** — per docker host repo.
- [ ] **PBS encryption key** — must never transit the agent.
- [ ] **SSH CA private key** (`~/.skynet-ca/ops_ca`) — the whole root-grant model. Custody = Ali only.
- [ ] **GitHub fine-grained PAT(s)** — repo access for a from-scratch clone.
- [ ] **rclone Google OAuth config** (`rclone.conf`) — off-site restore access.
- [ ] **Proxmox + OPNsense install ISOs on USB.**
- [ ] **NIC passthrough PCI IDs + BIOS notes** (also versioned in `runbooks/dr/pci-passthrough.md`).
- [ ] **One printed page:** "Clone both repos, open `runbooks/dr/`, follow it."

## Verify

Run these checks quarterly:

- age key decrypts a known `.env.sops`.
- restic/PBS keys open their repos.
- CA key signs a throwaway 10-minute cert (`grant-root docker-dmz 10m`) that then lapses.
- The kill switch is drilled: disable tokens + `qm stop 9090`, then restart.

## Rollback

If a check fails, stop the recovery drill, preserve the known-good kit, and replace only the failed
material through the password manager or physical source. Revoke any throwaway certificate or token used
for verification.

## Evidence

Record the verification date, which checks passed or failed, and any replacement/revocation in the
human-held recovery log. Never record secret values.
