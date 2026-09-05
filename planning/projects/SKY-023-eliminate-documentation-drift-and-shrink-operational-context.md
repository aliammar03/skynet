---
id: SKY-023
title: Eliminate documentation drift and shrink operational context
status: in-progress
horizon: short
created: 2026-09-04
updated: 2026-09-05
phases: 4
current_phase: 3
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

**Scope:** authored design, runbooks, their indexes, always-loaded summaries, active planning/current
code comments, digest resolution, nightly workflow consolidation, editor-artifact hygiene, and narrow
merge-gate/lint/render fixes needed to enforce existing policy and prevent drift. **Non-goals:** infrastructure
changes, new capabilities, autonomy promotion, permission changes, editing journal/scratchpad/archive
history to make it read like current truth, or hand-editing generated outputs. **Rollback:** `git revert`.
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

### Phase 2 — restore the documentation ownership model  (~1–2h)   `[x]` complete 2026-09-05

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

### Phase 3 — fix the merge gate, then prune operational context   `[ ]`

Execute in bounded ~1–2h checkpoint batches: merge-gate repair first, documentation/editor cleanup
second, digest/nightly consolidation third. Record the completed batch and exact next step at each
checkpoint; keep Phase 3 open until all exit criteria pass. The gate repair is a separately reviewable,
human-merged fix PR under this phase and must land before cosmetic cleanup proceeds.

**Safety prerequisite — enforce the existing nightly merge contract:**

- In `scripts/nightly-automerge.sh`, separate successful PR file-list retrieval from path filtering.
  The current `gh pr diff ... | grep ... || true` treats a failed fetch as an empty allowed diff.
  Any retrieval failure, incomplete/empty response, or ambiguous PR identity must leave the PR open.
- Resolve only the nightly's exact PR/branch; do not fall back to an unrelated latest same-day PR.
  Validate the existing allowed paths and CI against the same head commit, then require that expected
  head when merging. If the head changes, stop or repeat all validation against the new head.
- Add mocked failure tests with this repair (do not defer them to Phase 4): file-list/API failure,
  empty file list, disallowed authored path, wrong PR identity, failed/pending/missing checks, and
  a changed head must never call merge; a matching allowed, CI-green head can merge. No live merge
  is part of the test. Preserve the current allowlist, off-switch, and human-merge authority.

**Documentation and context cleanup:**

1. Split `publish-service.md` into a small router plus internal-route, forward-auth, and public-tunnel
   procedures. A simple internal publish must not load unrelated Authentik/Cloudflare instructions.
2. Standardize runbooks on compact metadata plus: Preconditions → Steps → Verify → Rollback → Evidence.
   Remove repeated philosophy, tier explanations, and historical narrative.
3. State “diagnose imperatively, fix declaratively” once in the diagnosis index; keep one-line record
   steps in leaf runbooks.
4. Replace duplicated backup provisioning in `provision-vm.md` with a precise link to `backup.md`.
5. Generate the runbook catalog from frontmatter, or make one existing generator own it.
6. Do one **current-truth sweep** across active planning, runbooks, and live code/config comments after
   SKY-008's archive:
   - repair hard-coded links that still point at `planning/projects/SKY-008-*`; link the archive when
     provenance is genuinely useful, otherwise point at the current owner/capability;
   - remove stale current-tense `svc-tofu` instructions and retired `tofu-proxmox*.env` references from
     operational surfaces; the current Proxmox tofu identity is `svc-ops@pve!operate` where applicable;
   - strip historical directive narration such as “SKY-008 P3 introduced ...” from live `tofu/`,
     `scripts/`, `nix/`, and runbook comments. Keep only present behavior, safety constraints, and
     non-obvious operational gotchas. **Do not rewrite journals, scratchpads, or archived directives**;
   - fix stale factual comments exposed by later work, including claims such as CT 240 being the only
     managed LXC;
   - move any `status: done` directive that still lives outside `planning/archive/` into the archive
     (known example: SKY-022), then regenerate the roadmap with `bin/plan list`.

7. Prune repeated policy in `AGENTS.md` and `README.md`: retain the compact always-loaded operating
   contract and load-bearing safety constraints; link detailed exceptions to their authoritative
   homes. Correct blanket "never self-merge" claims to agree with the existing generated-only nightly
   exception. Report before/after word or token counts and verify that no trust boundary changed.
8. Repair `scripts/render-digest.sh` so current work comes from directive status and explicit durable
   resolution records, not verbatim historical follow-ups presented as still open. Preserve append-only
   journal evidence; do not infer resolution solely from a guest being absent from inventory. Include
   PR #185/#186 (both merged at review) and completed phase dependencies as regression examples;
   unresolved items remain visible, and unavailable status is unknown rather than resolved. Parse
   frontmatter correctly so inline template comments do not leak into the digest; use explicit time
   metadata for same-day chronology rather than reverse filename order. Regenerate via the renderer.
9. Consolidate `bin/ops nightly` and `scripts/nightly.sh` around one deterministic maintenance
   sequence owning collection, envsync, rendering, and PR preparation. Keep agent analysis/narrative
   optional, and preserve report-only behavior, grant-audit requirements, engine fallback, and the
   existing merge gate. Remove duplicate renders (including the render already inside `collect`),
   include the current journal entry in the final digest, and ensure fallback cannot repeat completed
   mutation steps or discard partial work. Use mocked commands to verify order and failure behavior.
10. Stop tracking personal Obsidian workspace state and bundled plugin binaries unless a documented
    offline/rebuild requirement needs them. Keep shared vault settings, record the plugin/version
    installation path in `docs/obsidian-setup.md`, and add narrow ignore rules. Verify fresh setup
    remains reproducible; do not delete users' installed local plugins or rewrite git history.

**Boundary:** repo cleanup only. If a stale root-owned symlink or other live-host residue is discovered,
record it as a separate operator cleanup; SKY-023 does not mutate infrastructure.

**Exit:** runbook corpus at least **20% smaller**; each publish leaf loads at most **40%** of the old
4,719-token monolith; every leaf remains independently executable; no active path points at SKY-008's
former `projects/` location; current operational surfaces do not instruct agents to use retired
`svc-tofu` credentials; live comments describe present behavior rather than project history; and no
`status: done` directive remains outside `planning/archive/`. The merge gate fails closed and merges
only the validated head; the digest does not revive resolved PRs/phases or hide unknown work; one
nightly sequence owns each deterministic step; repeated policy agrees with the constitution; and
editor artifacts are removed from tracking or retained with a documented rebuild justification.

### Phase 4 — make drift fail CI  (~1–2h)   `[ ]`

1. Add narrow deterministic checks for:
   - bare production `tofu apply` in runbooks;
   - stale/missing token frontmatter;
   - manually divergent runbook-catalog metadata;
   - forbidden generated-output edits;
   - links to missing files/scripts;
   - active references to archived directive paths such as `planning/projects/SKY-008-*`;
   - completed directives (`status: done`) living outside `planning/archive/`;
   - retired credential/file names in **current-authority surfaces** (`AGENTS.md`, `README.md`, `docs/`,
     `runbooks/`, `tofu/`, `scripts/`, `nix/`). Keep history-bearing trees (`journal/`,
     `planning/scratchpad/`, `planning/archive/`) explicitly outside this stale-history gate.
2. Wire the Phase 3 merge-gate, digest-resolution, and nightly-sequence regression tests into CI.
   Exercise both agent-enabled and deterministic/fallback paths without credentials or network writes;
   verify unknown/error states remain visible, render ordering includes the current episode, and no
   failed allowlist lookup or changed head can reach merge. Add narrow checks for ignored editor
   artifacts and contradictory merge-policy summaries where deterministic checks are practical.
3. Encode stable duplicated facts in a machine-readable source or consistency test where generation is
   practical; do not attempt to lint judgement-heavy prose. Prefer a small denylist/allowlist for
   retired identities and paths over broad prose rules that would reject legitimate historical evidence.
4. Run the full repo checks, regenerate only through owning scripts, and perform a cold-session review:
   one reviewer finds the trust tier, deploy procedure, restore status, publish path, and current tofu
   identity without loading unrelated or historical files.
5. Record before/after token totals and archive the conflict matrix as a journal session, not design prose.

**Exit:** CI catches the failure classes that caused this cleanup, including stale archive paths,
retired operational identities, done-directive placement, stale digest resolutions, duplicate nightly
steps, and merge-gate failures; all links/checks pass; the PR reports
token deltas and proves no invariant, authority boundary, rollback, recovery step, or historical
evidence was lost.

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
- 2026-09-05 — Phase 2 complete on `phase/sky-023-p2`: reduced the constitution from 4,244 to
  1,047 words and the design corpus from 14,830 to 5,201 words; made every spoke current-state only;
  removed roadmap, rehearsal, and procedure duplication in favor of directives, journal evidence,
  scripts, and runbooks. The master age-key exception is now explicit: `0640 root:users` permits
  unprivileged sops decryption. Evidence: `journal/2026/2026-09-05-session-sky-023-p2-close-out.md`.
- 2026-09-05 — Post-SKY-008 housekeeping folded into the remaining work after Ali archived SKY-008:
  P3 now owns current operational-reference/comment cleanup plus done-directive roadmap hygiene; P4
  adds deterministic guards for archived paths, retired operational identities, and misplaced done
  directives. Historical journal/scratchpad/archive evidence is intentionally left untouched.

- 2026-09-05 — Folded the quick repository review at `27e03ef` into remaining Phase 3/4 work:
  fail-closed nightly merge validation first; then digest resolution, repeated-policy pruning,
  the existing publish split, one deterministic nightly sequence, and Obsidian artifact hygiene.
  Phase 4 owns ongoing regression enforcement. This is a planning update only; implementation
  and phase completion are not claimed, and the existing trust/merge boundaries are unchanged.

- 2026-09-05 — Phase 3 merge-gate checkpoint prepared on
  `fix/sky-023-p3-nightly-merge-gate`: exact nightly-PR identity, non-empty file retrieval,
  explicit CI readback, and `--match-head-commit` validation all fail closed. Mocked regression
  tests cover retrieval, identity, checks, and head-change failures. This fix needs human review
  and merge before the Phase 3 documentation/editor-cleanup batch begins. Evidence:
  `journal/2026/2026-09-05-session-sky-023-p3-merge-gate-checkpoint.md`.

- 2026-09-05 — Phase 3 runbook-contract/publish-split checkpoint prepared on
  `docs/sky-023-p3-runbook-context-cleanup` after PR #190 merged. Split the publishing monolith
  into a router plus independently executable internal-route, forward-auth, and public-tunnel
  leaves; standardized every runbook leaf and rendered the catalog from frontmatter. The context
  map now discovers nested runbooks. This is not Phase completion: the recursive runbook corpus is
  14,276 words, so the 20%-smaller exit target and the remaining current-truth/editor/digest/nightly
  work remain open. Evidence:
  `journal/2026/2026-09-05-session-sky-023-p3-runbook-contract-publish-split.md`.

- 2026-09-05 — Phase 3 current-truth sweep checkpoint prepared on
  `docs/sky-023-p3-current-truth-sweep` after PR #191 merged. Archived completed SKY-022 and
  regenerated the roadmap; repaired active/archive links; removed retired-Proxmox-identity and
  project-history comments from operational code; and corrected the Cloudflare DNS token read path
  to the materialized `0400 aliammar` contract. This is not Phase completion: substantive corpus
  reduction plus digest/nightly consolidation remain open. Evidence:
  `journal/2026/2026-09-05-session-sky-023-p3-current-truth-sweep.md`.
