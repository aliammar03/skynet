# Runbook — __TITLE__

**Tier:** T1|T2|T2+|T3 (PR-gated / grant). **Executor:** `<script or manual>`. **Rollback:** `<how>`.
<!-- Trigger (only if it has a natural spoken one): *"…"* -->

> One line: what this procedure does and when to reach for it. Engine-neutral markdown + bash so
> any agent runs it verbatim. — docs/conventions/docs.md
>
> **Before you finish: add this runbook to [`README.md`](README.md)** (with its Tier + Trigger).
> An uncatalogued runbook is invisible.

## When to run

<the trigger / precondition>

## Steps

1. …
2. …

## Verify

<how to confirm it worked>

## Rollback

<how to back out — `git revert`, disable a timer, `docker compose down`, …>
