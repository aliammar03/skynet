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
| Semantic | Current facts and agent orientation | authoritative `docs/`/config/state, `AGENTS.md`, the active directive |
| Procedural | Executable knowledge | `runbooks/`, `scripts/`, `bin/` |
| Episodic | What happened and why | `journal/`, ADRs, generated digest (retrieval view) |

## Default-lean retrieval

Context is scarce operational capacity. A fresh session starts with `AGENTS.md` plus the active
directive — whose status block is the one progress tracker — then opens only the authoritative
sources the task touches. There is no separate derived-memory layer to keep in sync.

For additional retrieval, use the generated [context map](../generated/07-context-map.md) on demand
to select one relevant document by path, trigger, and load cost. Use the generated [agent digest](../generated/06-agent-digest.md)
only when recent decisions, open threads, or raw episode pointers are useful. The digest is a cache,
not a fresh-session requirement or source of truth; its human counterpart is `05-state-of-the-lab.md`.
Use `skynet recall --repo <checkout> <topic> [...]` for ranked canonical-source retrieval. Terms are
OR-joined and interpreted as case-insensitive GNU extended regular expressions, preserving the
original scout dialect; generated derivatives are excluded and no retrieval result is persisted.

## Durable records

- **Journal:** raw dated session, incident, and decision episodes are append-only. Write with
  `skynet new journal`; correct an entry with a new one that links back. Write raw; summarize only when
  reading.
- **ADRs:** one amended-in-place record for each non-trivial settled decision.
- **Generated retrieval:** `skynet render digest` derives the recent-activity/episodic digest from
  git and the journal; `skynet render context` derives the on-demand load-cost index. Both
  views are caches, never truth.

The repository's memory is portable across engines and rebuildable from git. Private engine memory
may assist a session but is never authoritative.
