---
summary: "Publish an own-auth service on the internal apps Caddy front door."
trigger: "Give an authenticated service an internal aliammar.net URL"
tier: "T2 PR-gated"
executor: "apps Caddy GitOps sync and guarded DNS saved-plan"
rollback: "git revert the Caddyfile route; DNS deletion is a separate checkpoint"
---

# Runbook — internal route (own-auth)

**Tier:** T2 (PR-gated). **Executor:** apps Caddy GitOps sync plus the guarded DNS plan.
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

   `caddy fmt --overwrite /etc/caddy/Caddyfile` may be used to normalize formatting.

3. Open a teaching PR that states the service, origin `IP:port`, resulting URL, and that this is
   an own-auth internal route. Ali merges it; the agent does not merge its own PR.

4. From the human-merged revision, create and show the exact saved DNS plan. Apply only the shown
   plan after explicit approval:

   ```bash
   eval "$(scripts/tofu-env.sh)"
   tofu -chdir=tofu plan -out=/tmp/publish-<svc>.tfplan
   tofu -chdir=tofu show -no-color /tmp/publish-<svc>.tfplan  # expect only the derived A record
   TOFU_APPLY_SCOPE=technitium-dns scripts/tofu-apply.sh /tmp/publish-<svc>.tfplan
   ```

5. Let Arcane sync the merged Caddyfile. Caddy runs with `--watch`, so a route-only change hot
   reloads without a container recreate. Run `scripts/gitops-deploy.sh caddy-apps` only to force
   an immediate sync or after a compose change.

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

Revert the Caddyfile block in a PR and let Arcane reconcile the previous route. Removing the
derived Technitium record is a separate delete hard checkpoint: `scripts/tofu-apply.sh` refuses
delete plans and the current zone token lacks record-delete. Do not bypass either guard; leave an
unused record visible until a compliant deletion path is approved.

## Evidence

Record the PR and merge commit, Caddy validation result, saved-plan output and approval, deploy or
health result, the peer-DMZ response, and the internal `dig` result. Redact tokens and any secret
material.

The Caddy compose project already has the `proxy` role tag and a Caddy admin API healthcheck on
`:2019`; adding a site changes only the Caddyfile. Caddy certificate data persists at
`/opt/docker/appdata/caddy-apps/data` across restarts.
