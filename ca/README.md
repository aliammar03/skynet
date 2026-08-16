# 🔑 ca/ — public trust anchors (safe in git by design)

This folder holds **only public keys**. That's not an accident — it's the entire root-grant
security model. Everything secret is somewhere else, on purpose.

| File | What it is | Private half lives… |
|---|---|---|
| `skynet_ops_ca.pub` | The SSH **user-CA** public key — the trust anchor for auto-expiring root grants. Hosts trust it via `scripts/onboard-host.sh` (installed to `/etc/ssh/skynet_ops_ca.pub`). | **Only** on Ali's workstation (`~/.skynet-ca/ops_ca`) + the printed survival kit. |
| `skynet_ops_svc.pub` | The agent's own SSH public key — installed into the standing `svc-ops` user's `authorized_keys` for T2 access (inventory, docker contexts, envsync). | `0600` on skynet-ops (`~/.ssh/id_ed25519`). |

> ⚠️ **The CA private key never enters this repo, this host, or any transcript.** That's what
> makes root grants safe: the agent can *request* access, but it physically **cannot mint its
> own** — a human with the CA key has to sign a short-lived certificate. See
> [`../docs/design/access-and-trust.md`](../docs/design/access-and-trust.md) (the root-grant model) and
> [`../AGENTS.md`](../AGENTS.md) §1 for how the tiers use these keys.
