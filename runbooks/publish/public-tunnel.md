---
summary: "Add Cloudflare Tunnel and public DNS exposure to an already-working internal route."
trigger: "Expose an internally published service to the public internet"
tier: "T2 PR-gated"
executor: "cloudflared GitOps restart and guarded Cloudflare DNS saved-plan"
rollback: "git revert ingress; public DNS deletion is a separate checkpoint"
---

# Runbook — public tunnel (additive)

**Tier:** T2 (PR-gated). **Executor:** Cloudflare Tunnel GitOps restart plus the guarded Cloudflare
DNS plan. **Rollback:** revert the ingress by PR, restart the connector, then handle public DNS
deletion as an explicit hard checkpoint.

Design context: [`../../docs/design/identity-and-proxy.md`](../../docs/design/identity-and-proxy.md),
“The public path”.

## Preconditions

- The service already works through an internal apps Caddy route. This runbook does not create a
  route; the tunnel forwards to the same Caddy route and does not duplicate TLS or routing.
- The service self-gates at the edge: it has a strong own-auth login or uses Authentik
  forward-auth. A plain no-auth service must use [`forward-auth.md`](forward-auth.md) first.
- The scoped Cloudflare DNS token exists at restrictive local path
  `/opt/skynet-ops/secrets/cloudflare-dns.env` (mode `0400`, owner `aliammar`) with `CF_DNS_TOKEN`, `CF_ZONE=aliammar.net`, and
  `TUNNEL_ID`. Cloudflare account, Access, tunnel configuration, and zone settings are T3.
- The service is not sensitive infrastructure. Public exposure is deliberate and per-host.

## Steps

1. On a branch, add the host rule to `compose/cloudflared/config.yml` above the closing
   `- service: http_status:404` catch-all. First match wins:

   ```yaml
   - hostname: <svc>.aliammar.net
     service: https://10.10.100.35
     originRequest:
       originServerName: <svc>.aliammar.net
   ```

   The `originServerName` makes SNI select the host's Caddy certificate rather than a certificate
   for the origin IP.

2. If the internal route uses forward-auth, make the Authentik login host public as well. A
   forward-auth app redirects to `auth.aliammar.net`; without a public login host the redirect
   dead-ends off-network. This is a one-time prerequisite for all future forward-auth apps.

   In the `auth.aliammar.net` Caddy vhost, refuse only the admin UI over the tunnel:

   ```caddyfile
   auth.aliammar.net {
       @tunnel_admin {
           remote_ip 10.10.100.33
           path /if/admin/*
       }
       respond @tunnel_admin 404
       reverse_proxy 10.10.80.37:9000
   }
   ```

   Do not block `/api/v3/*` or `/if/flow/*`; the login flow executor uses them. Include the
   vhost change, the app ingress, and (for the first setup) an `auth.aliammar.net` ingress to the
   same apps Caddy origin in a PR. The app and `auth.aliammar.net` each need their own public
   CNAME. Add the Authentik ingress above the catch-all as:

   ```yaml
   - hostname: auth.aliammar.net
     service: https://10.10.100.35
     originRequest:
       originServerName: auth.aliammar.net
   ```

   Ensure the exposed Authentik account uses MFA or a passkey.

3. Open the public-exposure PR and wait for Ali to merge it. The agent does not merge its own PR.

4. Restart the connector after the merge:

   ```bash
   scripts/gitops-deploy.sh cloudflared
   ```

   `cloudflared` reads `config.yml` only at startup; a bind-mounted file change does not reload
   it. Confirm the connector is healthy (`tunnel ready`, four connections). The manual fallback is:

   ```bash
   ssh svc-ops@10.10.100.15 "docker restart cloudflared-cloudflared-1"
   ```

5. From the merged ingress revision, create and show the exact saved Cloudflare DNS plan. Apply
   only the shown plan after explicit approval:

   ```bash
   eval "$(scripts/tofu-env.sh)"
   tofu -chdir=tofu plan -out=/tmp/public-<svc>.tfplan
   tofu -chdir=tofu show -no-color /tmp/public-<svc>.tfplan  # expect only the derived CNAME(s)
   TOFU_APPLY_SCOPE=cloudflare-dns scripts/tofu-apply.sh /tmp/public-<svc>.tfplan
   ```

   The internal Technitium split-DNS record remains separate. The guarded break-glass helper,
   when specifically approved, is `scripts/cf-dns-route.sh <svc>.aliammar.net`; it is idempotent
   and refuses hosts outside `aliammar.net`.

## Verify

Test from a genuinely external vantage (for example, a phone on mobile data). Resolve the public
CNAME, then connect to the Cloudflare edge IP it returns; resolving `1.1.1.1` and using that as a
`--resolve` target would test the resolver service, not the tunnel edge:

```bash
edge=$(dig +short <svc>.aliammar.net @1.1.1.1 | grep -E '^[0-9]' | head -1)
curl -sSI --resolve <svc>.aliammar.net:443:"$edge" https://<svc>.aliammar.net
```

Expect a real status and a valid public certificate (`ssl_verify_result=0`). For a forward-auth
host, the external flow must redirect to Authentik and then return to the service. For the public
Authentik host, `/if/admin/` must be `404` over the tunnel while `/if/flow/…` and the public login
page serve normally. Also confirm the internal route remains direct to Caddy:

```bash
dig +short <svc>.aliammar.net @10.10.70.50  # expect 10.10.100.35, never a Cloudflare edge
```

## Rollback

Revert the `config.yml` ingress line (and any first-time Authentik edge restriction changes) by
PR, then restart `cloudflared`. The resulting DNS plan is a delete and
`scripts/tofu-apply.sh` refuses it; do not route it through the wrapper. Removing the public CNAME
is an explicit hard checkpoint:

```bash
scripts/cf-dns-route.sh --delete <svc>.aliammar.net
```

Afterward run a read-only `tofu plan` to confirm the refreshed state, source, and Cloudflare agree.
This removes public exposure only; the internal door remains.

## Evidence

Record the PR and merge commit, ingress diff, connector health, saved Cloudflare plan and approval,
external edge response, any Authentik admin/login split checks, and internal `dig` output. Never
record DNS tokens, tunnel credentials, or bearer headers.
