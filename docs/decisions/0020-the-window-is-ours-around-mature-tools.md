---
status: accepted
date: 2026-11-22
decision-makers: Ali
---

# The merge window is three small programs of our own, around mature tools

## Context and Problem Statement

The autonomy plan (`docs/plans/autonomy.md` → Merges) has the agent merge updates by itself in a
nightly window. Each PR is reviewed, merged one at a time just after its own undo point, verified on
what the lab shows, and rolled back, code and data, if it breaks. The pieces exist: Renovate writes
the PRs, GitHub's CI and ruleset gate them, doco-cd and comin deploy, btrbk takes the undo point,
and Gatus, VictoriaMetrics and VictoriaLogs see what broke. Nothing joins them into "merge this one
now, see that it works, undo it if not". Rule 6 (`AGENTS.md`) asks what was ruled out.

## Considered Options

- **Renovate's automerge** (`automerge`, `platformAutomerge`, `automergeSchedule`): it merges when
  CI is green, inside a schedule. Nothing then looks at the lab, and nothing rolls back: a bad
  update stays until someone reverts it, with no undo point for its data.
- **GitHub's merge queue:** CI runs on each PR merged onto main, one at a time. It's for
  repositories owned by an organization, and this one is a personal account's. It also stops at CI,
  before anything deploys.
- **A merge bot** (Mergify, Kodiak, bors-ng): labels and CI decide, as with Renovate. Each is one
  more GitHub app with write access, and none looks at the lab after the merge.
- **Progressive delivery** (Argo Rollouts, Flagger, Keptn): canaries, analysis against metrics,
  automatic rollback. All are for Kubernetes; the stacks here are Compose, deployed by doco-cd
  (ADR-0001).
- **Updating in place** (Watchtower, What's Up Docker): they pull new images onto running containers,
  outside git (rule 2), with no review and no rollback.
- **Programs of our own** around the tools above, deciding and sequencing only.

## Decision Outcome

Chosen option: **three programs of our own**, on ops, that only decide and sequence. Renovate still
writes the PRs, GitHub runs CI and holds the merge, doco-cd and comin deploy, btrbk keeps the undo
points, and the stores and Gatus are the evidence:
- `skynet-verify` (`packages/skynet-verify/`): whether a stack or a host is well after a change, as
  evidence anyone can read: the containers' images and health, doco-cd's counters, Gatus's rows, the
  error lines against yesterday's, a smoke check;
- `skynet-merge` (`packages/skynet-merge/`): whether a PR may merge now, gate by gate, then the undo
  point and the merge of the reviewed commit alone;
- `skynet-window` (`packages/skynet-window/`): the night, PR by PR, and the rollback.

The evening review that `skynet-merge` asks for is a headless run (`runbooks/review.md`), started by
`modules/window.nix`. All of it is code-owned, since it stands in for Ali's review (ADR-0013).
Because each tool above does one part well, and none decides "now, then check, then undo" for
Compose stacks and NixOS hosts.

### Consequences

- Good, because what a merge did is checked on the lab, not only in CI, and a bad one is undone
  with its data.
- Good, because each program prints its evidence, so a PR's merge and its verify read like a log.
- Bad, because they are ours to keep. They are shell and jq, a few hundred lines each, built and
  shellchecked like the rest (`packages/README.md`).
- Bad, because verify knows only what the lab shows. A change that breaks something nothing watches
  passes, so CI asks every service for a healthcheck and every routed app for a Gatus row (step 5's
  checks, in `.github/`).

## More Information

The plan, merged 2026-11-15 (#185), named these programs. Built as a dry run on 2026-11-22: the
window logs what it would merge and verifies what's live for a week before it merges anything
(step 6, a record superseding ADR-0013). A host's timed rollback (`skynet-activate`, step 7) gets its
own record if a mature tool doesn't fit; deploy-rs's magic rollback is the first to try.
