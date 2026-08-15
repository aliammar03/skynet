# Conventions

Rules every agent and every PR must follow. Short, enforceable, testable.

## Naming & addressing

- **VMID = 4 digits = VLAN + last octet.** VM 9090 = VLAN 90 + .90. Keep the convention.
- Static IPs are the exception, justified in an ADR (see `decisions/`). skynet-ops
  (10.10.90.90) is one such documented exception.
- Hostnames are lowercase, role-first: `vm-skynet-ops`, `docker-dmz`.

## Git

- **Never commit to `main` directly.** One branch per unit of work: `phase/<name>`,
  `deploy/<svc>`, `fix/<thing>`, `inventory/<date>`.
- One PR per phase / per change. PR descriptions **teach**: what changed, why, what merging causes.
- The agent **never merges its own PRs.** Ali merges. `git revert` is the rollback.
- Conventional-ish commit subjects: `scaffold:`, `deploy:`, `fix:`, `inventory:`, `docs:`.

## Secrets

- Only encrypted secrets in git: `compose/<svc>/.env.sops` (sops+age). Plaintext `.env`,
  `.env.git`, `project.env` are **gitignored**.
- Runtime private material lives 0600 under `/opt/skynet-ops/secrets/` — never in the repo.
- Never print a secret to logs, transcripts, or chat. Scripts must `set -euo pipefail`
  and avoid echoing secret values.

## Compose / Arcane

- Every `compose.yaml` **pins an exact version tag** — never `latest`. Renovate bumps them by PR.
- **Every service includes `env_file: .env`** so Arcane's merged env (`.env.git` + `project.env`) reaches it.
- Non-secret defaults *may* ship as a committed plaintext `.env` (Arcane ingests it as `.env.git`).
  **Secrets never** — they live only in `project.env` (→ `.env.sops`).
- One Arcane Git Sync per project dir; auto-sync on; Arcane auto-update off for git-synced projects.

## TLS to internal APIs — pin, never `-k`

Proxmox, PBS, and Technitium serve self-signed / private-CA certs. Collectors **never**
disable verification (`curl -k`) — the ops brain holds write tokens, so a MITM downgrade is
unacceptable. Instead each endpoint's cert is **pinned**:

- Pin once with `scripts/pin-cert.sh <host> <port> /opt/skynet-ops/certs/<name>.crt`.
- Collectors verify with `curl --cacert <pin>`; the pin path is `*_CACERT` in the secret env.
- **Pins are public** (a server cert is not a secret): they live in `/opt/skynet-ops/certs/`
  (dir 0755, files 0644, readable by the collector user) — *not* in `secrets/`.
- Re-pin if an endpoint rotates its cert (the collector will fail closed until you do).

## Generated / auto content — do not hand-edit

- `inventory/**` and `docs/generated/**` are machine-written. Edit the collector or renderer, never the output.

## Scripts

- Bash, `#!/usr/bin/env bash`, `set -euo pipefail`, a header comment (purpose, tier, usage).
- Idempotent where possible; read-only collectors must never mutate remote state.
