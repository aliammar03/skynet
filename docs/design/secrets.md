---
summary: "How Skynet holds secrets with sops+age and materializes GitOps service env from .env.git plus .env.sops."
---

# Spoke · Secrets

> How Skynet holds secrets so Google never sees plaintext and the repo can hold encrypted history
> safely. Governed by [`../system-design.md`](../system-design.md). Sourced from plan §5 (sops+age)
> and §4 (env layering).

## The master secret

One age keypair on skynet-ops is the root of the secret world:

```bash
age-keygen -o /opt/skynet-ops/secrets/age.key      # root:users 0640
```

```yaml
# .sops.yaml
creation_rules:
  - path_regex: compose/.*/\.env\.sops$
    age: age1<public-key>
```

The age **private key must survive skynet-ops**: password manager + the printed survival kit.
Without it, every `.env.sops` in git history is confetti. (See
[disaster-recovery](disaster-recovery.md) for the full kit.)

## Per-CT identities for pool NixOS LXCs (SKY-021 Option C)

A pool CT decrypts its own secrets with sops-nix at activation, so it needs an age key on the box.
It does **not** get the lab master key (one popped CT would be the whole secret world), and it does
**not** derive one from its ephemeral ssh host key (destroy+recreate would mint a new recipient and
orphan every ciphertext — breaking *rebuild-from-git*). Instead, a **two-tier hierarchy**:

```
lab master key ──decrypts──▶ per-CT age key ──decrypts──▶ that CT's service secrets
(survival kit)               (secrets/<h>-age.key.sops,     (secrets/<h>/*.sops, encrypted to
                             encrypted to the lab key,       BOTH the lab key AND the CT recipient)
                             COMMITTED, injected at provision)
```

- Mint once with [`scripts/ct-age-identity.sh`](../../scripts/ct-age-identity.sh) `new <host>` →
  `secrets/<host>-age.pub` (recipient) + `secrets/<host>-age.key.sops` (lab-encrypted private key).
- `.sops.yaml` routes `secrets/<host>/*.sops` to **both** recipients (CT reads at activation; ops/Ali
  always can too) and `secrets/*-age.key.sops` to the **lab key only**.
- At (re)provision, before the first deploy: `ct-age-identity.sh inject <host> root@<ct-ip>` streams
  the decrypted key to `/var/lib/sops-nix/age.key` (0400 root) — no plaintext on the ops disk.
- **Recreate re-injects the same identity**, so committed ciphertext stays valid — no re-encryption,
  no master key on the CT. Blast radius of a popped CT = that CT's secrets, not the lab.

## The GitOps env materialization

Arcane's GitOps projects do not merge `project.env` into the checked-out project. Their complete env
source is in git:

- **`.env.git`** — non-secret defaults, committed plaintext.
- **`.env.sops`** — secret values, encrypted to the lab age recipient.
- **effective `.env`** — materialized `0600` by `scripts/gitops-deploy.sh` from `.env.git` plus
  decrypted `.env.sops`, then consumed through each service's `env_file: .env`.

Decryption happens on vm-skynet-ops; plaintext crosses only the SSH stream into the project file.
Arcane owns reconciliation and project lifecycle, while the deploy wrapper owns env materialization.

## The two directions

- **Repo → host (normal deploy/restore).** `scripts/gitops-deploy.sh <svc>` combines the approved
  `.env.git` and `.env.sops`, writes the effective `.env`, redeploys, and checks health.
- **Legacy host → repo import.** `envsync.sh` encrypts `project.env` when a legacy/non-GitOps Arcane
  project still has one. Current GitOps projects do not require that file; its absence is expected,
  not a missing secret backup.

This is layer **L1** of the [backup model](../backup-strategy.md).

## Planned expansion — a vault beyond sops+age

sops+age is right for today's service count: file-level, git-native, one keypair, zero running
infrastructure. If the fleet outgrows it (many services, rotation needs, dynamic secrets, non-file
consumers), the migration path is an **external secrets backend** (Vault / Infisical / OpenBao):

- keep `.env` as the container injection point, so services do not change;
- move the *source of truth* from `.env.sops` in git to the backend, with the deploy wrapper writing
  the materialized `.env`;
- the backend itself becomes a tiered target — likely T3 for its administration, an operate-level
  token for read/lease, decided in [access-and-trust](access-and-trust.md).

Until then, the hard law stands: **sops-in-git or 0600, never plaintext.**
