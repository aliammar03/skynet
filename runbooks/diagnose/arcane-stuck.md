---
summary: "Triage a merged compose PR that didn't deploy — check the Arcane Git Sync status/error, compare git vs running, distinguish sync-fail vs apply-fail vs drift."
trigger: "A merged compose PR didn't deploy / Arcane isn't reconciling / git and running have drifted"
tier: "T1/T2"
executor: "Arcane API and unprivileged Docker inspection"
rollback: "git revert the declarative fix"
---

# Diagnose — Arcane stuck (GitOps not reconciling)

**Tier:** **T1/T2** (scoped Arcane read and unprivileged container inspection). **Trigger:** a
`compose/` PR merged to `main` but the change never went live, or running state drifted from git.
Reference: [[arcane-api-reference]], [gitops-loop](../../docs/design/gitops-loop.md).

## Preconditions

- The change is expected on `main`; have the service name, Arcane API key, and scoped host read access.
- Treat `ssh + docker context` as break-glass inspection only; fixes go through a `compose/` PR.

## Steps

### Confirm the sync and deployed state

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

### Classify the mismatch

| Signal | Cause | Next |
|---|---|---|
| sync `error`: auth / pull failed | Arcane can't reach the repo | the Git Sync credential / network to GitHub |
| lastSync old / never | Git Sync paused, or wrong branch tracked | check the sync is enabled and tracks `main` |
| synced OK, image not applied | compose invalid, or image pull failed | `docker` events/logs on the host; the pin exists? |
| synced, container up, still wrong | **drift** — a manual change on the host | reconcile it back into `compose/` (it's an orphan) |
| env-dependent failure | packaged materialization — `.env.git` + decrypted `.env.sops` → effective `.env` | [secrets](../../docs/design/secrets.md); did `skynet deploy service` replace the exact project `.env`? |
| PR "merged" but not on `main` | merged to the wrong base / not merged | fix the merge; Arcane only tracks `main` |

### Fix declaratively

Make **git** correct — fix the compose, the pin, or the env layer → branch → PR → Ali merges. Run
`skynet deploy service <svc> --branch <branch>` to select and report the exact local branch head,
reconcile its Arcane sync/project, materialize `.env`, and require complete runtime health. Add
`--gate` only for the separate report-only route verifier. Verify health via the Arcane API /
`docker context`, then commit refreshed inventory. Recovery is a reviewed inverse prepared with
`skynet rollback service <svc> <deploy-commit> --prepare`; Arcane only converges after that branch is
human-merged. Only if Arcane itself is down is `ssh svc-ops@<host>` + `docker context` the break-glass
path — and even then, reconcile any imperative change back into git the same session.

## Verify

Confirm the expected commit is on `origin/main`, Arcane reports a successful sync, and the running
container image/configuration matches the declared compose state. If a break-glass inspection was used,
reconcile any imperative change back into git in the same session.

## Rollback

Prepare and human-merge a rollback branch with `skynet rollback service <svc> <deploy-commit>
--prepare`, then run `skynet deploy service <svc>` against the merged branch. Do not repair drift with
an unrecorded host mutation; Arcane is not a rollback executor.

## Evidence

`bin/new journal incident "<svc> Arcane stuck — <sync-fail|apply-fail|drift>"` — the sync error or the
git-vs-running mismatch, and the PR that reconciled it. ([journal](../../journal/README.md).)
