# Project Diary

> Reusable derived decisions and lessons for agent intake. ADRs, current doctrine, active directives,
> and accepted evidence win conflicts; raw chronology belongs in [`journal/`](../journal/README.md).

## Decisions

- Git is operational truth. `agent_docs/` is compact agent memory derived from higher-authority
  sources, never runtime/configuration truth or a task database.
- Substantive construction uses Main-directed Light/Medium/Heavy routes. Main owns internal
  integration/implementation acceptance and authored-PR readiness inside the implementation swarm,
  plus implementation decisions and integration; bounded workers own their assigned context,
  implementation, verification, or docs. External final acceptance belongs only to a separate fresh
  reviewer manually started by Ali against the exact open PR head.
- Main owns progress, diary, and latest-session memory. Archivist owns assigned overview, technology,
  and structure memory plus assigned current docs; Archivist never decides internal integration
  acceptance or external final acceptance.
- Raw episodes are append-only and summarized only when read. Current docs contain current rules,
  not the story of how they were reached.
- Authored work always lands through a human-merged PR. Construction roles and implementation
  languages grant no production authority.
- Final acceptance review is operator-started. An implementation or fix session publishes its authored
  PR, reports the review handoff, and stops; Ali manually starts each fresh reviewer in a separate chat
  against that open PR. Implementation sessions never launch their own acceptance review or re-review.
  Only after ACCEPT does Ali human-merge the reviewed PR; durable post-merge state/archive updates are
  a bounded closeout, not another automatic acceptance review.
- The unprivileged NixOS `aliammar` account is the construction filesystem/OS boundary. Native
  construction inherits its no-prompt Codex posture; self-root and authored self-merge are forbidden,
  and production authority remains governed separately by trust-tier contracts.
- Cross-session construction continuity starts with the six `agent_docs/` files plus the active
  directive. The generated digest is only a recent-activity/episodic/open-thread retrieval view; the
  context map is only an on-demand load-cost router. Disposable checkpoint state has no repository role.

## Lessons

- Re-read the active directive from current `main` before relying on a local continuation: a
  concurrently merged decision can invalidate otherwise coherent work.
- Derived memory is useful only when its authority boundary is explicit and conflicts trigger repair
  against the higher-authority source.
- Token accounting must fail closed when ancestry, the first-commentary boundary, or recorded usage is
  incomplete; missing data is a limitation, not a value to estimate.
- Keep Main wakeups low by giving Companion bulky reusable context once and using delta/conflict checks
  later; retain direct Main reads for decision-critical evidence.
- Approval ergonomics are not an authority model: keep ordinary construction quiet at the Unix
  boundary and encode the two prohibited self-actions as deterministic hard blocks.
- A real conflict is better continuity evidence than a synthetic stale-memory fixture: when derived
  memory disagrees with merged Git or installed runtime, use the higher authority immediately and
  repair the handoff at the owned closure point.
- Current planning prompts and active directives are construction callers too; legacy-role scans that
  cover only role files and doctrine can miss live routing language there.
