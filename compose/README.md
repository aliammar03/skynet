---
summary: "The compose/ service catalog and the skynet deploy loop every project follows."
---

# compose — one dir per service, `skynet deploy` applies each

```
compose/<service>/
├── compose.yaml   # pinned image DIGESTS; env_file: .env; STRUCTURAL only
├── .env.git       # NON-secret config, committed plaintext
└── .env.sops      # secrets ONLY, sops+age (keys visible in diffs, values encrypted)
```

**The canonical "skynet way" for every service** (the standard this repo enforces):
digest-pinned images · `env_file: .env` · non-secret config in committed `.env.git` ·
secrets only in `.env.sops` · **a healthcheck on every service** (below) · deployed by
`skynet deploy` once merged. No inline compose config, no file-based `.txt` docker secrets. See
`runbooks/deploy-service.md` and `docs/design/gitops-loop.md`.

### Healthchecks — one per service

Every service **must** report health (so `skynet deploy` can verify it and dependents can wait on
`condition: service_healthy`). Either the image ships a built-in `HEALTHCHECK` (e.g. aiostreams,
karakeep-web) or the compose declares one. Prefer a real endpoint probe; fall back to a TCP
port-open when the image lacks an HTTP client. Use whatever tool the image actually has:

| image has | pattern |
|---|---|
| `curl` | `["CMD","curl","-fsS","-o","/dev/null","http://localhost:<port>/health"]` |
| busybox `wget` | `["CMD","wget","-q","-O","/dev/null","http://127.0.0.1:<port>/…"]` (use `127.0.0.1`) |
| `node` only | `["CMD","node","-e","require('http').get('http://127.0.0.1:<port>/',r=>process.exit(r.statusCode<500?0:1)).on('error',()=>process.exit(1))"]` |
| `bash` only | `["CMD","bash","-c","exec 3<>/dev/tcp/127.0.0.1/<port>"]` (TCP port-open) |

Standard timing: `interval: 30s, timeout: 10s, retries: 3, start_period: 10–30s`.
A container without a healthcheck fails deployment verification, and the deploy rolls back.

### Volume standard — the decision (apply to EVERY mount a service needs)

| the data is… | → type | host name | label |
|---|---|---|---|
| a **standalone DB-engine** container's storage — mongo, postgres, standalone redis, **meilisearch**, typesense, elasticsearch… | **named volume** | `<role>` (docker-managed; compose prefixes `<svc>_`) | **required** — see labels below |
| **everything else** — app data, configs, uploads, media, an app's **embedded SQLite** | **bind mount** | `/opt/docker/appdata/<svc>/<role>` | none (located by path; in the restic appdata sweep) |
| a **repo-tracked** config/code file (init scripts, patches) | relative mount | `./…:…:ro` (GitOps-synced) | none |

Rules that make it unambiguous:
- `<svc>` = the compose dir name (lowercase). `<role>` = a short purpose noun: `data`, `config`,
  `index`, `db`, `plugins`… **Every bind mount gets a `<role>` subdir even if the service has only
  one** (so `…/calibre/config`, never `…/calibre`). Don't repeat `<svc>` in `<role>`
  (`…/marinara/data`, not `…/marinara/marinara-data`).
- Switching a named volume ↔ bind mount: remove the orphan (`docker volume rm <svc>_<role>`, or
  `rm -rf` the stale appdata dir) so restic doesn't grab dead data.

### Role tag — one `x-arcane` tag per service

Every service declares **exactly one role tag** in its compose — its category, read by review and
inventory. (Arcane applied these on Git Sync; with its sync off it no longer does.)

```yaml
x-arcane:
  tags:
    - name: media       # the role
      color: purple
```

Role → colour (keep it consistent so a colour always means the same role):

| role | colour | examples |
|---|---|---|
| `media` | purple | aiostreams, aiometadata |
| `ai` | blue | marinara, silly |
| `books` | green | calibre |
| `bookmarks` | orange | karakeep |

One role per service (it's a *category*, not a severity — no `critical`/`important` tags). New
roles are fine; give each its own stable colour.

### Volume labels — the `skynet.*` namespace

**Every named volume carries all three:**

| label | values | meaning / who reads it |
|---|---|---|
| `skynet.service` | the service name | groups a volume to its service (`docker volume ls --filter label=skynet.service=<svc>`). Organizational today; A4 restore tooling will use it. |
| `skynet.backup` | `protect` \| `ephemeral` | **the backup intent** — `protect` = source of truth, `backup-restic.sh` pulls it into the backup; `ephemeral` = cache/index/regenerable, skipped. |
| `skynet.managed` | `gitops` | marks the volume as owned by this repo's GitOps flow (vs a hand-made stray). |

Reads like a sentence: *skynet: protect this, it's aiometadata's, managed by gitops.*
Bind mounts need no labels (found by their `/opt/docker/appdata/<svc>/…` path). The vocabulary is
open to extend later (`skynet.backup: snapshot`, a `skynet.tier` for retention) without breaking
`protect`/`ephemeral`.

## How env reaches a container

`skynet deploy` renders the service on vm-skynet-ops: `.env.git` + `sops -d .env.sops` become a
`0600` `.env` in a tmpfs directory, and Compose resolves the project (env inlined) to JSON that
reaches the Docker host only on the deploy command's stdin. Every service still declares
`env_file: .env` so those values reach it. No `.env` file exists on the Docker host.

Redeploying an older revision (`skynet deploy <svc> --revision <merged-commit>`) brings its env
with it; the verified revision is also what an automatic rollback returns to.
