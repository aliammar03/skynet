---
summary: "The current write actuators, deterministic recovery paths, and A4 eligibility of each capability."
---

# Spoke · Actuators & rollback executors

> The current registry of write paths and their recovery boundaries. Governed by
> [`../system-design.md`](../system-design.md) and the reversibility test in
> [ADR 0005](../decisions/0005-full-agent-control-as-terminal-goal.md).

Unattended action requires an automatic, failure-tested rollback performed by a deterministic
executor, not an LLM. Irreversible work remains a hard checkpoint. The current Compose path has no
automatic authored inverse, so it is not A4 eligible.

| Actuator | Write path | Recovery on failure | Deterministic decision | A4 eligible |
|---|---|---|---|---|
| Compose deploy | `skynet deploy service <service>` | No automatic rollback; inspect the exact outcome, then prepare a reviewed inverse with `skynet rollback service <service> <deploy-commit> --prepare` | Runtime reconciliation; optional `--gate` invokes the packaged report-only verifier | No |
| Existing-guest tofu update | `tofu-apply.sh <saved-plan>` | Snapshot before apply; preserve snapshot for verification/dirty-plan recovery | Post-apply plan and verification | No |
| Tofu guest create | Approved `tofu-apply.sh <saved-plan>` | None; never auto-destroy partial create | Post-apply plan | No |
| Tofu non-guest write | Approved `tofu-apply.sh <saved-plan>` | None | Post-apply plan | No |
| Cloudflare DNS break-glass | `cf-dns-route.sh` | `dns-revert.sh undo` replays a captured complete-record inverse | Inverse capture must succeed before mutation | Yes, executor only |
| NixOS deployment | deploy-rs / `nixos-rebuild` | deploy-rs magic rollback | Activation health check | Yes |
| OPNsense config | No live actuator | None | — | No |

The packaged Compose deployment binds service source bytes and executable modes to one exact local
branch-head identity before any Arcane write, then requires one existing exact repository/sync/project
identity with `autoSync=false`. It installs the selected environment before branch repoint or manual
source sync; Arcane's manual sync may itself redeploy a running project, followed by the command's
explicit bounded NDJSON redeploy. Scheduled sync remains disabled and the package does not bootstrap
missing projects. A legacy auto-sync project requires a one-time T2 migration and timed quiescence
while old source/environment still agree; disabling auto-sync cannot cancel an admitted run. Follow
the [deploy runbook](../../runbooks/deploy-service.md) for the duration and old-runtime check. A
manual source-sync request with an ambiguous outcome, or a non-terminal completion deadline, stops
without a second POST because Arcane exposes no in-flight operation lease; only positively newer
terminal failure evidence after a normally returned POST can permit a bounded retry. A failed or
ambiguous stage reports completed steps, `verification`, and `recovery`; once `source-synced` is
recorded, recovery states that source activation occurred. It never implies that an earlier write was
undone. `--no-deploy` prepares environment only, with source unselected.
`cloudflared` restart is limited to the reconciled container IDs and is followed by the same health
checks.

The optional P10 gate is separate and report-only. It can fail after runtime success without changing
the runtime, and it never invokes rollback. Arcane is the GitOps reconciler, not a rollback executor.

Rollback defaults to report-only validation. `--prepare` creates a temporary isolated worktree from
the attached base branch, creates a revert commit on a unique local
`rollback/<service>-<first-12-hex-of-revision>` branch, cleans the worktree, and leaves push/review/
human merge to the operator. Protected paths,
mixed-Compose-project commits, and commits outside the selected service are refused. Nothing is
pushed or merged by the command.

Automated rollback proof is unavailable during the SKY-025 repository-test embargo. Historical raw
rehearsal evidence remains in the journal, and no actuator may claim a new A4 promotion until a
post-transition review restores coherent failure-case automation.
