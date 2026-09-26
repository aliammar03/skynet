---
date: 2026-09-26
time: 20:07:17            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P13 deploy cutover
tier_touched: [T1, T2]  # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, ADR 0008, PR #268, vm-docker-dmz]
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-26 · session · SKY-025 P13 deploy cutover

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Built `skynet deploy` / `publish` / `withdraw` + `writepath.py` greenfield on branch
`phase/sky-025-p13-deploy` (did not reuse the unmerged `phase/sky-025-p11-deploy` prototype), then
cut docker-dmz over from Arcane Git Sync with Ali's §2 approval ("approve all steps").

Spike first (throwaway project `skynet-spike`, removed): `docker --context docker-dmz compose -p X
--project-directory /opt/docker/services/X/r1 -f - up --wait` with the resolved JSON on stdin works
from the ops VM — the client does not stat relative bind sources locally; the daemon mounted
`/opt/docker/services/X/r1/msg.txt`. `--wait` exits non-zero with "container … is unhealthy".
Release dir written by a pinned busybox over the same context (`/opt/docker/services` created as
root by the bind mount).

Render findings: `docker compose config --format json --no-path-resolution` inlines `env_file`
into `environment`, keeps `./` paths, and escapes `$` as `$$` (idempotent re-parse). With
`--no-path-resolution`, `env_file: .env` is resolved against the **process cwd**, not
`--project-directory` — first dry-run failed "compose render failed" until `cwd=project`.

## Actions & outcomes
- Arcane: PUT `autoSync:false` on all 10 syncs (librespeed was already false) → all false.
- Adopted in order librespeed, calibre, silly, marinara, karakeep, aiostreams, aiometadata,
  obsidian-livesync, cloudflared, caddy-apps → all `success`; cloudflared logged 4 registered
  tunnel connections after recreate; routed services re-verified after caddy-apps.
  Revisions: aiometadata 364f1bf, aiostreams/calibre/karakeep 9bfb658, caddy-apps f8072b3,
  cloudflared/obsidian-livesync 44ae7d3, librespeed bbf5c05, marinara 915335a, silly 009f3cb.
- `--pending` evaluated read-only: every service `noop`; `arcane-manager` showed DEPLOY → the
  manual-marker regex rejected the trailing `# comment` on `deploy: manual`. Fixed + test. A live
  `--pending` before merge would have tried to redeploy the Arcane controller (marker only on the
  branch), so the live `--pending` evidence waits for merge + Ali's ops-VM rebuild.
- Drill (`skynet-drill`, unmerged local revisions, only `merged()` overridden): A c45eb56 success →
  verified; B 5388a56 (healthcheck `false`) → execute failed "compose up failed" → rollback redeployed
  A (logs "release A", healthy) → outcome `rolled-back`, host `failed=5388a56…`.
- `open_revert_pr` demo → PR #268 (tree = verified `compose/skynet-drill/`) → closed, branch deleted.
- `skynet publish calibre` → success, 0 created, 302 → `https://auth.aliammar.net/application/o/authorize/`,
  public CNAME `present`. The probe first recorded the full redirect URL incl. the OAuth `state`
  JWT → trimmed to scheme/host/path in `deployment.probe`; scrubbed that one ledger line.
- Deleted the 10 service dirs under `/opt/docker/arcane-projects/` (0 `.env` left; Arcane's own
  `.env.global` kept), svc-ops `~/.local/state/skynet-deploy` (librespeed prototype), the drill
  project + its release dir.
- Final: `skynet verify deployment` → verified for all 10.
- Manual decrypt of a `.env.sops` to list key names was refused by the permission classifier
  (credential handling); decryption only ever ran inside `skynet deploy` (in memory/tmpfs).

## Graveyard — tried & abandoned
- `docker compose config` with `--project-directory` alone for env_file resolution → env_file is
  cwd-relative under `--no-path-resolution`; run with cwd = project dir instead.
- Compose `configs: content:` for Caddyfile/config.yml (no host files at all) → abandoned: needs
  compose rewrites and loses Caddy's file semantics; immutable per-revision release dirs instead.

## Follow-ups / open threads
- Operation record lives at `~/.local/state/skynet/operations.jsonl` until Ali rebuilds the ops VM
  (tmpfiles `/opt/skynet-ops/state`); then move the file and drop `--state-dir`.
- After merge: first `skynet-deploy` timer tick is the live `--pending` evidence; calibre and
  marinara redeploy once (this PR edits a comment in their dirs), arcane-manager must be skipped.
- Arcane still lists the 10 projects whose dirs are gone; its UI is dashboard-only now.
