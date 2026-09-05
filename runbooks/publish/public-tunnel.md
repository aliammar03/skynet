---
summary: "Add Cloudflare Tunnel and public DNS exposure to an already-working internal route."
trigger: "Expose an internally published service to the public internet"
tier: "T2 PR-gated"
executor: "cloudflared GitOps restart and guarded Cloudflare DNS saved-plan"
rollback: "git revert ingress; public DNS deletion is a separate checkpoint"
---

# Runbook — public tunnel

**Tier:** T2 PR-gated. The route must already work internally; tunnel traffic reaches that same apps-Caddy route. Cloudflare account, tunnel configuration, Access, and zone settings remain T3.

## Preconditions

- The service has strong own-auth or is protected by [`forward-auth.md`](forward-auth.md). Public exposure is deliberate, per host, and never for sensitive infrastructure.
- The restrictive local Cloudflare DNS file exists at `/opt/skynet-ops/secrets/cloudflare-dns.env` (`0400 aliammar`), containing the scoped DNS token, `CF_ZONE=aliammar.net`, and `TUNNEL_ID`.

## Steps

1. On a branch, add the hostname above the catch-all in `compose/cloudflared/config.yml`:
   ```yaml
   - hostname: <svc>.aliammar.net
     service: https://10.10.100.35
     originRequest:
       originServerName: <svc>.aliammar.net
   ```
   `originServerName` makes Caddy select the hostname certificate.
2. A forward-auth service also needs a public `auth.aliammar.net` route. Its Caddy vhost must reject tunnel traffic to `/if/admin/*` while leaving login APIs/flows accessible; include the app, auth route, and their CNAMEs in the PR. Require MFA or a passkey for the public Authentik account.
3. Open the exposure PR and wait for Ali to merge. Restart the connector from merged source:
   ```bash
   scripts/gitops-deploy.sh cloudflared
   ```
   Confirm the tunnel is ready with four connections. The SSH Docker restart is break-glass only.
4. Generate, show, approve, and apply the derived Cloudflare DNS plan:
   ```bash
   eval "$(scripts/tofu-env.sh)"
   tofu -chdir=tofu plan -out=/tmp/public-<svc>.tfplan
   tofu -chdir=tofu show -no-color /tmp/public-<svc>.tfplan
   TOFU_APPLY_SCOPE=cloudflare-dns scripts/tofu-apply.sh /tmp/public-<svc>.tfplan
   ```
   The public CNAME is derived from ingress; internal split DNS remains separately managed. Do not use the break-glass DNS script for routine work.

## Verify

- From an external network, confirm the hostname reaches the intended route, TLS validates, authentication behaves as designed, and the tunnel/CNAME are healthy.

## Rollback

- Revert ingress through a PR and redeploy cloudflared. Public DNS deletion is destructive and remains a separately approved checkpoint.

## Evidence

- Record the PR, approved saved plan, public endpoint check, authentication result, and tunnel status.
