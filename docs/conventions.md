# Conventions

The house style every agent and every PR follows. **This file is the hub** — the invariant rules
that never move, plus an index into the spokes that carry the depth. It mirrors the constitution ↔
[`docs/design/`](design/) pattern: shrink the hub, push detail to spokes, keep one authoritative
home per rule. Governed by (and an extension point of) [`system-design.md`](system-design.md).

Every rule in the spokes is tagged **[testable]** (a lint gate could assert it mechanically) or
**[manual]** (holds by review). The tags exist so the parked convention lint gate
(`planning/scratchpad/2026-08-17-lint-gate-convention-enforcement.md`) can lift them verbatim when
it's revived.

## Invariants — the rules that never move

These hold everywhere and don't get a "unless"; the spokes elaborate, never loosen them.

- **Never commit to `main` directly; the agent never merges its own PRs.** One branch per unit of
  work, one PR per change, `git revert` is the rollback. → [`conventions/git.md`](conventions/git.md)
- **No plaintext secrets in git — ever.** Only sops-encrypted `*.env.sops`, or `0600` under
  `/opt/skynet-ops/secrets/`. The pre-commit scan enforces it.
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

## The spokes

| Spoke | Covers |
|---|---|
| [naming](conventions/naming.md) | VMID/IP scheme, static addressing, hostnames, **entity IDs + VLAN slugs**, slugs, branch names |
| [layout](conventions/layout.md) | Repo map; required files per artifact type; generated dirs |
| [scripts](conventions/scripts.md) | Bash header/flags, `REPO_DIR` idiom, TLS pinning, `bin/` vs `scripts/` |
| [compose](conventions/compose.md) | The skynet way: pinned digests, env layering, healthchecks, volumes, tags |
| [git](conventions/git.md) | Branch grammar, PR discipline, commit subjects, what never commits |
| [docs](conventions/docs.md) | Hub-and-spoke pattern, ADR & runbook format, README-as-catalog |
| [metadata](conventions/metadata.md) | Directive/service frontmatter schemas, compose label/tag namespaces |

**Adding a convention:** put the rule in the right spoke (or add a spoke), tag it
[testable]/[manual], and — if it's load-bearing — surface a one-liner in the invariants above. A
new spoke is a PR here, the same way a new design spoke is a PR to the constitution.
