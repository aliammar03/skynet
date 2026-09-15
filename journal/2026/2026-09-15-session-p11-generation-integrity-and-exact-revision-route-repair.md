---
date: 2026-09-15
time: 20:08:35
kind: session
title: P11 generation integrity and exact-revision route repair
tier_touched: [T1]
grants: []
refs: [SKY-025, PR #259, ADR 0007, docker-dmz, cloudflared]
thread_status: none
---

# 2026-09-15 · session · P11 generation integrity and exact-revision route repair

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
A fresh external review posted FIX for base `f8072b390c10957a572eda4aa112da0583e46796`
and reviewed head `b1b49b1e740757f9c1e0623bb5af336e9159e5ce`. It identified three P11 defects:
generation publication flattened runtime modes to `0600`, runtime rollback trusted a retained
revision directory without reconstructing the historical Git release, and deployment verification
read route declarations from the checkout instead of the expected revision.

Two bounded Executors repaired generation integrity and route revision binding. Main wired exact
historical validation into `rollback --apply` before the activation pipeline. An independent Tester
then exercised the integrated fixes in disposable Git, filesystem, Compose, and route fixtures. No
live deployment or production mutation was repeated.

## Actions & outcomes
- Inspected the pinned `cloudflare/cloudflared:2026.8.2` image through the read-only `docker-dmz`
  context → image config reported user `65532:65532`, confirming that a generation-owned `0600`
  `config.yml` is unusable for the current non-root container.
- Changed generation staging/publication → Git `100644` files publish as `0644`, Git `100755` files
  publish as `0755`, runtime directories including the generation root publish as `0755`, and the
  surrounding service/state directories remain `0700`; `.env` and `release.json` remain `0600`.
- Reused the same byte/mode comparison for publication and retained validation → identical
  generations reuse without mutation; retained file, config, `.env`, manifest, or mode drift fails.
- Added historical retained validation → the explicit 40-hex object must exist locally as a commit;
  its complete service tree and effective environment are reconstructed and compared directly over
  bounded SSH stdin before rollback activation. No plaintext hash or output is produced.
- Wired `rollback --apply` to historical validation → a validation failure never reaches the
  activation pipeline; report-only rollback remains report-only; successful disposable rollback
  changed no Git ref, index, or worktree byte.
- Added exact-revision route reads → the verifier reads the selected commit's Caddyfile and Compose
  service-address inputs even when the worktree differs.
- Independent disposable verification → a required route at revision R remained required after a
  dirty worktree removed it; a genuinely unrouted revision skipped; duplicate, case-ambiguous, and
  malformed route evidence failed; DMZ network, pinned curl digest, verified TLS, and HTTP below 500
  semantics remained unchanged.
- Independent disposable generation verification → non-root config access, executable helper mode,
  exact `.env` mode, historical validation after branch advance, missing-object refusal, current-head
  idempotence, all retained tamper cases, pre-activation refusal, and zero Git mutation passed.

## Graveyard — tried & abandoned
- Protecting the generation root itself as `0700` → abandoned because a relative directory bind mount
  must expose a traversable directory inode to a non-root container; confidentiality remains at the
  protected parent directories and the mode-`0600` secret files.
- Trusting `release.json` plus the generation directory name during rollback → abandoned because
  neither identity proves retained runtime or environment bytes have not changed.
- Requiring a clean checkout for route verification → abandoned because exact Git-object reads give
  the required revision binding without coupling unrelated worktree state to a report-only verifier.

## Follow-ups / open threads
- Push the repaired head to existing PR #259 and request a completely fresh external review. Accepted
  numbered progress remains P10; do not merge or enter accepted closeout.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
