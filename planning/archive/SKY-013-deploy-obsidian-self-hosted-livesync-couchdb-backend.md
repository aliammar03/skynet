---
id: SKY-013
title: Deploy Obsidian Self-hosted LiveSync (CouchDB backend)
status: done
horizon: short
created: 2026-08-18
updated: 2026-08-19
phases: 2
current_phase: 2
tier_touched: [T2]    # new service on the existing DMZ docker host, inside the current
                      # blast radius. No trust boundary moves → no system-design.md PR.
related:
  - compose/obsidian-livesync/
  - compose/caddy-apps/Caddyfile
  - runbooks/deploy-service.md
  - runbooks/publish-service.md
  - docs/design/gitops-loop.md
  - "[[SKY-013-progress]]"
---

# SKY-013 · Deploy Obsidian Self-hosted LiveSync (CouchDB backend)

> Stand up a CouchDB sync hub the skynet way and publish it at `obsidian.aliammar.net`, so the
> Obsidian Self-hosted LiveSync plugin gives live, multi-device, end-to-end-encrypted vault sync.
> First real end-to-end test of Skynet's deploy → publish loop on a *stateful* service.

## 1. Problem / motivation

Ali wants live Obsidian vault sync across devices and bounced off it years ago. The wall was never
CouchDB itself — it was the surround: no trusted TLS (LiveSync misbehaves over self-signed / raw
`IP:port`), CORS not set, and the CouchDB tuning knobs (`require_valid_user`, `single_node`, chunk
sizes) undocumented and hand-applied, so nothing was reproducible.

Skynet erases exactly those failures:

- **Trusted TLS + real hostname** — the apps-Caddy front door issues a publicly-trusted cert for
  `*.aliammar.net` (ACME DNS-01 over Cloudflare), zero device-trust install. `obsidian.aliammar.net`
  just works on every device.
- **Config as reviewed git** — the CORS + tuning live in a repo-tracked `local.ini`, not a mystery.
- **Reproducible + backed up** — digest-pinned image, password in `.env.sops`, and the notes volume
  labelled `skynet.backup: protect` so restic sweeps it automatically.

## 2. Approach — what we're building

A single-service CouchDB deployment following the standard in
[`runbooks/deploy-service.md`](../../runbooks/deploy-service.md), published via
[`runbooks/publish-service.md`](../../runbooks/publish-service.md):

- **Backend: CouchDB 3.x** — the mature LiveSync remote; true continuous multi-device replication
  with revision-based conflict handling. (Backend choice is the one open call — see §6; flipping to
  the S3/object-storage remote would rewrite Phase 1 only and cost us a MinIO stand-up.)
- **Placement:** `vm-docker-dmz`, new DMZ IP **`10.10.100.95`**, port **5984**.
- **Storage:** CouchDB is a standalone DB engine → one **named volume** `data` (its `/opt/couchdb/data`),
  labelled `skynet.service: obsidian-livesync` + `skynet.backup: protect` + `skynet.managed: gitops`.
- **Config:** repo-tracked `local.ini` → relative `:ro` mount at
  `/opt/couchdb/etc/local.d/local.ini` (CouchDB's supported drop-in dir; it writes its own runtime
  config elsewhere, so `:ro` is safe). This carries the CORS + LiveSync tuning (§ Phase 1).
- **Auth:** CouchDB's own admin login (`COUCHDB_USER` in `.env.git`, `COUCHDB_PASSWORD` in
  `.env.sops`) → this is a **real login**, so the front door is **own-auth path A** (plain
  `reverse_proxy`, no Authentik).
- **Role tag:** a new **`notes`** role, colour **teal** (free — purple/blue/green/orange/red taken).
- **Client:** the Obsidian **Self-hosted LiveSync** plugin, end-to-end encryption on (passphrase),
  pointed at `https://obsidian.aliammar.net`.

**Non-goals:** no MinIO/S3 backend; no Authentik forward-auth (CouchDB self-gates); no public
internet exposure (internal ingress only, same as every other app); no multi-node CouchDB cluster
(`single_node = true`).

## 3. The plan

- **Scope / non-goals:** as §2. Two phases: (1) the CouchDB backend healthy on the DMZ; (2) publish
  through Caddy + bring up the Obsidian client and prove sync + backup.
- **Hosts & tiers touched:** `vm-docker-dmz` (T2, via Arcane GitOps + `svc-ops`), apps-Caddy (T2),
  Technitium wildcard already resolves `*.aliammar.net`. **No T2+/T3, no `system-design.md` PR.**
- **Rollback posture:** `git revert` the compose / Caddyfile PR → `gitops-deploy.sh` reconciles the
  old state back. The `data` volume persists across redeploys; a full teardown is
  `down` + `docker volume rm obsidian-livesync_data` (destroys the sync hub — devices still hold the
  vault and can re-seed a fresh DB).
- **Grants / human actions:** none beyond the standing T2 path. Every phase's only human step is
  **Ali merges the PR** (the agent never merges its own).

### Phase 1 — CouchDB backend, the skynet way  (~1–2h)   `[x]` done

Steps:
1. **Branch** `deploy/obsidian-livesync`. Create `compose/obsidian-livesync/`:
   - `compose.yaml` — one `couchdb` service, **digest-pinned** `couchdb:3.x` (resolve the current
     digest when writing it), `restart: unless-stopped`, `env_file: [.env]`, `x-arcane` tag
     `notes`/teal, on the `dmz` network at `10.10.100.95`, mounts:
     - named volume `data:/opt/couchdb/data` (+ the three `skynet.*` labels, `backup: protect`),
     - `./local.ini:/opt/couchdb/etc/local.d/local.ini:ro`.
   - **Healthcheck** against CouchDB's `/_up` endpoint. ⚠ the `couchdb` image ships **without curl** —
     verify the available tool in-container and use it: prefer `curl -fsS .../_up` if present, else a
     bash `/dev/tcp` TCP-open on 5984 (see the compose README healthcheck table). Confirm which, don't
     assume.
   - `.env.git` — `COUCHDB_USER=<admin>` (non-secret).
   - `.env.sops` — `COUCHDB_PASSWORD=<generated>` (sops+age; never plaintext in the PR).
   - `local.ini` — the LiveSync-recommended config (reviewed once, teaches the actual fix):
     ```ini
     [couchdb]
     single_node = true
     max_document_size = 50000000

     [chttpd]
     require_valid_user = true
     max_http_request_size = 4294967296

     [chttpd_auth]
     require_valid_user = true

     [httpd]
     WWW-Authenticate = Basic realm="couchdb"
     enable_cors = true

     [cors]
     origins = app://obsidian.md,capacitor://localhost,http://localhost
     credentials = true
     headers = accept, authorization, content-type, origin, referer
     methods = GET, PUT, POST, HEAD, DELETE
     max_age = 3600
     ```
     (Admin comes from the `COUCHDB_USER`/`_PASSWORD` env, not `[admins]` here.)
2. **Validate:** `cd compose/obsidian-livesync && printf 'COUCHDB_USER=x\nCOUCHDB_PASSWORD=y\n' > .env && docker compose config -q && rm .env`.
3. **PR** with a teaching description (what LiveSync is, CouchDB's role, the `local.ini` tuning and
   why, port 5984, the `protect` volume = your notes). **⚠ Ali merges.**
4. `scripts/gitops-deploy.sh obsidian-livesync` — materialises `.env`, deploys, health-checks.
5. **Verify** CouchDB is up and configured: from a DMZ peer, `curl` the admin API and confirm
   `GET /_up` → `{"status":"ok"}`, `GET /_membership` shows a single node, and the `[cors]` /
   `require_valid_user` settings are live (`GET /_node/_local/_config/cors` etc.). Create the vault
   database (e.g. `PUT /obsidiannotes`).

Exit criteria: `obsidian-livesync` shows **(healthy)** in Arcane, the tuned config is confirmed live,
the vault DB exists, and refreshed inventory is committed.
Grants / human actions: **⚠ Ali merges the PR** — no grant needed.

### Phase 2 — Publish through the front door + client bring-up  (~1–2h)   `[x]` done

Steps:
1. **Branch** `deploy/caddy-apps`. Add to `compose/caddy-apps/Caddyfile` under OWN-AUTH:
   ```
   # obsidian-livesync — CouchDB, gated by its own admin login.
   obsidian.aliammar.net {
       reverse_proxy 10.10.100.95:5984
   }
   ```
2. **Validate** the Caddyfile (the `caddy validate` container run from `publish-service.md`), **PR**
   with a teaching description, **⚠ Ali merges**, then `scripts/gitops-deploy.sh caddy-apps` (or let
   Caddy `--watch` reload).
3. **Verify** from a peer **DMZ container** (the apps-Caddy is unreachable from the ops VM):
   `curl -sSI --resolve obsidian.aliammar.net:443:10.10.100.35 https://obsidian.aliammar.net/_up`
   → expect a real status + valid public cert (`ssl_verify_result=0`); first hit may TLS-fail ~15–30s
   while ACME issues, retry.
4. **Obsidian client:** install the **Self-hosted LiveSync** community plugin; configure the remote
   DB → URI `https://obsidian.aliammar.net`, database `obsidiannotes`, the admin user/pass; enable
   **End-to-End Encryption** with a passphrase (stored in Ali's password manager, never in git). Run
   the plugin's **"Check database configuration"** — it green-lights the CORS/tuning we set, or names
   what's missing. Do the initial vault upload.
5. **Prove it:** sync a second device (or a second vault), confirm an edit propagates live both ways.
   Confirm restic sweeps the `data` volume (it's `protect`) on the next backup run.

Exit criteria: `obsidian.aliammar.net` serves a valid cert and LiveSync's config check passes; a real
edit round-trips between two devices; the `data` volume is confirmed in the restic backup set.
Grants / human actions: **⚠ Ali merges the PR**; Ali installs/configures the plugin and holds the E2EE
passphrase. No grant needed.

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive. Swap `<N>` for the phase to run.
```
Read planning/projects/SKY-013-deploy-obsidian-self-hosted-livesync-couchdb-backend.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
Run this every time a phase finishes successfully — it's what makes the next session cold-startable:
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-013-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-013-deploy-obsidian-self-hosted-livesync-couchdb-backend.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-013-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
*(One dated line per milestone — cite PR numbers; convert relative dates to absolute. Newest last.)*
- 2026-08-18 — created; started into projects/. Backend = CouchDB (recommended); S3/object-storage
  remote considered and set aside (would require a MinIO stand-up; less-proven live sync). Backend is
  the one still-open decision — flipping it rewrites Phase 1 only.
- 2026-08-18 — Phase 1: CouchDB backend built + deployed (PR #62). First deploy went healthy but the
  Arcane GitOps sync FAILED — the `:rw` `local.ini` mount let couchdb's root entrypoint chown the HOST
  git file to uid 5984, blocking Arcane (uid 1000) from promoting it. Fixed (PR #63): mount `local.ini`
  `:ro` at a neutral path outside `/opt/couchdb` + entrypoint copies it into `local.d/`. Host file stays
  1000:1000, sync green. (Two-layer couchdb-chown gotcha logged in [[SKY-013-progress]].)
- 2026-08-19 — Phase 2: published at `obsidian.aliammar.net` (PR #64). Verified from a DMZ peer:
  `/_up` → 200 with a valid **Let's Encrypt** cert (chains to ISRG Root), root without creds → 401
  (CouchDB self-gates through Caddy). Obsidian Self-hosted LiveSync client configured (E2EE on,
  enhanced chunks, no storage-cap warning — self-hosted); first-device overwrite seeded the empty
  remote, second device fetched, and a live edit round-trips **both ways**. `data` volume carries
  `skynet.backup=protect` and is matched by `backup-restic.sh` — swept on the next restic run.
  **Directive complete.** The years-old wall (self-signed TLS + hand-applied CORS/tuning) is gone —
  every knob is now reviewed git.
