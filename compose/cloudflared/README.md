# cloudflared — Skynet-managed Cloudflare Tunnel

The connector that gives Skynet a **sanctioned public path**: an outbound-only tunnel whose single
origin is the apps Caddy (`10.10.100.35`). Publishing an app to the internet = one `ingress` line in
[`config.yml`](config.yml) + one public DNS record. Design: [`docs/design/identity-and-proxy.md`](../../docs/design/identity-and-proxy.md).
Directive: [`planning/projects/SKY-014-*`](../../planning/projects/).

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

1. **Create/attach the tunnel** in Cloudflare (or `cloudflared tunnel create skynet`). This yields a
   `credentials.json` and a **Tunnel ID** (a UUID).
2. **Put the TunnelID** into [`config.yml`](config.yml) (`tunnel:` — replaces `TODO-TUNNEL-ID`). The
   UUID is not secret (it's also the public CNAME target `<id>.cfargotunnel.com`).
3. **Encrypt for git/DR** (the `.sops.yaml` rule already covers this path):
   ```bash
   sops -e --input-type json --output-type json credentials.json \
     > compose/cloudflared/credentials.json.sops
   ```
4. **Place the runtime copy** on `vm-docker-dmz`, `0600`, at the bind-mount source:
   ```bash
   # from the sops copy (the repo→host restore direction, per docs/design/secrets.md):
   install -d -m700 /opt/docker/appdata/cloudflared/creds
   sops -d compose/cloudflared/credentials.json.sops \
     | install -m600 /dev/stdin /opt/docker/appdata/cloudflared/creds/credentials.json
   ```
5. **Confirm egress** (already true): OPNsense rule 800 permits `.33 → 443,7844`, so no firewall
   change. (If `7844` were ever removed, cloudflared falls back to `443`.)

## Deploy (Phase 2 — not yet)

`.33` still belongs to CT 1033, so this service is **built and validated, not deployed**, in Phase 1.
Cutover (`pct stop 1033` → `scripts/gitops-deploy.sh cloudflared`), publishing the pilot, and
retiring CT 1033 are Phase 2. Rollback for the cutover is `docker compose down` + `pct start 1033`.
