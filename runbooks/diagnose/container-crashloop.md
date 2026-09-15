---
summary: "Triage a container that restarts, is unhealthy, or exits — read exit code + logs + healthcheck, branch to the cause, fix in compose/."
trigger: "A container is Restarting / unhealthy / keeps exiting"
tier: "T1"
executor: "svc-ops Docker inspection"
rollback: "git revert the compose fix"
---

# Diagnose — container crash-loop

**Tier:** **T1** to diagnose with unprivileged `svc-ops` docker access. **Trigger:** recon's
*Containers* section shows `Restarting`, `unhealthy`, or an `Exited` service that should be up. The
fix is a `compose/` PR; never hand-edit the host.

## Preconditions

- Have the affected Docker host and service name; use unprivileged `svc-ops` inspection only.
- Keep secret values out of commands, output, and journal evidence.

## Steps

### Inspect state, logs, and health

```bash
scripts/recon.sh <docker-host>                          # the Containers section, first pass
ssh svc-ops@<docker-host> docker ps -a --filter name=<svc>
ssh svc-ops@<docker-host> docker inspect --format \
  '{{.State.Status}} exit={{.State.ExitCode}} restarts={{.RestartCount}} oom={{.State.OOMKilled}}' <svc>
ssh svc-ops@<docker-host> docker logs --tail 120 --timestamps <svc>
ssh svc-ops@<docker-host> docker inspect --format '{{json .State.Health}}' <svc> | jq .   # if it has a healthcheck
```

(`docker context use <host>` works too — the same read from the ops VM.)

### Classify the failure

| Signal | Likely cause | Next probe |
|---|---|---|
| `ExitCode=137`, `OOMKilled=true` | out of memory | recon *Load/memory*; the compose `mem_limit` vs host RAM |
| `ExitCode=1` + a stack trace in logs | app-level fault (bad config, missing dep) | read the last log lines; check env below |
| `ExitCode=127` / "executable not found" | wrong `command`/`entrypoint` or image | `docker inspect` the image's cmd; check the pin |
| Exits `0` but keeps restarting | healthcheck flapping, or `restart: always` on a one-shot | inspect `.State.Health`; is this meant to be long-running? |
| `unhealthy`, app "up" | healthcheck command wrong, or a dependency (DB) not ready | run the healthcheck cmd by hand; check the depended-on container |
| Env/secret missing at boot | `.env` layering broke | see below |

**Env / secret materialization** (the usual silent cause): `skynet deploy service` builds the
effective `.env` from `.env.git` **+** decrypted `.env.sops` and replaces the exact project file. A
missing key means decryption/materialization failed or the key was omitted from git. Confirm both
source layers and the effective file without printing values — details in [gitops-loop](../../docs/design/gitops-loop.md)
+ [secrets](../../docs/design/secrets.md).

### Fix declaratively

Edit `compose/<svc>/` — pin the image, correct the healthcheck, set `mem_limit`, or fix an env key
(secret values only in `.env.sops`) — then branch → PR → Ali merges. Run
`skynet deploy service <svc>` against that exact merged branch head. The command prepares one
coherent immutable generation, directly activates it under lock, and requires complete Docker
container/health and DMZ route/TLS verification before stable promotion. Arcane may display the
externally managed project but is not the deployment verifier. Refresh inventory through its
normal collector. If verification fails, inspect `skynet deploy status`; old `stable` remains the
explicit runtime rollback candidate. Do not treat a failed activation as an authored Git revert.

## Verify

`skynet verify deployment <svc> <full-revision>` proves the selected release manifest, complete
Docker generation identity and health, and any declared ingress route from the DMZ vantage with
verifying TLS. A missing healthcheck is a failure.

## Rollback

Explicitly run `skynet rollback service <svc> [--to <retained-full-revision>] --apply` to restore a
known generation under the same verification path. This does not change Git; correct authored source
through a reviewed PR. Record Docker/operation evidence in the journal.

## Evidence

Append a raw journal incident: `bin/new journal incident "<svc> crash-loop — <one-line cause>"` — the
exit code, the log line that named the fault, the `compose/` PR that fixed it. ([journal](../../journal/README.md).)
