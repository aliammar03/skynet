---
summary: "Triage a container that restarts, is unhealthy, or exits — read exit code + logs + healthcheck, branch to the cause, fix in compose/."
trigger: "A container is Restarting / unhealthy / keeps exiting"
---

# Diagnose — container crash-loop

**Trigger:** recon's *Containers* section shows `Restarting`, `unhealthy`, or an `Exited` service
that should be up.
**Tier:** **T1 to diagnose** — unprivileged `svc-ops` docker on the host reads logs, state, and
health with no grant. The **fix is a `compose/` PR** (Arcane reconciles), never a hand-edit on the host.

> **Diagnose imperatively, fix declaratively.** Looking is T1 and free. Whatever the fix, it goes
> back through git — a `compose/<svc>/` change — so nothing is orphaned. ([recon](../recon.md), SKY-005.)

## 1. Confirm — get the container's own words

```bash
scripts/recon.sh <docker-host>                          # the Containers section, first pass
ssh svc-ops@<docker-host> docker ps -a --filter name=<svc>
ssh svc-ops@<docker-host> docker inspect --format \
  '{{.State.Status}} exit={{.State.ExitCode}} restarts={{.RestartCount}} oom={{.State.OOMKilled}}' <svc>
ssh svc-ops@<docker-host> docker logs --tail 120 --timestamps <svc>
ssh svc-ops@<docker-host> docker inspect --format '{{json .State.Health}}' <svc> | jq .   # if it has a healthcheck
```

(`vm-docker-dmz` is `10.10.100.15`. `docker context use <host>` works too — same read, from the ops VM.)

## 2. Branch on what you see

| Signal | Likely cause | Next probe |
|---|---|---|
| `ExitCode=137`, `OOMKilled=true` | out of memory | recon *Load/memory*; the compose `mem_limit` vs host RAM |
| `ExitCode=1` + a stack trace in logs | app-level fault (bad config, missing dep) | read the last log lines; check env below |
| `ExitCode=127` / "executable not found" | wrong `command`/`entrypoint` or image | `docker inspect` the image's cmd; check the pin |
| Exits `0` but keeps restarting | healthcheck flapping, or `restart: always` on a one-shot | inspect `.State.Health`; is this meant to be long-running? |
| `unhealthy`, app "up" | healthcheck command wrong, or a dependency (DB) not ready | run the healthcheck cmd by hand; check the depended-on container |
| Env/secret missing at boot | `.env` layering broke | see below |

**Env / secret layering** (the usual silent cause): the effective `.env` is `.env.git` **+** the
secret-bearing `project.env` → merged. A missing key means the `.env.sops` didn't decrypt or a key was
dropped. Confirm the effective env and the sops layer — details in
[gitops-loop](../../docs/design/gitops-loop.md) + [secrets](../../docs/design/secrets.md).

## 3. Fix declaratively

Edit `compose/<svc>/` — pin the image, correct the healthcheck, set `mem_limit`, fix the env key (secret
values only ever go into `.env.sops`) — then **branch → PR → Ali merges → Arcane reconciles**. Verify
health via the Arcane API / `docker context`, then commit refreshed inventory. Rollback is `git revert`;
Arcane rolls it back. Break-glass only: `ssh svc-ops@<host>` + `docker context` to look, never to mutate.

## 4. Record

Append a raw journal incident: `bin/new journal incident "<svc> crash-loop — <one-line cause>"` — the
exit code, the log line that named the fault, the `compose/` PR that fixed it. ([journal](../../journal/README.md).)
