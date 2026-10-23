# DNS speed test

Chooses Technitium's forwarders (`dns/settings.json`) by measuring from the lab, not by geography.
Run it on ops as `skynet`. `quick` takes ~3 min; the log runs as long as you leave it.

## Why it's done this way

- **Anycast:** each resolver uses one IP worldwide, and the ISP's routing decides which city answers.
  Geography misleads: on 2026-10-22, Cloudflare answered from Karachi in ~120 ms, then 25 ms an
  hour later, while Dubai (OpenDNS, Quad9) held at ~45 ms. So measure, and measure over time.
- **Two things decide speed:** how fast the answer comes, and which server it points at. CDNs pick
  the server by where the resolver is, or by the client subnet it passes on (ECS). Cloudflare is
  fast but sent YouTube video to ~260 ms servers. Google and OpenDNS reach the 4 ms caches inside the
  ISP. The mapping also shifts within the hour, so `cdnlog` records it over the whole run.
- **Cached vs uncached:** Technitium answers repeats from its own cache, so upstream speed only
  matters for names it doesn't hold. "Cached" asks popular names twice (the resolver has them).
  "Uncached" asks a random name under a real, unsigned domain, so the resolver must go to that
  domain's servers. Signed domains are avoided: a resolver can answer random names under them from
  cache. Every resolver and protocol gets its **own** random name. One shared name made the 2026-10-23
  night's later asks cache hits at the same provider.
- **Raced:** Technitium sends each lookup to every forwarder it races (`forwarderConcurrency`) and
  takes the first answer. `report` simulates pairs and the OpenDNS + Google + Quad9 triple. In the
  CDN log, the winner also decides which server you get. A fast non-ECS resolver winning costs the
  in-ISP caches.
- **ECS caching:** resolvers that pass your subnet (OpenDNS, Google, Quad9's 9.9.9.11) cache
  location-dependent answers per subnet. Popular CDN names are then often uncached for you (~145 ms)
  where plain Quad9 or Cloudflare answer them from a shared cache (~25–45 ms). Technitium's own cache
  and serve-stale hide most of this from clients.
- **DoH and idle connections:** providers close an idle DoH connection within a minute. The first
  lookup after a quiet spell pays a new TLS connection: 100–230 ms here, overnight, against 45–60 ms
  on a warm connection. The once-a-minute log shows that cost, while `quick` (a burst) doesn't.
- **YouTube:** the video servers (`rrN---sn-….googlevideo.com`) are named in the watch page, picked
  by the client's IP. They sit inside the ISP (2–4 ms), and every resolver returns the same IP for
  them, whichever Google front end served the page. DNS picks the servers for the rest: the page and
  its API, thumbnails, avatars, static files. A far front end made the watch page 5 s instead of 1 s.
  `ytlog` covers 19 public resolvers, PTCL's own included (a provider's second address can land at
  another site), and Technitium (what clients get today). `report` ranks every resolver, pair and
  triple.
- **One line:** everything follows the default gateway (PTCL); Storm is failover only.

## Firewall

- DoH (:443) works from ops as-is. Plain DNS (:53) from ops reaches only 1.1.1.1, 8.8.8.8 and 9.9.9.9
  through rule 150, until P2 removes that rule. The script skips anything it can't reach.
- For the other resolvers over UDP, and for `recursion`, Ali adds a temporary rule. He clones rule
  110 ("CORE — Resolvers → approved upstreams", which passes `ROLE_DNS_RESOLVERS` → any :53), and
  sets sequence `115`, source `HOST_SKYNET_OPS`, description `TEST — ops DNS benchmark`. He deletes it
  when the test is done.

## Run

```sh
cd ~/skynet
PY=(nix shell --impure --expr '(builtins.getFlake "nixpkgs").legacyPackages.x86_64-linux.python3.withPackages (p: [ p.httpx p.h2 ])' -c python3 -I runbooks/dns-speed-test/dnsbench.py)

"${PY[@]}" quick          # where each resolver answers from; cached/uncached p50 p90; CDN servers

# recursion: a throwaway Unbound on 127.0.0.1:5353 (needs rule 115)
d=$(mktemp -d); sed "s#@DIR@#$d#g" runbooks/dns-speed-test/unbound.conf > "$d/unbound.conf"
nix shell nixpkgs#unbound -c unbound-anchor -a "$d/root.key"   # exit 1 just means "anchor written"
nix shell nixpkgs#unbound -c unbound -d -c "$d/unbound.conf" & ub=$!
"${PY[@]}" recursion; kill $ub      # recursion waits up to 10 s for Unbound to answer

# a long run: answer times (one round a minute) and CDN servers (every 2 min), then the reports
"${PY[@]}" log /tmp/dns-latency.csv --minutes 360 &    # or --until 09:00; add --recursion while Unbound runs
"${PY[@]}" cdnlog /tmp/dns-cdn.csv --minutes 360 &     # --every N to change the 2 min
"${PY[@]}" ytlog /tmp/dns-yt.csv --minutes 360 &       # YouTube, 20 resolvers (needs rule 115)
"${PY[@]}" report /tmp/dns-latency.csv
"${PY[@]}" report /tmp/dns-cdn.csv
"${PY[@]}" report /tmp/dns-yt.csv
```

A long run belongs to the shell that started it. Use tmux, or the agent's background task, so it
survives.

## Reading it

- p50 is a typical lookup and p90 a bad minute. The "raced" lines are what Technitium will see.
- CDN table: ~4 ms = a cache inside the ISP, ~45 ms = Dubai/Doha, 100+ = far away. The `cdnlog`
  report gives each resolver's median, its share of in-ISP servers (<10 ms) and of far ones
  (>100 ms), and a per-name table.
- YouTube report: "mean" is the YouTube server a resolver hands out (the mean over names of each
  name's median connect ms); "page" and "thumb" are a new HTTPS connection plus one request. Raced
  sets list only those whose every member wins 2%+ of lookups; "other CDNs" shows what the same set
  does to the P2 names (TikTok and Steam's in-ISP caches).
- Pick the fastest raced pair whose CDN column matches the best one. Change `dns/settings.json`
  by PR.
- The script prints where a resolver answered from, never the lab's public IP. Some debug answers
  contain it (OpenDNS `debug.opendns.com`, Google `o-o.myaddr`).

## Last result (2026-10-23, night and day)

Plain UDP to OpenDNS + Google, raced. The day run (11:58–17:58) gave p50 / p90 of 44 / 148 ms for
cached names and 62 / 152 for uncached ones, and both resolvers get the in-ISP caches. The triple
with Quad9 is no faster on uncached names, and Quad9 then wins most races, losing those caches.
Full numbers: `skynetv2.md` → P2 → Prechecks. Still to do: a run that covers the evening peak.
