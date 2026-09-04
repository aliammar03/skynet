---
summary: "Triage DNS failures — split internal (Technitium) vs public (Cloudflare), read NXDOMAIN/SERVFAIL, fix the record through the sanctioned T2 path."
trigger: "A name won't resolve / service unreachable by hostname / ACME DNS-01 failing"
---

# Diagnose — DNS failure

**Trigger:** a hostname won't resolve, a service is unreachable by name (but fine by IP), or an ACME
**DNS-01** challenge is failing.
**Tier:** **T1 to read.** `dig` costs nothing; viewing a **Technitium zone** or a **Cloudflare record**
is T1. *Changing* a record is **T2** (scoped token, PR-gated — Technitium zones, Cloudflare `DNS:Edit`
on `aliammar.net`). Technitium **server settings** and the Cloudflare **account** are T3 — never touched here.

> **Diagnose imperatively, fix declaratively.** The lab is **static-IP-first**; a name that should
> resolve is a *record*, and records change through the sanctioned T2 path, not a hand-edit. (SKY-005.)

## 1. Confirm — and locate the split

The lab is split-horizon: **Technitium** answers internal names, **Cloudflare** answers public ones.
Ask both, so you know which half is broken:

Query an actual **resolver**, not a service's web-UI hostname. The resolvers are the `tdns-*`
hosts in VLAN 70 — `ROLE_DNS_RESOLVERS` in
[`docs/generated/20-firewall.md`](../../docs/generated/20-firewall.md)
(`10.10.70.30/.31/.50/.51`; `tdns-core` = `10.10.70.51`, `tdns-network` = `10.10.70.50`).
Confirm there — **don't** use a proxied `<name>.aliammar.net` admin URL: e.g. `technitium-core.aliammar.net`
resolves to `HOST_PROXY_ADMIN` (Management Caddy, T3), which is the console front door, not the DNS server.

```bash
TDNS=10.10.70.51                        # tdns-core — verify against ROLE_DNS_RESOLVERS above
dig +short <name> @"$TDNS"             # internal resolver (Technitium)
dig +short <name> @1.1.1.1             # public (Cloudflare-published)
dig <name> @"$TDNS"                    # full answer — read the status line (NOERROR/NXDOMAIN/SERVFAIL)
resolvectl status                      # what resolver is THIS client actually using?
```

## 2. Branch on the answer

| Signal | Reading | Where the record lives |
|---|---|---|
| resolves **public**, not **internal** | Technitium zone missing the record (or forwarder down) | Technitium **zone** (T2) |
| resolves **internal**, not **public** | Cloudflare record missing, or set DNS-only vs proxied wrong | Cloudflare `aliammar.net` (T2) |
| `NXDOMAIN` | the record simply isn't there | add it (the correct side above) |
| `SERVFAIL` | resolver/forwarder/DNSSEC problem, not a missing record | Technitium forwarder health (view T1; settings are T3 → stop, ask) |
| resolves, wrong IP | stale record after a move | correct the record; the lab is static-IP-first, so the *right* IP is known |
| ACME **DNS-01** TXT never appears | Cloudflare `DNS:Edit` token scope, or TXT propagation delay | see [cert-expired](cert-expired.md) + the token |

Host aliases + DHCP reservations + zone records are merged into the generated host map by
`render-docs.sh` — cross-check the expected name/IP there before editing.

## 3. Fix declaratively

A record change is a **T2, PR-gated** operation.

Fix the declarative source on a branch, attach the speculative plan to the PR, and wait for Ali to
merge. From the merged revision, save and show the exact plan; apply it only after approval:

```bash
eval "$(scripts/tofu-env.sh)"
tofu -chdir=tofu plan -out=/tmp/dns-fix.tfplan
tofu -chdir=tofu show -no-color /tmp/dns-fix.tfplan
scripts/tofu-apply.sh /tmp/dns-fix.tfplan
```

- **Internal `aliammar.net` records are tofu-managed (SKY-008).** The declarative source of truth is
  `tofu/dns-aliammar-net.tf` — the app-service records are *derived from the apps Caddyfile*, the admin
  vanity names are an explicit map. So a missing/wrong internal record is fixed in **git via the
  saved-plan path above**, not a hand-run token call —
  the scoped Technitium token is what tofu authenticates with under the hood.
  ⚠ **Caveat:** that token can *add/modify* but **not delete** records yet — removing a stale record
  needs the record-delete grant (or a manual Technitium-UI delete). The DNSSEC-signed resolver zone
  `tdns.home.aliammar.net` is **not** yet tofu-managed (provider read bug) — edit it via the UI/token.
- **Public `aliammar.net` records are also tofu-managed (SKY-014).** The tunnel CNAMEs live in
  `tofu/cloudflare-dns.tf`, *derived from the cloudflared ingress* (`compose/cloudflared/config.yml`) —
  fix through the same saved-plan path. Break-glass
  for an immediate change: `scripts/cf-dns-route.sh` (scoped Cloudflare `DNS:Edit` token).

Record the fix so the generated host map stays truthful. Anything that reaches for Technitium
**settings** or the Cloudflare **account/zone settings** is **T3 — stop and request a session**.

## 4. Record

`bin/new journal incident "<name> DNS failure — <NXDOMAIN|SERVFAIL|wrong side>"` — which resolver failed,
the status code, the record you added/fixed and on which side. ([journal](../../journal/README.md).)
