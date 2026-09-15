---
summary: "The single 'skynet way' every service's compose conforms to, so the fleet is uniform and Skynet generations can deploy it."
---

# Spoke · Compose & the "skynet way" for services

> The standard every service conforms to so Skynet generations can deploy it uniformly. Governed by
> [`../conventions.md`](../conventions.md).

This spoke is the **canonical rule statement**. The co-located [`compose/README.md`](../../compose/README.md)
carries the worked reference — healthcheck probe table per image, exact label semantics, the env
materialisation walkthrough — and stays in sync with the rules here; when they disagree, this
spoke wins.

Tags: **[testable]** = a lint gate could assert it; **[manual]** = holds by review.

## Directory layout (one dir per service)

```
compose/<svc>/
├── compose.yaml   # pinned image DIGESTS; env_file: .env; STRUCTURAL only
├── .env.git       # NON-secret committed defaults
└── .env.sops      # secrets ONLY, sops+age; omit if the service has none
```

- **`compose.yaml` present** in every service dir `[testable]`.
- **`.env.git` present** (may be minimal) `[testable]`; **`.env.sops` present iff the service has
  secrets** `[manual]`.

## compose.yaml rules

- **Digest-pinned images, never a floating tag** `[testable]`:
  `image: repo/name:vX.Y@sha256:…`. No `:latest` without a digest. Renovate bumps by PR.
- **Every service declares `env_file: .env`** `[testable]` so the materialised effective env
  reaches it.
- **No inline `environment:` config** `[manual]` — config lives in `.env.git`, not scattered in
  compose. Exception: a structural key that interpolates a secret (e.g. a computed `REDIS_URL`).
- **A healthcheck on every service** `[testable]` — image built-in `HEALTHCHECK` or a
  compose-declared one, so Docker reports `(healthy)` and dependents can wait on
  `condition: service_healthy`. Match the probe to the image's tools; standard timing
  `interval: 30s, timeout: 10s, retries: 3, start_period: 10–30s`. See the probe table in
  `compose/README.md`.
- **Exactly one role tag** via `x-arcane.tags` `[testable]` — a *category* (`media`/`ai`/`books`/
  `bookmarks`/…), one per service, with a **stable colour per role** (purple=media, blue=ai,
  green=books, orange=bookmarks). Not a severity; no `critical`/`important`. New roles are fine —
  give each its own stable colour.

## Volumes — the decision table

| the data is… | → type | host name / path | label |
|---|---|---|---|
| a **standalone DB-engine** container's storage (mongo, postgres, redis, meilisearch, …) | **named volume** | `<role>` (compose prefixes `<svc>_`) | **required** (below) |
| **everything else** (app data, configs, uploads, media, embedded SQLite) | **bind mount** | `/opt/docker/appdata/<svc>/<role>` | none (found by path) |
| a **repo-tracked** config/code file | relative mount | `./…:…:ro` (generation-contained) | none |

- **Every bind mount gets a `<role>` subdir**, even single-volume services `[manual]`
  (`…/calibre/config`, never `…/calibre`). Don't repeat `<svc>` in `<role>`.
- **Every named volume carries all three `skynet.*` labels** `[testable]`:
  `skynet.service=<svc>`, `skynet.backup=protect|ephemeral`, `skynet.managed=gitops`. The retained
  `gitops` label means repo-authored service ownership; it does not grant Arcane sync authority.
  Bind mounts need no labels.

## Env layering & secrets

- **`.env.git`** = non-secret defaults, committed plaintext (committed non-secret input).
- **`.env.sops`** = secrets only, sops+age — keys visible in diffs, values encrypted `[testable]`.
- **Secrets never appear in `.env.git`, `compose.yaml`, or plaintext `.env`/`project.env`**
  `[testable]` (pre-commit `secret-scan.sh` enforces).
- `skynet deploy prepare <svc>` reads only Git objects at an exact full local branch-head revision,
  stages the complete runtime subtree remotely, materialises effective `.env` from `.env.git` plus
  decrypted `.env.sops` in local memory, and streams plaintext through bounded SSH stdin only. The
  selected immutable generation alone retains `.env`, mode `0600`, inside the protected state tree.
  Neither a local temporary plaintext file, argv, output, report, commit, nor plaintext hash is made.
  `skynet deploy service <svc>` activates that exact generation and promotes it only after complete
  independent verification. See `compose/README.md` and [`../design/secrets.md`](../design/secrets.md).

## The loop

- **One deployment owner per service** `[manual]`: Skynet's packaged synchronous generation path uses
  the standing `svc-ops` Docker-host T2 capability, a per-service `flock`, direct Compose with a
  stable project name, Docker generation labels, complete health/route verification, and atomic stable
  promotion. Arcane remains UI/observation; an existing Git Sync with `autoSync=true` is a pre-write
  refusal. Disable and drain legacy scheduling while old source/environment agree and verify the old
  live revision before first takeover. Do not delete disabled sync metadata by guesswork. Roll back
  only on explicit `skynet rollback service <svc> [--to <full-revision>] --apply`; authored Git
  correction goes through a normal reviewed PR. The shell names are forwarders until P22. See
  [`../design/gitops-loop.md`](../design/gitops-loop.md) and
  [`../../runbooks/deploy-service.md`](../../runbooks/deploy-service.md).
