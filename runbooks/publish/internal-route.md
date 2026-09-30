---
summary: "Publish an own-auth service on the internal apps Caddy front door."
trigger: "Give an authenticated service an internal aliammar.net URL"
tier: "T2 PR-gated"
executor: "skynet deploy caddy-apps, skynet tofu (technitium-dns), skynet publish"
rollback: "git revert the Caddyfile route; its derived DNS record is deleted with it"
---

# Runbook — internal route (own-auth)

**Tier:** T2 (PR-gated). **Executor:** `skynet deploy caddy-apps`, the guarded DNS plan, and
`skynet publish`.
**Rollback:** revert the Caddyfile change by PR; leave the DNS record in place unless a compliant
delete path is separately approved.

Design context: [`../../docs/design/identity-and-proxy.md`](../../docs/design/identity-and-proxy.md).

## Preconditions

- The origin runs on the DMZ network and its actual `IP:port` is known from
  `compose/<svc>/compose.yaml`.
- The service has a real login of its own. A plain no-auth service belongs in
  [`forward-auth.md`](forward-auth.md), even if its internal route is intentionally private.
- The service is not sensitive infrastructure. The Management Caddy is T3 and is out of scope.
- Each site address in `compose/caddy-apps/Caddyfile` derives its own Technitium `A` record to
  `10.10.100.35` through `tofu/dns-aliammar-net.tf`; there is no wildcard fallback.
- Caddy obtains a publicly trusted certificate with ACME DNS-01 through Cloudflare. There is no
  per-service certificate or device-trust installation step.

## Steps

1. Create or use a `deploy/caddy-apps` branch. Add one site block to
   `compose/caddy-apps/Caddyfile`, using the origin's actual listen port:

   ```caddyfile
   <svc>.aliammar.net {
       reverse_proxy <origin-ip>:<origin-port>
   }
   ```

   Use the actual listen port (for example, `karakeep-web` is `10.10.100.75:3000`, not `8080`).

2. Validate the file before opening the PR:

   ```bash
   cd compose/caddy-apps
   docker run --rm -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" \
     ghcr.io/caddybuilds/caddy-cloudflare:2.11.4-alpine \
     caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   ```

   `caddy fmt --overwrite /etc/caddy/Caddyfile` normalizes formatting.

3. Commit the Caddyfile, then write the derived DNS record's approved plan into the same PR (from a
   branch rebased on `main`):

   ```bash
   skynet tofu plan technitium-dns --approve  # expect only the derived A record (one create)
   ```

   Open a teaching PR that states the service, origin `IP:port`, resulting URL, and that this is
   an own-auth internal route, and commit `tofu/technitium-dns/approved-plan.json` with it. Ali
   merges it; the agent does not merge its own PR.

4. After the merge, `skynet tofu apply --pending` creates the record (`skynet log --kind tofu`). A `held`
   `tofu/technitium-dns` means the merged plan differs from the approved one: re-plan in a new PR.

5. The timer deploys the merged `caddy-apps` revision (the container is recreated with the new
   Caddyfile; a Caddy that fails its healthcheck rolls back by itself). Then run
   `skynet publish <svc>`: it checks the front door runs `main` and probes the route.

6. Check the origin's proxy-facing behavior before declaring success. If it allow-lists clients,
   it must allow apps Caddy (`10.10.100.35`) and its forwarded clients in the service's own
   versioned configuration. For example, SillyTavern uses
   `SILLYTAVERN_WHITELIST=["::1","127.0.0.1","10.10.0.0/16"]` in
   `compose/silly/.env.git`; it crash-loops with `whitelistMode=false`. If the origin uses OIDC,
   its redirect host `auth.aliammar.net` must already exist in the Caddyfile.

## Verify

Run the request from a peer DMZ container. Apps Caddy uses a macvlan address and is not reachable
from its own Docker host or the ops VM:

```bash
ssh svc-ops@10.10.100.15 "docker exec <some-dmz-container> \
  curl -sSI --resolve <svc>.aliammar.net:443:10.10.100.35 https://<svc>.aliammar.net"
```

Expect a real application status (`200`, `302`, `401`, and so on) and a valid public certificate
(`ssl_verify_result=0`). The first request can briefly fail while ACME DNS-01 obtains the
certificate; retry after roughly 15–30 seconds. A `502` immediately after deploy usually means
the upstream is still warming up. Also confirm the internal record:

```bash
dig +short <svc>.aliammar.net @10.10.70.50  # expect 10.10.100.35
```

## Rollback

Revert the Caddyfile block in a PR carrying the `technitium-dns` approval
(`skynet tofu plan --changed --approve`; expect only the derived A record's delete). After the
merge the timer deploys the previous route and `skynet tofu apply --pending` deletes the record.
If the delete does not land (for example the zone token lacks record-delete), the stack is held
and alerts; fix the cause, then re-apply by a new merge.

## Evidence

Record the PR and merge commit, Caddy validation result, the `approved-plan.json` and its `skynet log` line, deploy or
health result, the peer-DMZ response, and the internal `dig` result. Redact tokens and any secret
material.

The Caddy compose project already has the `proxy` role tag and a Caddy admin API healthcheck on
`:2019`; adding a site changes only the Caddyfile. Caddy certificate data persists at
`/opt/docker/appdata/caddy-apps/data` across restarts.
