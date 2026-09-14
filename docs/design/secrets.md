---
summary: "How Skynet holds secrets with sops+age and safely materializes GitOps service environments."
---

# Spoke · Secrets

> How Skynet keeps secret values encrypted in Git and delivers a service environment to the exact
> Arcane project. Governed by [`../system-design.md`](../system-design.md).

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

## GitOps service environment

Each service's reproducible environment has two repository inputs:

- **`.env.git`** — committed non-secret defaults.
- **`.env.sops`** — secret assignments encrypted to the lab age recipient; optional when no secrets
  are needed.

The effective `.env` is not Arcane's `project.env` layer. `skynet deploy service` reads the two
inputs from the selected checkout, runs `sops -d --input-type dotenv --output-type dotenv` on
vm-skynet-ops with `SOPS_AGE_KEY_FILE`, and concatenates the bounded output in memory. Plaintext is
sent to the off-host project only through the SSH command's stdin; it is never placed in a local
temporary file, command argument, log, or JSON outcome. The age key stays on vm-skynet-ops.

The remote writer is constrained to the exact Arcane project path
`/opt/docker/arcane-projects/<service>`. It verifies the path's numeric owner, uses a pinned BusyBox
image to create a same-directory temporary file, applies that owner, sets mode `0600`, and atomically
renames it to `.env`. A non-regular source, symlink, path mismatch, malformed owner, or failed
stream leaves the operation failed/ambiguous for inspection; it is never reported as a successful
environment replacement.

Every service declares `env_file: .env` so Docker Compose consumes this materialized file. Arcane
owns Git Sync and project lifecycle; the packaged deployment owner owns environment materialization.
The retained [`gitops-deploy.sh`](../../scripts/gitops-deploy.sh) name is a temporary compatibility
forwarder to `skynet deploy service` for P22 removal, not a second secret path.

## Operations

Deploy or restore with [`deploy-service.md`](../../runbooks/deploy-service.md) and
[`restore-service.md`](../../runbooks/restore-service.md), using the packaged command shown there.
Secrets are sops-encrypted in Git or held in restrictive local files under
`/opt/skynet-ops/secrets/`; plaintext never enters Git, reports, transcripts, or chat.
