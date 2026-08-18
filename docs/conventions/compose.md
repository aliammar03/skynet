---
summary: "The single 'skynet way' every service's compose conforms to, so the fleet is uniform and Arcane's GitOps loop can own it."
tokens: 1085
---

# Spoke · Compose & the "skynet way" for services

> The single standard every service conforms to, so the whole fleet looks identical and Arcane's
> GitOps loop can own it. Governed by [`../conventions.md`](../conventions.md).

This spoke is the **canonical rule statement**. The co-located [`compose/README.md`](../../compose/README.md)
carries the worked reference — healthcheck probe table per image, exact label semantics, the env
materialisation walkthrough — and stays in sync with the rules here; when they disagree, this
spoke wins.

Tags: **[testable]** = a lint gate could assert it; **[manual]** = holds by review.

## Directory layout (one dir per service)

```
compose/<svc>/
├── compose.yaml   # pinned image DIGESTS; env_file: .env; STRUCTURAL only
├── .env.git       # NON-secret config, committed plaintext (Arcane's git layer)
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
  compose-declared one, so Arcane reports `(healthy)` and dependents can wait on
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
| a **repo-tracked** config/code file | relative mount | `./…:…:ro` (GitOps-synced) | none |

- **Every bind mount gets a `<role>` subdir**, even single-volume services `[manual]`
  (`…/calibre/config`, never `…/calibre`). Don't repeat `<svc>` in `<role>`.
- **Every named volume carries all three `skynet.*` labels** `[testable]`:
  `skynet.service=<svc>`, `skynet.backup=protect|ephemeral`, `skynet.managed=gitops`. Reads as a
  sentence: *protect this, it's `<svc>`'s, managed by gitops.* Bind mounts need no labels.

## Env layering & secrets

- **`.env.git`** = non-secret defaults, committed plaintext (Arcane's git layer).
- **`.env.sops`** = secrets only, sops+age — keys visible in diffs, values encrypted `[testable]`.
- **Secrets never appear in `.env.git`, `compose.yaml`, or plaintext `.env`/`project.env`**
  `[testable]` (pre-commit `secret-scan.sh` enforces).
- `scripts/gitops-deploy.sh` **materialises** the effective `.env` = `.env.git` + `sops -d
  .env.sops`, written `0600`, decrypted on-host (the age key never leaves the ops VM). Full flow:
  `compose/README.md` and [`../design/secrets.md`](../design/secrets.md).

## The loop

- **One Arcane Git Sync per project dir; auto-sync on; Arcane auto-update off** for git-synced
  projects `[manual]`. Deploy via `scripts/gitops-deploy.sh <svc>`; rollback is `git revert`. See
  [`../design/gitops-loop.md`](../design/gitops-loop.md) and `runbooks/deploy-service.md`.
