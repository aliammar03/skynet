---
summary: "The current two-door proxy, split-DNS, Authentik boundary, and Cloudflare Tunnel public path."
---

# Spoke · Identity & proxy

> The current routing and identity boundary for publishing services. Governed by
> [`../system-design.md`](../system-design.md); publishing procedures live in `runbooks/`.

## Two doors

| Door | Address | Tier | Scope |
|---|---|---|---|
| Management Caddy | `10.10.60.35`, VLAN 60 | T3 | Sensitive infrastructure; admin-workstation-only |
| Apps Caddy | `10.10.100.35`, VLAN 100 | T2 | Everyday services; app-client VLANs |

Skynet operates the apps Caddy GitOps stack, not Management Caddy. Routes are explicit Caddyfile
entries, deployed through the normal reviewed PR → Arcane reconciliation loop. Caddy routes by
`IP:port`, has no Docker socket, and is the only path from app clients to declared origins.

## DNS and TLS

`aliammar.net` is split-horizon:

| Client | Resolution | Effect |
|---|---|---|
| Internal | Technitium A record → apps Caddy | The normal, non-Cloudflare path |
| External | Explicit Cloudflare CNAME → tunnel | Only deliberately public hostnames resolve |

Apps Caddy uses Let's Encrypt DNS-01 through Cloudflare's public authoritative DNS. Its scoped
Cloudflare DNS token writes only `aliammar.net` challenges; it reaches the Cloudflare API over 443,
not authoritative DNS on port 53. Internal A records are derived from the apps Caddyfile through
the reviewed saved-plan DNS path.

## Internal publish paths

- **Own-auth service:** a plain `reverse_proxy` site to its declared origin.
- **No-auth service:** the same site with `forward_auth` to the existing Authentik outpost, then the
  origin proxy.

The scoped Authentik token may CRUD applications and providers and bind the existing outpost. It
cannot touch flows, policies, users, groups, system settings, outpost tokens, or signing keys.
Network rules restrict clients to Apps Caddy, and Caddy to Authentik/origins; their exact aliases and
rules are in [network](network.md). The publish runbook owns the concrete route and provider steps.

## Public path

`compose/cloudflared/` is a T2 GitOps connector at `10.10.100.33`. It has no inbound firewall rule:
it dials Cloudflare outbound and forwards every permitted public request to Apps Caddy at
`https://10.10.100.35`, preserving TLS to the origin.

A hostname is public only when both are present in reviewed configuration:

1. An explicit locally managed tunnel `ingress` entry; the catch-all is `404`.
2. Its Cloudflare CNAME, derived from the ingress and applied through the scoped DNS path.

The human merge of the ingress change is the publish gate. Cloudflare DNS record writes are T2, but
account, Access policy, tunnel configuration, and zone settings are T3. The saved-plan executor
refuses deletion; removing a public record uses the explicit hard-checkpoint `cf-dns-route.sh --delete`
path with `dns-revert.sh` evidence. Internal clients always resolve directly to Apps Caddy and never
transit Cloudflare.

## Residual boundary

`svc-ops` has Docker-group access on the DMZ host, which is effectively host-root. Therefore the
sanctioned route/auth change is guarded by the human merge gate, network segmentation confines
origins to internal app clients, and Arcane reconciliation restores tracked configuration. The
nightly collector reads committed routes; it does not compare live Caddy configuration with git.
Diagnose suspected live-route drift through Arcane; no route is automatically reverted from an
observation alone.
