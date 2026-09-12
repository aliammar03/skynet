# Project Diary

> Reusable derived decisions and lessons for agent intake. ADRs, current doctrine, active directives,
> and accepted evidence win conflicts; raw chronology belongs in [`journal/`](../journal/README.md).

## Decisions

- Git is operational truth. `agent_docs/` is compact agent memory derived from higher-authority
  sources, never runtime/configuration truth or a task database.
- Substantive construction uses Main-directed Light/Medium/Heavy routes. Main owns internal
  integration/implementation acceptance and authored-PR readiness inside the implementation swarm;
  bounded workers own assigned context, implementation, verification, or docs. External final
  acceptance belongs only to a separate fresh reviewer manually started by Ali.
- Fresh review resolves current target/base SHA + PR-head SHA, reviews that integration result, and
  rechecks both immediately before verdict. Every final ACCEPT/FIX/BLOCKED verdict is persisted as one
  machine-readable `skynet-acceptance:v1` marker on the PR. The newest applicable marker is authoritative;
  a newer FIX/BLOCKED revokes any older ACCEPT even when the reviewed revisions are unchanged.
- After ACCEPT, the original implementation/fix session validates that the newest applicable marker is
  still ACCEPT and performs **bounded closeout on that same accepted PR before merge**. Allowed
  post-ACCEPT Git changes are directive/archive/planning state, Main-owned deployment-state `agent_docs`,
  append-only journal closure evidence, and generator-owned closure views. Source/runtime/config/tests/
  invariants/AGENTS/doctrine/runbooks/behavioral docs/stable memory or other substantive changes
  invalidate ACCEPT and require fresh review.
- The sanctioned closeout commit moves PR head by design and does not itself invalidate ACCEPT. A
  reviewed-base movement, unexplained head movement, newer non-ACCEPT review-state marker, or
  substantive post-ACCEPT delta does. Main proves marker-head..final-head is closeout-only; Ali never
  performs SHA comparison.
- Normal authored work therefore uses **one PR and one human merge**: implementation → fresh review →
  durable verdict marker → same-PR closeout only when newest verdict is ACCEPT → human merge. There is
  no closeout-only PR and no automatic second review for a valid closeout-only delta.
- SKY-026's first real same-PR closeout proved the stale-ACCEPT escape hatch: final CI exposed a
  regression test that assumed the directive could never move from `planning/projects/` to
  `planning/archive/`. Fixing that test was substantive, so the ACCEPT was invalidated and SKY-026
  returned to fresh review instead of disguising the repair as bookkeeping.
- Private GitHub Free leaves a residual race between the final agent recheck and Ali clicking Merge;
  the workflow does not claim atomicity and does not require a paid GitHub feature or manual SHA work.
- Main owns progress, diary, and latest-session memory. Archivist owns assigned overview, technology,
  and structure memory plus assigned current docs **before external review**; those stable surfaces are
  frozen after ACCEPT because accepted closeout is Main-only bookkeeping.
- Raw episodes are append-only and summarized only when read. Current docs contain current rules, not
  the story of how they were reached.
- Authored work always lands through a human-merged PR. Construction roles and implementation languages
  grant no production authority.
- A directive may define one bounded legacy transition for work already merged before the current
  pre-merge lifecycle. A legacy FIX opens a corrective PR and returns to the normal lifecycle. If a
  legacy ACCEPT has no open PR but a natural next implementation PR follows, carry the tiny accepted-
  state bookkeeping into that next PR rather than creating a standalone closeout PR.
- SKY-025 uses one open authored PR per numbered phase from P8 onward. Internal slices remain on that
  phase PR. A normal phase is reviewed while open, then closed out on that same accepted PR and merged
  once. P7 is the sole already-merged legacy exception; P7 ACCEPT is recorded as opening bookkeeping in
  the P8 PR, while corrective P7 uses the normal open-PR lifecycle.
- The unprivileged NixOS `aliammar` account is the construction filesystem/OS boundary. Native
  construction inherits its no-prompt Codex posture; self-root and authored self-merge are forbidden,
  and production authority remains governed separately by trust-tier contracts.
- Cross-session construction continuity starts with the six `agent_docs/` files plus the active
  directive. The generated digest is only a recent-activity/episodic/open-thread retrieval view; the
  context map is only an on-demand load-cost router. Disposable checkpoint state has no repository role.

## Lessons

- Re-read the active directive from current `main` before relying on a local continuation: a concurrently
  merged decision can invalidate otherwise coherent work.
- Derived memory is useful only when its authority boundary is explicit and conflicts trigger repair
  against the higher-authority source.
- Keep accepted closeout mechanically boring. If it needs to touch implementation or behavioral truth,
  it is not closeout anymore and must go back through review.
- A green pre-ACCEPT suite is not enough to prove the closeout transition itself works; lifecycle tests
  must tolerate legitimate state movement such as an active directive becoming archived.
- Durable review state must persist negative verdicts too. Otherwise an older ACCEPT can survive a newer
  FIX/BLOCKED on the exact same revision and incorrectly authorize closeout.
- The reviewer-owned PR marker plus a machine-checked closeout-only delta gives the implementation
  session enough evidence to close accepted work without making Ali shuttle revision hashes.
- Token accounting must fail closed when ancestry, the first-commentary boundary, or recorded usage is
  incomplete; missing data is a limitation, not a value to estimate.
- Keep Main wakeups low by giving Companion bulky reusable context once and using delta/conflict checks
  later; retain direct Main reads for decision-critical evidence.
- Approval ergonomics are not an authority model: keep ordinary construction quiet at the Unix boundary
  and encode prohibited self-actions as deterministic hard blocks.
- Current planning prompts and active directives are construction callers too; legacy scans that cover
  only role files and doctrine can miss live routing language there.
