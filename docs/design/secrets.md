---
summary: "How Skynet holds secrets with sops+age and safely materializes immutable Compose generation environments."
---

# Spoke · Secrets

> How Skynet keeps secret values encrypted in Git and delivers a service environment to the exact
> protected Compose generation. Governed by [`../system-design.md`](../system-design.md).

## The master secret

One age keypair on skynet-ops is the root of the secret world. Its private key is
`/opt/skynet-ops/secrets/age.key` (`root:users`, `0640`) so `aliammar` can decrypt sops without
sudo. sops-nix separately materializes host/service secret files as `0400 aliammar` under
`/run/secrets/`, with the existing `/opt/skynet-ops/secrets/` paths linking to them. The age key
must survive skynet-ops in the password manager and printed survival kit; without it, encrypted
history cannot be recovered.

```yaml
# .sops.yaml
creation_rules:
  - path_regex: compose/.*/\.env\.sops$
    age: age1<public-key>
```

## Per-CT identities for pool NixOS LXCs

A pool CT decrypts only its own service secrets with sops-nix at activation. It does not receive the
lab key and does not derive an identity from its ephemeral SSH host key. The two-tier hierarchy is:

```
lab master key ──decrypts──▶ per-CT age key ──decrypts──▶ that CT's service secrets
(survival kit)               (secrets/<host>-age.key.sops,     (secrets/<host>/*.sops, encrypted to
                             encrypted to the lab key)         BOTH the lab key and CT recipient)
```

- [`ct-age-identity.sh`](../../scripts/ct-age-identity.sh) creates the recipient and lab-encrypted
  private key.
- `.sops.yaml` encrypts `secrets/<host>/*.sops` to both recipients and
  `secrets/*-age.key.sops` to the lab key only.
- LXC provisioning injects the same identity to `/var/lib/sops-nix/age.key` (`0400 root`) before
  the first deploy; see [`provision-lxc.md`](../../runbooks/provision-lxc.md).

## Compose generation environment

Each service has two authored inputs at one exact full Git revision:

- `.env.git` — committed non-secret defaults;
- `.env.sops` — optional secret assignments encrypted to the lab age recipient.

The packaged `skynet deploy prepare` owner reads Git objects, not dirty checkout bytes. It layers
those selected inputs in local memory. sops receives the revision's ciphertext over bounded stdin
and decrypts on `vm-skynet-ops` with `SOPS_AGE_KEY_FILE`; the age key never leaves that host. Secret
plaintext travels only through bounded SSH stdin to the protected remote generation staging area.
The staging `.env` is mode `0600`; only the selected published generation persists it inside
`/home/svc-ops/.local/state/skynet-deploy/<service>/generations/<full-revision>/`. No local plaintext
file, argv, retained subprocess output, report, journal, commit, or JSON contains it. The public
release manifest may record Git blob and ciphertext identities but never secret values or a hash of
effective plaintext. A low-entropy secret must not become guessable through a published hash.

Compose uses `env_file: .env` relative to that generation. Preparation validates Compose expansion
against its own effective environment before atomic publication. Direct activation runs Compose from
the immutable generation. Arcane `project.env` and Git Sync are not secret or deployment authority;
enabled legacy auto-sync is refused before Docker mutation. The retained `gitops-deploy.sh` shell
name is a temporary packaged-command forwarder until P22.

## Operations

Deploy or restore with [`deploy-service.md`](../../runbooks/deploy-service.md) and
[`restore-service.md`](../../runbooks/restore-service.md), using the packaged command shown there.
Secrets are sops-encrypted in Git or held in restrictive local files under
`/opt/skynet-ops/secrets/`; plaintext never enters Git, reports, transcripts, or chat.
