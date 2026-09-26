---
summary: "How Skynet holds secrets with sops+age and renders service env from .env.git plus .env.sops at deploy."
---

# Spoke · Secrets

> How Skynet holds secrets so Google never sees plaintext and the repo can hold encrypted history
> safely. Governed by [`../system-design.md`](../system-design.md).

## The master secret

One age keypair on skynet-ops is the root of the secret world. Its private key is
`/opt/skynet-ops/secrets/age.key` (`root:users`, `0640`) so the agent can decrypt sops without
sudo. sops-nix materializes service secret files as `0400 aliammar` under `/run/secrets/`, with the
existing `/opt/skynet-ops/secrets/` paths linking to them. The agent reads both paths unprivileged.

```yaml
# .sops.yaml
creation_rules:
  - path_regex: compose/.*/\.env\.sops$
    age: age1<public-key>
```

The age **private key must survive skynet-ops**: password manager + the printed survival kit.
Without it, every `.env.sops` in git history is confetti. (See
[disaster-recovery](disaster-recovery.md) for the full kit.)

## Per-CT identities for pool NixOS LXCs

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

- [`ct-age-identity.sh`](../../scripts/ct-age-identity.sh) creates the recipient
  `secrets/<host>-age.pub` and lab-encrypted private key `secrets/<host>-age.key.sops`.
- `.sops.yaml` routes `secrets/<host>/*.sops` to **both** recipients (CT reads at activation; ops/Ali
  always can too) and `secrets/*-age.key.sops` to the **lab key only**.
- LXC provision injects the decrypted identity to `/var/lib/sops-nix/age.key` (`0400 root`) before
  its first deploy; use [`provision-lxc.md`](../../runbooks/provision-lxc.md).
- **Recreate re-injects the same identity**, so committed ciphertext stays valid — no re-encryption,
  no master key on the CT. Blast radius of a popped CT = that CT's secrets, not the lab.

## Service env at deploy

A service's complete env source is in git:

- **`.env.git`** — non-secret defaults, committed plaintext.
- **`.env.sops`** — secret values, encrypted to the lab age recipient.

`skynet deploy` decrypts `.env.sops` on vm-skynet-ops from the git object (stdin to `sops`),
joins it with `.env.git` (a key defined twice is refused), and writes the result `0600` into a
tmpfs render directory that Compose reads for `env_file: .env` and interpolation. The resolved
project goes to the Docker host on the deploy command's stdin; the render directory is deleted
before the deploy returns. No `.env` exists on the Docker host — the values live only in the
container configuration, as with any Compose env.

## Operations

- **Deploy or restore:** [`deploy-service.md`](../../runbooks/deploy-service.md) and
  [`restore-service.md`](../../runbooks/restore-service.md) run `skynet deploy <svc>`.

This is layer **L1** of the [backup model](../backup-strategy.md). Secrets are sops-encrypted in git
or stored as the agent-readable restrictive local files above. Plaintext never enters git.
