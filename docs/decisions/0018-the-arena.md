---
status: accepted
date: 2026-11-04
decision-makers: Ali
---

# The arena: a bench for testing agents on Ali's subscriptions

## Context and Problem Statement

Ali (2026-11-04): Terra vs Sol vs Haiku vs Sonnet vs Opus, "how much usage they consume? What
effort is the best?", and a place to "make a test for model x, y or z, testing whatever … report me
results", not rigid: Skynet's summaries, media recommendations, Home Assistant, Gemini later. On his
subscriptions, not the API: usage is the share of his plans, read from what each CLI reports.

## Considered Options

- promptfoo, the mature eval runner: its Codex SDK is pinned below the Codex that lists
  `gpt-6.1-terra`, it reads no plan window, and it has no sandboxed world;
- a bench of our own, borrowing promptfoo's ideas (the judge, steps, variants, repeats, the matrix
  page).

## Decision Outcome

Chosen option: the **arena**, a bench of our own. A contestant is a lane (an agent CLI on one of
Ali's plans: Codex on ChatGPT, Claude Code on Claude) × model × effort × variant. It runs a test's
rounds in a frozen world of its own, the test's tools faked and nothing real reachable, scored by
the test's checks, a judge model and Ali's blind votes, with each run's share of the plan's windows
measured. The bench is in git (`stacks/dmz/arena`); the tests are the agent's working files, run
when the agent starts them.

### Consequences

- Good, because a question about models is answered on Ali's own tasks and plans.
- Bad, because the runs spend the plans the comics agent and the Skynet agent share: nothing runs
  on a deploy or a boot; the agent starts, watches, stops and reports, and the lanes pace
  themselves on the plans' windows.
- Bad, because it is a program of our own.

## More Information

Ali, 2026-11-04 (#161, #167). The first test, the comics agent's own tasks in a frozen library
(seven rounds from its first week):
- the qualifier, Codex at high effort (2026-11-04): Terra 98.2, Sol 98.2, Luna 96.6 at a quarter of
  Terra's plan a run; Astra dropped after three rounds (97.0, at 12 times Terra's plan a run);
- open-ended (`comics-open`): with the skill, Terra and Sol 100; cold (role and tools only), Sol
  92.9, Terra 90.2, Luna 81.0;
- the lean skill, all six models in one night (`comics-final`, 2026-11-05): Sol 100, Luna 100,
  Terra 99.6, Sonnet 99.6, Opus 99.3, Haiku 98.9, every miss in the patrol.

Ali chose Sol for `#comics` (2026-11-05): the best unaided, at about 0.3% of the Plus week a task.
The bench's parts: `stacks/dmz/arena/README.md`.
