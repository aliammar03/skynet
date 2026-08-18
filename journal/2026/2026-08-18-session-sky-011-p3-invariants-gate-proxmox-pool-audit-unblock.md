---
date: 2026-08-18
kind: session          # session | incident | decision
title: SKY-011 P3 — invariants gate + Proxmox pool-audit unblock
tier_touched: [T1, T3]  # T1 repo/greps; T3 = Ali ran a pveum ACL grant on both nodes
grants: []              # no SSH root cert grants; the pveum change was Ali's own node-root action
refs: [SKY-011, ADR-0003, PR-58, PR-59]
---

# 2026-08-18 · session · SKY-011 P3 — invariants gate + Proxmox pool-audit unblock

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Goal: build SKY-011 P3 — `scripts/check-invariants.sh`, the deterministic gate that fails a PR
violating a hard law. First assertion needed pool membership: "no excluded VMID (5001/635/837/2020)
is a member of any pool." Discovered `inventory/*.json` had no membership — the collector fetched
`/pools` (poolids only), never `/pools/{id}` (members).

Tried to just extend the collector, but probing the live API with the readonly token
(`svc-ops@pve!readonly`) showed the token could not see pools at all *anymore*:
- `GET /pools` → `[]` on both nodes
- `GET /pools/ops-managed` → **403**
- `cluster/resources` pool entries → `[]`

But the committed inventory from 2026-08-15 *had* `pools:[{poolid:"ops-managed"}]`. So visibility
had regressed since. `GET /access/permissions` explained it: the token has `Pool.Audit` at `/pool`
but NOT at `/pool/ops-managed` — at the pool path it only carries the `OpsOperator` VM.* privs.
`bootstrap-proxmox.sh` grants `OpsOperator` to the user at `/pool/ops-managed` (the A6 privsep fix),
and that shadowed pool-audit visibility there for the readonly token. Reading `/pools/{id}` needs
`Pool.Audit` on the specific pool path; there is no other read path for membership (guest configs
don't carry it).

Fix is a `pveum` ACL change = Proxmox node root = T3, which the agent can't do. Checkpointed to Ali
(AskUserQuestion), he chose "apply the grant, full gate." He ran on both nodes:
`pveum acl modify /pool/ops-managed --users svc-ops@pve --roles PVEAuditor`.

After the grant: `/pools/ops-managed` readable. core ops-managed members = 10015 (vm-docker-dmz),
240 (lxc-proxmox-backup-server); network ops-managed = empty. No excluded VMID present. Reran
`collect-proxmox.sh core|network` → inventory now carries `pools[].members`.

Wrote the gate; proved all three checks by planting violations (VM 5001 as a member → caught;
pool renamed to ops-rogue → drift caught; a fake `AGE-SECRET-KEY-…` file → secret caught); clean
tree passes exit 0. Wired into `.githooks/pre-commit` + `.github/workflows/checks.yml`.

Mid-session Ali pushed back hard on me writing incident narrative INTO the design spokes
(the "privsep trap (learned at A6)" style). Agreed: design docs carry the rule + small actionable
notes; the story lives here in the journal / build-log. Added the convention to `docs/conventions/docs.md`
and swept the design docs, trimming the privsep-trap callout, an "(A5 fix)" tag, and the A6 DR-drill
findings down to actionable rules (the stories are already in `docs/history/build-log.md`).

## Actions & outcomes
- Probed readonly token pool access → `/pools`=[], `/pools/ops-managed`=403 on both nodes (regression).
- `GET /access/permissions` → `Pool.Audit` at `/pool` but not at `/pool/ops-managed` (OpsOperator shadows it).
- Ali ran `pveum acl modify /pool/ops-managed --users svc-ops@pve --roles PVEAuditor` on core + network → membership readable.
- Extended `collect-proxmox.sh` (reads `/pools/{id}`, members→stable fields, null when unreadable) → reran → inventory has membership.
- `bootstrap-proxmox.sh` + `access-and-trust.md` recipe updated with the PVEAuditor-on-pool line.
- Wrote `scripts/check-invariants.sh`; 3 planted violations all caught, clean = exit 0.
- Wired gate into pre-commit hook + CI `checks.yml` (new `invariants` job).
- Renamed a `secret=` path var → `secret_file` in collect-proxmox.sh (secret-scan false positive on the >20-char path).
- Doc-hygiene: new "state the rule, not the incident" convention + trimmed 3 war-stories from spokes.

## Graveyard — tried & abandoned
- Reading pool membership from `cluster/resources` or guest configs → abandoned: neither carries
  per-guest pool membership; only `/pools/{id}` does.
- Extending the collector without the ACL grant → abandoned: pointless, the token literally could
  not see the pool; would have regressed inventory to `pools:[]`.
- `git commit --no-verify` to get past the secret-scan false positive → not used; renamed the
  offending variable instead so the gate keeps working.

## Follow-ups / open threads
- The Pool.Audit visibility regression predates this session (inventory lost the pool sometime after
  2026-08-15). Root cause understood (OpsOperator grant shadowing), now fixed in bootstrap; no
  further action, but worth remembering if a rebuild ever drops it again.
- Gate reads the working tree via `git grep` in pre-commit (not the staged blob) — coarser than
  secret-scan.sh which checks staged content. Acceptable; CI is the definitive check.
- SKY-011 P3 close-out + PR next; the branch is stacked on the P2 branch (invariants.json), rebase
  onto main once PR #59 merges.
