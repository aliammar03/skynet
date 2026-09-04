---
summary: "The compose/ service catalog and the Arcane GitOps deployment loop every project follows."
---

# compose — one dir per service, Arcane git-syncs each

```
compose/<service>/
├── compose.yaml   # pinned image DIGESTS; env_file: .env; Arcane makes this read-only in its UI
├── .env.git       # NON-secret config, committed plaintext — Arcane's git layer
└── .env.sops      # secrets ONLY, sops+age (keys visible in diffs, values encrypted)
```

**The canonical "skynet way" for every service** (the standard this repo enforces):
digest-pinned images · `env_file: .env` · non-secret config in committed `.env.git` ·
secrets only in `.env.sops` · **a healthcheck on every service** (below) · deployed via Arcane
GitOps Sync from this repo. No inline compose config, no file-based `.txt` docker secrets. Deploy
with `scripts/gitops-deploy.sh <svc>` — see `runbooks/deploy-service.md` for how the effective
`.env` is materialised (Arcane GitOps does not merge `.env.git`/`project.env`).

### Healthchecks — one per service

Every service **must** report health (so Arcane shows `(healthy)` and dependents can wait on
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
`gitops-deploy.sh` warns after every deploy if any service has no health status.

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

Every service declares **exactly one role tag** in its compose so Arcane's UI groups the fleet
at a glance (Arcane applies `x-arcane.tags` automatically on GitOps sync — `sources: [compose]`):

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
roles are fine; give each its own stable colour. `scripts/gitops-deploy.sh` reports the applied
tag after every deploy and warns if a service is untagged.

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

## How env reaches a container (Arcane GitOps)

Arcane's GitOps sync copies `compose.yaml` (and the compose dir, incl. subdirs) and owns the
project lifecycle, but it does **not** merge `.env.git`/`project.env` into `.env` — that layering
only applies to Arcane's *non-GitOps* projects. A GitOps project just runs `docker compose`
against whatever `.env` is on disk.

So `scripts/gitops-deploy.sh` **materialises** the effective `.env` = `.env.git` +
`sops -d .env.sops`, written `0600` and owned by Arcane's project UID, decrypted on
vm-skynet-ops. Every service still declares `env_file: .env` so those values reach it. Arcane
leaves a populated `.env` untouched on re-sync; auto-sync only redeploys already-running projects
(a stopped one updates on next manual start).

Restore the selected `.env.git`/`.env.sops` revision with `scripts/gitops-deploy.sh <svc>`; the
wrapper rematerializes the effective file and redeploys it.
