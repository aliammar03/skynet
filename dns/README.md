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
- **Forwarder zone:** the `FWD "this-server"` line makes the server answer the file's records and
  resolve every other `aliammar.net` name publicly. That includes the apex SOA and NS, which Caddy's
  DNS-01 checks need. Keep the SOA and FWD lines.
- No wildcard until P3.

## Settings: `settings.json`

Only these keys are set; every other setting keeps Technitium's default. The sync fails if a key
doesn't read back as written (a typo, say), so the deploy fails and comin posts to `#alerts`.

| Keys | Value | Why |
|---|---|---|
| `recursion`, `recursionNetworkACL` | loopback, 10.10.0.0/16, 100.64.0.0/10 | the lab and Tailscale only |
| `qpmLimitBypassList` | 10.10.0.0/16, 100.64.0.0/10 | Technitium rate-limits every client by default (600 queries/min per IP, 6000 per /24), and a Docker host's containers count as one IP |
| `forwarders`, `forwarderProtocol` | OpenDNS 208.67.222.222, Google 8.8.8.8; UDP | fastest from PTCL among the resolvers that hand out the in-ISP CDN caches (`runbooks/dns-speed-test/`) |
| `concurrentForwarding`, `forwarderConcurrency` | on, 2 | both are asked; the first answer wins |
| `forwarderTimeout`, `forwarderRetries` | 1000 ms, 2 | a dead forwarder is skipped quickly |
| `dnssecValidation` | off | no extra key lookups on misses. Nothing checks answers over plain UDP; accepted for speed |
| `saveCache`, `serveStale`, `serveStaleTtl`, `serveStaleMaxWaitTime` | on, on, 3 days, 0 | an expired name answers from cache at once and refreshes in the background; the cache survives restarts |
| `cacheMaximumEntries`, `enableCachePrefetch` | 100 000 (default 10 000), on | popular names refresh before they expire |
| `enableBlocking`, `blockingType`, `blockListUrls`, `blockListUpdateIntervalHours` | HaGeZi Pro, NXDOMAIN, daily | HaGeZi's wildcard format: a listed domain blocks its subdomains too |
| `loggingType`, `useLocalTime` | console, on | logs go to the journal, in PKT |

## The web UI

http://10.10.70.50:5380 and .51 (or via caddy-admin). It's read-only in practice: the zone and the keys
above are overwritten on the next sync, and a setting changed only in the UI isn't in git. Log in as
`admin`. The password is `technitium_admin_password` in `secrets/technitium-<node>.yaml`:
`nix shell nixpkgs#sops -c sops -d --extract '["technitium_admin_password"]' secrets/technitium-network.yaml`.
It's used on the server's first start only, so changing it in sops doesn't change the server's.

A failed sync shows in `journalctl -u technitium-sync`.
