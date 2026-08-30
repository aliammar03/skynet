---
summary: "The report-only nightly maintenance run on both engine paths, and what it refreshes."
trigger: "Run the nightly / nightly timer"
tokens: 990
---

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
  narrative of `docs/generated/05-state-of-the-lab.md` and appends a raw journal session entry.
- **Fallback path** (`scripts/nightly.sh`): reached when *every* configured engine fails/absent —
  the same inventory refresh + render (incl. the agent digest `06-agent-digest.md`) + PR + a raw (LLM-free)
  journal entry, minus the LLM-authored **narrative prose** and grant audit.

## Steps (both paths)

1. **Refresh inventory** — `bin/ops collect` (every collector idempotent, read-only; no creds
   yet = exits 0 without writing).
2. **envsync** — `scripts/envsync.sh` re-encrypts any changed `project.env` → `.env.sops`.
3. **Render docs** — `scripts/render-docs.sh` rewrites the factual `docs/generated/` pages, then
   `scripts/render-digest.sh` regenerates the **agent cold-boot digest** `06-agent-digest.md`
   (recent decisions / open threads / recent episodes, from ADRs + the journal + the roadmap), and
   `scripts/render-context-map.sh` regenerates the **context map** `07-context-map.md` (what's
   loadable + its token cost). Both paths run all three; they are deterministic, machine-facing pages.
4. **(agent only) Narrative** — rewrite `docs/generated/05-state-of-the-lab.md`: the *human*
   state-of-the-lab — a beautifully formatted, honest read with agent commentary and *what changed
   since last night* (diff vs `main`). Have personality; keep it accurate; never overclaim. (The
   machine digest is a separate page, `06-agent-digest.md`, rendered in step 3 — don't hand-write it.)
5. **(agent only) Root-grant audit** — if a grant is active, grep each host's sshd log for cert
   KeyIDs (`grant+<host>+<ts>+by-ali`) → `inventory/grant-audit.json`. Skip if no root.
6. **Journal the run** — append a **raw** episodic session entry to `journal/` (episodic memory;
   [`journal/README.md`](../journal/README.md)). Agent path: `bin/new journal session "nightly
   <date>"`, filled with concrete facts (what ran, what changed vs `main`, anomalies, and any
   dead-ends under Graveyard). Fallback path: a minimal factual entry from the diff stat. **Raw,
   append-only, summarized only at read time — never pre-digested.**
7. **Open a PR** on branch `inventory/<date>` with the diff + summary. **The engine never merges by
   hand.** The merge is decided afterward by the deterministic gate `scripts/nightly-automerge.sh`
   (both paths call it): generated-only diff **and** green CI → squash-merge; anything else → left
   open for a human (merge-gate carve-out, [ADR 0004](../docs/decisions/0004-auto-merge-generated-only-nightly-prs.md); off-switch `OPS_NIGHTLY_AUTOMERGE=0`).

## Guardrails

- No T2 write or granted-root action unless it is on the auto-approve list (currently empty).
- Any anomaly (host unreachable, health red, unexpected diff) → flag in the summary; don't fix
  silently.
- The report is the artifact. Ali reads a week of these before autonomy widens.
