# dns

The internal zone and the settings of both Technitium servers, technitium-network and technitium-core
(skynetv2.md → P2). `technitium-sync` (`modules/dns.nix`, `modules/technitium-sync.sh`) applies them
through Technitium's API at boot and on every deploy that changes them.

## Records: `aliammar.net.zone`

- **A change** = edit + PR. Both servers apply it within ~2 min of the merge. Check it with
  `dig @10.10.70.50 <name>.aliammar.net` and `@10.10.70.51`.
- **Format:** Technitium's export format, one record per line. The file is the whole zone: a record
  missing from it is deleted on the next sync. An export of the zone equals the file, except the SOA
  serial, which Technitium bumps on every change.
- **Primary zone:** inside the lab the file is all of `aliammar.net`. A name missing from it is
  NXDOMAIN, and a type a name lacks (AAAA) is "no record", never NXDOMAIN. A Forwarder zone sent
  missing types to public DNS, and musl and systemd-resolved then dropped the whole name. Public
  records at Cloudflare aren't visible inside, so caddy-admin's DNS-01 skips its own propagation
  check (`stacks/admin/caddy-admin/conf/Caddyfile`). Keep the SOA, NS and `ns` lines. The SOA's last
  field (60 s) is how long a "doesn't exist" answer is cached. Keep it short: a name asked for
  before its record syncs would otherwise stay missing on that client for the whole time, and Gatus
  would post a false DOWN for every new app.
- No wildcard inside: each name gets its own line, pointing at its door (`runbooks/new-stack.md` →
  Route). The `*` CNAME exists only at Cloudflare, for the tunnel.

## Settings: `settings.json`

Only these keys are set; every other setting keeps Technitium's default. The sync fails if a key
doesn't read back as written (a typo, say), so the deploy fails and comin posts to `#alerts`.

| Keys | Value | Why |
|---|---|---|
| `recursion`, `recursionNetworkACL` | loopback, 10.10.0.0/16, 100.64.0.0/10 | the lab and Tailscale only |
| `qpmLimitBypassList` | 10.10.0.0/16, 100.64.0.0/10 | Technitium rate-limits every client by default (600 queries/min per IP, 6000 per /24), and a Docker host's containers count as one IP |
| `forwarders`, `forwarderProtocol` | PTCL 39.39.39.39, OpenDNS 208.67.222.222, Google 8.8.8.8; UDP | PTCL (the ISP's own) answers names it holds in ~5 ms; OpenDNS is fastest on names nobody asked for yet; all three hand out the same YouTube servers and the in-ISP CDN caches (`runbooks/dns-speed-test/`) |
| `concurrentForwarding`, `forwarderConcurrency` | on, 3 | all three are asked; the first answer wins. PTCL answers REFUSED for sites on Pakistan's blocklist, and Technitium then takes OpenDNS's or Google's answer |
| `forwarderTimeout`, `forwarderRetries` | 1000 ms, 2 | a dead forwarder is skipped quickly |
| `dnssecValidation` | off | no extra key lookups on misses. Nothing checks answers over plain UDP; accepted for speed |
| `saveCache`, `serveStale`, `serveStaleTtl`, `serveStaleMaxWaitTime` | on, on, 3 days, 0 | an expired name answers from cache at once and refreshes in the background; the cache survives restarts |
| `cacheMaximumEntries`, `enableCachePrefetch` | 100 000 (default 10 000), on | popular names refresh before they expire |
| `enableBlocking`, `blockingType`, `blockListUrls`, `blockListUpdateIntervalHours` | HaGeZi Pro, NXDOMAIN, daily | HaGeZi's wildcard format: a listed domain blocks its subdomains too |
| `loggingType`, `useLocalTime` | console, on | logs go to the journal, in PKT |
| `logQueries` | on | every query too: the query log, below |

## The query log

Each query is a line in the journal, so VictoriaLogs keeps 30 days of who asked what (Ali's call,
2026-10-28; every device's lookups, the family's included):
`[<client>:<port>] [UDP] QNAME: <name>; QTYPE: A; QCLASS: IN; RCODE: Refused; ANSWER: […]`. Both
servers together write about 160,000 a day. Who was refused in the last hour, and for what:
```
_time:1h _SYSTEMD_UNIT:="technitium-dns-server.service" "RCODE: Refused" | extract "Local] [<client>:<_>] [<proto>] QNAME: <qname>; QTYPE: <qtype>;" | stats by (_HOSTNAME, client, proto, qname, qtype) count() hits | sort by (hits desc)
```
A storm past journald's cap (about 100 lines a second, `modules/observability.nix`) loses lines;
`LogsDropped` says how many.

## The web UI

http://10.10.70.50:5380 and .51 (or via caddy-admin). It's read-only in practice: the zone and the keys
above are overwritten on the next sync, and a setting changed only in the UI isn't in git. Log in as
`admin`. The password is `technitium_admin_password` in `secrets/technitium-<node>.yaml`:
`nix shell nixpkgs#sops -c sops -d --extract '["technitium_admin_password"]' secrets/technitium-network.yaml`.
It's used on the server's first start only, so changing it in sops doesn't change the server's.

A failed sync shows in `journalctl -u technitium-sync`.
