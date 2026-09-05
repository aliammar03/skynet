---
date: 2026-09-06
time: 02:18:36            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-023 Phase 10 lxc-base template upload
tier_touched: [T1, T2]  # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023, server-proxmox-core] # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-06 · session · SKY-023 Phase 10 lxc-base template upload

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
With explicit approval, read the `local` `vztmpl` storage content on `server-proxmox-core`, built
the merged `lxc-base` flake output, copied its archive to a temporary file named
`nixos-lxc-base-26.05.tar.xz`, and uploaded it through the scoped `svc-ops@pve!operate` API token.
The Proxmox upload task completed with `OK`; a second storage-content read returned
`local:vztmpl/nixos-lxc-base-26.05.tar.xz`.

The first upload attempt stopped before any API write because the Nix output contains the archive
under its `tarball/` directory, not at the output root. The retry used that nested archive. The old
template remained untouched. No guest, OpenTofu state, firewall, credential file, or root grant changed.

## Actions & outcomes
- Proxmox storage read → `local` accepts `vztmpl` content on server-proxmox-core.
- Template upload → `nixos-lxc-base-26.05.tar.xz` uploaded and API-visible as the expected volume ID.
- Local validation → `tofu fmt -check`, `tofu validate`, provisioning truth, and temporal hygiene passed.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Archive lookup at the Nix output root → abandoned because the output is a directory; the archive is
  nested under `tarball/`.

## Follow-ups / open threads
- Merge the declaration-only PR, then create and show a saved Proxmox-core plan. Existing CTs must be
  no-op before any apply. The old template is retained until the new declaration path is proven.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
