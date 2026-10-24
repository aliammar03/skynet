# cloudflared

- **Purpose:** the public path. An outbound-only connector for Cloudflare Tunnel `skynet`
  (`f550cc58-fc42-4300-a774-1619888fe700`), so internet visitors reach caddy-apps with nothing open
  inbound.
- **Routes:** `config.yml`, one line per public name → `https://caddy-apps` (SNI = the name), then
  404. The tunnel is locally managed, so these lines are its whole routing table. Cloudflare holds one
  proxied `*` CNAME → `<id>.cfargotunnel.com` (D10); a name without a line here gets 404.
- **Where:** macvlan `dmz` only, 10.10.100.33 = OPNsense `HOST_CLOUDFLARED` (rule 800: TCP/UDP 443 and
  7844 to Cloudflare; QUIC first, HTTP/2 if UDP fails). It reaches caddy-apps (.35) by name on the
  macvlan, and no app directly.
- **Auth mode:** none of its own. Each public app keeps its own login, or goes through the apps'
  Authelia (`login`).
- **Data:** none.
- **Secrets** (`secret.sops.env`): `TUNNEL_TOKEN` (the tunnel's credentials as one token, from
  `cloudflared tunnel token skynet`).
- **Upstream:** [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) ·
  [configuration file](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/configure-tunnels/local-management/configuration-file/)

**Gotchas**
- Don't migrate the tunnel to dashboard management in Cloudflare: a remotely managed tunnel takes
  its routes from the dashboard and ignores `config.yml`.
- The token, not a credentials file: doco-cd writes decrypted files readable by root only, and the
  container runs as the image's own user (65532), read-only, with no capabilities.
- `cloudflared tunnel ready` needs `--metrics`, the same address as the run command
  (127.0.0.1:2000). Without it the check always fails, and doco-cd would keep restarting the tunnel.
  It reports healthy only while cloudflared holds a connection to Cloudflare.
- Check a route change before its PR:
  `nix run nixpkgs#cloudflared -- tunnel --config stacks/dmz/cloudflared/config.yml ingress validate`
  and `… ingress rule https://<name>.aliammar.net`.
- Gatus's `public` row tests the whole path (Cloudflare → tunnel → caddy-apps → the apps' Authelia).
