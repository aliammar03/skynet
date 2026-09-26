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
- `skynet` is on PATH as an ops VM system package; after a merge that changes `src/`, run
  `rebuild` so the nightly uses the merged engine.

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
2. **Refresh inventory** — `skynet collect all --repo .`. Every collector (Proxmox nodes and
   operate-token ACLs, PBS, Docker, Technitium DNS, live OPNsense, Omada, certificates, routes)
   validates and atomically publishes its observations plus matching receipt-bound markers
   (OPNsense publishes the paired firewall config + live state under two markers). A failed read
   retains its previous snapshot and records unavailable/failed evidence, while the remaining reads
   continue. Initial evidence setup failure invalidates prior success through the local attempt
   receipt and stops before reads; unconfirmed Docker reader cleanup stops the workflow with
   `recovery-required`. See the [package contract](../nix/README.md) for local
   storage/process recovery. Collection never renders docs.
3. **Render factual docs** — `skynet render docs --repo <checkout>` requires matching core, network, ACL, PBS, and Docker refresh evidence
   from this pass, within a 36-hour age ceiling. Failure leaves factual pages unchanged and
   records a render failure. A failed SQLite rebuild cannot supply an old cache to new pages.
4. **Optional agent work** — when an engine is available, it may write the human narrative and
   grant audit only. This stage cannot own the branch or PR lifecycle.
5. **Journal then render retrieval indexes** — the finalizer appends a raw journal session entry
   first, then `skynet render digest --repo <checkout>` regenerates the **recent-activity / episodic / open-thread
   retrieval view** `06-agent-digest.md` (recent decisions / open threads / recent episodes, from ADRs
   + the journal + the roadmap), and `skynet render context --repo <checkout>` regenerates the **on-demand
   context map** `07-context-map.md` (loadable paths + token costs). The current entry is therefore
   visible in the digest, while the map refreshes its routing metadata and episodic-store pointer.
6. **Open a PR** — the deterministic finalizer stages generated evidence, commits, pushes, and opens
   the PR on branch `inventory/<date>-<HHMM>` (the `HHMM` suffix lets same-day re-runs each
   get their own branch instead of colliding) with the diff + summary. **The engine never merges by
   hand.** Nightly auto-merge is suspended: every nightly PR remains open for human review. ADR 0004
   records the suspended generated-only carve-out.

## Verify

- Confirm the PR contains only the expected generated/encrypted paths, the current raw journal entry
  appears in the digest, the context map exposes current load-cost/routing rows, the deterministic
  PR is left open for human merge, and anomalies are visible.
- Run `skynet collect-status --repo .` before interpreting Proxmox, PBS, Docker, DNS, OPNsense or Omada observations; markers
  alone cannot establish freshness without their matching durable local receipt. The optional
  narrative must label retained snapshots/pages as previous evidence when that refresh failed.
  Collection freshness does not establish service health.

## Rollback

- Revert an incorrect generated-only nightly PR. Do not use the nightly to repair an anomaly; route a fix through its normal declarative PR.

## Evidence

- The raw journal entry, generated inventory/docs, grant audit when available, and nightly PR are the run evidence.

## Guardrails

- No T2 write or granted-root action unless it is on the auto-approve list (currently empty).
- Any anomaly (host unreachable, health red, unexpected diff) → flag in the summary; don't fix
  silently.
- The report is the artifact. Ali reads a week of these before autonomy widens.
