# Runbook — deploy / update a service (Arcane GitOps)

**Tier:** T2 (PR-gated). **Executor:** Arcane Git Sync. **Rollback:** `git revert`.

## Steps

1. **Branch** `deploy/<svc>`. Create/edit `compose/<svc>/compose.yaml`:
   - pin an exact image tag (never `latest`);
   - include `env_file: .env` on every service (so Arcane's merged env reaches it);
   - commit non-secret defaults as plaintext `.env` if useful (Arcane ingests as `.env.git`). **Secrets never.**
2. **Secrets** (if any) live in Arcane's `project.env` (the UI). `envsync.sh` captures them to
   `compose/<svc>/.env.sops`. To seed on restore: `sops -d compose/<svc>/.env.sops > project.env`.
3. **PR** with a teaching description: what the service is, ports, front door, backup impact.
4. **Ali merges.** Arcane Git Sync polls → pulls → reconciles. The compose goes read-only in the UI.
   (Auto-sync only redeploys already-running projects; a stopped one updates on next manual start.)
5. **Verify health** via Arcane API / `docker context`. If red → `git revert`, Arcane converges back.
6. **Land evidence:** refresh inventory, commit, summarize. Add a DNS split-record via Technitium (T2)
   if the service needs one.
