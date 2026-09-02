---
date: 2026-09-03
kind: session          # session | incident | decision
title: SKY-018 P6 — L7 rollback executors
tier_touched: [T1, T2]  # T1 build; T2 live runs (Cloudflare DNS write, Proxmox operate-token snapshot)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-018, ADR-0005, PR-141]                # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
---

# 2026-09-03 · session · SKY-018 P6 — L7 rollback executors

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Continue-prompt: verify P5 closed on main, then execute P6 (L7 rollback executors), no P7/SKY-020.

P5 verify: PR #141 merged (a7968ec). scripts/collect-routes.sh, collect-certs.sh, inventory/
routes.json + certs.json, vhost audit, 30-services all present. memory/phase-box/frontmatter/digest/
roadmap all already at 5/12. The one gap: the directive §6 status log had NO P5 entry (last entry
was the P3/P4 combined one). Added a P5 entry — metadata reconciliation only, no architecture change.

P6 branch surprise: `phase/sky-018-p6-rollback-executors` ALREADY existed with one commit c241489
"SKY-018 P6 (1/3): DNS rollback executor". `git diff main..branch` showed ~57 files incl. DELETIONS
of tofu/*.tf, journal entries, SKY-008 P3 work — looked like it would revert landed work. It was NOT:
`git merge-base --is-ancestor c241489^ main` → the branch parent (edfb521, an OLDER main) IS on main,
so the "deletions" were just the branch being behind. `git rebase main` → clean; the real P6 commit
touches only 5 files. Rebased, kept the good DNS executor.

Built the other two executors. Design rule throughout: the rollback DECISION is deterministic tooling,
not the LLM (ADR 0005 §3). Each executor is dumb + agent-independent + tested in the failure case.

## Actions & outcomes
- rebased P6 branch onto main → only c241489 (DNS, 5 files) on top, clean
- scripts/gitops-rollback.sh (compose executor: git revert deploy commit → push → best-effort Arcane
  re-sync) → new
- scripts/deploy-gate.sh (deterministic decider: probe every project container Running/!Restarting/
  healthy-or-none; DEPLOY_GATE_PROBE injectable) → new; fires the executor on failure, exit 1
- gitops-deploy.sh gained `--gate [--revert-commit <sha>]`, execs deploy-gate at the end → edited
- tests/compose-rollback-test.sh → 7/7 (unhealthy→executor fires; healthy→doesn't; revert+push asserted)
  - FIRST RUN failed: `local arc() {...}` inside default_probe = bash syntax error near `(`. `bash -n`
    caught it. Fix: `arc() {...}`. → green.
- scripts/pve-snapshot.sh (create/rollback/delete via Proxmox API + operate token; waits on the UPID
  task) → new
- scripts/tofu-apply.sh (saved-plan only; refuses delete/replace + T3 excluded guests exit 3; snapshot
  every touched in-pool guest, fail-closed exit 4; apply; verify post-apply plan clean; rollback on
  apply exit 5 / verify exit 6; prune on success) → new
- tests/tofu-rollback-test.sh → 9/9
  - FIRST RUN failed: test made `${TMP}/tofu` both the stub binary AND the TOFU_DIR (`Is a directory`,
    rc 126). Fix: TOFU_DIR=`${TMP}/tdir`. → green.
- docs/design/actuators.md (new spoke: executor registry table + deterministic-rollback rule) → new;
  system-design §7 row + gitops-loop rollback pointer added
- both new tests wired into .github/workflows/checks.yml + .githooks/pre-commit
- full gate suite green: budget --check, check-invariants, entity 45/45, digest 5/5, dns-revert 5/5,
  compose-rollback 7/7, tofu-rollback 9/9, secret-scan
- directive frontmatter current_phase 5→6, updated →2026-09-03, P6 box [x]; §6 P5+P6 log entries;
  memory SKY-018-progress refreshed; bin/plan list → 6/12

## Live production runs (2026-09-03, after the PR) + bugs they caught
Ali: "let's mint the PVE_OPERATE_TOKEN. live production runs after please."
- **Nothing to mint.** The operate token already exists (A6 bootstrap) and is already sops-managed —
  the secret files carry it as `PVE_TOKEN_OPERATE` (`svc-ops@pve!operate=…`), NOT the `PVE_OPERATE_TOKEN`
  my script guessed. Verified auth on both nodes (GET /version OK). Fixed pve-snapshot.sh to read
  `PVE_TOKEN_OPERATE` (env `PVE_OPERATE_TOKEN` still overrides for a one-off). Also learned: the agent
  (aliammar) READS these secrets directly (sops-nix → /run/secrets/<name> owner=aliammar → symlinked
  into /opt/skynet-ops/secrets); the secrets DIR is 0711 root so you can't `ls` it, but you can read a
  known file. `sudo -n` is only `systemctl … skynet-*`.
- **LIVE snapshot create+delete on docker-dmz (10015)** via pve-snapshot.sh + operate token → worked,
  non-disruptive. Real operate-token snapshot lifecycle proven.
- **LIVE DNS create→revert on real Cloudflare** (throwaway sky018-p6-canary.aliammar.net). Caught TWO
  bugs the harness missed (harness undo was `touch`, no option tokens, no re-record):
  1. `jq … --args … --delete …` → jq parses `--delete` as its OWN option → the inverse was never
     recorded, canary left lingering. Fix: build the undo array via `--argjson` (printf|jq -R|jq -s),
     no `--args`. +regression test (option-like token).
  2. The revert's own `cf-dns-route --delete` re-recorded a counter-inverse → endless pending chain.
     Fix: dns-revert sets `DNS_REVERT_REPLAYING=1` around the replay; cf-dns-route's `record_inverse`
     helper skips recording when set. +regression test (guard exported). Re-ran clean: create→present→
     revert→gone→log settled. dns-revert-test now 7/7.
  3. `/opt/skynet-ops/state` doesn't exist / not agent-writable → changed dns-revert default log to
     `${XDG_STATE_HOME:-~/.local/state}/skynet/dns-revert.jsonl` (agent-owned, persisted, no root dir).
- **LIVE compose gate** — deploy-gate.sh probed healthy `librespeed` (Arcane status + docker health
  over svc-ops SSH to 10.10.100.15) → kept it, rc 0, no rollback. Decision path runs live.

## Graveyard — tried & abandoned
- LIVE snapshot ROLLBACK of a running in-pool guest → no safe target exists. Tried template 9000:
  Proxmox refuses ("you can't take a snapshot if it's a template") — pve-snapshot's wait_task caught
  it correctly, 9000 intact. The only running in-pool guests are 10015 (all apps, disruptive), 240
  (PBS CT, NFS mount blocks LXC snapshot), and 9090 (this ops VM). So a live running-guest rollback +
  a broken-deploy auto-revert are deferred to a disposable canary (SKY-017 proving ground); the 9/9 +
  7/7 harnesses prove the decision + executor logic meanwhile.
- Refusing ALL tofu deletes (incl. DNS record deletes) vs only guest destroys: chose to refuse ANY
  delete/replace outright in the wrapper — stricter, matches "destroy refused outright", DNS reverts
  are the DNS executor's job. A legit DNS delete is human-run or via a deliberate future PR.

## Follow-ups / open threads
- ⚠ pve-snapshot.sh needs the OPERATE token (PVE_OPERATE_TOKEN); standing proxmox-<node>.env only has
  the readonly token. Confirm it's materialized before any live `tofu-apply.sh`. Until then tofu-apply
  fails closed (can't snapshot → won't apply) — correct, but means no live tofu rollback demo yet.
- P6 wrappers are opt-in and not yet wired into bin/ops / the nightly (report-only). That wiring is a
  SKY-017 autonomy-promotion step, not P6.
- NEXT: P7 (conftest/Rego over `tofu plan`) — explicitly NOT started this session.
