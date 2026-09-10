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
| Episodic | What happened and why | `journal/`, ADRs, generated digest |

## Default-lean retrieval

Context is scarce operational capacity. A substantive Medium/Heavy construction session reads the
six compact files in [`../../agent_docs/`](../../agent_docs/) once plus its active directive, then
opens only decision-critical authoritative evidence. `agent_docs/` is derived memory: constitution,
runtime/configuration, current operational docs, active directives, and accepted evidence always win
conflicts. For other retrieval, load the smallest high-signal contract and use the generated
[context map](../generated/07-context-map.md) to select one relevant document.

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
