---
summary: "Start-here triage: take one T1 read-only host snapshot with scripts/recon.sh, reason over it, then branch to a diagnosis runbook."
trigger: "Figure out why X is broken / what's going on with <host>"
tokens: 771
---

# Runbook — recon (start here)

**Trigger:** *"Figure out why `<host>` is broken"* / *"what's going on with `<host>`?"* — any
investigation that starts with *looking*.
**Tier:** **T1 read-only.** Recon takes **no grant**: the whole point of this step is that
observing a host costs nothing and touches nothing. Reach for root only *after* the snapshot
tells you what to look at — via a diagnosis runbook, under a narrowest-host/shortest grant.

> Principle: **diagnose imperatively, fix declaratively.** This runbook is the imperative
> *looking*. The eventual fix is a PR to `compose/` / a module / a tofu resource — never an
> orphan mutation of the host. (SKY-005.)

## 1. Take the snapshot

```bash
scripts/recon.sh <host>        # remote host as svc-ops over SSH
scripts/recon.sh               # this host (the ops VM) — no arg
scripts/recon.sh <host> > /tmp/recon-<host>.md   # keep it to attach to a journal record
```

`<host>` is a bare label (mapped to `svc-ops@<label>`) or an explicit `user@host`. One
Markdown snapshot comes back: host/kernel/uptime, load+memory, disk **and inode** pressure,
failed systemd units, listening sockets, container health (unprivileged docker), recent
journal warnings, and recent `/etc` + package changes. Sections that would need root say so
rather than failing — recon never blocks on a grant.

## 2. Reason over it — what each section is telling you

| Section | Read it for |
|---|---|
| Load / memory / CPU | Runaway process, memory pressure, OOM risk. |
| Disk (usage + **inodes**) | A full FS **or** inode exhaustion (looks like "disk full" with space free). |
| systemd — failed units | The fastest single signal: a unit in `failed` is usually *the* incident. |
| Listening sockets | Missing port (service down) or unexpected one. |
| Containers | Crash-loops (`Restarting`), `unhealthy`, or an exited container. |
| Recent warnings/errors | The failure's own words — grep the unit name here. |
| Recent config / package changes | *What changed just before it broke* — the usual root cause. |

## 3. Branch to a diagnosis runbook

Once the snapshot points at a failure class, follow the matching triage runbook (each embeds
the deeper diagnostic commands + decision branches, and ends in a **journal incident record**):

- container crash-loop · disk full · cert expired · DNS failure · backup missed · Arcane stuck

*(The diagnosis library is SKY-005 Phase 2 — `runbooks/diagnose/`. Until it lands, reason from
the snapshot and record what you found in the [journal](../journal/README.md).)*

## 4. Fix declaratively

Whatever the fix is, route it back through git so nothing is orphaned: a `compose/` PR, a
config module, a tofu resource. If an emergency forced an imperative change on the host,
**reconcile it back into declared state in the same session** and note it in the journal.
