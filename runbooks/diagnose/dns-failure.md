---
summary: "Triage DNS failures — split internal (Technitium) vs public (Cloudflare), read NXDOMAIN/SERVFAIL, fix the record through the sanctioned T2 path."
trigger: "A name won't resolve / service unreachable by hostname / ACME DNS-01 failing"
tokens: 789
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

```bash
dig +short <name> @10.10.90.53          # internal resolver (Technitium — use the real server IP)
dig +short <name> @1.1.1.1              # public (Cloudflare-published)
dig <name> @10.10.90.53                 # full answer — read the status line (NOERROR/NXDOMAIN/SERVFAIL)
resolvectl status                       # what resolver is THIS client actually using?
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

A record change is a **T2, PR-gated** operation: make it via the scoped Technitium token (zones only) or
the Cloudflare `DNS:Edit` token (`aliammar.net` only), and record it so the generated host map stays
truthful. Anything that reaches for Technitium **settings** or the Cloudflare **account/zone settings**
is **T3 — stop and request a session**, never a standing path.

## 4. Record

`bin/new journal incident "<name> DNS failure — <NXDOMAIN|SERVFAIL|wrong side>"` — which resolver failed,
the status code, the record you added/fixed and on which side. ([journal](../../journal/README.md).)
