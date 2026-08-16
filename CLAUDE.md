# CLAUDE.md — Skynet ops agent (Claude Code)

Skynet is **agent-agnostic by contract**: the operating manual is vendor-neutral and lives in
[`AGENTS.md`](AGENTS.md) (Codex CLI reads that natively; Claude Code, Goose, Amp and others honor
it). The authoritative design is [`docs/system-design.md`](docs/system-design.md).

To keep **one source of truth** — so the two engines can't drift — this file adds nothing of its
own; it imports the shared contract below. Everything in `AGENTS.md` applies to you exactly as
written: the trust tiers, the plan-loudly/run-quietly execution policy, and the Judgement Day
invariants (never merge your own PRs, no plaintext secrets, narrowest/shortest grants).

If this file and `AGENTS.md` ever disagree, `AGENTS.md` wins and this file is the bug — edit the
shared contract, not a Claude-only fork.

@AGENTS.md
