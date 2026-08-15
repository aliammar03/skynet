# compose — one dir per service, Arcane git-syncs each

```
compose/<service>/
├── compose.yaml   # pinned image DIGESTS; env_file: .env; Arcane makes this read-only in its UI
├── .env.git       # NON-secret config, committed plaintext — Arcane's git layer
└── .env.sops      # secrets ONLY, sops+age (keys visible in diffs, values encrypted)
```

**The canonical "skynet way" for every service** (the standard this repo enforces):
digest-pinned images · `env_file: .env` · non-secret config in committed `.env.git` ·
secrets only in `.env.sops` · **backup-friendly volumes** (absolute `/opt/docker/appdata/<svc>/…`
bind mounts, or named volumes labelled `com.aliammar.backup`; never relative in-project-dir data) ·
deployed via Arcane GitOps Sync from this repo. No inline compose config, no file-based `.txt`
docker secrets. Deploy with `scripts/gitops-deploy.sh <svc>` — see `runbooks/deploy-service.md`
for how the effective `.env` is materialised (Arcane GitOps does not merge `.env.git`/`project.env`).

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
