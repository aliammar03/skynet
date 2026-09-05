---
date: 2026-09-05
time: 20:48:04
kind: session
title: SKY-023 P3 Obsidian artifact hygiene
tier_touched: [T1]
grants: []
refs: [SKY-023]
thread_status: none
---

# 2026-09-05 · session · SKY-023 P3 Obsidian artifact hygiene

## What happened

Continued Phase 3 after PR #194 merged. This was T1 repository work only: no infrastructure command,
credential read, T2 write, or root grant ran.

Removed four personal Obsidian artifacts from git tracking with `git rm --cached`: the local workspace
layout plus the bundled Obsidian Git 2.39.0 plugin JavaScript, stylesheet, and manifest. The files
remain on this workstation and are now ignored, so no local plugin or workspace data was deleted.
The five shared vault settings remain tracked. The render and nightly paths do not read either class
of removed file.

Documented opening the repository root as the configured vault, the local Community Plugins install
path, and the shared-versus-local metadata boundary. Added a narrow regression test which requires
only the shared settings in the index and verifies ignored workspace/plugin paths.

## Actions & outcomes

- Updated `.gitignore` and Obsidian setup instructions → fresh clones retain shared settings while
  local layout and installed plugins are reconstructed locally.
- Ran the hygiene regression, syntax checks, invariant gate, and complete shell test suite → passed.

## Graveyard — tried & abandoned

- Bundling the Obsidian Git plugin in the repository → removed because it is generated local plugin
  payload, not a required runtime or rebuild input.

## Follow-ups / open threads

- Continue SKY-023 Phase 3 with substantive runbook and repeated-policy reduction. The corpus-size
  and remaining Phase exit targets are still open.
