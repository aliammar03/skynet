# cloudflared — Skynet-managed Cloudflare Tunnel

The connector that gives Skynet a **sanctioned public path**: an outbound-only tunnel whose single
origin is the apps Caddy (`10.10.100.35`). Publishing an app to the internet = one `ingress` line in
[`config.yml`](config.yml) + one public DNS record. Design: [`docs/design/identity-and-proxy.md`](../../docs/design/identity-and-proxy.md).

## Why locally-managed (credentials file, not a token)

A `--token` run is **remotely-managed**: cloudflared pulls its ingress from the Cloudflare dashboard
and **ignores a local `config.yml`** ([cloudflared #1029](https://github.com/cloudflare/cloudflared/issues/1029)).
That would put our routing table back in a dashboard snowflake. So we run **locally-managed**: the
ingress lives in git (`config.yml`), and the credential is a `credentials.json` file (AccountTag,
TunnelID, TunnelSecret).

## The credential (⚠ Cloudflare checkpoint — Ali)

The credential is a secret, so it never lives plaintext in git. Source of truth is
`credentials.json.sops` (sops+age, this dir); the runtime copy is `0600` on the docker host,
bind-mounted read-only. Steps, done once when the tunnel is created:

1. **Create/attach the tunnel.** The tunnel reuses the id
   `7f4c50f9-cee6-40bb-ad5a-ef6c7f30ca56`; its credential was reconstructed into a `credentials.json`
   from the original `--token-file`. (A fresh tunnel via `cloudflared tunnel create` works
   identically.) The **Tunnel ID** is not secret — it's also the public CNAME target
   `<id>.cfargotunnel.com`.
2. **Put the TunnelID** into [`config.yml`](config.yml) (`tunnel:`).
3. **Encrypt for git/DR.** The `.sops` extension makes sops guess *binary*, and encrypting from a
   path that doesn't match the creation rule fails with "no matching creation rules" — so pass the
   json types **and** `--filename-override` (so it matches the `.sops.yaml` rule):
   ```bash
   sops --encrypt --filename-override compose/cloudflared/credentials.json.sops \
     --input-type json --output-type json credentials.json \
     > compose/cloudflared/credentials.json.sops
   ```
4. **Place the runtime copy** on `vm-docker-dmz`, `0600`, at the bind-mount source (repo→host restore,
   per docs/design/secrets.md — note the explicit json types on decrypt too):
   ```bash
   install -d -m700 /opt/docker/appdata/cloudflared/creds
   sops -d --input-type json --output-type json compose/cloudflared/credentials.json.sops \
     | install -m600 /dev/stdin /opt/docker/appdata/cloudflared/creds/credentials.json
   ```
5. **Confirm egress** (already true): OPNsense rule 800 permits `.33 → 443,7844`, so no firewall
   change. (If `7844` were ever removed, cloudflared falls back to `443`.)

## Deploy

**Live** on `vm-docker-dmz` — the old CT 1033 that previously ran the tunnel is retired. Publishing
an app is one `ingress` line in [`config.yml`](config.yml) + a public DNS record, merged and
reconciled by Arcane. Rollback is `git revert` (Arcane converges back), or `docker compose down` for
the break-glass path.
