---
summary: "The current write actuators, deterministic rollback paths, and A4 eligibility of each capability."
---

# Spoke · Actuators & rollback executors

> The current registry of write paths and their recovery boundaries. Governed by
> [`../system-design.md`](../system-design.md) and the reversibility test in
> [ADR 0005](../decisions/0005-full-agent-control-as-terminal-goal.md).

Unattended action requires an automatic failure-tested rollback performed by a deterministic executor,
not an LLM. Irreversible work remains a hard checkpoint. The executor rejects tofu delete/replace
plans and T3-excluded guests rather than attempting to make them reversible.

| Actuator | Write path | Recovery on failure | Deterministic decision | A4 eligible |
|---|---|---|---|---|
| Compose deploy | `gitops-deploy.sh --gate` | `gitops-rollback.sh --prepare` creates a reviewed inverse; no automatic authored revert | `deploy-gate.sh` health verdict | No |
| Existing-guest tofu update | `tofu-apply.sh <saved-plan>` | Snapshot before apply; preserve snapshot for verification/dirty-plan recovery | Post-apply plan and verification | No |
| Tofu guest create | Approved `tofu-apply.sh <saved-plan>` | None; never auto-destroy partial create | Post-apply plan | No |
| Tofu non-guest write | Approved `tofu-apply.sh <saved-plan>` | None | Post-apply plan | No |
| Cloudflare DNS break-glass | `cf-dns-route.sh` | `dns-revert.sh undo` replays a captured complete-record inverse | Inverse capture must succeed before mutation | Yes, executor only |
| NixOS deployment | deploy-rs / `nixos-rebuild` | deploy-rs magic rollback | Activation health check | Yes |
| OPNsense config | No live actuator | None | — | No |

The saved-plan wrapper applies one approved scope and never re-plans. Existing-guest updates fail
closed when a snapshot cannot be made. An apply/API failure can use that snapshot; a post-apply
verification failure preserves it for operator recovery. New guests and non-guest resources have no
automatic inverse, so they remain supervised below A4.

The test suites named by the registry are the durable proof locations:
`tests/compose-rollback-test.sh`, `tests/tofu-rollback-test.sh`, and
`tests/dns-revert-test.sh`. Raw rehearsal evidence belongs in the journal; deployment and
provisioning procedures belong in their runbooks.
