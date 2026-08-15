# Runbook — nightly maintenance (report-only)

**Trigger:** systemd timer (`skynet-nightly.timer` on vm-skynet-ops) → `bin/ops nightly`.
**Tier:** T1 read + PR. **Mode:** report-only until actions are promoted to the AGENTS.md
auto-approve list.

## How it runs

`bin/ops nightly` prefers the **LLM engine**, and **falls back to a deterministic script** if
the engine can't run (missing/unauthed/errors) — so the nightly always produces a report.

- **Pick the engine:** `OPS_ENGINE=codex` (default) or `OPS_ENGINE=claude`. Set it in the
  timer's env file (`/home/ali/.config/skynet-ops/ops.env`) to experiment without editing units.
  `OPS_ENGINE_CMD` overrides the command entirely; `OPS_NIGHTLY_MODE=script` forces the
  deterministic path.
- **Agent path** (`OPS_ENGINE_BIN` present): the engine runs the pass below and additionally
  (re)writes the human-readable narrative `docs/generated/05-state-of-the-lab.md`.
- **Fallback path** (`scripts/nightly.sh`): the same inventory refresh + render + PR, minus the
  LLM-authored narrative and the root-grant audit.

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
6. **Open a PR** on branch `inventory/<date>` with the diff + summary. **Never merge it.**

## Guardrails

- No T2 write or granted-root action unless it is on the auto-approve list (currently empty).
- Any anomaly (host unreachable, health red, unexpected diff) → flag in the summary; don't fix
  silently.
- The report is the artifact. Ali reads a week of these before autonomy widens.
