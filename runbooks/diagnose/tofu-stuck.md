---
summary: "Triage a merged OpenTofu PR that didn't apply or alerted — read the record and the state branch, classify (held, waiting, rolled back, rollback-failed, deferred), and recover through the supervised path."
trigger: "A merged tofu PR didn't apply / a tofu alert arrived / a guest or record delete is deferred / retire a guest"
tier: "T1/T2"
executor: "skynet tofu (log, drift, apply --ignore-hold) and the Proxmox operate API"
rollback: "git revert the declarative change; the timer applies the revert"
---

# Diagnose — tofu stuck (a merged change didn't apply, or alerted)

**Tier:** **T1/T2**. **Trigger:** a `tofu/` (or derived-DNS) PR merged but the change is not live, a
`skynet: tofu/<stack> …` alert arrived, `skynet tofu drift` lists a deferred change, or a guest is
being retired. Reference: [actuators](../../docs/design/actuators.md).

## Preconditions

- The change is on `main`; know the stack (`proxmox-core`, `technitium-dns`, `cloudflare-dns`).
- Fixes go through a PR. Proxmox API calls below are T2 and only for the guests named in the plan;
  never touch an excluded guest (5001, 635, 837, 2020).

## Steps

### Read what the executor did

```bash
skynet log --kind tofu --limit 10
journalctl -u skynet-tofu -n 40 -o cat              # the timer's per-pass lines and steps
tail -n 30 /opt/skynet-ops/state/operations.jsonl | jq -c 'select(.kind=="tofu" and .phase=="final")
  | {ts, id, source: .source[0:12], outcome, reason, recovery, steps}'
git fetch -q origin tofu-state && git show origin/tofu-state:<stack>/held.json   # absent = no hold
skynet tofu drift                                     # read-only plan of every stack at main
systemctl status skynet-tofu.timer
```

### Classify

| Signal | Cause | Next |
|---|---|---|
| no record for the merge; timer inactive | the timer isn't running | `systemctl start skynet-tofu.timer`, or run `skynet tofu apply --pending` |
| `refused — plan differs from the approved plan` / stale approval / `does not validate` | the merged plan is not the approved one | held until `main` moves: re-plan on a branch rebased on `main` (`skynet tofu plan <stack> --approve`) in a new PR |
| `unavailable — tofu could not be started` | the `tofu` binary is missing from the unit's PATH | nothing changed; retried with backoff, alerts on the third pass; fix the package and rebuild |
| `unavailable — … has pending config changes` | a guest already has changes waiting for a restart | restart that guest (below) or revert its pending change; the next pass applies |
| `refused — another write holds the lock` / `deferred — a deploy holds the write lock` | a deploy or another apply is running | wait; not counted, no alert |
| `rolled-back` | the apply failed; every guest's saved config was written back and proven | held: fix forward or merge a revert; either moves `main` |
| `rollback-failed` (exit 4) | the restore or its proof failed, or an apply was interrupted (`interrupted tofu apply`) | **hard checkpoint**: tell Ali, then *Recover after rollback-failed* |
| success with `pending: left — <guest> (<keys>)` | the change landed but needs a guest restart | restart the guest (below); until then its next change waits |
| success with `deferred: announced — <address>` / drift lists `deferred (hard checkpoint)` | a guest delete/replace/forget or a hand-listed DNS record removal | **hard checkpoint**: *Retire a guest*, or remove the record by hand / restore its declaration |
| `skipped — a guest write is changing the Docker host` from `skynet watch` | a Docker-host update holds the fence | expected for up to 5 h; deploys there wait |

### Operate API helper (T2; never echo the env)

Quote every path (zsh globs an unquoted `?`). `run` posts an action and waits for its task, so the
next step never races a running stop or shutdown.

```bash
set -a; . /opt/skynet-ops/secrets/proxmox-core.env; set +a
pve() { local m=$1 p=$2; shift 2; curl -sS --cacert "$PVE_CACERT" -X "$m" \
  -H "Authorization: PVEAPIToken=$PVE_TOKEN_OPERATE" "https://$PVE_HOST:8006/api2/json/$p" "$@"; }
N=nodes/server-proxmox-core
run() {   # run METHOD PATH [curl args…]: start a task, wait for it, fail unless it ends OK
  local upid st; upid=$(pve "$@" | jq -r .data)
  [[ $upid == UPID:* ]] || { echo "no task: $upid" >&2; return 1; }
  while st=$(pve GET "$N/tasks/$(jq -rn --arg u "$upid" '$u|@uri')/status" | jq -r .data.status); \
    [[ $st != stopped ]]; do sleep 2; done
  pve GET "$N/tasks/$(jq -rn --arg u "$upid" '$u|@uri')/status" | jq -e '.data.exitstatus == "OK"' >/dev/null \
    || { echo "task failed: $upid" >&2; return 1; }
}
K=qemu   # or lxc, for a container
```

### Restart a guest with pending changes

Graceful first, forced if ignored (a guest still booting or without ACPI ignores a plain reboot):

```bash
run POST "$N/$K/<vmid>/status/shutdown" -d forceStop=1 -d timeout=120   # up to 120 s, then forced
run POST "$N/$K/<vmid>/status/start"
pve GET "$N/$K/<vmid>/pending" | jq '[.data[] | select(.pending != null or .delete != null)]'  # []
```

### Recover after rollback-failed

1. Read the guests and the kept snapshot from the record (`context.guests`, `context.snapshot` =
   `skynet-<operation>`). Compare each guest's live config with the snapshot's:
   `pve GET "$N/$K/<vmid>/config"` vs `pve GET "$N/$K/<vmid>/snapshot/skynet-<op>/config"`.
2. Bring each guest to the intended config: restart it if changes are pending (above); fix a key
   by hand only with Ali's go.
3. Either re-run the merged revision supervised — `skynet tofu apply <stack> --ignore-hold` (one
   stack, never `--pending`) — or move `main` with a fix or revert PR.
4. Once every guest is proven, delete the kept snapshot on each:
   `run DELETE "$N/$K/<vmid>/snapshot/skynet-<op>"`; `jq '._cleanup'
   /opt/skynet-ops/state/tofu/pending.json` must be `[]`.

### Retire a guest (deferred delete)

1. PR: remove the guest's declaration (and its `invariants.json` entity exception, if any) with its
   approval; expect `deferred` in `approved-plan.json`. After the merge the timer defers it and
   alerts once.
2. Ali approves the destroy (hard checkpoint, every time).
3. Check identity (VMID, name, pool, not a template, not excluded), then destroy; `K=lxc` for a
   container:
   ```bash
   pve GET "cluster/resources?type=vm" | jq '.data[] | select(.vmid==<vmid>) | {vmid,type,name,pool,template}'
   run POST "$N/$K/<vmid>/status/stop"
   run DELETE "$N/$K/<vmid>?purge=1&destroy-unreferenced-disks=1"
   ```
4. `skynet tofu drift` no longer lists it; the next apply drops it from state.

## Verify

The newest record for the stack says `success`, `skynet tofu drift` shows `no changes` with no
unintended deferral, and `held.json` is absent (or names only a revision you mean to keep held).

## Rollback

Revert the PR; the timer applies the revert like any merge (a deferred delete is undone by restoring
the declaration, which plans empty).

## Evidence

`skynet new journal incident "tofu/<stack> — <held|rolled-back|rollback-failed|deferred>"` — the
record lines, the API calls made, and the PR that resolved it. ([journal](../../journal/README.md).)
