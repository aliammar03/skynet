# The lab

Ali's homelab: two Proxmox nodes, the guests on them, and what git configures. Times are PKT
(Asia/Karachi). The guests below were read from both nodes on 2026-11-16; check before relying on a
number.

## Nodes

| Node | Address | CPUs, memory | Storage |
|---|---|---|---|
| server-proxmox-core | 10.10.50.11 | 12, 31 GiB | `local` (ISOs), `local-lvm` (disks), `pbs` (VM 2040) |
| server-proxmox-network | 10.10.50.10 | 8, 14.5 GiB | the same |

PVE 9.2 on Debian 13. The nodes aren't clustered. What the lab adds to them is `pve/`; their
config otherwise is Ali's.

## VLANs

`10.10.<vlan>.0/24`, gateway `.1`: 10 Trusted · 20 Servers · 30 IoT · 40 Guest · 50 Mgmt (vmbr0's
native VLAN on both nodes) · 60 Admin access · 70 Net services · 80 Identity · 90 Ops · 100 DMZ ·
300 ISP L2 passthrough (not routed).

## Guests

| Guest | Node | Address | Size | Configured by |
|---|---|---|---|---|
| ops, VM 9091 | core | 10.10.90.91 | 4 vCPU, 8 GB (6 from its next restart) | `hosts/ops/` |
| docker-dmz, VM 10010 | core | 10.10.100.10; caddy-apps .35, cloudflared .33 | 6 vCPU, 12 GB | `hosts/docker-dmz/`, `stacks/dmz/` |
| technitium-core, VM 7051 | core | 10.10.70.51 | 2 vCPU, 1 GB | `hosts/technitium-core/`, `dns/` |
| PBS, VM 2040 | core | 10.10.20.40, and 10.10.50.24 for the nodes | 2 vCPU, 4 GB | `pbs/` |
| Unraid, VM 2020 | core | 10.10.20.20 | 4 vCPU, 4 GB | Ali; `unraid/` describes what the lab adds |
| Home Assistant OS, VM 3050 | core | 10.10.30.50 | 2 vCPU, 2 GB | Ali |
| athena, CT 10030 | core | 10.10.100.30 | 2 vCPU, 2 GB | its own repo |
| OPNsense, VM 5001 | network | 10.10.50.1 | 4 vCPU, 4 GB | Ali (below); its config to `skynet-opnsense` through os-git-backup |
| docker-admin, VM 5040 | network | 10.10.50.40; caddy-admin 10.10.60.60 | 2 vCPU, 4 GB | `hosts/docker-admin/`, `stacks/admin/` |
| technitium-network, VM 7050 | network | 10.10.70.50 | 2 vCPU, 1 GB | `hosts/technitium-network/`, `dns/` |
| Omada, CT 525 | network | 10.10.50.25 | 2 vCPU, 3 GB | Ali |

Apps with an address of their own, on docker-dmz's macvlan, because a firewall rule names them:
aiostreams .65, SABnzbd .66, sillytavern .69, marinara .85 (`stacks/README.md` → Networks).

## Change flow

1. The agent pushes a branch and opens a PR.
2. CI runs, on GitHub's free runners.
3. Ali merges.
4. comin (hosts) and doco-cd (stacks) pull `main` within about 60 s.
5. Failures post to Discord `#alerts`.

Nothing outside the lab pushes into it (ADR-0003).

## Domain

`aliammar.net`: public DNS at Cloudflare, which holds the tunnel's `*` CNAME; inside the lab, the
zone in `dns/aliammar.net.zone` on both Technitium servers (split horizon). Each name points at its
door: admin names at 10.10.60.60, app names at 10.10.100.35.

## What only Ali applies

Git doesn't hold these; Ali applies them, and the PR that needs a change gives the exact steps.

### OPNsense

The rules and aliases the lab relies on, as read through `skynet-read` on 2026-11-16. A new host
gets a `HOST_` alias, nested (not its IP) in the roles its job needs (`runbooks/new-vm.md`, step
2).

- **Roles:** `ROLE_DNS_RESOLVERS` (both Technitium servers), `ROLE_NIX_CACHE_CLIENTS` (every NixOS
  host but ops), `ROLE_METRICS_TARGETS` and `ROLE_LOG_SHIPPERS` (ops, docker-dmz, both DNS servers,
  PBS, Unraid), `ROLE_USENET_CLIENTS` (.65, .66), `ROLE_DMZ_AI_CLIENTS` (.69, .85). Ports:
  `PORT_METRICS` (4243, 9100, 9120, 9338, 9633), `PORT_LOG_INGEST` (9429, 5515). `NET_WEB_EGRESS`
  holds VLANs 20, 50, 60, 70, 80, 90 and 100; `NET_TAILNET` is 100.64.0.0/10.
- **DNS:** 100 every Skynet VLAN → the resolvers :53; 110 the resolvers → any :53 (forwarding); 135
  docker-admin → 1.1.1.1 :53 (Gatus's `public` row); 140 blocks every other DNS and DoT. DHCP on
  every VLAN, and OPNsense itself, list both .50 and .51.
- **The doors:** 200 app clients → caddy-apps :80/:443; 210 ops and the admin clients →
  caddy-admin :443; 230 caddy-admin → the admin targets on their UI ports; 235 docker-admin → the
  same (Gatus, the exporters); 245 the resolvers → caddy-admin (Technitium's login through admin
  Authelia); 430 caddy-apps → Home Assistant; 830 the doors and resolvers → any :53 (ACME). System
  → Settings → Administration → Alternate Hostnames lists `opnsense.aliammar.net` and
  `auth.aliammar.net`.
- **Observability:** 236 docker-admin → `ROLE_METRICS_TARGETS` : `PORT_METRICS`; 237
  `ROLE_LOG_SHIPPERS` → docker-admin : `PORT_LOG_INGEST`, for docker-dmz the DMZ's one opening into
  the management VLAN, write-only. Remote logging: 10.10.50.40, TCP 5514, RFC 5424. Hosts on VLAN
  50 need no rule.
- **Storage and backups:** 280 docker-admin → Unraid :2049 (PBS's datastore, read-only); 300
  docker-dmz → Unraid SMB/NFS (`Storage`); 320 the nodes → PBS :8007.
- **ops:** 260 → PBS and the nodes :8006–8007; 265 the Nix cache's clients → ops :5000; 390 ops →
  every Skynet VLAN on any port.
- **Egress:** 800 cloudflared → Cloudflare :443, :7844; 810 `NET_WEB_EGRESS` → any :80/:443; 820
  `ROLE_USENET_CLIENTS` → :119/:563; 340 the two AI apps → ComfyUI on the workstation :8188; 700
  blocks Skynet → the other private ranges; 950 denies the rest.
- **The tailnet:** below.
- **Users:** `skynet-read` (ops's key: diagnostics, aliases, rules, config writes denied;
  `docs/credentials.md`) and the exporter's API user (`stacks/admin/exporters`).

### Cloudflare

- The zone `aliammar.net`: its NS records and one proxied `*` CNAME →
  `<tunnel id>.cfargotunnel.com` (ADR-0010). A public name is a line in
  `stacks/dmz/cloudflared/config.yml`; any other name gets 404.
- The tunnel `skynet`, locally managed: its routes are that file (`stacks/dmz/cloudflared`).
- Two API tokens, Zone → DNS → Edit on `aliammar.net` only, one for each door's DNS-01
  (`docs/credentials.md`).

### Tailscale

- Ali's account. OPNsense is the subnet router (`os-tailscale`, key expiry off), advertising
  10.10.50.0/24, 10.10.60.60/32, 10.10.70.50/32, 10.10.70.51/32 and 10.10.100.35/32, each route
  approved in the admin console.
- DNS: nameservers 10.10.70.50 and .51, restricted to `aliammar.net` (split DNS); MagicDNS on,
  "override local DNS" off.
- On OPNsense, interface `TAILSCALE` (`tailscale0`), rules from `NET_TAILNET`: 270 → caddy-admin
  :443; 271 → the resolvers :53; 272 → the management VLAN on the break-glass ports; 273 →
  caddy-apps :80/:443.
- ops is a node, `tag:ops`, in userspace (`hosts/ops/README.md`); what `tag:ops` may reach is the
  tailnet policy's.
- A device: install Tailscale and sign in (Linux: `tailscale up --accept-routes`).
