---
summary: "Triage a merged compose PR that isn't running — read the operation record and host facts, then classify: held, refused, rolled back, or drifted."
trigger: "A merged compose PR didn't deploy / a deploy rolled back / git and running have drifted"
tier: "T1/T2"
executor: "skynet deploy (record, dry-run, verify) and Docker inspection over the context"
rollback: "git revert the declarative fix"
---

# Diagnose — deploy stuck (a merged change isn't running)

**Tier:** **T1/T2**. **Trigger:** a `compose/` PR merged to `main` but the change never went live,
a deploy rolled back, or running state drifted from git.
Reference: [gitops-loop](../../docs/design/gitops-loop.md).

## Preconditions

- The change is expected on `main`; have the service name.
- Fixes go through a `compose/` PR; the Docker context is for looking.

## Steps

### Read what the executor did

```bash
tail -n 20 /opt/skynet-ops/state/operations.jsonl | jq -c 'select(.target=="svc/<svc>")
  | {ts, phase, source: .source[0:12], outcome, reason, recovery, steps}'
systemctl status skynet-deploy.timer skynet-deploy.service; journalctl -u skynet-deploy -n 50
skynet verify deployment <svc>            # what runs now, and is it healthy?
git log --oneline -3 origin/main -- compose/<svc>/
```

### Classify

| Signal | Cause | Next |
|---|---|---|
| no record for the merge; timer inactive | the timer isn't running | `systemctl start skynet-deploy.timer`; run `skynet deploy <svc>` |
| `outcome: refused`, `compose pull failed` | image tag/digest missing or registry down | fix the pin by PR; a transient pull retries next tick |
| `outcome: refused`, `compose render failed` / env key defined twice | the compose or env layer is invalid | `skynet deploy <svc> --dry-run <ref>` locally; fix by PR |
| `outcome: refused`, `secret decryption failed` | age key or `.env.sops` recipient problem | [secrets](../../docs/design/secrets.md) |
| `outcome: rolled-back`; `pending` says `held` | the revision failed verification and the verified one runs again | read `reason`; merge the revert PR or a fix — either moves `main` and releases the hold |
| `outcome: rollback-failed` (exit 4) | the verified revision also failed | hard checkpoint: stop, inspect the containers, tell Ali |
| `outcome: failed`, `no-rollback-target` | first deploy of a service with no verified revision | fix forward by PR |
| `skynet verify` fails with no new record | **drift** — a change made on the host | `skynet deploy <svc> --revision <running>` restores git's state |
| `outcome: unavailable`, lock held | another write is running | wait for it; a `started` entry with no `final` is reconciled by the next run |

### Fix declaratively

Make **git** correct → branch → PR (with the `--dry-run` effect) → Ali merges → the timer applies
it. Never repair a service with an unrecorded host mutation.

## Verify

`skynet verify deployment <svc>` passes at the expected revision and the newest record for the
service says `outcome: success`.

## Rollback

Revert the compose PR; the timer applies the revert like any merge.

## Evidence

`skynet new journal incident "<svc> deploy stuck — <held|refused|rollback-failed|drift>"` — the
operation record lines and the PR that fixed it. ([journal](../../journal/README.md).)
