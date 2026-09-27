---
date: 2026-09-27
time: 19:29:21            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-025 P15 tofu executor and state split
tier_touched: [T1, T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-025, ADR 0008]                # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: open     # none | open | resolved | unknown; digest shows only explicit open
# resolves: [<episode-basename>, …]   # optional: close earlier episodes' open threads (append-only-safe)
---

# 2026-09-27 · session · SKY-025 P15 tofu executor and state split

## What happened
Ali asked to start SKY-025 Phase 15 and to "greenfield the mechanisms": design a new executor, not
a port of tofu-apply.sh. Ali chose (plan-mode questions): merge is the only approval and the 30 s
deploy timer applies it; the approved effect is a committed `tofu/<stack>/approved-plan.json`
(sha256 of normalized resource changes + address→action list), not the PR body.

Built on branch `sky-025-p15-tofu`: `src/skynet/tofu.py` (stack registry, normalized-change hash,
plan/apply/pending/drift, tofu-state branch via git plumbing with an FF-only push), `src/skynet/pve.py`
(snapshot create/rollback/delete over the operate token), a `skynet check` gate for tofu/ dirs +
approved plans, `deploy.pending` running `tofu.pending` last, and `tests/test_tofu.py` (34 tests).
Deleted tofu-env.sh, tofu-apply.sh, and pve-snapshot.sh. `bin/check` is green.

Live read-only monolith plan (19:1x PKT): `Plan: 0 to add, 2 to change, 0 to destroy`. The 09-11
drift file (1 destroy) is stale; the athena `moved` had already applied (state 09:51 today shows
`core_ct["athena"]`). The two changes:
- CT 240 `startup { order = 2 }` is live but not in code (Ali's 09-26 boot-order fix) → declared
  in `lxc-pbs.tf`.
- Template 9000: the code description was edited to "Ubuntu base…" and live still says
  "SKY-008 base…" → code restored to the live text, so the split starts from zero.

Legacy state copied (cp -p, sha256 6b7087807f355818 matches) to
`/opt/skynet-ops/state/tofu/legacy/` (13 files). The original `tofu/terraform.tfstate*` is untouched.

## Actions & outcomes
- First split attempt: copy the legacy state to `state/tofu/proxmox-core.tfstate`, then `init` in the
  new stack → `tofu init failed`. Cause: the copied state still holds cloudflare/technitium resources,
  and init wants their providers, which a one-provider `-lockfile=readonly` lock can't give.
  Left behind: `state/tofu/proxmox-core.tfstate`, an unmodified copy of legacy.
- Second attempt: `state rm -state=<copy>` in the legacy monolithic root (origin/main, all providers)
  → `state list -state=` worked, `state rm` failed: "failed to write backup file: Unsupported state
  file format: This state file is encrypted and can not be read without an encryption configuration".
  The legacy `-state` flag's backup write bypasses the encryption config.
- Third approach (place each copy at the legacy root's default `terraform.tfstate` in a throwaway
  checkout, `state rm` foreign types there, copy it out): the permission classifier denied running it
  (Modify Shared Resources). Not run. It waits for Ali.

## Graveyard — tried & abandoned
- Split by init-in-the-new-stack then `state rm` → abandoned: a readonly single-provider lock can't
  init a state that references other providers.
- `tofu state rm -state=<path>` with an encrypted state → abandoned: the backup write ignores the
  encryption block.

## Follow-ups / open threads
- Run the split (script: this session's scratchpad `split.py`; remove the leftover
  `state/tofu/proxmox-core.tfstate` first). Expect proxmox-core 5, technitium-dns 21, and cloudflare-dns 6
  addresses. Then `skynet tofu plan <stack>` → zero changes for each, and a first
  `skynet tofu apply <stack>` records empty plans and bootstraps the `tofu-state` branch.
- Exit drills: a wrong approved hash is held + alerts; a rejected athena `cores` value rolls back from
  a snapshot; deleting the local state rebuilds it from `tofu-state`.
- After the drills, remove the root `tofu/terraform.tfstate*` and `tofu/.terraform/` from the checkout
  (the legacy copy stays in `state/tofu/legacy/` until Phase 18).
