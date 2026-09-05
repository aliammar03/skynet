---
summary: "Choose the runbook for publishing a service through apps Caddy, Authentik, or the Cloudflare Tunnel."
trigger: "Publish or expose a service"
tier: "T2 PR-gated"
executor: "Choose and follow one publish leaf"
rollback: "See the selected leaf"
---

# Runbook — publish a service

**Tier:** T2 (PR-gated). **Executor:** choose and follow one leaf below. **Rollback:** use the
selected leaf's rollback procedure.

## Preconditions

- Know the service's origin, whether it has a real login, and whether it needs public reachability.
- Do not publish sensitive infrastructure through apps Caddy.

## Steps

Choose the smallest path that meets the service's authentication and reachability needs:

| Need | Runbook |
|---|---|
| An internally reachable service with its own login | [`publish/internal-route.md`](publish/internal-route.md) |
| An internally reachable service with no login of its own | [`publish/forward-auth.md`](publish/forward-auth.md) |
| Public internet access for an already-working internal route | [`publish/public-tunnel.md`](publish/public-tunnel.md) |

The internal hostname is `https://<svc>.aliammar.net`. Internal split-DNS points it to apps Caddy
(`10.10.100.35`); public DNS and the Cloudflare Tunnel are separate, additive configuration. A
service with no gate of its own must use forward-auth before any public exposure. Never publish
sensitive infrastructure (`opnsense`, `technitium`, `arcane`, `pbs`, and similar services) through
the apps Caddy door.

## Verify

- The selected leaf matches the service's authentication and public-exposure requirement before editing a route.

## Rollback

- Follow the selected leaf; route rollback is normally a reverting PR, while DNS/object deletion remains separately gated.

## Evidence

- The selected leaf's PR, saved-plan approval where applicable, and post-deploy probe are the publish evidence.
