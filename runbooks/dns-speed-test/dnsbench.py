# DNS speed test from the lab (runbooks/dns-speed-test/README.md). Modes:
#   quick              answer times per resolver (UDP, DoH; cached vs uncached) + CDN servers handed out
#   recursion          a local Unbound on 127.0.0.1:5353 vs OpenDNS/Google
#   log CSV [--until HH:MM | --minutes N] [--recursion]   one round a minute
#   cdnlog CSV [--minutes N] [--every M]   every M min: which CDN server each resolver points to
#   report CSV         p50/p90/p99, raced pairs, hourly p50; for a cdnlog CSV, the CDN servers
# Prints where a resolver answered from, never the lab's public IP (some debug answers contain it).
import csv, collections, datetime, ipaddress, json, random, socket, statistics, string, struct, sys, time
import httpx

RESOLVERS = {  # name: (plain-DNS IP, DoH URL)
    "OpenDNS": ("208.67.222.222", "https://doh.opendns.com/dns-query"),
    "Google": ("8.8.8.8", "https://dns.google/dns-query"),
    "Quad9": ("9.9.9.9", "https://dns.quad9.net/dns-query"),
    "Quad9-ECS": ("9.9.9.11", "https://dns11.quad9.net/dns-query"),
    "Cloudflare": ("1.1.1.1", "https://cloudflare-dns.com/dns-query"),
    "AdGuard": ("94.140.14.140", "https://unfiltered.adguard-dns.com/dns-query"),
}
WARM = ["google.com", "youtube.com", "facebook.com", "instagram.com", "whatsapp.net", "tiktok.com", "netflix.com",
        "microsoft.com", "apple.com", "amazon.com", "wikipedia.org", "github.com", "x.com", "linkedin.com",
        "reddit.com", "daraz.pk", "dawn.com", "spotify.com", "openai.com", "bing.com"]
NEW = ["yahoo.com", "zoom.us", "canva.com", "adobe.com", "dropbox.com", "slack.com", "discord.com", "twitch.tv",
       "imdb.com", "booking.com", "paypal.com", "ebay.com", "aliexpress.com", "cnn.com", "bbc.com", "medium.com",
       "quora.com", "pinterest.com", "wordpress.com", "shopify.com", "samsung.com", "olx.com.pk", "geo.tv", "hbl.com"]
# Unsigned zones only: for DNSSEC-signed ones a resolver can answer a random name from cache (aggressive NSEC).
PARENTS = ["github.com", "wikipedia.org", "reddit.com", "dawn.com", "daraz.pk", "linkedin.com", "spotify.com",
           "stackoverflow.com", "nytimes.com", "bbc.co.uk", "zoom.us", "adobe.com", "imdb.com", "olx.com.pk"]
# Names whose answer depends on where the resolver (or the subnet it passes on) is.
CDN = ["redirector.googlevideo.com", "i.ytimg.com", "static.xx.fbcdn.net", "video.xx.fbcdn.net", "assets.nflxext.com",
       "www.microsoft.com", "www.apple.com", "d1.awsstatic.com", "www.tiktok.com", "steamcdn-a.akamaihd.net"]

def query(name, qtype=1, qclass=1):
    m = struct.pack(">HHHHHH", random.randint(0, 65535), 0x0100, 1, 0, 0, 0)
    for label in name.rstrip(".").split("."): m += bytes([len(label)]) + label.encode()
    return m + b"\x00" + struct.pack(">HH", qtype, qclass)

def answers(resp):  # -> [(type, rdata bytes)]
    def skip(i):
        while resp[i]:
            if resp[i] >= 192: return i + 2
            i += resp[i] + 1
        return i + 1
    qd, an = struct.unpack(">HH", resp[4:8]); i = 12
    for _ in range(qd): i = skip(i) + 4
    out = []
    for _ in range(an):
        i = skip(i); t, _, _, n = struct.unpack(">HHIH", resp[i:i + 10]); i += 10
        out.append((t, resp[i:i + n])); i += n
    return out

def rcode_ok(resp): return resp[3] & 0xF in (0, 3)   # NOERROR, NXDOMAIN; SERVFAIL/REFUSED count as failures
def a_records(resp): return [socket.inet_ntoa(d) for t, d in answers(resp) if t == 1 and len(d) == 4]
def txt(resp):
    out = []
    for t, d in answers(resp):
        j = 0
        while t == 16 and j < len(d): out.append(d[j + 1:j + 1 + d[j]].decode(errors="replace")); j += d[j] + 1
    return out
rand_name = lambda parent: "".join(random.choices(string.ascii_lowercase, k=14)) + "." + parent

class Udp:
    def __init__(self, ip, port=53, timeout=3): self.addr, self.timeout = (ip, port), timeout
    def __call__(self, body):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(self.timeout); t = time.perf_counter(); s.sendto(body, self.addr); d = s.recv(65535)
        return (time.perf_counter() - t) * 1000, d

class Doh:  # one HTTP/2 connection, reopened after an error (a resolver's real behaviour)
    def __init__(self, url): self.url, self.c = url, None
    def __call__(self, body):
        self.c = self.c or httpx.Client(http2=True, timeout=3)
        try:
            t = time.perf_counter()
            r = self.c.post(self.url, content=body, headers={"content-type": "application/dns-message", "accept": "application/dns-message"})
            r.raise_for_status(); return (time.perf_counter() - t) * 1000, r.content
        except Exception:
            self.c.close(); self.c = None; raise

def reachable(ask):
    try: return rcode_ok(ask(query("example.com"))[1])
    except Exception: return False

def timed(ask, name):
    ms, resp = ask(query(name))
    if not rcode_ok(resp): raise RuntimeError(f"rcode {resp[3] & 0xF}")
    return ms

def ms_list(ask, names):
    xs, fails = [], 0
    for n in names:
        try: xs.append(timed(ask, n))
        except Exception: fails += 1
    return xs, fails
pct = lambda xs, p: sorted(xs)[min(len(xs) - 1, int(len(xs) * p))]
fmt = lambda xs: f"{pct(xs, .5):5.0f} {pct(xs, .9):5.0f}" if xs else "    -     -"

def connect_ms(ip):
    best = None
    for _ in range(2):
        try:
            t = time.perf_counter(); socket.create_connection((ip, 443), timeout=2).close()
            best = min(best or 1e9, (time.perf_counter() - t) * 1000)
        except Exception: pass
    return best

def cdn_table(askers):
    print(f"\nCDN servers handed out: TCP connect ms (~4 = inside the ISP, ~45 = Dubai/Doha, 100+ = far)")
    print(f"  {'name':28}" + "".join(f"{k:>11}" for k in askers))
    cols = collections.defaultdict(list)
    for n in CDN:
        row = f"  {n:28}"
        for k, ask in askers.items():
            try: ms = min([m for m in map(connect_ms, a_records(ask(query(n))[1])[:2]) if m] or [None])
            except Exception: ms = None
            if ms: cols[k].append(ms)
            row += f"{(f'{ms:.0f}' if ms else '-'):>11}"
        print(row, flush=True)
    print(f"  {'median':28}" + "".join(f"{(f'{statistics.median(cols[k]):.0f}' if cols[k] else '-'):>11}" for k in askers))

def pops():
    def first(ask, *q):
        try: return txt(ask(query(*q))[1])
        except Exception: return []
    found = {"Quad9": ",".join(first(Doh(RESOLVERS["Quad9"][1]), "id.server", 16, 3)),
             "Cloudflare": ",".join(first(Udp(RESOLVERS["Cloudflare"][0]), "id.server", 16, 3)),
             "OpenDNS": ",".join(s for s in first(Doh(RESOLVERS["OpenDNS"][1]), "debug.opendns.com", 16) if s.startswith("server"))}
    egress = [s for s in first(Doh(RESOLVERS["Google"][1]), "o-o.myaddr.l.google.com", 16) if "edns0" not in s]
    try:
        prefixes = httpx.get("https://www.gstatic.com/ipranges/publicdns.json", timeout=5).json()["prefixes"]
        ip = ipaddress.ip_address(egress[0])
        found["Google"] = next(p["scope"] for p in prefixes if "ipv4Prefix" in p and ip in ipaddress.ip_network(p["ipv4Prefix"]))
    except Exception: found["Google"] = "?"
    print("Answered from: " + " · ".join(f"{k} {v or '?'}" for k, v in found.items()))

def quick():
    pops()
    print(f"\n{'resolver':11} {'proto':5} {'cached p50 p90':>15} {'uncached p50 p90':>17}  fails")
    for name, (ip, url) in RESOLVERS.items():
        for proto, ask in (("udp", Udp(ip)), ("doh", Doh(url))):
            if not reachable(ask): print(f"{name:11} {proto:5} unreachable (firewall? see README)"); continue
            ms_list(ask, WARM)                       # prime the resolver's cache with these names
            warm, f1 = ms_list(ask, WARM * 3)
            cold, f2 = ms_list(ask, [rand_name(p) for p in PARENTS])
            print(f"{name:11} {proto:5} {fmt(warm):>15} {fmt(cold):>17}  {f1 + f2}", flush=True)
    cdn_table({k: Doh(url) for k, (_, url) in RESOLVERS.items() if k != "AdGuard"})

def recursion():
    rec = Udp("127.0.0.1", 5353, 8)
    for _ in range(20):                      # Unbound may still be starting
        if reachable(Udp("127.0.0.1", 5353, 1)): break
        time.sleep(0.5)
    else: sys.exit("no resolver on 127.0.0.1:5353: start Unbound first (README)")
    askers = {"Recursion": rec, "OpenDNS": Udp(RESOLVERS["OpenDNS"][0]), "Google": Udp(RESOLVERS["Google"][0])}
    for k in [k for k, ask in askers.items() if not reachable(ask)]:
        print(f"skipping {k}: unreachable (firewall? see README)"); del askers[k]
    print(f"{'':10} {'new site p50 p90':>17} {'unknown name p50 p90':>21}")
    for k, ask in askers.items():
        new, _ = ms_list(ask, NEW)
        cold, _ = ms_list(ask, [rand_name(p) for p in PARENTS])
        print(f"{k:10} {fmt(new):>17} {fmt(cold):>21}", flush=True)
    cdn_table(askers)

def log(path, until=None, minutes=None, with_recursion=False):
    targets = [(n, p, Udp(ip) if p == "udp" else Doh(url)) for n, (ip, url) in RESOLVERS.items() for p in ("udp", "doh")]
    if with_recursion: targets.append(("Recursion", "udp", Udp("127.0.0.1", 5353, 8)))
    for t in [t for t in targets if not reachable(t[2])]:
        print(f"skipping {t[0]}/{t[1]}: unreachable (firewall? see README)"); targets.remove(t)
    now = datetime.datetime.now()
    if minutes: end = now + datetime.timedelta(minutes=minutes)
    else:
        h, m = map(int, (until or "09:00").split(":")); end = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if end <= now: end += datetime.timedelta(days=1)
    print(f"logging to {path} until {end:%Y-%m-%d %H:%M}", flush=True)
    with open(path, "a", buffering=1) as out:
        out.write(f"# run {int(time.time())}\n")   # report drops each run's first round (connection setup)
        i = 0
        while datetime.datetime.now() < end:
            start, warm = time.time(), WARM[i % len(WARM)]
            for name, proto, ask in targets:
                # A fresh name per target: one shared name would make every later ask a cache hit.
                miss = rand_name(PARENTS[i % len(PARENTS)])
                for kind, n in ([("miss", miss)] if name == "Recursion" else [("warm", warm), ("miss", miss)]):
                    try: v = f"{timed(ask, n):.1f}"
                    except Exception: v = "fail"
                    out.write(f"{int(start)},{name},{proto},{kind},{v}\n")
            i += 1; time.sleep(max(0, 60 - (time.time() - start)))

def cdnlog(path, minutes=360, every=2):
    """Every `every` minutes: each resolver/protocol resolves the CDN names; log the connect time
    to the server it points at (min over its first two A records). Rows: ts,resolver,proto,cdn:<name>,ms"""
    askers = []
    for name, (ip, url) in RESOLVERS.items():
        for proto, ask in (("udp", Udp(ip)), ("doh", Doh(url))):
            if reachable(ask): askers.append((name, proto, ask))
            else: print(f"skipping {name}/{proto}: unreachable (firewall? see README)")
    end = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    print(f"CDN log to {path} every {every} min until {end:%Y-%m-%d %H:%M}", flush=True)
    with open(path, "a", buffering=1) as out:
        out.write(f"# run {int(time.time())}\n")
        while datetime.datetime.now() < end:
            start = time.time()
            for name, proto, ask in askers:
                for n in CDN:
                    try: ms = min([m for m in map(connect_ms, a_records(ask(query(n))[1])[:2]) if m] or [None])
                    except Exception: ms = None
                    out.write(f"{int(start)},{name},{proto},cdn:{n},{'fail' if ms is None else f'{ms:.1f}'}\n")
            time.sleep(max(0, every * 60 - (time.time() - start)))

def cdn_report(rows):
    by = collections.defaultdict(list)                  # (resolver, proto) -> [ms]
    cell = collections.defaultdict(list)                # (name, resolver, proto) -> [ms]
    for (name, proto, kind), v in rows:
        by[(name, proto)].append(v); cell[(kind[4:], name, proto)].append(v)
    print("CDN servers each resolver points to (TCP connect ms; <10 = inside the ISP, >100 = far)")
    print(f"{'resolver':11} {'proto':5} {'n':>4} {'median':>7} {'in-ISP':>7} {'far':>5}")
    for (name, proto), xs in sorted(by.items(), key=lambda kv: statistics.median(kv[1])):
        print(f"{name:11} {proto:5} {len(xs):4} {statistics.median(xs):7.0f} {100*sum(x < 10 for x in xs)/len(xs):6.0f}% {100*sum(x > 100 for x in xs)/len(xs):4.0f}%")
    cols = sorted(by, key=lambda k: statistics.median(by[k]))
    print("\nPer name, median ms:\n" + f"{'':28}" + "".join(f"{(n[:8] + '/' + p):>14}" for n, p in cols))
    for n in CDN:
        print(f"{n:28}" + "".join(f"{(f'{statistics.median(cell[(n, r, p)]):.0f}' if cell.get((n, r, p)) else '-'):>14}" for r, p in cols))

def report(path):
    # A round starts whenever the run's first row type comes round again. "# run" lines start a run;
    # each run's first round is dropped (it includes connection setup).
    runs, cur = [], None
    for row in csv.reader(open(path)):
        if not row: continue
        if row[0].startswith("#"): cur = None; continue
        ts, name, proto, kind, v = row; key = (name, proto, kind)
        if cur is None: cur = {"first": key, "rounds": []}; runs.append(cur)
        if key == cur["first"]: cur["rounds"].append({"ts": int(ts)})
        cur["rounds"][-1][key] = None if v == "fail" else float(v)
    rounds = [r for run in runs for r in run["rounds"][1:]]
    cdn = [(k, v) for r in runs for rr in r["rounds"] for k, v in rr.items() if k != "ts" and k[2].startswith("cdn:") and v is not None]
    if cdn: return cdn_report(cdn)
    data, fails, hourly, hours = collections.defaultdict(list), collections.Counter(), collections.defaultdict(list), []
    for r in rounds:
        h = datetime.datetime.fromtimestamp(r["ts"]).hour
        if h not in hours: hours.append(h)                      # in order, also across midnight
        for key, v in r.items():
            if key == "ts": continue
            if v is None: fails[key] += 1
            else: data[key].append(v); hourly[key + (h,)].append(v)
    print(f"{len(rounds)} rounds\n{'resolver':11} {'proto':5} {'kind':4} {'n':>4} {'fail':>4} {'p50':>5} {'p90':>5} {'p99':>5}")
    for k in sorted(data, key=lambda k: (k[2], statistics.median(data[k]))):
        xs = data[k]; print(f"{k[0]:11} {k[1]:5} {k[2]:4} {len(xs):4} {fails[k]:4} {pct(xs,.5):5.0f} {pct(xs,.9):5.0f} {pct(xs,.99):5.0f}")
    print("\nRaced (the faster of two each round, what Technitium's concurrent forwarding gets):")
    for a, b in (("OpenDNS", "Google"), ("Quad9", "Google"), ("Quad9", "Cloudflare"), ("OpenDNS", "Cloudflare")):
        for proto in ("udp", "doh"):
            for kind in ("warm", "miss"):
                xs = [min(r[(a, proto, kind)], r[(b, proto, kind)]) for r in rounds
                      if r.get((a, proto, kind)) is not None and r.get((b, proto, kind)) is not None]
                if xs: print(f"  {a}+{b} {proto} {kind}: p50 {pct(xs,.5):.0f}  p90 {pct(xs,.9):.0f}  p99 {pct(xs,.99):.0f}")
    cols = sorted({(n, p) for (n, p, _) in data})
    print("\nHourly p50, cached/uncached:\nhour " + "".join(f"{n[:8] + '/' + p:>14}" for n, p in cols))
    for h in hours:
        cell = lambda n, p: "/".join(f"{statistics.median(hourly[(n, p, k, h)]):.0f}" if hourly.get((n, p, k, h)) else "-" for k in ("warm", "miss"))
        print(f"{h:02d}   " + "".join(f"{cell(n, p):>14}" for n, p in cols))

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["quick"]: quick()
    elif a[:1] == ["recursion"]: recursion()
    elif a[:1] == ["log"] and len(a) > 1:
        opt = lambda f: a[a.index(f) + 1] if f in a else None
        log(a[1], opt("--until"), int(opt("--minutes")) if opt("--minutes") else None, "--recursion" in a)
    elif a[:1] == ["cdnlog"] and len(a) > 1:
        opt = lambda f, d: int(a[a.index(f) + 1]) if f in a else d
        cdnlog(a[1], opt("--minutes", 360), opt("--every", 2))
    elif a[:1] == ["report"] and len(a) > 1: report(a[1])
    else: sys.exit(__doc__ or "usage: dnsbench.py quick | recursion | log CSV [--until HH:MM|--minutes N] [--recursion] | cdnlog CSV [--minutes N] [--every M] | report CSV")
