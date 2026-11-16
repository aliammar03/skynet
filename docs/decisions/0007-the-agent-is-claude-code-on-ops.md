---
status: accepted
date: 2026-10-21
decision-makers: Ali
---

# The agent is Claude Code on ops, reached through Discord and the Claude app

## Context and Problem Statement

The agent needs a home inside the lab and a way for Ali to talk to it from anywhere. Telegram is
blocked here.

## Decision Outcome

Chosen option: **Claude Code** on the ops VM, as user `skynet`, reached through **Discord** (the
Channels plugin, `#skynet`) and the **Claude app** (Remote Control), because there is no custom UI
to build.

### Consequences

- Good, because both ways in already exist and work from a phone.
- Bad, because the agent's runs share Ali's Claude plan, so the unattended runs have a daily budget
  (`modules/agent-runs.nix`).

## More Information

Ali, 2026-10-21, at the start. ops and its sessions: `hosts/ops/README.md`.
