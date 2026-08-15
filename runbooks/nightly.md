# Runbook — nightly maintenance (report-only)

**Trigger:** systemd timer → `bin/ops nightly`. **Tier:** T1 read + PR. **Mode:** report-only
until actions are promoted to the AGENTS.md auto-approve list.

## Steps

1. **Refresh inventory** — run every collector (`bin/ops collect`), each idempotent and
   read-only. A collector with no creds yet exits 0 without writing.
2. **Harvest the root-grant audit** — grep each onboarded host's sshd log for cert KeyIDs
   (`grant+<host>+<ts>+by-ali`) and append to `inventory/` (who/what/when had root).
3. **envsync** — `scripts/envsync.sh` re-encrypts any changed `project.env` → `.env.sops`.
4. **Render docs** — `scripts/render-docs.sh` rewrites `docs/generated/` from fresh inventory.
5. **Open a PR** on branch `inventory/<date>` with the diff + a written summary. Never merge it.

## Guardrails

- No T2 write or granted-root action unless it is on the auto-approve list.
- Any anomaly (host unreachable, health red, unexpected diff) → flag in the summary, don't fix silently.
- The report is the artifact. Ali reads a week of these before autonomy widens.
