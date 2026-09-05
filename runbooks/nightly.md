---
summary: "The report-only nightly maintenance run on both engine paths, and what it refreshes."
trigger: "Run the nightly / nightly timer"
tier: "T1 read + generated-only PR"
executor: "bin/ops nightly"
rollback: "git revert generated nightly PR"
---

# Runbook — nightly maintenance (report-only)

**Trigger:** systemd timer (`skynet-nightly.timer` on vm-skynet-ops) → `bin/ops nightly`.
**Tier:** T1 read + PR. **Mode:** report-only until actions are promoted to the AGENTS.md
auto-approve list.

## Preconditions

- Keep the configured engine and fallback in the timer environment; the job remains report-only outside the versioned auto-approve list.

## Steps

### Choose an execution path

`bin/ops nightly` always runs one deterministic sequence. It may insert an **LLM engine** for the
optional human narrative and root-grant audit; an unavailable or failed engine does not repeat or
discard the prepared deterministic work.

- **Engine order:** nightly tries **primary → fallback engine** for the optional stage, then always
  finalizes deterministically. Set it
  all in the timer's env file (`/home/ali/.config/skynet-ops/ops.env`, example:
  `scripts/systemd/ops.env.example`) — edits apply on the next run, no unit editing:
  - `OPS_ENGINE=codex|claude` — primary (default `codex`).
  - `OPS_ENGINE_FALLBACK=codex|claude|none` — secondary engine (default: the *other* one; so
    "prefer claude, run codex as fallback" is just `OPS_ENGINE=claude`).
  - `OPS_CODEX_MODEL` / `OPS_CLAUDE_MODEL` — model per engine (unset = engine default).
  - `OPS_ENGINE_CMD` — full override of the primary command; `OPS_NIGHTLY_MODE=script` forces
    the deterministic path.
- **Optional agent stage:** after deterministic preparation, the engine may harvest a live root-grant
  audit and rewrite `docs/generated/05-state-of-the-lab.md`. It does not collect, render deterministic
  pages, journal, commit, push, create a PR, or merge.
- **Fallback:** if every configured engine fails or is absent, `scripts/nightly.sh --finalize` runs
  against the already-prepared branch. It preserves that partial work, adds the LLM-free evidence,
  and prepares the same PR.

### Run the shared maintenance sequence

1. **Prepare one branch** — `scripts/nightly.sh --prepare` requires a clean worktree, fetches the
   latest `main`, then creates the timestamped nightly branch. A failed fetch stops safely rather
   than producing a report against an unknown base.
2. **Refresh inventory** — `scripts/collect-all.sh` runs every idempotent, read-only collector;
   a failed collector is recorded while the remaining T1 collection continues. It never renders docs.
3. **Legacy env import** — `scripts/envsync.sh` encrypts any legacy `project.env` it finds; current
   GitOps services already use committed `.env.git` + `.env.sops`, so a missing file is expected.
4. **Render factual docs** — `scripts/render-docs.sh` rewrites the factual `docs/generated/` pages.
5. **Optional agent work** — when an engine is available, it may write the human narrative and
   grant audit only. This stage cannot own the branch or PR lifecycle.
6. **Journal then render routing pages** — the finalizer appends a raw journal session entry first,
   then `scripts/render-digest.sh` regenerates the **agent cold-boot digest** `06-agent-digest.md`
   (recent decisions / open threads / recent episodes, from ADRs + the journal + the roadmap), and
   `scripts/render-context-map.sh` regenerates the **context map** `07-context-map.md` (what's
   loadable + its token cost). The current entry is therefore visible in both machine-facing pages.
7. **Open a PR** — the deterministic finalizer stages generated evidence, commits, pushes, and opens
   the PR on branch `inventory/<date>-<HHMM>` (the `HHMM` suffix lets same-day re-runs each
   get their own branch instead of colliding) with the diff + summary. **The engine never merges by
   hand.** The merge is decided afterward by the deterministic gate `scripts/nightly-automerge.sh`
   (both paths call it): generated-only diff **and** green CI → squash-merge; anything else → left
   open for a human (merge-gate carve-out, [ADR 0004](../docs/decisions/0004-auto-merge-generated-only-nightly-prs.md); off-switch `OPS_NIGHTLY_AUTOMERGE=0`).

## Verify

- Confirm the PR contains only the expected generated/encrypted paths, the current raw journal entry
  appears in the digest, the deterministic merge gate reports its decision, and anomalies are visible.

## Rollback

- Revert an incorrect generated-only nightly PR. Do not use the nightly to repair an anomaly; route a fix through its normal declarative PR.

## Evidence

- The raw journal entry, generated inventory/docs, grant audit when available, and nightly PR are the run evidence.

## Guardrails

- No T2 write or granted-root action unless it is on the auto-approve list (currently empty).
- Any anomaly (host unreachable, health red, unexpected diff) → flag in the summary; don't fix
  silently.
- The report is the artifact. Ali reads a week of these before autonomy widens.
