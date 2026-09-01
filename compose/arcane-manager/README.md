# arcane-manager — the Arcane GitOps controller

This is **Arcane itself** — the tool that watches this repo's `compose/` and reconciles every *other*
project onto the docker hosts (the deployment loop in AGENTS.md §4). It is captured here so it is a
**declared entity** (SKY-018) and **rebuildable from git** (AGENTS.md §6), not an undocumented
snowflake living only on the DMZ host.

## Two things make it different from every other project here

1. **It is a bootstrap component — NOT reconciled by its own Git Sync.** A controller that
   git-reconciles itself would restart mid-reconcile on its own updates. So it is deployed and
   updated **by hand** (break-glass), and this directory is its source of truth, not a sync target.
   Do not add it as an Arcane project.
2. **Relocation pending — [[SKY-019]].** Today it runs *inside* `guest/docker-dmz-10015` (VLAN 100,
   the DMZ) and manages that host through a local `docker.sock` — the management brain sitting in the
   least-trusted VLAN. SKY-019 moves it to a **dedicated Management (VLAN 50) docker VM** (cloned from
   the `9000` template), managing `docker-dmz` and any future docker host **remotely over unprivileged
   SSH**. When that lands, the `ports:` binding, the `docker.sock` mount, and this note all change.

## Env layering (same as every project; assembled manually because it is not synced)

Effective `.env` = `.env.git` (committed, non-secret) + decrypt(`.env.sops`) (JWT_SECRET,
ENCRYPTION_KEY). At deploy time on the host:

```
cat .env.git > .env
sops -d .env.sops >> .env        # needs the age key at /opt/skynet-ops/secrets/age.key
docker compose up -d
```

`ENCRYPTION_KEY` is load-bearing: it encrypts Arcane's stored state under `/app/data`. Losing it
means losing any credentials Arcane holds for remote environments — which is exactly what SKY-019
introduces, so keep the sops copy authoritative.

## Not captured on purpose

The live `arcane.env` also carried `NVIDIA_*` / `ROCR_*` / `HIP_*` / `ONEAPI_*` / `LD_LIBRARY_PATH` —
image-baked GPU/runtime defaults, not Arcane config. Excluded here; review at SKY-019.
