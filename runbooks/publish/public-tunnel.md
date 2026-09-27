---
summary: "Add Cloudflare Tunnel and public DNS exposure to an already-working internal route."
trigger: "Expose an internally published service to the public internet"
tier: "T2 PR-gated"
executor: "skynet deploy cloudflared, skynet tofu (cloudflare-dns), skynet publish"
rollback: "git revert ingress; public DNS deletion is skynet withdraw (a separate checkpoint)"
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
3. Commit the ingress, then write the derived CNAMEs' approved plan into the same PR (from a branch
   rebased on `main`):
   ```bash
   skynet tofu plan cloudflare-dns --approve  # expect one CNAME create per new hostname
   ```
   Open the exposure PR (with `skynet deploy cloudflared --dry-run HEAD`) and wait for Ali to
   merge. The timer redeploys cloudflared with the new `config.yml` (every revision recreates the
   connector, so no manual restart). Confirm the tunnel is ready with four connections.
4. The `skynet-tofu` timer creates the CNAMEs (`skynet log --kind tofu`). A `held` `tofu/cloudflare-dns`
   means the merged plan differs from the approved one: re-plan in a new PR. Internal split DNS is
   the `technitium-dns` stack.
5. `skynet publish <svc>` — checks the front door and tunnel run `main`, reconciles Authentik for a
   forward-auth vhost, probes the route, and reports the CNAME as `present` or `pending tofu apply`.

## Verify

- From an external network, confirm the hostname reaches the intended route, TLS validates, authentication behaves as designed, and the tunnel/CNAME are healthy.

## Rollback

- Revert ingress through a PR; the timer redeploys cloudflared. Deleting the public CNAME is
  destructive and separately approved: after the revert merges,
  `skynet withdraw <svc>.aliammar.net --confirm <svc>.aliammar.net` deletes the CNAME (and any
  Authentik objects), snapshotting what it removes. Until then the `cloudflare-dns` stack is held
  (its plan is a refused delete). Afterwards `skynet tofu drift` confirms state and Cloudflare
  agree.

## Evidence

- Record the PR, its `approved-plan.json` and `skynet log` line, public endpoint check, authentication result, and tunnel status.
