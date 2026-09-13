# ADR 0004 — Auto-merge generated-only nightly PRs

- **Status:** suspended during the SKY-025 test/CI embargo
- **Date:** 2026-08-20

## Context

The current constitutional dial requires human merge for every PR. GitHub CI and automated
repository tests are absent during SKY-025, so the evidence required for unattended merge does not
exist. `scripts/nightly-automerge.sh` is a fail-closed compatibility stub, and
`OPS_NIGHTLY_AUTOMERGE` has no enabling effect during the embargo.

This ADR originally addressed a backlog of mechanical nightly PRs. The nightly writes refreshed
`inventory/`, re-rendered `docs/generated/`, append-only journal evidence, and sometimes encrypted
`compose/*/.env.sops`. Requiring repeated human merges for that generated-only class created latency
and encouraged rubber-stamp review. The repository is private on GitHub Free, so enforced branch
protection was unavailable and the safety gate had to live in version-controlled code.

The former capability was deliberately narrower than authored self-merge. It required the supplied
open PR to be the exact nightly PR, every changed path to be generated-only, a non-empty all-green CI
result, and an unchanged head through the merge call. Authored design, code, Compose, runbook,
ingress, and publishing changes were never eligible.

## Decision

The generated-only nightly auto-merge capability is **suspended** for the duration of SKY-025. Every
PR, including a nightly generated-only PR, remains open until Ali reviews and merges it.

The compatibility executor must:

1. perform no GitHub lookup or mutation;
2. contain no `gh pr merge` or other merge path;
3. report that auto-merge is suspended and leave the PR open;
4. ignore any legacy `OPS_NIGHTLY_AUTOMERGE` value as an enabling signal.

Restoration requires a human-merged constitutional change to `docs/system-design.md` and `AGENTS.md`.
That change must restore one coherent, non-vacuous verification architecture and a deterministic
executor that proves all of the following before mutation:

- the caller supplied the exact open nightly PR and expected head;
- every changed path is under `inventory/`, `docs/generated/`, `journal/`, or matches
  `compose/*/.env.sops`;
- at least one required CI check exists and every required check passed;
- the PR identity, branch, and head remain unchanged through a head-bound merge call;
- any missing, pending, failed, malformed, or changing evidence leaves the PR open.

The historical `OPS_NIGHTLY_AUTOMERGE=0` off-switch may return only with that reviewed restoration;
it is not the current enforcement mechanism.

## Historical implementation note

The capability was first placed only in `scripts/nightly.sh`. On 2026-08-30 it was extracted into
`scripts/nightly-automerge.sh` so both deterministic and agent-assisted nightly paths could call one
literal path/CI/head gate. That plumbing drained generated-only backlog PRs #113, #115, and #116.
The current embargo replaces that executor with the fail-closed stub without erasing the rationale or
the safeguards a future implementation must recover.

## Consequences

- No A4 capability is active during SKY-025; all PRs require human merge.
- Nightly generated evidence may accumulate as open PRs until Ali reviews it.
- No absent or vacuous CI state can be interpreted as green evidence.
- The local secret scan and hard-invariant checker remain safety controls, but they do not authorize
  unattended merge.
- Historical auto-merge evidence remains in Git and the journal; it is not current authority.
- A future restoration is a new reviewed dial change, not automatic reactivation when SKY-025 ends.
