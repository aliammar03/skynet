# Project Diary

> Reusable derived decisions and lessons for agent intake. ADRs, current doctrine, active directives,
> and accepted evidence win conflicts; raw chronology belongs in [`journal/`](../journal/README.md).

## Decisions

- Git is operational truth. `agent_docs/` is compact agent memory derived from higher-authority
  sources, never runtime/configuration truth or a task database.
- Substantive construction uses Main-directed Light/Medium/Heavy routes. Main owns decisions and
  integration; bounded workers own their assigned context, implementation, verification, or docs.
- Main owns progress, diary, and latest-session memory. Archivist owns assigned overview, technology,
  and structure memory plus assigned current docs; Archivist never decides acceptance.
- Raw episodes are append-only and summarized only when read. Current docs contain current rules,
  not the story of how they were reached.
- Authored work always lands through a human-merged PR. Construction roles and implementation
  languages grant no production authority.

## Lessons

- Re-read the active directive from current `main` before relying on a local continuation: a
  concurrently merged decision can invalidate otherwise coherent work.
- Derived memory is useful only when its authority boundary is explicit and conflicts trigger repair
  against the higher-authority source.
- Token accounting must fail closed when ancestry, the first-commentary boundary, or recorded usage is
  incomplete; missing data is a limitation, not a value to estimate.
- Keep Main wakeups low by giving Companion bulky reusable context once and using delta/conflict checks
  later; retain direct Main reads for decision-critical evidence.
