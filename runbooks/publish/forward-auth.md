---
summary: "Publish a service with no native login behind Authentik forward-auth on apps Caddy."
trigger: "Put a no-login service behind Authentik"
tier: "T2 PR-gated"
executor: "skynet deploy caddy-apps, skynet publish, guarded DNS saved-plan"
rollback: "git revert the route, then skynet withdraw (separately approved)"
---

# Runbook — internal route (Authentik forward-auth)

**Tier:** T2 (PR-gated) for the Caddy route, DNS, and scoped Authentik Applications/Providers
operations. **Executor:** `skynet deploy caddy-apps`, `skynet publish` (scoped Authentik API), and
the guarded DNS plan. **Rollback:** revert the route by PR; remove Authentik objects only as an explicitly approved
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
- Only apps Caddy (`10.10.100.35`) can reach Authentik (firewall rule 240); `skynet publish` calls
  the API from inside `caddy-apps-caddy-1`.

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

2. Open a PR describing the service, origin `IP:port`, Authentik protection, and URL (with
   `skynet deploy caddy-apps --dry-run HEAD`). Ali merges it; the timer deploys `caddy-apps`. The
   route fails closed until its provider exists.

3. Publish it — this creates the Authentik objects git cannot hold, then proves the route:

   ```bash
   skynet publish <svc> --dry-run   # which vhosts, which need Authentik objects
   skynet publish <svc>
   ```

   It refuses unless `caddy-apps` runs `main`. For each forward-auth vhost of the service it
   creates, only if missing, a `forward_single` proxy provider (flows copied from an existing
   one; the token cannot list flows), the application (slug = the vhost's first label), and the
   binding on the embedded outpost — appending to its provider list, never replacing it. It then
   probes the vhost anonymously and requires a `302` to `https://auth.aliammar.net/`, retrying
   while the outpost picks the provider up. If the probe fails, it deletes only the objects it
   created and restores the outpost's list. The token travels on stdin into `curl -K -` inside
   `caddy-apps-caddy-1` (firewall rule 240), never in argv.

4. Create the internal DNS record from the merged revision and apply only the approved saved plan:

   ```bash
   eval "$(scripts/tofu-env.sh)"
   tofu -chdir=tofu plan -out=/tmp/publish-<svc>.tfplan
   tofu -chdir=tofu show -no-color /tmp/publish-<svc>.tfplan  # expect only the derived A record
   TOFU_APPLY_SCOPE=technitium-dns scripts/tofu-apply.sh /tmp/publish-<svc>.tfplan
   ```

## Verify

`skynet publish <svc>` already proved the anonymous `302` to Authentik. In a browser, confirm the
full sequence: unauthenticated → Authentik login → service. Also confirm the split-DNS record:

```bash
dig +short <svc>.aliammar.net @10.10.70.50  # expect 10.10.100.35
```

## Rollback

Revert the Caddyfile block by PR; the timer deploys the previous route. Deleting the Authentik
objects (and any public CNAME) is a separate hard checkpoint: once approved and the revert is on
`main`, run `skynet withdraw <svc>.aliammar.net --confirm <svc>.aliammar.net`. Do not send delete
plans through `scripts/tofu-apply.sh`; leave the Technitium record visible until its compliant
delete path exists.

## Evidence

Record the PR and merge commit, Caddy validation, the `skynet publish` output (created objects,
probe result), saved DNS plan and approval, browser login result,
and internal `dig` output. Redact all credentials and bearer headers.
