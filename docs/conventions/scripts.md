# Spoke · Scripts (`scripts/`, `bin/`)

> Every executable in the repo looks the same, fails safe, and says what tier it runs at.
> Governed by [`../conventions.md`](../conventions.md).

Tags: **[testable]** = a lint gate could assert it; **[manual]** = holds by review.

## Every script

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
  backup, envsync). `[manual]`
