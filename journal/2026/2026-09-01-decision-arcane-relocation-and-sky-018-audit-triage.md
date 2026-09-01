---
date: 2026-09-01
kind: decision          # session | incident | decision
title: arcane relocation and SKY-018 audit triage
tier_touched: [T1, T2]  # T2 = svc-ops read of docker-dmz to capture arcane config
grants: []
refs: [SKY-018, SKY-019, SKY-008, ADR-0001]
---

# 2026-09-01 · decision · arcane relocation and SKY-018 audit triage

<!-- RAW EPISODE. Concrete facts, not a lesson. -->

## What happened
Triaged the SKY-018 P1 audit holes with Ali. Ali is destroying the leftovers himself (T3): CT 101,
CT 231, CT 720, VM 999, VM 9091, CT 1035, and **CT 526 (UniFi)**. I was asked to fix the deviations
and propose a fix for arcane-manager.

## Decisions & outcomes
- **VM 9000 is NOT stale — it is the OpenTofu clone template** (`tofu/template-ubuntu-2404.tf`,
  `template = true`, in ops-managed). It was in Ali's destroy list; destroying it breaks `tofu apply`
  for every future guest. **Caught before action.** Fixed the audit to be template-aware
  (`template=1` → its own bucket, never a stale-destroy proposal) + a test. This was the whole point
  of "verify before destroy."
- **CT 1035 cleared for destroy.** Verified the `10.10.100.35` front-door dependency: `.35` now lives
  on the `caddy-apps` container via the DMZ macvlan (`compose/caddy-apps/compose.yaml:35`,
  `ipv4_address: 10.10.100.35`). The old `lxc-caddy-dmz` serves nothing — safe.
- **CT 526 (UniFi) → destroy.** Knock-on: SKY-018 P4's network-gear collector shrinks to **Omada-only**,
  and 526 stops being "the surprise hole" (resolves by removal, not collection).
- **arcane-manager → relocate, not tidy-up (new directive SKY-019).** It's Arcane itself, running on
  `guest/docker-dmz-10015` with a local `docker.sock` (root-equiv on the DMZ host) — the management
  brain inside the least-trusted VLAN. Ali's call: move it to a **dedicated Management (VLAN 50) docker
  VM** cloned from the 9000 template, managing docker-dmz **remotely over unprivileged SSH**. Fresh
  secrets on the new host. Minted SKY-019 (4 phases; P3 needs a system-design PR for the topology +
  remote credential).
- **Interim capture landed** (`compose/arcane-manager/`): pulled the live config off docker-dmz via
  svc-ops (docker-group read of the 0700 dir), split into `.env.git` (config) + `.env.sops`
  (JWT_SECRET, ENCRYPTION_KEY, sops-encrypted). Bootstrap component, NOT self-synced, relocation-pending.
  Audit now shows services 11 matched / 0 running-unmapped.

## Concrete facts captured
- arcane image `ghcr.io/getarcaneapp/manager:latest`, container `arcane`, bound `10.10.100.15:3552`,
  mounts docker.sock + `/opt/docker/arcane-projects` + `/opt/docker/appdata/arcane-manager`.
- Live `arcane.env` also held `NVIDIA_*`/`ROCR_*`/`HIP_*`/`ONEAPI_*`/`LD_LIBRARY_PATH` — image-baked
  GPU/runtime defaults, not Arcane config. Excluded from the capture; flagged for SKY-019 review.
- sops **encryption** needs only the age recipient from `.sops.yaml` (no private key), so I (uid
  aliammar, can't read the root:root age.key) could encrypt `.env.sops` fine; decrypt would need the key.

## Graveyard — tried & abandoned
- Proposed two arcane fixes (git-tracked-bootstrap vs full self-management) → Ali rejected both for a
  third: relocate off the DMZ entirely. Better call — recorded as SKY-019.

## Follow-ups / open threads
- Ali to perform the destroys (T3, his hands). After that: re-collect inventory + re-run `bin/ops
  entities`; the remaining flagged running entities should be zero (or only what's genuinely pending).
- SKY-019 P1 when ready. SKY-018 P2 still next for the entity spine.
- Confirm 9090 is the live NixOS ops VM before 999/9091 are destroyed (SKY-007 renumber thread).
