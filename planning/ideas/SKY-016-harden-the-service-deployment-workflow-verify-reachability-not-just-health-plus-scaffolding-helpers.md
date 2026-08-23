---
id: SKY-016
title: Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers
status: draft
horizon: short
created: 2026-08-23
updated: 2026-08-23
phases: 3
current_phase: 0
tier_touched: [T1, T2]  # editing scripts/runbooks/docs + gitops-deploy runs as T2 (svc-ops).
                        # No new access, no blast-radius move → no docs/system-design.md PR.
related:
  - scripts/gitops-deploy.sh
  - runbooks/publish-service.md
  - runbooks/deploy-service.md
  - compose/README.md
  - templates/compose/compose.yaml
  - bin/new
  - "[[arcane-api-reference]]"
  - "[[skynet-service-standard]]"
  - "[[SKY-016-progress]]"
---

# SKY-016 · Harden the service-deployment workflow: verify reachability not just health, plus scaffolding helpers

> Close the gap between "the deploy said (healthy)" and "the service actually works," and delete the
> manual toil (digest, IP, secret-read) that every new service currently re-incurs.

> **Status: idea.** Sketched, not scheduled. Promote with `bin/plan start SKY-016` when it's picked up.

## 1. Problem / motivation

Deploying **librespeed** (PR #96) end-to-end surfaced a cluster of workarounds — small alone, but
together they mean adding a service is slower and less safe than it should be. The exhibit that makes
this worth a session:

- **A green deploy hid a broken service.** `gitops-deploy.sh librespeed` reported
  `project status = running` + `(healthy)` while `https://speed.aliammar.net` served
  **ERR_SSL_PROTOCOL_ERROR** — Caddy had no TLS cert. Root cause: certmagic's DNS-01 **self-check**
  queries authoritative NS on **:53**, which the apps Caddy couldn't reach (firewall rule 830 omitted
  `HOST_PROXY_APPS`). The deploy verifies the *container*, never that the service is *reachable as
  designed*, so a real outage looked like success. Every **new** cert (and every cached cert at
  renewal) would hit this — it was invisible because health ≠ reachability.

The rest, each a hand-rolled step that a helper should own:

- **Digest pinning is manual.** The compose standard requires `image@sha256:…`, but there's no helper
  — I resolved it by hand with a registry token + `docker buildx imagetools inspect`.
- **No DMZ IP source of truth.** Picked `10.10.100.72` by `grep`-ing `compose/` for used octets.
  Nothing prevents a collision or names the next free address.
- **`sops -d` bites everyone.** `.env.sops` is dotenv but the name has no `.env` extension sops
  recognises, so a bare `sops -d` fails with `invalid character 'P'` — it needs
  `--input-type dotenv`. Both the agent and Ali hit this reading the librespeed stats password.
- **Caddyfile validation false-fails.** `runbooks/publish-service.md` says validate with
  `caddy validate`, which *provisions* TLS and errors on `{env.*}` placeholders offline. The check
  that actually works is `caddy adapt` (syntax/adapt only, no provisioning).
- **Publish is a two-project step that's easy to forget.** A new service needs
  `gitops-deploy.sh <svc>` **and** `gitops-deploy.sh caddy-apps` (separate project) to publish its
  route. The first "verify" attempts failed partly because the route wasn't live yet.
- **Verification vantage is a trap.** `curl` from the ops VM (VLAN 90, not on the ingress path) times
  out; from the docker host (macvlan host↔container isolation) it's refused — both are false
  negatives. Ingress is only truthfully testable from the **dmz network / inside the caddy container**.
- **New role tags silently don't apply.** `netdiag` was declared in compose but never showed in
  Arcane; `compose/README.md` claims Arcane "applies x-arcane.tags automatically on sync," but it only
  attaches tags that already exist — and the deploy's "no role tag" warning reads as if the compose
  forgot to declare one.

## 2. Approach

Fix the highest-leverage gap first — make the deploy **prove reachability**, since that's what turned a
firewall-alias omission into a silent outage — then delete the repetitive toil with small `bin/`
helpers, then polish the two-project coupling and the tag-accuracy paper cuts. Everything here is
editing scripts/runbooks/docs over data already in git; `gitops-deploy.sh` already runs as T2
(`svc-ops`). No new access, no blast-radius move → **no `docs/system-design.md` PR**. Each helper is
additive and independently revertable.

## 3. The plan

- **Scope:** a post-deploy reachability/cert gate in `gitops-deploy.sh`; the correct Caddyfile-check
  command in the runbook; `bin/` helpers for digest-pin, next-free-IP, and secret-read; the two-project
  publish coupling made explicit; the x-arcane tag docs + warning corrected.
- **Non-goals:** re-collecting inventory (SKY-015 owns renderer truth); any new T2+/T3 access; changing
  the GitOps loop's shape; auto-creating Arcane tags via API (the endpoint is read-only — POST 404s).
- **Hosts & tiers touched:** T1 (docs/scripts) + T2 (`gitops-deploy.sh` verification runs as
  `svc-ops`, read-only probes). No blast-radius move.
- **Rollback posture:** every change is a script/doc/helper — `git revert`. New checks warn-by-default
  before they fail-hard, so a false positive can't wedge a deploy.
- **Grants / human actions:** none beyond the standing T2 path the deploy already uses.

### Phase 1 — deploy proves reachability, not just health  (~1–2h)   `[ ]` not started
Steps:
1. In `gitops-deploy.sh`, after health passes, if `<svc>` (or a hostname mapping to it) has a route in
   `compose/caddy-apps/Caddyfile`, run an **ingress probe from the correct vantage**: a throwaway
   `curlimages/curl` container on the `dmz` network, `--resolve <fqdn>:443:10.10.100.35`, asserting
   `http_code` < 400 **and** `ssl_verify_result == 0` (publicly-trusted cert present). Report loudly;
   start as a **warning** (non-fatal) so it can't wedge deploys during rollout, with a note to promote
   to hard-fail once proven.
2. Add a cert-presence hint: if the probe fails on TLS, surface the likely ACME cause
   (`/data/caddy/certificates/**/<fqdn>` missing → check issuance logs) rather than a bare failure.
3. `runbooks/publish-service.md`: change the pre-PR check from `caddy validate` to
   `caddy adapt --config Caddyfile --adapter caddyfile` (syntax/adapt only; works offline with
   `{env.*}` placeholders). Note *why* (validate provisions TLS and false-fails).
4. Document the **verification vantage** in `runbooks/publish-service.md` (and/or `deploy-service.md`):
   ingress is only truthful from the dmz network / inside `caddy-apps-caddy-1`; the ops VM and docker
   host give false negatives (VLAN-90 routing; macvlan host↔container isolation).

Exit criteria: a service whose route has no working cert is caught **by the deploy**, not by a browser;
the runbook's Caddyfile check runs clean offline; the vantage trap is written down.

### Phase 2 — scaffolding helpers kill the manual toil  (~1–2h)   `[ ]` not started
Steps:
1. `bin/ops pin <image:ref>` → prints `image:tag@sha256:<index-digest>` via
   `docker buildx imagetools inspect`. Wire it into `bin/new service` so a scaffolded compose lands
   digest-pinned (or emits a one-line TODO with the exact command).
2. `bin/ops next-ip <segment>` → next free host octet for the DMZ macvlan, computed from the union of
   `ipv4_address` across `compose/**/compose.yaml` (+ the Caddyfile). Have `bin/new service` suggest it.
3. `bin/ops secret <svc>` → decrypts `compose/<svc>/.env.sops` with the correct flags
   (`sudo SOPS_AGE_KEY_FILE=/opt/skynet-ops/secrets/age.key sops -d --input-type dotenv …`), for
   reading a value without re-deriving the incantation. Fix the decrypt command shown in
   `runbooks/deploy-service.md` / `compose/README.md` to include `--input-type dotenv`.

Exit criteria: scaffolding a new service needs no hand-rolled registry curl, no `grep` for a free IP,
and no half-remembered sops flags; the docs show the working decrypt command.

### Phase 3 — publish coupling + tag accuracy  (~1–2h)   `[ ]` not started
Steps:
1. Make the two-project publish explicit: `gitops-deploy.sh <svc>` detects a Caddyfile route for
   `<svc>` and, if the running apps-Caddy config lacks it, prints a clear "route not live yet — run
   `gitops-deploy.sh caddy-apps`" reminder (or offers to chain it). Add the two-step to the
   service-add path in the runbook.
2. Correct the x-arcane tag story: fix `compose/README.md`'s "applies automatically" claim to state
   that Arcane **attaches existing** tags but won't create a brand-new one on redeploy/sync (new roles
   must be introduced at project creation or added once in the Arcane UI). Make `gitops-deploy.sh`'s
   "no role tag" message distinguish *undeclared in compose* from *declared-but-not-yet-registered in
   Arcane* (read the compose x-arcane and compare to the applied tags).

Exit criteria: nobody is surprised that a route isn't live after deploying only the service, or that a
new role tag didn't appear; the messages tell the truth.

## 4. ▶ Execute prompt
> Paste into a fresh Skynet session to run this directive (after `bin/plan start SKY-016`). Swap `<N>`.
```
Read planning/projects/SKY-016-harden-the-service-deployment-workflow-verify-reachability-not-just-health-plus-scaffolding-helpers.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. When the phase's exit criteria are met, do the "Phase close-out" at the bottom.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-016-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-016-harden-the-service-deployment-workflow-verify-reachability-not-just-health-plus-scaffolding-helpers.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-016-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-23 — created (idea) out of the librespeed deploy (PR #96). Trigger: `gitops-deploy.sh`
  reported `(healthy)` while `speed.aliammar.net` served ERR_SSL_PROTOCOL_ERROR — Caddy couldn't issue
  a cert because certmagic's DNS-01 self-check hit :53, blocked by firewall rule 830 omitting
  `HOST_PROXY_APPS` (Ali fixed the rule; cert then issued from LE production, HTTPS 200, TLS verify=0).
  Bundled that gap with the digest / IP / sops / caddy-validate / two-project-publish / vantage /
  tag-apply workarounds from the same run into a 3-phase hardening directive. Left as an idea.
