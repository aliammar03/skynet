---
summary: "Publish a service with no native login behind Authentik forward-auth on apps Caddy."
trigger: "Put a no-login service behind Authentik"
tier: "T2 PR-gated"
executor: "apps Caddy GitOps, guarded DNS saved-plan, scoped Authentik API"
rollback: "git revert the route; Authentik/DNS deletion is separately approved"
---

# Runbook — internal route (Authentik forward-auth)

**Tier:** T2 (PR-gated) for the Caddy route, DNS, and scoped Authentik Applications/Providers
operations. **Executor:** apps Caddy GitOps sync, the guarded DNS plan, and the scoped Authentik
API. **Rollback:** revert the route by PR; remove Authentik objects only as an explicitly approved
separate action.

Design context: [`../../docs/design/identity-and-proxy.md`](../../docs/design/identity-and-proxy.md).

## Preconditions

- The origin runs on the DMZ network and its actual `IP:port` is known from
  `compose/<svc>/compose.yaml`.
- The service has no login of its own and must remain protected by Authentik. Authorization-policy
  changes are T3 and are not part of this runbook.
- The scoped Authentik `svc-skynet` token exists at restrictive local path
  `/opt/skynet-ops/secrets/authentik.env` (mode `0400`, owner `aliammar`) with `AUTHENTIK_TOKEN` and `AUTHENTIK_URL`. Ali must
  perform the T3 ceremony that creates it; it can CRUD Applications/Providers and view/bind
  outposts, but cannot manage flows, users, policies, settings, keys, or other T3 objects.
- The Authentik embedded proxy outpost exists and is served by Authentik at
  `10.10.80.37:9000`.
- Only apps Caddy (`10.10.100.35`) can reach Authentik (firewall rule 240). Run API calls from
  inside `caddy-apps-caddy-1`; feed the token through stdin to `curl -K -`, or read it inside the
  container. Never put it in argv, a committed file, or evidence.

## Steps

1. On a `deploy/caddy-apps` branch, add the route and validate it before the PR:

   ```caddyfile
   <svc>.aliammar.net {
       reverse_proxy /outpost.goauthentik.io/* 10.10.80.37:9000
       forward_auth 10.10.80.37:9000 {
           uri /outpost.goauthentik.io/auth/caddy
           copy_headers X-Authentik-Username X-Authentik-Groups X-Authentik-Email X-Authentik-Name X-Authentik-Uid
           trusted_proxies private_ranges
       }
       reverse_proxy <origin-ip>:<origin-port>
   }
   ```

   ```bash
   cd compose/caddy-apps
   docker run --rm -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" \
     ghcr.io/caddybuilds/caddy-cloudflare:2.11.4-alpine \
     caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   ```

2. Open a PR describing the service, origin `IP:port`, Authentik protection, and URL. Ali merges
   it. Do not create the provider or application from an unmerged proposal; the route fails closed
   until its provider exists.

3. After the merge, use the scoped token from inside `caddy-apps-caddy-1` to list proxy providers:

   ```text
   GET /api/v3/providers/proxy/
   ```

   Copy `authorization_flow` and `invalidation_flow` UUIDs from an existing provider. The token
   cannot list flows because flows are T3.

4. Create the per-service `forward_single` proxy provider:

   ```text
   POST /api/v3/providers/proxy/
   {
     "name": "<svc>",
     "mode": "forward_single",
     "external_host": "https://<svc>.aliammar.net",
     "authorization_flow": "<uuid>",
     "invalidation_flow": "<uuid>"
   }
   ```

   Keep the returned provider primary key (`pk`). Perform this and the following calls from the
   Caddy container, with the bearer header supplied through stdin rather than argv.

5. Create the application bound to that provider:

   ```text
   POST /api/v3/core/applications/
   {
     "name": "<Svc>",
     "slug": "<svc>",
     "provider": <pk>,
     "meta_launch_url": "https://<svc>.aliammar.net"
   }
   ```

6. Find the embedded outpost and preserve its current provider list:

   ```text
   GET /api/v3/outposts/instances/
   PATCH /api/v3/outposts/instances/<outpost-pk>/
   {"providers":[<existing…>, <pk>]}
   ```

   Never replace the existing entries with only the new provider; that would unbind every other
   application. The outpost should pick up the provider within seconds. Sanity-check from the
   Caddy container:

   ```bash
   docker exec caddy-apps-caddy-1 curl -sI -H "Host: <svc>.aliammar.net" \
     http://10.10.80.37:9000/outpost.goauthentik.io/auth/caddy
   # expect 302 -> auth.aliammar.net
   ```

7. Create the internal DNS record from the merged revision and apply only the approved saved plan:

   ```bash
   eval "$(scripts/tofu-env.sh)"
   tofu -chdir=tofu plan -out=/tmp/publish-<svc>.tfplan
   tofu -chdir=tofu show -no-color /tmp/publish-<svc>.tfplan  # expect only the derived A record
   TOFU_APPLY_SCOPE=technitium-dns scripts/tofu-apply.sh /tmp/publish-<svc>.tfplan
   ```

## Verify

From a peer DMZ container, an unauthenticated request must redirect to Authentik and must not
serve the application:

```bash
ssh svc-ops@10.10.100.15 "docker exec <some-dmz-container> \
  curl -sI --resolve <svc>.aliammar.net:443:10.10.100.35 https://<svc>.aliammar.net"
```

Expect `302` with a `Location` at `https://auth.aliammar.net/...`. In a browser, confirm the full
sequence: unauthenticated → Authentik login → service. Also confirm the split-DNS record:

```bash
dig +short <svc>.aliammar.net @10.10.70.50  # expect 10.10.100.35
```

## Rollback

Revert the Caddyfile block by PR and let Arcane reconcile. Authentik and DNS deletion are separate
hard checkpoints; do not send delete plans through `scripts/tofu-apply.sh`. If cleanup is approved,
remove the application first and provider second with scoped-token calls. Leave the Technitium
record visible until its compliant delete path exists.

## Evidence

Record the PR and merge commit, Caddy validation, provider/application/outpost response identifiers
(not tokens), saved DNS plan and approval, outpost redirect, peer-DMZ `302`, browser login result,
and internal `dig` output. Redact all credentials and bearer headers.
