---
summary: "How Skynet keeps portable semantic, procedural, episodic, and working memory without overloading a fresh agent."
---

# Spoke · Agent memory

> How a stateless operator stores and retrieves memory. Governed by
> [`../system-design.md`](../system-design.md); journal record format lives in
> [`../../journal/README.md`](../../journal/README.md).

| Kind | Holds | Authoritative home |
|---|---|---|
| Working | The current task | Context window |
| Semantic | Current facts and state | `docs/`, `inventory/`, `docs/generated/` |
| Procedural | Executable knowledge | `runbooks/`, `scripts/`, `bin/` |
| Episodic | What happened and why | `journal/`, ADRs, generated digest |

## Default-lean retrieval

Context is scarce operational capacity. Load the smallest high-signal contract first, then retrieve
one relevant document through the generated [context map](../generated/07-context-map.md). It supplies
summary, trigger, and approximate load cost for each on-demand artifact. For broad historical
questions, use `bin/recall <topic>` or targeted journal search; retain the conclusion for the task,
not the entire corpus. A temporary retrieval summary is never a source of truth.

On cold boot, read the generated [agent digest](../generated/06-agent-digest.md) after the baseline
contract. The digest points to recent ADRs, open directives, and raw episodes; it does not replace
them. Its human counterpart is `05-state-of-the-lab.md`.

## Durable records

- **Journal:** raw dated session, incident, and decision episodes are append-only. Write with
  `bin/new journal`; correct an entry with a new one that links back. Write raw; summarize only when
  reading.
- **ADRs:** one amended-in-place record for each non-trivial settled decision.
- **Generated retrieval:** `scripts/render-digest.sh` derives the digest from git and the journal.
  Derived views are caches, never truth.

The repository's memory is portable across engines and rebuildable from git. Private engine memory
may assist a session but is never authoritative.
