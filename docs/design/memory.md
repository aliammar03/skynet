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
| Semantic | Current facts and compact agent orientation | authoritative `docs/`/config/state plus derived `agent_docs/` |
| Procedural | Executable knowledge | `runbooks/`, `scripts/`, `bin/` |
| Episodic | What happened and why | `journal/`, ADRs, generated digest (retrieval view) |

## Default-lean retrieval

Context is scarce operational capacity. A fresh or substantive Medium/Heavy Main session starts with
the six compact files in [`../../agent_docs/`](../../agent_docs/) plus its active directive, then
opens only decision-critical authoritative evidence. `agent_docs/` is derived memory: constitution,
runtime/configuration, current operational docs, active directives, and accepted evidence always win
conflicts. This is the normal cross-session continuity path; it does not replace those authoritative
sources.

For additional retrieval, use the generated [context map](../generated/07-context-map.md) on demand
to select one relevant document by path, trigger, and load cost. Use the generated [agent digest](../generated/06-agent-digest.md)
only when recent decisions, open threads, or raw episode pointers are useful. The digest is a cache,
not a fresh-session requirement or source of truth; its human counterpart is `05-state-of-the-lab.md`.

## Durable records

- **Journal:** raw dated session, incident, and decision episodes are append-only. Write with
  `bin/new journal`; correct an entry with a new one that links back. Write raw; summarize only when
  reading.
- **ADRs:** one amended-in-place record for each non-trivial settled decision.
- **Generated retrieval:** `scripts/render-digest.sh` derives the recent-activity/episodic digest from
  git and the journal; `scripts/render-context-map.sh` derives the on-demand load-cost index. Both
  views are caches, never truth.

The repository's memory is portable across engines and rebuildable from git. Private engine memory
may assist a session but is never authoritative.
