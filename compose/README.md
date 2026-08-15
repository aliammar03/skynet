# compose — one dir per service, Arcane git-syncs each

```
compose/<service>/
├── compose.yaml   # pinned image DIGESTS; env_file: .env; Arcane makes this read-only in its UI
├── .env.git       # NON-secret config, committed plaintext — Arcane's git layer
└── .env.sops      # secrets ONLY, sops+age (keys visible in diffs, values encrypted)
```

**The canonical "skynet way" for every service** (the standard this repo enforces):
digest-pinned images · `env_file: .env` · non-secret config in committed `.env.git` ·
secrets only in `.env.sops` · deployed via Arcane GitOps Sync from this repo. No inline
compose secrets, no file-based `.txt` docker secrets.

## The env-layering contract (Arcane, resolved in plan §4)

Arcane merges two layers into the effective `.env`:

- **`.env.git`** — repo-sourced, non-secret defaults (optional, committed plaintext).
- **`project.env`** — your UI edits, the **secret-bearing** layer, not reproducible from the repo.
  Your overrides always win; Arcane rewrites in place preserving order/comments. No clobbering by design.

Therefore:

1. `project.env` is what `scripts/envsync.sh` encrypts → `.env.sops` (nightly, on change).
2. **Every service must declare `env_file: .env`** in its compose so the merged values reach it.
3. Non-secret defaults *may* be a committed plaintext `.env` (ingested as `.env.git`); **secrets never**.
4. Auto-sync **only redeploys already-running projects** — a stopped project updates on next manual start.

Restore: `sops -d compose/<svc>/.env.sops > project.env` into the project dir; Arcane re-merges.
