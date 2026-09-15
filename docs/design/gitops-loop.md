---
summary: "Exact-Git-revision Compose generations, direct activation, deployment state, and runtime rollback."
---

# Spoke · Compose deployment loop

> How a reviewed service revision becomes running containers. Governed by
> [`../system-design.md`](../system-design.md), the Compose rules in
> [`../conventions/compose.md`](../conventions/compose.md), and secret custody in
> [`secrets.md`](secrets.md).

Git is the authored source of system truth. The full local branch-head commit is the canonical
release identity. The packaged synchronous `skynet deploy` owner reads Git objects at that exact
commit; dirty or untracked worktree bytes never become release input.

```text
reviewed Git revision -> protected immutable generation -> direct Docker Compose activation
  -> independent Docker/health/DMZ-route verification -> stable promotion
```

Arcane remains a Docker UI, observation surface, and emergency human tool. Arcane repositories,
Git Sync branch mutation, manual source-sync POSTs, sync polling, and sync-triggered redeploys are not
deployment authority. An existing sync with `autoSync=true` is a pre-write refusal. A disabled legacy
sync may remain during transition; its schedule must be disabled and drained while old source and
old environment agree, and the running old revision must be verified before first takeover. The
takeover evidence names the exact old Compose service set. Docker labels must match that whole set
and the legacy project/config path under the lock; the agent does not gain read access to Arcane's
protected checkout.

## Generation and state

`/home/svc-ops/.local/state/skynet-deploy/<service>/` is on the persistent Docker host. The existing
mode-`0700` `svc-ops` home protects the state root without a root bootstrap. Its layout is:

```text
<service>/
  generations/<full-git-revision>/  # complete runtime subtree, .env, release.json
  operations/<operation-id>.json    # non-secret steps, state, reconciliation evidence
  active                            # generation believed running, reconciled against Docker
  stable-state.json                 # stable + previous changed in one atomic replacement
  deploy.lock                       # per-service host flock
```

Preparation stages the complete committed `compose/<service>/` runtime subtree and validates it
with Docker Compose against its own effective `.env`. Only a completely valid staging directory is
published atomically. `release.json` records schema, service, full revision, Git tree/Compose/blob
identities, optional `.env.git` blob, optional `.env.sops` ciphertext blob, and preparation time.
It contains no secret values or hash of effective plaintext. A retained generation is immutable;
re-preparation of the same revision verifies manifest identity and reuses it or fails on conflict.

The effective `.env` is `.env.git` plus locally decrypted `.env.sops` from the exact commit.
Plaintext stays in local process memory and crosses to the remote staging directory only through
bounded SSH stdin. Only the selected retained generation contains it, mode `0600` inside the protected tree.
Neither argv, local temporary files, human/JSON reports, retained subprocess output, nor Git commits
contain plaintext.

## Activation and verification

Before mutation, the owner acquires remote `flock`, inspects operation/pointer state and actual
Compose containers, reconciles any interrupted activation, and refuses a different generation while
state is unresolved. It also refuses enabled Arcane auto-sync. Compose runs from the selected
immutable directory with explicit stable project identity `-p <service>` and `compose.yaml` there.
Relative mounts and environment paths therefore resolve inside the same generation.

The `active` pointer is a belief, never proof. Docker Compose project/config-file/working-directory
labels independently identify the generation each container runs. A complete one-generation project
can be reconciled; missing, partial, mixed, stopped, or label-ambiguous project state cannot establish
success. A timed-out transport records unresolved activation, checks the old lock on the next call,
then reconciles Docker before any retry. Once the lock is free, applying the **same** immutable target
can resume convergence. A different target cannot pass unresolved state.

Independent verification checks release manifest revision, stable project name, exact complete
Compose service set, container-generation labels, running/healthy status and required healthchecks.
Declared ingress routes retain P10's `dmz` vantage, TLS validation, and HTTP gate. Arcane observation
is not required. Docker accepting Compose only changes `active`; only successful independent
verification atomically promotes `stable`. Promotion retains the old stable as `previous`.

```text
candidate B activated, verification pending/failed: active=B, stable=A
B verified and promoted:                  active=B, stable=B, previous=A
```

Verification failure reports the retained rollback candidate and leaves old stable metadata intact.
P11 never rolls back automatically.

## Runtime rollback

`skynet rollback service <service>` is report-only until `--apply` is explicit. It selects an
unambiguous retained previous stable generation or an explicit full `--to` revision, then uses the
same lock/reconciliation, Compose activation, verification, and promotion path. It never creates a
branch or commit, pushes, merges, or changes authored Git state. After successful runtime rollback,
runtime and Git may intentionally diverge; correct authored source by the ordinary reviewed PR path.
The old shell command names are thin package forwarders until P22.
