---
summary: "The Compose service catalog and immutable Skynet generation deployment loop."
---

# compose — one dir per service, deployed as immutable Skynet generations

```
compose/<service>/
├── compose.yaml   # pinned image DIGESTS; env_file: .env; complete generation input
├── .env.git       # NON-secret config, committed plaintext — non-secret revision input
└── .env.sops      # secrets ONLY, sops+age (keys visible in diffs, values encrypted)
```

**The canonical "skynet way" for every service** (the standard this repo enforces):
digest-pinned images · `env_file: .env` · non-secret config in committed `.env.git` ·
secrets only in `.env.sops` · **a healthcheck on every service** (below) · deployed by direct Docker Compose from an immutable Git-revision generation. No inline compose config, no file-based `.txt` docker secrets. Deploy
with `skynet deploy service <svc>` — see `runbooks/deploy-service.md` for the exact source,
environment, and runtime contract (Arcane does not own the generation).

### Healthchecks — one per service

Every service **must** report health (so Docker shows `(healthy)` and dependents can wait on
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
`skynet deploy service` treats a missing health status as a failed runtime observation; it does not
turn successful Compose application into a health claim.

### Volume standard — the decision (apply to EVERY mount a service needs)

| the data is… | → type | host name | label |
|---|---|---|---|
| a **standalone DB-engine** container's storage — mongo, postgres, standalone redis, **meilisearch**, typesense, elasticsearch… | **named volume** | `<role>` (docker-managed; compose prefixes `<svc>_`) | **required** — see labels below |
| **everything else** — app data, configs, uploads, media, an app's **embedded SQLite** | **bind mount** | `/opt/docker/appdata/<svc>/<role>` | none (located by path; in the restic appdata sweep) |
| a **repo-tracked** config/code file (init scripts, patches) | relative mount | `./…:…:ro` (generation-contained) | none |

Rules that make it unambiguous:
- `<svc>` = the compose dir name (lowercase). `<role>` = a short purpose noun: `data`, `config`,
  `index`, `db`, `plugins`… **Every bind mount gets a `<role>` subdir even if the service has only
  one** (so `…/calibre/config`, never `…/calibre`). Don't repeat `<svc>` in `<role>`
  (`…/marinara/data`, not `…/marinara/marinara-data`).
- Switching a named volume ↔ bind mount: remove the orphan (`docker volume rm <svc>_<role>`, or
  `rm -rf` the stale appdata dir) so restic doesn't grab dead data.

### Role tag — one `x-arcane` tag per service

Every service declares **exactly one role tag** in its compose so Arcane can group the fleet at a
glance. This is Compose metadata, not a release or Git tag; deployment does not create tags.

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
roles are fine; give each its own stable colour. The packaged deployment command does not report or
create role/release tags; the declaration remains reviewable in the Compose revision.

### Volume labels — the `skynet.*` namespace

**Every named volume carries all three:**

| label | values | meaning / who reads it |
|---|---|---|
| `skynet.service` | the service name | groups a volume to its service (`docker volume ls --filter label=skynet.service=<svc>`). Organizational today; A4 restore tooling will use it. |
| `skynet.backup` | `protect` \| `ephemeral` | **the backup intent** — `protect` = source of truth, `backup-restic.sh` pulls it into the backup; `ephemeral` = cache/index/regenerable, skipped. |
| `skynet.managed` | `gitops` | retained label for repo-authored service ownership; Arcane does not own deployment. |

Reads like a sentence: *skynet: protect this, it's aiometadata's, managed by gitops.*
Bind mounts need no labels (found by their `/opt/docker/appdata/<svc>/…` path). The vocabulary is
open to extend later (`skynet.backup: snapshot`, a `skynet.tier` for retention) without breaking
`protect`/`ephemeral`.

## How env reaches a container (Skynet generation)

`skynet deploy prepare <svc>` selects one exact full local branch-head Git revision and copies the
complete committed `compose/<svc>/` runtime subtree, including relative config/code files, into a
protected remote staging generation. It constructs effective `.env` = `.env.git` + locally decrypted
`.env.sops` in memory and streams plaintext only through bounded SSH stdin. No local plaintext
file, argv, report, retained subprocess output, or plaintext hash is made. The selected published
generation retains `.env` at mode `0600`; Compose validation runs against that generation before it
becomes prepared. Dirty or untracked checkout bytes are never selected.

`skynet deploy service <svc>` activates the immutable generation through direct Docker Compose as
`svc-ops`, with a stable project name and the selected directory as Compose working location.
A per-service host lock and Docker generation-label reconciliation precede mutation. Independent
complete health and DMZ route/TLS verification must pass before `stable` promotion. A failed
candidate may be active while the previous stable remains the explicit rollback candidate. An
existing Arcane Git Sync with `autoSync=true` is a pre-write refusal; disable and drain its scheduled
writes while old source/environment agree and verify the old live revision before first takeover.
Arcane may display the externally managed project as UI observation but does not sync or redeploy it.

`skynet deploy status <svc>` is report-only. `skynet rollback service <svc> [--to <full-revision>]`
reports the retained candidate; `--apply` explicitly reactivates and verifies it without editing
Git. Correct authored source separately through a reviewed PR. The old `scripts/gitops-deploy.sh`
and `scripts/gitops-rollback.sh` names are thin forwarders until P22.
