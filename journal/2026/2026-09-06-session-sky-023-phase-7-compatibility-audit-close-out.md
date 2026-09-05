---
date: 2026-09-06
time: 01:06:42            # local HH:MM:SS; orders same-day episodes in the digest
kind: session          # session | incident | decision
title: SKY-023 Phase 7 compatibility audit close-out
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023]         # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
thread_status: none     # none | open | resolved | unknown; digest shows only explicit open
---

# 2026-09-06 · session · SKY-023 Phase 7 compatibility audit close-out

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Verified that Phase 6 merged as `44ae7d3`, fast-forwarded local `main`, and created
`chore/sky-023-p7-compatibility-audit`. This was T1 repository work only: no infrastructure command,
credential access, T2 write, or root grant ran.

Traced every repository caller and current operational reference for `scripts/envsync.sh`,
`scripts/collect-firewall.sh`, `scripts/cf-dns-route.sh`, and `lxc-proof`. `envsync.sh` was called
only by the deterministic nightly and its fixture. Current GitOps services source `.env.git` plus
`.env.sops`; no current procedure or DR document depends on `project.env`. Deleted the helper, its
nightly stage, its fixture, its operator catalog reference, and stale onboarding references.

Retained `collect-firewall.sh` as the offline/DR parser of the mirrored OPNsense config: the normal
collector is live API data, while `render-docs.sh` names the mirror parser for DR. Retained
`cf-dns-route.sh` as the documented Cloudflare DNS break-glass executor; it records an inverse through
`dns-revert.sh` and remains the explicit delete checkpoint because saved-plan OpenTofu refuses deletes.
Retained the `lxc-proof` configuration and template name because both declared core CT resources
reference `local:vztmpl/nixos-lxc-proof-26.05.tar.xz`; renaming it without uploading a matching
template would break future provisioning.

## Actions & outcomes
- `rg` caller/recovery scan → no live caller or recovery dependency for `envsync.sh` after deletion.
- `rg` retained-helper scan → current triggers found for the firewall DR parser and DNS break-glass
  executor; active OpenTofu CT declarations reference the LXC template target.
- `bash .githooks/pre-commit` → all deterministic checks passed, including the updated nightly
  sequence test (10 passed).
- `git diff --check` → no whitespace errors.

## Graveyard — tried & abandoned
Negative results are memory too. Anything attempted that did NOT work — and *why* — so a future
cold agent doesn't re-walk the dead end. Leave a single "— nothing abandoned —" line only if the
episode genuinely tried no path it dropped.

- Keeping `envsync.sh` as a dormant compatibility utility → abandoned because no current caller,
  configuration, or documented recovery path required it; retaining it would leave a T2 SSH/env path
  in the normal maintenance surface without a job.
- Renaming `lxc-proof` in this phase → abandoned because production OpenTofu declarations reference
  the uploaded template name and Phase 7 does not authorize live template replacement.

## Follow-ups / open threads
- Continue SKY-023 at Phase 8; read [[SKY-023-progress]], verify reality, and execute only that phase.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
