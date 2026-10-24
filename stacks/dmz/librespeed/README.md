# librespeed

- **Purpose:** a LAN speed test: a wifi client measures its link to the lab, not the ISP. Every test
  is kept, with the client's IP, at `/results/stats.php`.
- **URL:** https://speed.aliammar.net (caddy-apps → `librespeed:8080` on `edge`). Inside only: no
  tunnel line, because a test through Cloudflare would measure the internet path.
- **Auth mode:** none (a LAN test). The stats page asks for `PASSWORD`.
- **Data:** `/opt/appdata/librespeed/data` → `/database` (`db.sql`, sqlite: the results; backup
  class: data). Copied from v1 (P3 → Data).
- **Secrets** (`secret.sops.env`): `PASSWORD` (stats page, from v1), `OBFUSCATION_SALT` (result IDs).
  The salt must be `0x` + hex (`0x` and 8 hex digits); anything else makes the image pick a random
  salt at every start, and result links stop resolving after a restart. v1's wasn't, so v1 had that
  problem too.
- **Upstream:** [librespeed/speedtest](https://github.com/librespeed/speedtest) ·
  [Docker settings](https://github.com/librespeed/speedtest/blob/master/doc_docker.md)

**Gotchas**
- Client IPs come from Caddy's `X-Forwarded-For`; without the proxy every test would show the door's
  address.
