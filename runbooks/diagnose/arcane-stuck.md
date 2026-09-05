---
summary: "Triage a merged compose PR that didn't deploy — check the Arcane Git Sync status/error, compare git vs running, distinguish sync-fail vs apply-fail vs drift."
trigger: "A merged compose PR didn't deploy / Arcane isn't reconciling / git and running have drifted"
---

# Diagnose — Arcane stuck (GitOps not reconciling)

**Trigger:** a `compose/` PR merged to `main` but the change never went live, or running state has
drifted from git.
**Tier:** **T1/T2** — reading Git Sync status is the **Arcane API key** (T2, scoped); comparing running
containers is unprivileged `svc-ops` docker (T1). The fix is a `compose/` PR; `ssh + docker context` is
break-glass **look**, not mutate. Reference: [[arcane-api-reference]], [gitops-loop](../../docs/design/gitops-loop.md).

> **Diagnose imperatively, fix declaratively.** Arcane *is* the declarative executor — the fix is almost
> always to make git correct and let it converge, never to `docker compose up` by hand. (SKY-005.)

## 1. Confirm — did the sync run, and did it error?

```bash
# Arcane GitOps sync status (X-API-Key auth; host vm-docker-dmz). See the api-reference memory.
curl -fsS -H "X-API-Key: $ARCANE_API_KEY" https://<arcane-host>/api/environments/0/gitops-syncs \
  | jq '.[] | {project, lastSync, status, error}'
```

Then compare **git** to **running**:

```bash
git log --oneline -3 origin/main -- compose/<svc>/     # is the change actually on main?
ssh svc-ops@<docker-host> docker inspect --format '{{.Config.Image}}' <svc>   # running image
grep -R image compose/<svc>/                            # pinned image in git
```

## 2. Branch on the mismatch

| Signal | Cause | Next |
|---|---|---|
| sync `error`: auth / pull failed | Arcane can't reach the repo | the Git Sync credential / network to GitHub |
| lastSync old / never | Git Sync paused, or wrong branch tracked | check the sync is enabled and tracks `main` |
| synced OK, image not applied | compose invalid, or image pull failed | `docker` events/logs on the host; the pin exists? |
| synced, container up, still wrong | **drift** — a manual change on the host | reconcile it back into `compose/` (it's an orphan) |
| env-dependent failure | wrapper materialization — `.env.git` + decrypted `.env.sops` → effective `.env` | [secrets](../../docs/design/secrets.md); did `gitops-deploy.sh` write it? |
| PR "merged" but not on `main` | merged to the wrong base / not merged | fix the merge; Arcane only tracks `main` |

## 3. Fix declaratively

Make **git** correct — fix the compose, the pin, or the env layer → branch → PR → Ali merges → Arcane
polls, pulls, reconciles (project stays read-only in the UI). Verify health via the Arcane API /
`docker context`, then commit refreshed inventory. Rollback is `git revert`; Arcane converges back.
Only if Arcane itself is down is `ssh svc-ops@<host>` + `docker context` the break-glass path — and even
then, reconcile any imperative change back into git the same session.

## 4. Record

`bin/new journal incident "<svc> Arcane stuck — <sync-fail|apply-fail|drift>"` — the sync error or the
git-vs-running mismatch, and the PR that reconciled it. ([journal](../../journal/README.md).)
