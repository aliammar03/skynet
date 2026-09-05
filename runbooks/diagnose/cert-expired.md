---
summary: "Triage an expired/failing TLS cert — read the served cert's dates, find why ACME isn't renewing (HTTP-01 vs DNS-01, rate limit, clock), fix in Caddy config."
trigger: "Cert warning / TLS handshake fails / 'certificate expired' / ACME renewal failing"
tier: "T1"
executor: "TLS probes and Caddy log inspection"
rollback: "git revert the Caddy configuration fix"
---

# Diagnose — cert expired

**Tier:** **T1** to inspect with unprivileged `svc-ops` access. **Trigger:** a browser cert warning, TLS
handshake failure, expired-certificate error, or Caddy ACME renewal failure. The fix is a Caddy-config
PR; certificate material is never hand-placed on a host.

## Preconditions

- Have the affected hostname and read access to its endpoint and Caddy container logs.
- Do not copy certificate or key material onto a host; inspect only served metadata and logs.

## Steps

### Confirm the served certificate

```bash
echo | openssl s_client -connect <host>:443 -servername <name> 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

Read `notAfter` (expired?), `issuer` (Let's Encrypt vs Caddy's internal CA vs stale self-signed), and
`subject` (right name?). Then the issuer's own words:

```bash
CADDY=$(ssh svc-ops@<docker-host> docker ps --filter name=caddy --format '{{.Names}}' | head -1)  # e.g. caddy-apps-caddy-1
ssh svc-ops@<docker-host> docker logs --tail 150 "$CADDY" 2>&1 | grep -iE 'acme|cert|tls|error'
date -u                                  # and on the host — clock skew breaks TLS + ACME
ssh svc-ops@<docker-host> timedatectl    # NTP synced?
```

### Classify the cause

| Signal | Cause | Next |
|---|---|---|
| `issuer` = Caddy internal CA, browser distrusts it | served internal cert instead of ACME | Caddy site meant to be public? check the Caddyfile block |
| ACME log: `too many certificates` / rate limited | Let's Encrypt rate limit | back off; don't loop retries; wait out the window |
| ACME **DNS-01** never validates | Cloudflare token scope / TXT propagation | [dns-failure](dns-failure.md) + the `DNS:Edit` token |
| ACME **HTTP-01** 404/timeout | `:80` challenge path not reachable (proxy/firewall) | check the ingress path to `/.well-known/acme-challenge/` |
| cert valid but handshake fails | clock skew, or wrong cert bound to the vhost | `timedatectl` (NTP), then the Caddyfile site match |
| Authentik/other origin cert expired | that origin's own renewal | inspect that service, same method |

### Fix declaratively

Edit the **Caddyfile in git** (the site block, the ACME method, the DNS provider config) →
branch → PR → Ali merges → deploy → Caddy re-issues. If clock skew was the cause, fix **NTP in the
host's config module**, not by hand. Never copy a `.crt`/`.key` onto a host — that is an orphan the next
reconcile erases. Cloudflare tunnel/Access config is **T3**; a DNS *record* for the challenge is T2.

## Verify

Confirm the endpoint serves the expected hostname, issuer, and unexpired `notAfter` date, and Caddy
logs show successful issuance or renewal. Check the challenge path again when HTTP-01 or DNS-01 was the
cause.

## Rollback

Revert the Caddyfile or host configuration PR and let the normal deployment restore the prior issuance
configuration. Never roll back by copying certificate files onto the host.

## Evidence

`bin/new journal incident "<name> cert expired — <ACME cause>"` — the served `notAfter`, the ACME log
line, and the config PR that restored issuance. ([journal](../../journal/README.md).)
