# 🧩 services — the onboarding catalog

scratchpad ▸ ideas ▸ backlog ▸ projects ▸ archive
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└─ **`services`** ─┘ *(feeds projects)*

**The "someday we'll self-host X" list** — the side track that feeds the main pipeline. Each
entry is a **SKY-###** sketch of a service to bring onto *the Skynet way*: what it is, why we'd
run it, image/compose notes, and its secrets / DNS / backup needs up front.

The bar for the Skynet way is set by the agent's `skynet-service-standard` memory and
[`docs/conventions.md`](../../docs/conventions.md): digest-pinned images, `env_file: .env`,
secrets in `.env.sops`, a healthcheck on every service, deployed via Arcane GitOps.

**→ Out:** when we commit to onboarding one, `bin/plan start SKY-###` turns the sketch into a
real [`../projects/`](../projects/) directive with the actual deployment phases.
