---
date: 2026-09-04
kind: session          # session | incident | decision
title: SKY-021 P3a — Option C per-CT age identity + pivot to adguard-core (731)
tier_touched: [T1]      # read-only recon this episode; the destructive cutover is P3b
grants: []
refs: [SKY-021, SKY-007, SKY-008]
---

# 2026-09-04 · session · SKY-021 P3a — Option C per-CT age identity + pivot to adguard-core (731)

## What happened
Started P3 (convert a real pool CT to NixOS + set the new-CT default). Ali asked, after the P2
close-out Q&A, to **implement Option C** (per-CT age key, sops-encrypted to the lab key, injected at
provision) and start the phase.

**The recreation hole Option C fixes** (from the P2 wrap Q "how will recreation work with a
host-derived key?"): a host-key-derived age identity is minted fresh on destroy+recreate → new
recipient → every ciphertext in git orphaned → breaks rebuild-from-git. Lab-master-key-on-every-CT
spreads the crown-jewel. Option C = two tiers: lab key → per-CT key (committed, lab-encrypted,
injected) → service secrets (dual-recipient lab+CT). Recreate re-injects the SAME key → ciphertext
stays valid.

**Recon surfaced two things that reshaped the phase:**
1. The directive's pilot `adguard-network` is **CT 730 on the NETWORK node** — pool-scoped token
   there (no /vms root, no Datastore.AllocateTemplate), so template-upload + new-VMID mint are
   grant-walled (the P1b wall the core /-broaden already retired). Ali redirected mid-session: **"CT
   731 my dude"** → pivot to **adguard-core (731) on the CORE node**, where the token self-provisions
   (P1/P2 proven). 730 stays up as the fallback filter during cutover.
2. **SSH ops(VLAN90)→VLAN70 was firewalled** (731/730 both timed out). Flagged it (deploy-rs needs
   that path; widening ROLE_OPS_SSH_TARGETS is a self-leash change = Ali-merged). Ali **"firewall
   updated"** → 731:22 now REACHES, but the agent key isn't authorized on the Debian community-script
   731 (`Permission denied (publickey,password)`), so I still can't read its AdGuardHome.yaml.

**Built + validated Option C (all as `aliammar`, no root — the lab age key at
/nix/persist/opt/skynet-ops/secrets/age.key is readable by the agent user, and sops -d works with
it):**
- `scripts/ct-age-identity.sh` (new/pubkey/inject). age, age-keygen, sops are all on-PATH on the ops
  box. Encrypt-to-lab uses `sops encrypt --filename-override secrets/<h>-age.key.sops` so the repo
  .sops.yaml rule applies to a tmp input. `inject` streams `sops -d | ssh root@ct 'install -m400 -D
  /dev/stdin /var/lib/sops-nix/age.key'` — plaintext never on ops disk.
- Minted the pilot identity: `ct-age-identity.sh new lxc-adguard-core` → recipient
  `age1vr4fpg7tgegx6vgv5z5hqdfnqq9pmdf2sj3euzkesken0prcyupszj4k7k`; private half lab-encrypted at
  secrets/lxc-adguard-core-age.key.sops. Round-trip verified: decrypt → `age-keygen -y` → matches the
  committed .pub.
- `.sops.yaml`: `secrets/*-age.key.sops` → lab only; `secrets/lxc-adguard-core/*.sops` →
  dual-recipient (lab + CT). Verified both routes by test-encrypting to each path.
- `docs/design/secrets.md`: added the "Per-CT identities" subsection (terse doctrine + diagram).

Landed on branch `feat/sky-021-nixos-lxc-p3` (based on **main**, not the P2 branch — avoid-stacked-
PR: Option C touches no file #161 touches). **PR #162.** Gates green (secret-scan, check-invariants).

## Actions & outcomes
- `ct-age-identity.sh new lxc-adguard-core` → identity minted, lab-encrypted, round-trip OK ✓
- `.sops.yaml` dual/lab-only routing → verified by test-encrypt to each path ✓
- secret-scan + check-invariants → green ✓
- PR #162 (P3a, off main) ✓
- did NOT author hosts/lxc-adguard-core yet — blocked on 731's live config (agent key not authorized)

## Graveyard — tried & abandoned
- `nix run nixpkgs#age-keygen` / `github:Mic92/sops-nix#ssh-to-age` → wrong attrs; age-keygen is in
  the `age` pkg (and already on-PATH here), ssh-to-age is `nixpkgs#ssh-to-age`.
- `sops -e <tmpfile>` from repo root or scratch → "no matching creation rules"; use
  `--filename-override <target-path>` so the .sops.yaml rule for the destination applies.
- Targeting adguard-network (730) per the directive → abandoned for 731: 730 is on the network node
  (grant-walled), 731 is on core (self-provisioning). Ali's call.

## Follow-ups / open threads
- **P3b (needs Ali):** authorize the agent key on 731 (or paste /opt/AdGuardHome/AdGuardHome.yaml) so
  the AdGuard config ports faithfully into `services.adguardhome`. Then author hosts/lxc-adguard-core,
  provision the NixOS replacement on core (inject the Option C key before first deploy), cut DNS
  filtering over keeping old 731 stopped as rollback, and PR docs/system-design.md (new-CT default).
- **Merge order:** P3b touches flake.nix (adguard-core deploy node + sops-nix module) → base on merged
  #161 to avoid a conflict.
- **Security follow-up (out of P3 scope):** the lab MASTER age key is readable by the `aliammar`
  (agent) user — narrowest-grant doctrine would want it root-only, decrypt via a privileged helper.
  Pre-existing, not introduced here. Worth a SKY item.
- Directive frontmatter/status-log NOT bumped on this branch (P2's directive edit is on #161; bump
  when P3 completes on merged main to avoid a conflict).
