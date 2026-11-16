---
status: accepted
date: 2026-11-05
decision-makers: Ali
---

# A comics agent of its own runs the library's day to day

## Context and Problem Statement

CLU needed eight fixes and still needed judgment: which volume, a series posted under another name,
a post damaged at upload against its repost, the right edition, digital over scan. Ali
(2026-10-30): "comics are really just gonna need a nanny llm agent". His Codex subscription sat
idle.

## Considered Options

- **Discord to the agent:** OpenAB (a thread per conversation, a Codex session per thread,
  allowlists, scheduled prompts); codex-discord-mcp (one session per channel); a bot of our own.
- **The model's home:** Codex CLI on Ali's ChatGPT subscription; the Skynet agent through its
  Discord plugin (its budget is Ali's Claude plan).
- **Its hands:** `comics-tools`, a program of our own with a fixed list of verbs; the agent on CLU's
  network with curl (CLU's internal port has no login, and one route rewrites every setting); an
  MCP server (more code).

## Decision Outcome

Chosen option: a **comics agent** of its own: Codex CLI on Ali's ChatGPT subscription, in Discord
through **OpenAB** (`#comics`, its desk thread), with a skill for comics and manga. It adds and
fills series and grabs by itself, at most 360 grabs an hour; swaps and deletions wait for Ali's ✅.
It holds no key: **`comics-tools`**, beside it, holds them and offers a fixed list of verbs, and is
the one thing besides the doors on CLU's network. Because the judgment calls need a model, and
Ali's idle subscription runs it, not the Skynet agent's budget.

### Consequences

- Good, because the agent itself stays off CLU's network and holds no key.
- Bad, because `comics-tools` and CLU's patches (`stacks/dmz/clu/patches`, until CLU ships them)
  are programs of our own.
- Bad, because it is a second agent with its own contract (`stacks/dmz/comics-agent/agent/`).
  Library changes are its work; the Skynet agent's are read-only checks and PRs.

## More Information

Ali, 2026-10-30; the plan PR #138 (2026-11-03); its exit test passed 2026-11-04. Its model is Sol at
high effort, chosen in the arena (ADR-0018; Ali, 2026-11-05). The stack: `stacks/dmz/comics-agent`.
