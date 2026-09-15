---
date: 2026-09-15
time: 21:30:19
kind: session
title: P11 rollback default-host integration repair
tier_touched: [T1]
grants: []
refs: [SKY-025, PR #259, docker-dmz]
thread_status: none
---

# 2026-09-15 · session · P11 rollback default-host integration repair

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Independent review of head `39fd8587dc1b2282f746571e3b7f6c2df903afb8` found that the new
historical rollback validator received activation's default SSH spelling
`svc-ops@10.10.100.15`. Generation validation accepts only a bare host because it adds the fixed
`svc-ops@` user itself, so the documented default `rollback --apply` path stopped at host parsing.
The existing prepare/deploy paths already crossed this boundary through `_generation_host()`.

## Actions & outcomes
- Changed the rollback validation call to use `_generation_host(host)` → the default activation
  spelling becomes bare `10.10.100.15` for generation validation, while activation continues to
  require and use `svc-ops@10.10.100.15`.
- Exercised the public source CLI with no `--host` → status used the fixed-user activation spelling,
  historical validation received the bare default host, and the activation pipeline retained the
  `svc-ops` target.
- Exercised bare `10.20.30.40` and `svc-ops@10.20.30.40` overrides → both generation-validation
  paths received bare `10.20.30.40`; activation normalized both to `svc-ops@10.20.30.40`.
- Exercised `root@10.20.30.40`, `bad/host`, and `svc-ops@bad@host` → each failed before historical
  validation or activation.
- Exercised report-only rollback → it observed state and returned without historical validation or
  activation.

## Graveyard — tried & abandoned
- Widening generation host parsing to accept arbitrary `user@host` → abandoned because runtime
  mutation and generation transport must remain fixed to the documented `svc-ops` T2 identity.

## Follow-ups / open threads
- Complete installed-package and retained-integrity regression evidence, push the repaired head to
  existing PR #259, and stop for a manually started fresh review. Accepted progress remains P10.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
