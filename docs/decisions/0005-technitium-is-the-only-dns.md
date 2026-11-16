---
status: accepted
date: 2026-10-24
decision-makers: Ali
---

# Technitium is the only DNS, configured from git

## Context and Problem Statement

The lab needs its own names under `aliammar.net` (split horizon), ad-blocking, and fast lookups
from Pakistan. v1 ran AdGuard beside two Technitium containers set up by hand.

## Considered Options

Upstreams, measured from the lab over two nights and a day (`runbooks/dns-speed-test.md` → Last
result):
- recursion of our own (Unbound): the same CDN servers, but 3–7 times slower on names not cached;
- DoH: 100–230 ms lost each time the connection went idle, which the providers close within a
  minute;
- Cloudflare: fastest on cached names, but it sent YouTube's video to servers ~260 ms away;
- Quad9: misses the CDN caches inside the ISP;
- PTCL, OpenDNS and Google over plain UDP, raced.

## Decision Outcome

Chosen option: **Technitium** is the only DNS: two equal NixOS VMs, technitium-network
(10.10.70.50, the network node) and technitium-core (.51, the core node), each loading the zone
and its settings from `dns/` in git. Ad-blocking with HaGeZi Pro. Lookups forwarded over plain UDP
to PTCL, OpenDNS and Google, all three raced. AdGuard retired. Because it is one product whose
records and settings are reviewed in PRs, and a rebuilt VM comes back complete.

### Consequences

- Good, because PTCL answers names it holds in about 5 ms, OpenDNS is fastest on names nobody asked
  for yet, Google is a second fallback, and all three hand out the CDN caches inside the ISP. PTCL's
  REFUSED for a site on Pakistan's blocklist falls through to the other two.
- Good, because either server alone serves the lab, each on its own node.
- Bad, because nothing checks an answer on its way in: plain UDP, and DNSSEC validation off for
  speed.
- Bad, because the UI is read-only in practice: the next sync overwrites what it changes.

## More Information

Ali, 2026-10-21 (Technitium only); 2026-10-23, with the DNS plan (#36): two VMs configured from
git; 2026-10-24 (#46): PTCL, OpenDNS and Google, raced. The settings and why: `dns/README.md`.
