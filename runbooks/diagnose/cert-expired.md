---
summary: "Triage an expired/failing TLS cert — read the served cert's dates, find why ACME isn't renewing (HTTP-01 vs DNS-01, rate limit, clock), fix in Caddy config."
trigger: "Cert warning / TLS handshake fails / 'certificate expired' / ACME renewal failing"
---

# Diagnose — cert expired

**Trigger:** a browser cert warning, a TLS handshake failure, an "expired certificate" error, or the
apps **Caddy** logging ACME renewal failures.
**Tier:** **T1 to inspect** the served cert and read Caddy logs (unprivileged `svc-ops` docker). The
**fix is a Caddy-config PR** (the Caddyfile lives in git) and/or resolving the ACME path; cert *material*
is never hand-placed on a host.

> **Diagnose imperatively, fix declaratively.** Certs are issued by config (Caddy + ACME), so the fix is
> a config change in git, not a file dropped on the box. ([recon](../recon.md), SKY-005.)

## 1. Confirm — what is actually being served

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

## 2. Branch on the cause

| Signal | Cause | Next |
|---|---|---|
| `issuer` = Caddy internal CA, browser distrusts it | served internal cert instead of ACME | Caddy site meant to be public? check the Caddyfile block |
| ACME log: `too many certificates` / rate limited | Let's Encrypt rate limit | back off; don't loop retries; wait out the window |
| ACME **DNS-01** never validates | Cloudflare token scope / TXT propagation | [dns-failure](dns-failure.md) + the `DNS:Edit` token |
| ACME **HTTP-01** 404/timeout | `:80` challenge path not reachable (proxy/firewall) | check the ingress path to `/.well-known/acme-challenge/` |
| cert valid but handshake fails | clock skew, or wrong cert bound to the vhost | `timedatectl` (NTP), then the Caddyfile site match |
| Authentik/other origin cert expired | that origin's own renewal | inspect that service, same method |

## 3. Fix declaratively

Edit the **Caddyfile in git** (the site block, the ACME method, the DNS provider config) →
branch → PR → Ali merges → deploy → Caddy re-issues. If clock skew was the cause, fix **NTP in the
host's config module**, not by hand. Never copy a `.crt`/`.key` onto a host — that is an orphan the next
reconcile erases. Cloudflare tunnel/Access config is **T3**; a DNS *record* for the challenge is T2.

## 4. Record

`bin/new journal incident "<name> cert expired — <ACME cause>"` — the served `notAfter`, the ACME log
line, and the config PR that restored issuance. ([journal](../../journal/README.md).)
