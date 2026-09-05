---
date: 2026-09-05
kind: session          # session | incident | decision
title: SKY-023 P2 close-out
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023]         # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
---

# 2026-09-05 · session · SKY-023 P2 close-out

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened

Ran SKY-023 Phase 2 on `phase/sky-023-p2` after Phase 1 merged as PR #185. This was T1 repository
work only: no infrastructure command, credential read, T2 write, or root grant ran. The initial
`bin/plan start SKY-023` attempted to move the directive from `projects/` to itself and printed
`fatal: can not move directory into itself`; it still regenerated the roadmap and made no directive
change. The directive was already active, so work continued on Phase 2.

Replaced the 4,244-word constitution with a 1,047-word authority document: authority/scope,
terminal goal + ladder, hard laws, dials, trust spine, operator-extension index, and spoke index.
Removed ACL command recipes, growth directions, rollout narrative, and duplicate self-leash text.
The design corpus changed from 14,830 to 5,201 words. The resulting docs point to directives for
future work, journal for raw rehearsal evidence, runbooks/scripts for procedures, and generated
views for live state.

One Builder edited only disaster recovery, GitOps loop, network, observability, and secrets spokes;
one Scout supplied the migration audit. The lead reviewed both outputs. A local markdown-link scan,
`./scripts/check-invariants.sh`, every `tests/*-test.sh`, and `git diff --check` all passed.

During close-out Ali corrected the master age-key description: the agent decrypts sops without sudo.
`scripts/gitops-deploy.sh` already attempts unprivileged decryption using the group-readable key.
Updated the authoritative contract, summaries, system design, secrets/access spokes, and stale Nix/
script comments to state the deliberate `0640 root:users` age-key exception; other secret material
remains restrictive.

## Actions & outcomes

- Pruned `docs/system-design.md` → 4,244 to 1,047 words; its retained content matches the Phase 2
  authority model.
- Pruned all design spokes → 14,830 to 5,201 words; no `Planned expansion` section remains.
- Replaced setup commands with script/runbook links and moved raw rehearsal detail out of the
  actuator registry → current test paths remain linked as proof locations.
- Ran `./scripts/render-context-map.sh` and `./scripts/render-digest.sh` after close-out updates →
  regenerated only their owned files.
- Ran `./scripts/check-invariants.sh` and all `tests/*-test.sh` → all checks passed.

## Graveyard — tried & abandoned

- `bin/plan start SKY-023` on an already-project directive → abandoned as a phase-start mechanism;
  it attempts a self-move and prints a fatal error. The directive was already in-progress, so no
  move was needed.
- Treating generic `0600` prose as the master-key permission → abandoned after the explicit runtime
  correction and `gitops-deploy.sh` inspection showed unprivileged sops decryption is intentional.

## Follow-ups / open threads

- Phase 3: split the publishing monolith and make all runbooks task-shaped.
- The directive references `[[SKY-023-progress]]`, but no repository-backed progress-memory file
  exists. This raw close-out episode is the durable repo record for resumption.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
