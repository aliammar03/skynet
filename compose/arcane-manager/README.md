# arcane-manager — the Arcane GitOps controller

This is **Arcane itself** — the tool that watches this repo's `compose/` and reconciles every *other*
project onto the docker hosts (the deployment loop in AGENTS.md §4). It is captured here as a
declared, rebuildable component rather than an undocumented host-local service.

## Two things make it different from every other project here

1. **It is a bootstrap component — NOT reconciled by its own Git Sync.** A controller that
   git-reconciles itself would restart mid-reconcile on its own updates. So it is deployed and
   updated **by hand** (break-glass), and this directory is its source of truth, not a sync target.
   Do not add it as an Arcane project.
2. **It runs on the managed host.** Arcane runs inside `guest/docker-dmz-10015` (VLAN 100) and
   manages that host through a local `docker.sock`. Its host, socket mount, and port binding define
   its current deployment boundary.

## Env layering (same as every project; assembled manually because it is not synced)

Effective `.env` = `.env.git` (committed, non-secret) + decrypt(`.env.sops`) (JWT_SECRET,
ENCRYPTION_KEY). At deploy time on the host:

```
cat .env.git > .env
sops -d .env.sops >> .env        # needs the age key at /opt/skynet-ops/secrets/age.key
docker compose up -d
```

`ENCRYPTION_KEY` is load-bearing: it encrypts Arcane's stored state under `/app/data`. Keep the
sops copy authoritative so a rebuild preserves stored credentials.

## Not captured on purpose

The runtime's GPU-library defaults (`NVIDIA_*`, `ROCR_*`, `HIP_*`, `ONEAPI_*`, and
`LD_LIBRARY_PATH`) are image configuration, not Arcane configuration, and are excluded here.
