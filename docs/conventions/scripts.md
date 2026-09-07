---
summary: "Capability contracts, Python procedural code, existing Bash entry points, and verified TLS."
---

# Spoke · Capabilities and procedural code

> Every capability declares its scope, fails honestly, and provides verification and recovery.
> Governed by [`../conventions.md`](../conventions.md).

Tags: **[testable]** = a lint gate could assert it; **[manual]** = holds by review.

## Language and capability contract

- **New procedural logic uses Python** `[manual]`: one `src/skynet/` package and thin CLI,
  ordinary functions, synchronous execution first. Nix, OpenTofu, Compose/Caddy, SQL, and Markdown
  keep their declarative or documentation roles. Use existing Git, SSH, sops, restic, rclone, and PBS tools.
- **Scope, inputs, outcomes, verification, and recovery are explicit** `[manual]`. Missing, malformed,
  empty, stale, or unavailable evidence cannot establish health. Report success, failure, unavailable,
  skipped, or recovery-required with meaningful exit codes; JSON output must preserve those distinctions.
- **External boundaries fail safely** `[manual]`: validate responses, use argument arrays and timeouts,
  check subprocess results, redact errors, and preserve TLS verification. Reconcile an uncertain write
  before retrying. Record target, source/plan identity, completed steps, and required recovery.
- **Keep the package small** `[manual]`: stdlib first; dependencies and shared helpers need concrete
  callers. Nix owns runtime/dependencies; no production pip/npm installs. Test behavioral decisions
  with fake external boundaries; lint/type-check Python in CI when the package is introduced.
- **Shell requires a concrete caller or rescue/bootstrap need** `[manual]`. Record its owner and
  removal condition in planning. Existing Bash commands remain the installed implementation.

## Existing Bash scripts

- **Shebang `#!/usr/bin/env bash`** `[testable]` — bash, not `sh`.
- **`set -euo pipefail`** as the first executable line `[testable]`. Fail on error, unset var, or
  broken pipe.
- **A header comment block** `[testable]` directly under the shebang, stating:
  1. **purpose** — one line: `<name> — <what it does> → <what it produces>`
  2. **tier** — T1 / T2 / T2+ / T3, so the reader knows the blast radius before running it
  3. **usage** — the invocation, args, and where it reads creds/secrets from
- **`REPO_DIR` idiom** for path-independence `[manual]`:
  ```bash
  REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  ```
- **Guard required args** with `${1:?usage: …}` `[manual]` so a bare call self-documents.
- **Idempotent where possible** `[manual]` — re-running should converge, not duplicate.
- **Read-only collectors never mutate remote state** `[manual]`. A `collect-*.sh` is T1 by
  contract; if it would write, it isn't a collector.
- **Never echo a secret** `[manual]` — no secret value to stdout, logs, or transcripts. Read creds
  from `/opt/skynet-ops/secrets/<name>.env` and reference by var, never by literal.
- **Keep comments current-state only** `[manual]` — explain present behavior, constraints, and
  failure modes. Completed directive IDs, migration stories, and replacement narratives belong in
  journal/history/ADRs, not executable artifacts.

## TLS to internal APIs — pin, never `-k`

Proxmox, PBS, and Technitium serve self-signed / private-CA certs. Because the ops brain holds
write tokens, a silent MITM downgrade is unacceptable, so collectors **never** disable
verification.

- **Never `curl -k` / `--insecure`** against an internal API `[testable]`.
- **Pin the cert once** with `scripts/pin-cert.sh <host> <port> /opt/skynet-ops/certs/<name>.crt`
  `[manual]`; verify with `curl --cacert <pin>`. The pin path is a `*_CACERT` var in the secret env.
- **Pins are public, not secret** `[manual]` — a server cert isn't a secret. They live in
  `/opt/skynet-ops/certs/` (dir `0755`, files `0644`, collector-readable), **not** under
  `secrets/`. Re-pin when an endpoint rotates (the collector fails closed until you do).

## `bin/` vs `scripts/`

- **`bin/`** = operator-facing entry points a human/agent invokes directly (`bin/plan`, `bin/ops`,
  `bin/grant-root`). `[manual]`
- **`scripts/`** = the procedures those entry points and runbooks call (collectors, deploy,
  backup). `[manual]`
