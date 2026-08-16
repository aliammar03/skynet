# Spoke · Secrets

> How Skynet holds secrets so Google never sees plaintext and the repo can hold encrypted history
> safely. Governed by [`../system-design.md`](../system-design.md). Sourced from plan §5 (sops+age)
> and §4 (env layering).

## The master secret

One age keypair on skynet-ops is the root of the secret world:

```bash
age-keygen -o /opt/skynet-ops/secrets/age.key      # root:root 0600
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

## The env layering that makes it safe

Arcane handles env layering natively for git-synced projects. The compose file goes read-only in
the UI, but `.env` stays editable — internally Arcane keeps three layers:

- **`.env.git`** — repo-sourced, non-secret defaults (optional; ingested from a committed plaintext `.env`).
- **`project.env`** — the UI-edited override layer. **This is the secret-bearing layer** — the only
  env content not reproducible from the repo.
- **effective `.env`** — Arcane merges both, overrides winning, rewritten in place preserving order
  and comments. No clobbering is possible by design.

Every service must declare **`env_file: .env`** in its compose to receive the merged values (see
[conventions](../conventions.md)).

## The two directions

- **Host → repo (backup).** Nightly `envsync.sh` reads each project's `project.env` over SSH,
  encrypts it (`sops --encrypt --input-type dotenv`), and commits `compose/<svc>/.env.sops` **only
  on change**. Ali keeps editing envs in Arcane's UI; git holds encrypted history within a day.
- **Repo → host (restore).** `sops -d compose/$svc/.env.sops > project.env` into the project dir —
  Arcane re-merges with `.env.git` on its own. The repo half of every env restores itself by
  definition; only the override layer needs the vault.

This is layer **L1** of the [backup model](../backup-strategy.md).

## Planned expansion — a vault beyond sops+age

sops+age is right for today's service count: file-level, git-native, one keypair, zero running
infrastructure. If the fleet outgrows it (many services, rotation needs, dynamic secrets, non-file
consumers), the migration path is an **external secrets backend** (Vault / Infisical / OpenBao):

- keep `project.env` as the injection point Arcane already merges, so services don't change;
- move the *source of truth* from `.env.sops` in git to the backend, with a sync shim writing
  `project.env` (the way `envsync` writes today, inverted);
- the backend itself becomes a tiered target — likely T3 for its administration, an operate-level
  token for read/lease, decided in [access-and-trust](access-and-trust.md).

Until then, the hard law stands: **sops-in-git or 0600, never plaintext.**
