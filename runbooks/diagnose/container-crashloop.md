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
skynet recon <docker-host>                              # the Containers section, first pass
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

**Env / secrets** (the usual silent cause): `skynet deploy` renders the env from `.env.git` **+**
decrypted `.env.sops`. A missing key was omitted from git; `skynet deploy <svc> --dry-run <ref>`
names the env keys a change adds, removes, or changes (never values) — details in
[gitops-loop](../../docs/design/gitops-loop.md) + [secrets](../../docs/design/secrets.md).

### Fix declaratively

Edit `compose/<svc>/` — pin the image, correct the healthcheck, set `mem_limit`, fix the env key (secret
values only ever go into `.env.sops`) — then **branch → PR → Ali merges → the timer deploys it**.
`skynet deploy` verifies health and rolls a failed revision back by itself. Rollback of a merged
change is `git revert`. `ssh svc-ops@<host>` + `docker context` are for looking, never to mutate.

## Verify

Confirm the service remains running, reports healthy where a healthcheck exists, and its image,
configuration, and effective non-secret environment match the merged compose state:
`skynet verify deployment <svc>` passes.

## Rollback

Revert the compose PR; the timer deploys the previous image/configuration. Break-glass docker
access is inspection only and must not become the rollback mechanism.

## Evidence

Append a raw journal incident: `skynet new journal incident "<svc> crash-loop — <one-line cause>"` — the
exit code, the log line that named the fault, the `compose/` PR that fixed it. ([journal](../../journal/README.md).)
