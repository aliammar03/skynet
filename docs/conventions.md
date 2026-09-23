# Conventions

The house style every agent and every PR follows. **This file is the hub** — the invariant rules
that never move, plus an index into the spokes that carry the depth. It mirrors the constitution ↔
[`docs/design/`](design/) pattern: shrink the hub, push detail to spokes, keep one authoritative
home per rule. Governed by (and an extension point of) [`system-design.md`](system-design.md).

Every rule in the spokes is tagged **[testable]** (a lint gate could assert it mechanically) or
**[manual]** (holds by review). The tags distinguish rules that admit a deterministic gate from
rules that require judgment.

## Invariants — the rules that never move

These hold everywhere and don't get a "unless"; the spokes elaborate, never loosen them.

- **Never commit to `main` directly; every PR is human-merged.** Nightly self-merge is suspended.
  One branch per unit of work, one PR per change, `bin/check` green before review, `git revert` is
  the rollback. → [`conventions/git.md`](conventions/git.md)
- **No plaintext secrets in git — ever.** Only sops-encrypted `*.env.sops`, or agent-readable
  restrictive files under `/opt/skynet-ops/secrets/` (`0400 aliammar`; lab age key
  `0640 root:users`). The agent decrypts sops without sudo. The pre-commit scan enforces it.
  → [`conventions/compose.md`](conventions/compose.md), [`design/secrets.md`](design/secrets.md)
- **Never hand-edit generated dirs** (`inventory/**`, `docs/generated/**`) — edit the collector or
  renderer. → [`conventions/layout.md`](conventions/layout.md)
- **Collectors are read-only and never `curl -k`** against an internal API — pin the cert instead.
  → [`conventions/scripts.md`](conventions/scripts.md)
- **Every service conforms to the skynet way** — digest-pinned image, `env_file: .env`, secrets
  only in `.env.sops`, a healthcheck, one role tag. → [`conventions/compose.md`](conventions/compose.md)
- **VMID = VLAN + last octet; static addressing is the standard for every guest.**
  → [`conventions/naming.md`](conventions/naming.md)
- **One authoritative home per rule** — state it once, link everywhere else.
  → [`conventions/docs.md`](conventions/docs.md)
- **Construction is agent-agnostic and unprivileged** — one session owns a change on one PR, proves
  it with `bin/check`, and gets a Light or Full review; **no engine ever gains production authority**. → [`conventions/construction.md`](conventions/construction.md)

## The spokes

| Spoke | Covers |
|---|---|
| [naming](conventions/naming.md) | VMID/IP scheme, static addressing, hostnames, **entity IDs + VLAN slugs**, slugs, branch names |
| [layout](conventions/layout.md) | Repo map; required files per artifact type; generated dirs |
| [scripts](conventions/scripts.md) | Language-neutral contracts, Python procedural code, existing Bash style, TLS pinning |
| [compose](conventions/compose.md) | The skynet way: pinned digests, env layering, healthchecks, volumes, tags |
| [git](conventions/git.md) | Branch grammar, PR discipline, commit subjects, what never commits |
| [docs](conventions/docs.md) | Hub-and-spoke pattern, ADR & runbook format, README-as-catalog |
| [metadata](conventions/metadata.md) | Directive/service frontmatter schemas, compose label/tag namespaces |
| [construction](conventions/construction.md) | The build loop, Light/Full review tiers, test evidence, engine-agnostic trust boundary |

**Adding a convention:** put the rule in the right spoke (or add a spoke), tag it
[testable]/[manual], and — if it's load-bearing — surface a one-liner in the invariants above. A
new spoke is a PR here, the same way a new design spoke is a PR to the constitution.
