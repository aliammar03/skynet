---
date: 2026-08-20
kind: session
title: Publish calibre publicly behind Authentik forward-auth (+ admin lockdown)
tier_touched: [T1, T2]
grants: []
refs: [SKY-003, SKY-014, PR #79, calibre.aliammar.net, auth.aliammar.net]
---

# 2026-08-20 · session · Publish calibre publicly behind Authentik forward-auth (+ admin lockdown)

## What happened
Right after SKY-003 P3 closed out (calibre gated internally by Authentik forward-auth), Ali asked to
make calibre reachable from the public internet, behind Authentik, with the least-friction repeatable
setup ("don't want to go to the Cloudflare dashboard every time"). That requirement decided the auth
model: Cloudflare Access = a dashboard policy per app (our CF token is DNS:Edit only, no API path to
Access) → rejected; Authentik forward-auth = one-time publish of auth.aliammar.net, then every future
app is pure git+token. Chose Authentik-public with an admin lockdown (Ali's variant).

Key realization: a forward-auth app can't be published alone. An unauthenticated request to
calibre.aliammar.net is 302'd to auth.aliammar.net to log in; if the login host doesn't resolve
publicly, the redirect dead-ends. So auth.aliammar.net had to be published too — exposing the
Authentik login UI to the internet. Ali confirmed passkey-only auth on his account (phishing-resistant).

PR #79 (merged by Ali):
- compose/cloudflared/config.yml: ingress entries for calibre.aliammar.net + auth.aliammar.net (both
  → https://10.10.100.35, originServerName set), above the http_status:404 catch-all.
- compose/caddy-apps/Caddyfile: auth.aliammar.net vhost gained a tunnel-admin guard —
  `@tunnel_admin { remote_ip 10.10.100.33; path /if/admin/* } respond @tunnel_admin 404`. cloudflared
  connects to Caddy from .33, so remote_ip .33 == "arrived via the public tunnel". Deliberately did
  NOT block /api/v3/* or /if/flow/* — the login flow executor lives there.

Rollout (post-merge):
- gitops-deploy.sh caddy-apps → Caddy --watch hot-reloaded the lockdown (grep confirmed /if/admin in
  the running Caddyfile).
- gitops-deploy.sh cloudflared did NOT recreate the container (compose spec unchanged, only the
  mounted config.yml) → still "Up 13 hours" with old ingress. Had to `docker restart
  cloudflared-cloudflared-1` to load the new ingress. (cloudflared has no --watch; a mounted-file
  change needs a restart.)
- cf-dns-route.sh initially failed as `ali` ("missing cloudflare-dns.env") because the secret is 0600
  root-owned — the script reads it directly, so it must run under sudo. `sudo -n scripts/cf-dns-route.sh
  <host>` created both proxied CNAMEs → b5171e13-….cfargotunnel.com. (TUNNEL_ID in cloudflare-dns.env
  matched config.yml's tunnel: b5171e13-f6c4-409c-8b60-760f769c706b.)

Verified from a simulated-external vantage (resolve via 1.1.1.1 → Cloudflare anycast 104.21.57.57 /
172.67.159.145, curl --resolve to the edge IP):
- calibre (public) → 302 to auth.aliammar.net/application/o/authorize/?client_id=4FSYZhe70… (provider
  14, calibre callback) — full external chain works.
- auth root (public) → 302 → follows to final 200 (login UI serves).
- auth /if/flow/default-authentication-flow/ (public) → 200 (login executor reachable).
- auth /if/admin/ over tunnel → 404 (lockdown holds); /if/admin/ from an internal DMZ container
  (remote_ip 10.10.100.53) → 200. Lockdown is exactly tunnel-scoped.

## Actions & outcomes
- decision: Authentik-public over Cloudflare Access, driven by "no dashboard per app" → one-time auth publish
- PR #79 merged (config.yml ingress + Caddyfile admin lockdown), validated (cloudflared ingress OK, caddy validate clean)
- deploy: caddy-apps hot-reloaded; cloudflared needed an explicit `docker restart` (no --watch)
- cf-dns-route.sh needs sudo (0600 root secret); created both proxied CNAMEs
- external verification matrix all green (gated calibre, public login, admin 404-over-tunnel / 200-internal)

## Graveyard — tried & abandoned
- Cloudflare Access as the gate → abandoned: dashboard policy per app (no API token for Access), which
  is exactly the friction Ali rejected.
- `cf-dns-route.sh` as `ali` → failed on the 0600 root secret; must run under sudo.
- Expecting `gitops-deploy.sh cloudflared` to reload the ingress → it doesn't recreate on a mounted-file-only
  change; restart the container.

## Follow-ups / open threads
- **Ali's human test:** open https://calibre.aliammar.net from a truly external device (phone on
  mobile data) → Authentik passkey login → calibre loads. (Simulated-external checks pass; only the
  passkey ceremony needs a real browser.)
- Reusable pattern captured in runbooks/publish-service.md Path C (forward-auth app → publish auth too
  + admin lockdown).
- SKY-014 could note the public path is now realized for a forward-auth app (was "revisited then").
