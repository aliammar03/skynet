---
date: 2026-09-05
kind: session          # session | incident | decision
title: SKY-023 P2 secret-access clarification
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-023, PR #186] # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
---

# 2026-09-05 · session · SKY-023 P2 secret-access clarification

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened

After PR #186 opened, Ali clarified that secret files are intentionally readable by the agent: the
agent must not sudo for normal sops decryption or ordinary token reads. Inspected
`nix/modules/secrets.nix` and `scripts/gitops-deploy.sh`: sops-nix materializes token files as
`0400 aliammar` under `/run/secrets/` and links their normal `/opt/skynet-ops/secrets/` paths;
`gitops-deploy.sh` first runs sops unprivileged with the age key and only has a compatibility fallback.

Updated AGENTS.md, README.md, the conventions hub, system design, access/secrets spokes, and the
Cloudflare token description to state the agent-readable model. The master age key is
`0640 root:users`; service secret files are `0400 aliammar`. Updated only stale permission comments
in `nix/modules/secrets.nix`, `nix/modules/impermanence.nix`, and `scripts/envsync.sh`; no permission
or secret-material change ran.

## Actions & outcomes

- Inspected the Nix secret declarations and GitOps decrypt path → confirmed the intended
  unprivileged read/decrypt model.
- Reworded the documentation contract → no generic `0600` rule now implies agent sudo is normal.

## Graveyard — tried & abandoned

- Treating the master age key as a root-only `0600` bootstrap file → abandoned; it contradicts the
  agent's normal sops decrypt path.

## Follow-ups / open threads

- PR #186 needs CI and human review. The agent does not merge authored changes.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
