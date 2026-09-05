---
id: SKY-023
title: Eliminate documentation drift and shrink operational context
status: in-progress
horizon: short
created: 2026-09-04
updated: 2026-09-05
phases: 4
current_phase: 2
tier_touched: [T1]
related:
  - docs/system-design.md
  - docs/design/
  - runbooks/
  - AGENTS.md
  - README.md
  - docs/architecture.md
  - planning/archive/SKY-009-convention-bedrock-doctrine-spine-and-golden-templates.md
  - planning/archive/SKY-010-default-lean-context-load-on-demand.md
  - planning/ideas/SKY-012-runbooks-as-executable-capabilities.md
  - planning/ideas/SKY-016-harden-the-service-deployment-workflow-verify-reachability-not-just-health-plus-scaffolding-helpers.md
  - planning/projects/SKY-020-firewall-as-code-opnsense-config-to-t2-via-opentofu.md
  - "[[SKY-023-progress]]"
---

# SKY-023 · Eliminate documentation drift and shrink operational context

> Re-establish one authoritative home per fact, fix unsafe contradictions first, then remove prose
> that makes agents load history, rationale, roadmap, or unrelated procedures during routine work.

## 1. Problem

At commit `9484f19`, design + runbooks total about **26.4K words**. Five files hold nearly half.
Repeated policy has drifted: saved-plan OpenTofu vs bare `tofu apply`; PR-before-apply vs apply-before-PR;
two incompatible Arcane env models; conflicting OPNsense/Unraid scopes; L5 restore both proven and
untested; Omada and forward-auth both realized and planned; per-host certs and single-cert limits;
report-only drift detection described as auto-revert. `system-design.md` also carries spoke detail
and a 700-word roadmap despite declaring itself a short constitution.

## 2. Decisions

- **One home per kind:** constitution = laws/dials/ladder; ADR = why; spoke = current design;
  runbook = procedure; planning = future; journal = evidence/history; generated docs = live state.
- **Reality before prose:** resolve every conflict against code, tests, inventory, and current
  infrastructure. Never choose the newest-sounding paragraph.
- **No authority change:** this directive clarifies existing policy only. Any discovered boundary
  change stops and becomes a separate human-approved constitution decision.
- **Move, link, or delete:** preserve load-bearing meaning, but do not repeat it for reassurance.
- **Sibling boundaries:** SKY-012 owns executable-capability conversion; SKY-016 owns deploy feature
  improvements; SKY-020 owns firewall-as-code implementation. SKY-023 fixes their documentation
  contracts without absorbing their builds.

## 3. Plan

**Scope:** authored design, runbooks, their indexes, always-loaded summaries, and small lint/render
changes needed to prevent drift. **Non-goals:** infrastructure changes, new capabilities, autonomy
promotion, permission changes, or hand-editing generated outputs. **Rollback:** `git revert`.
**Human actions:** PR review/merge only; no grants or credentials.

### Phase 1 — reconcile truth before pruning  (~1–2h)   `[x]` complete 2026-09-05

1. Create a temporary conflict matrix: claim, competing sources, runtime evidence, chosen authority.
2. Resolve every contradiction named in §1, including:
   - all production OpenTofu procedures use the reviewed **saved-plan wrapper**; PR/approval precedes apply;
   - one verified Arcane env-materialization model;
   - current OPNsense, core-node/Unraid, Omada, forward-auth, L5-restore, grant-file, and drift behavior.
3. Update `AGENTS.md`, `README.md`, and `docs/architecture.md` to the same current truth.
4. Run existing invariant, link, and command checks. Do not weaken a gate to make prose pass.

**Exit:** no known conflicting operational instruction remains; each resolution cites its runtime or
test evidence; production runbooks contain no bare re-planning `tofu apply` path.

### Phase 2 — restore the documentation ownership model  (~1–2h)   `[ ]`

1. Reduce `docs/system-design.md` to authority, hard laws, versioned dials, autonomy ladder, agent
   contract, and extension/spoke index. Merge duplicate self-leash rules; replace growth prose with
   links to `planning/`; move ACL/API mechanics to their proper homes.
2. Make every spoke current-state only. Move rollout plans to directives, incidents/live rehearsals
   to `journal/`, rationale to ADRs, setup commands to scripts/runbooks, and live addresses/state to
   generated docs.
3. Collapse duplicated trust/auth/backup explanations into links to their authoritative spoke.
4. Keep a short migration map in the PR so reviewers can see where removed knowledge went.

**Exit:** constitution is at least **40% smaller**; design corpus at least **30% smaller**; no
`Planned expansion` sections remain in spokes; all removed load-bearing content has one reachable home.

### Phase 3 — make runbooks task-shaped  (~1–2h)   `[ ]`

1. Split `publish-service.md` into a small router plus internal-route, forward-auth, and public-tunnel
   procedures. A simple internal publish must not load unrelated Authentik/Cloudflare instructions.
2. Standardize runbooks on compact metadata plus: Preconditions → Steps → Verify → Rollback → Evidence.
   Remove repeated philosophy, tier explanations, and historical narrative.
3. State “diagnose imperatively, fix declaratively” once in the diagnosis index; keep one-line record
   steps in leaf runbooks.
4. Replace duplicated backup provisioning in `provision-vm.md` with a precise link to `backup.md`.
5. Generate the runbook catalog from frontmatter, or make one existing generator own it.

**Exit:** runbook corpus at least **20% smaller**; each publish leaf loads at most **40%** of the old
4,719-token monolith; every leaf remains independently executable.

### Phase 4 — make drift fail CI  (~1–2h)   `[ ]`

1. Add narrow deterministic checks for:
   - bare production `tofu apply` in runbooks;
   - stale/missing token frontmatter;
   - manually divergent runbook-catalog metadata;
   - forbidden generated-output edits;
   - links to missing files/scripts.
2. Encode stable duplicated facts in a machine-readable source or consistency test where generation is
   practical; do not attempt to lint judgement-heavy prose.
3. Run the full repo checks, regenerate only through owning scripts, and perform a cold-session review:
   one reviewer finds the trust tier, deploy procedure, restore status, and publish path without loading
   unrelated files.
4. Record before/after token totals and archive the conflict matrix as a journal session, not design prose.

**Exit:** CI catches the failure classes that caused this cleanup; all links/checks pass; the PR reports
token deltas and proves no invariant, authority boundary, rollback, or recovery step was lost.

## 4. ▶ Execute prompt

```
Promote SKY-023 with bin/plan start SKY-023, then read the resulting
planning/projects/SKY-023-eliminate-documentation-drift-and-shrink-operational-context.md in full.
Verify current repository and infrastructure reality before editing. Execute Phase <N> only.
Follow AGENTS.md; preserve docs/system-design.md authority; never hand-edit generated outputs; never
merge your own PR. Stop if reconciliation implies an authority change. Validate the phase exit
criteria, then perform Phase close-out.
```

## 5. Phase close-out

- Land one reviewable PR; the agent never merges it.
- Update `[[SKY-023-progress]]`, phase checkbox/frontmatter, and run `bin/plan list`.
- Continue with: `Continue SKY-023 at Phase <N+1>; read [[SKY-023-progress]], verify reality, and execute only that phase.`

## 6. Status log

- 2026-09-04 — minted from a repository-wide design/runbook redundancy audit; draft idea, not scheduled.
- 2026-09-04 — Phase 1 paused on `phase/sky-023-p1` after delegated final review found remaining
  contradictions in DNS deletion rollback, non-guest OpenTofu rollback, live Caddy drift detection,
  OPNsense actuator availability, forward-auth status, and Authentik mutation ordering. The working
  tree is a checkpoint, not a phase close-out. Resume Phase 1 only. Evidence:
  `journal/2026/2026-09-04-session-sky-023-p1-truth-reconciliation.md`.
- 2026-09-05 — Phase 1 complete in [PR #185](https://github.com/aliammar03/skynet/pull/185) on
  `phase/sky-023-p1`. Resolved the six final-review blockers,
  added a failure test that distinguishes existing-guest snapshot rollback from non-guest recovery,
  regenerated owned views, and passed the invariant, test, syntax, link, command-reference, and diff
  gates. The PR is merge-clean and CI-green after integrating current `main`. Evidence:
  `journal/2026/2026-09-05-session-sky-023-p1-close-out.md` and
  `journal/2026/2026-09-05-session-sky-023-p1-pr-integration.md`.
- 2026-09-05 — Corrected the Phase 1 overreach before merge: supervised T2 guest creates are allowed
  through the exact saved-plan wrapper; only A4 promotion remains blocked pending automatic rollback.
  Evidence: `journal/2026/2026-09-05-decision-sky-023-p1-create-blocker-correction.md`.
- 2026-09-05 — Re-audited and remediated the delegated-review blockers before close-out: authored
  Compose reverts are now report/prepare-only, Cloudflare inverses preserve complete records, saved-plan
  recovery fails closed, native core CTs are no longer described as pool members, and host root certs
  select one matching certificate. Evidence:
  `journal/2026/2026-09-05-session-sky-023-phase-1-audit-remediation.md`.
