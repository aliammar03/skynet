---
summary: "Current write actuators, recovery paths, and A4 eligibility."
---

# Spoke · Actuators and rollback executors

> Write-path registry governed by [`../system-design.md`](../system-design.md) and
> [ADR 0005](../decisions/0005-full-agent-control-as-terminal-goal.md).

Unattended A4 action requires an automatic, failure-tested rollback performed by a deterministic
executor rather than the same LLM. Irreversible work remains a hard checkpoint. The current Compose
path is supervised T2 with explicit human-controlled runtime rollback and is not A4 eligible.

| Actuator | Write path | Recovery on failure | Verification | A4 eligible |
|---|---|---|---|---|
| Compose deploy | `skynet deploy service <service>` | Preserve old stable; inspect active/operation/Docker identity; explicitly `skynet rollback service ... --apply` to a retained generation | Independent exact generation, complete health, DMZ route/TLS gate before promotion | No |
| Existing-guest tofu update | `tofu-apply.sh <saved-plan>` | Snapshot before apply; preserve for verification/dirty-plan recovery | Post-apply plan and verification | No |
| Tofu guest create | Approved `tofu-apply.sh <saved-plan>` | None; never auto-destroy partial create | Post-apply plan | No |
| Tofu non-guest write | Approved `tofu-apply.sh <saved-plan>` | None | Post-apply plan | No |
| Cloudflare DNS break-glass | `cf-dns-route.sh` | `dns-revert.sh undo` replays complete-record inverse | Inverse capture before mutation | Yes, executor only |
| NixOS deployment | deploy-rs / `nixos-rebuild` | deploy-rs magic rollback | Activation health check | Yes |
| OPNsense config | No live actuator | None | — | No |

Compose preparation reads one exact Git revision and atomically publishes a validated immutable
remote generation; failure leaves running and stable state untouched. The packaged owner activates
through direct `svc-ops` Docker Compose under remote `flock`, first refusing enabled Arcane auto-sync
and reconciling actual Docker generation labels against operation/pointer state. `active` may be an
unverified candidate while `stable` remains the old verified generation. Timed-out activation is
unresolved until the old lock releases and Docker evidence is inspected; only convergence to the
same immutable generation can resume over a partial application. A different generation is refused
over ambiguity.

Verification and promotion are separate: Docker Compose accepting a change cannot move `stable`.
Failure preserves the old stable rollback candidate; no automatic rollback occurs. Explicit retained
generation runtime rollback activates, independently verifies, and promotes the selected generation
without Git branch/commit/push/merge. Authored source correction is a normal reviewed PR. Arcane may
observe projects but Git Sync is not a deployment or rollback executor. A disabled legacy sync can
remain; enabled scheduling is a pre-write refusal until drained and old runtime revision is proved.

Automatic rollback proof is unavailable during the SKY-025 test/CI embargo; no new A4 promotion can
be claimed until coherent failure-case automation is restored and human-merged.
