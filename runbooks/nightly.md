# Runbook — nightly maintenance (report-only)

**Trigger:** systemd timer (`skynet-nightly.timer` on vm-skynet-ops) → `bin/ops nightly`.
**Tier:** T1 read + PR. **Mode:** report-only until actions are promoted to the AGENTS.md
auto-approve list.

## How it runs

`bin/ops nightly` prefers the **LLM engine**, and **falls back to a deterministic script** if
the engine can't run (missing/unauthed/errors) — so the nightly always produces a report.

- **Engine order:** nightly tries **primary → fallback engine → deterministic script**. Set it
  all in the timer's env file (`/home/ali/.config/skynet-ops/ops.env`, example:
  `scripts/systemd/ops.env.example`) — edits apply on the next run, no unit editing:
  - `OPS_ENGINE=codex|claude` — primary (default `codex`).
  - `OPS_ENGINE_FALLBACK=codex|claude|none` — secondary engine (default: the *other* one; so
    "prefer claude, run codex as fallback" is just `OPS_ENGINE=claude`).
  - `OPS_CODEX_MODEL` / `OPS_CLAUDE_MODEL` — model per engine (unset = engine default).
  - `OPS_ENGINE_CMD` — full override of the primary command; `OPS_NIGHTLY_MODE=script` forces
    the deterministic path.
- **Agent path:** the engine runs the pass below and additionally (re)writes the human-readable
  narrative `docs/generated/05-state-of-the-lab.md` and appends a raw journal session entry.
- **Fallback path** (`scripts/nightly.sh`): reached when *every* configured engine fails/absent —
  the same inventory refresh + render + PR + a raw (LLM-free) journal entry, minus the LLM-authored
  narrative and grant audit.

## Steps (both paths)

1. **Refresh inventory** — `bin/ops collect` (every collector idempotent, read-only; no creds
   yet = exits 0 without writing).
2. **envsync** — `scripts/envsync.sh` re-encrypts any changed `project.env` → `.env.sops`.
3. **Render docs** — `scripts/render-docs.sh` rewrites the factual `docs/generated/` pages.
4. **(agent only) Narrative** — rewrite `docs/generated/05-state-of-the-lab.md`: a beautifully
   formatted, honest state-of-the-lab with agent commentary and *what changed since last night*
   (diff vs `main`). Have some personality; keep it accurate; never overclaim.
5. **(agent only) Root-grant audit** — if a grant is active, grep each host's sshd log for cert
   KeyIDs (`grant+<host>+<ts>+by-ali`) → `inventory/grant-audit.json`. Skip if no root.
6. **Journal the run** — append a **raw** episodic session entry to `journal/` (episodic memory;
   [`journal/README.md`](../journal/README.md)). Agent path: `bin/new journal session "nightly
   <date>"`, filled with concrete facts (what ran, what changed vs `main`, anomalies, and any
   dead-ends under Graveyard). Fallback path: a minimal factual entry from the diff stat. **Raw,
   append-only, summarized only at read time — never pre-digested.**
7. **Open a PR** on branch `inventory/<date>` with the diff + summary. **Never merge it.**

## Guardrails

- No T2 write or granted-root action unless it is on the auto-approve list (currently empty).
- Any anomaly (host unreachable, health red, unexpected diff) → flag in the summary; don't fix
  silently.
- The report is the artifact. Ali reads a week of these before autonomy widens.
