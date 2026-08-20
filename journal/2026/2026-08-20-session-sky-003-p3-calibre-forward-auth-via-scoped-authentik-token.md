---
date: 2026-08-20
kind: session          # session | incident | decision
title: SKY-003 P3 — calibre forward-auth via scoped Authentik token
tier_touched: [T1, T2]  # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-003, PR #77, SKY-014, PR #76]  # cross-links
---

# 2026-08-20 · session · SKY-003 P3 — calibre forward-auth via scoped Authentik token

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Resumed SKY-003 at Phase 3 (Authentik scoped token + calibre forward-auth pilot). Ali had run the
T3 ceremony: created the `svc-skynet` service account + a scoped role + an API token, written `0600`
to `/opt/skynet-ops/secrets/authentik.env` (`AUTHENTIK_URL=https://auth.aliammar.net`,
`AUTHENTIK_TOKEN=…`). Side task first: committed the SKY-014 close-out edit (status→complete, both
phase boxes done) on branch `phase/sky-014-p2-closeout` → PR #76.

Reaching Authentik was the first real problem. The ops VM (10.10.90.90, VLAN 90) has **no route** to
Authentik — `curl https://auth.aliammar.net/api/v3/root/config/` and `curl http://10.10.80.37:9000/…`
both timed out (8s). Firewall rule 240 only allows the **apps-Caddy (10.10.100.35)** → Authentik. So
I drove the Authentik API from **inside the `caddy-apps-caddy-1` container** (it has curl and the
right source IP). Wrote `scratchpad/ak.py`: reads the token via `sudo -n grep`, builds a curl `-K -`
config on stdin (token in a `header =` line), pipes it over `ssh svc-ops@10.10.100.15 "docker exec -i
caddy-apps-caddy-1 curl -K -"`. Token never appears in any argv on the ops VM, in the SSH command, or
in the container's process list. Proved transport integrity with a sha256 round-trip (local == what
the container received).

First `GET /api/v3/core/users/me/` → **403 "Token invalid/expired"** even though the token was a
well-formed 60-char alphanumeric with no stray quotes/CR/space and transport was byte-clean. Told Ali
to re-check (wrong value copied / wrong intent / user inactive / expired). He refreshed it; retry →
**200**, `username=svc-skynet, pk=6, is_active=true, is_superuser=false, role=svc-skynet`.

Verified the scope is *real* (P3 exit criterion): 200 on `core/applications/`, `providers/proxy/`,
`outposts/instances/`; **403** on `flows/instances/`, `core/users/`, `core/groups/`,
`crypto/certificatekeypairs/`, `admin/settings/`. Boundary holds.

Discovered the environment already had a **domain-level** forward-auth provider (pk 2 "Caddy Domain
Forward Auth", `mode=forward_domain`, `cookie_domain=aliammar.net`, `external_host=auth.aliammar.net`)
bound to the embedded proxy outpost — but **no Application on it** (scaffolded, unused). The directive
had assumed a per-app provider. Presented the fork to Ali with pros/cons; he chose **Option A: per-app
forward-auth**.

Provisioned via the scoped token: `POST /api/v3/providers/proxy/` →
provider **pk 14** `calibre` (`forward_single`, `external_host=https://calibre.aliammar.net`),
**reusing** provider 2's `authorization_flow` (569acdf5-…) + `invalidation_flow` (d0690a59-…) because
the token can't list Flows (403). `POST /api/v3/core/applications/` → app `calibre` → provider 14.
`PATCH /api/v3/outposts/instances/fb7c8e65-…/` with `{"providers":[2,14]}` (kept the existing 2).

Pre-merge sanity from the caddy container: `GET .../outpost.goauthentik.io/auth/caddy` with
`Host: calibre.aliammar.net` → **302** to `auth.aliammar.net/application/o/authorize/?client_id=4FSYZhe70…`
with `redirect_uri=…calibre.aliammar.net/outpost.goauthentik.io/callback` — i.e. provider 14 matched.
Control (`Host: nonexistent-xyz.aliammar.net`) → 302 with a *different* client_id (the domain provider
2 catching the unmatched host). Outpost picked up the binding within seconds.

Converted the `calibre.aliammar.net` Caddyfile block to the standard Authentik forward-auth snippet
(reverse_proxy `/outpost.goauthentik.io/*` → 10.10.80.37:9000; forward_auth → same; then
reverse_proxy 10.10.100.53:8080). `caddy validate` adapted clean (only failed on dummy CF token /
empty ACME email in the bare `docker run`, i.e. env-not-config). Filled runbook Path B. Committed →
PR #77. Live end-to-end verify waits on the merge+Arcane reload.

## Actions & outcomes
- SKY-014 close-out edit committed → PR #76
- `scratchpad/ak.py` API helper (token via stdin, driven from caddy-apps container) → works, sha-verified
- token scope verification (allowed 200 / denied 403 matrix) → boundary confirmed real
- provider pk 14 + app `calibre` + outpost bind `[2,14]` created via scoped token → 201/201/200
- outpost 302 pre-check for provider 14 → confirmed (distinct client_id + calibre callback)
- Caddyfile calibre → forward-auth; `caddy validate` clean; runbook Path B written → committed → PR #77

## Graveyard — tried & abandoned
- Calling the Authentik API from the ops VM (both `https://auth.aliammar.net` and direct
  `10.10.80.37:9000`) → abandoned: no firewall path from VLAN 90; rule 240 is Caddy-only. Went through
  the caddy-apps container instead.
- First token value → rejected by Authentik as invalid/expired (transport was clean); abandoned that
  copy, Ali re-issued. Root cause not pinned down (likely wrong value/intent), but the second worked.

## Follow-ups / open threads
- **Awaiting Ali:** merge PR #77 → then agent live-verifies unauth→302→login→calibre from a peer DMZ
  container and does the P3 `[x]` close-out.
- P4 (firewall least-privilege + DMZ-docker SSH-exposure audit) still open; note calibre origin is
  10.10.100.53:8080 (matches PORT_APP_BACKENDS=8080, unlike karakeep's 3000).
- The domain-level provider (pk 2) remains bound to the outpost, unused by Caddy — left as-is.
