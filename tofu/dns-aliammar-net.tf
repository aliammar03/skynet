# SKY-008 P3 — the aliammar.net vanity A records under tofu (T2, Technitium zones-only).
# aliammar.net is a Forwarder zone that also holds authoritative A overrides for the lab's admin
# vanity names. It is UNSIGNED (no DNSKEY), so kevynb/technitium v0.4.0 reads it fine — unlike the
# DNSSEC-signed resolver zone tdns.home.aliammar.net, deferred until a release carries b2f6b89c.
#
# The named admin hosts front onto the Management Caddy (10.10.60.35). The record-scoped provider
# manages ONLY these records and leaves the zone's SOA / FWD / DNSSEC-none machinery untouched.
# NB: the former `*.aliammar.net` wildcard (→ 10.10.100.35) is deliberately NOT managed here — it is
# being retired (Ali, 2026-09-02); its live deletion is pending record-delete on the token.
locals {
  aliammar_net_a = {
    # name (relative to zone) => { ip, ttl }
    "arcane"             = { ip = "10.10.60.35", ttl = 300 }
    "caddy"              = { ip = "10.10.60.35", ttl = 300 }
    "omada"              = { ip = "10.10.60.35", ttl = 300 }
    "opnsense"           = { ip = "10.10.60.35", ttl = 300 }
    "pbs"                = { ip = "10.10.60.35", ttl = 300 }
    "proxmox-core"       = { ip = "10.10.60.35", ttl = 300 }
    "proxmox-network"    = { ip = "10.10.60.35", ttl = 300 }
    "unraid"             = { ip = "10.10.60.35", ttl = 300 }
    "technitium-core"    = { ip = "10.10.60.35", ttl = 3600 }
    "technitium-network" = { ip = "10.10.60.35", ttl = 3600 }
  }
}

resource "technitium_record" "aliammar_net" {
  for_each = local.aliammar_net_a

  # zone is intentionally omitted — it is optional and inferred from the FQDN domain. Import doesn't
  # populate it, so declaring it reads as a phantom `~ + zone` diff on every record (state null).
  domain     = "${each.key}.aliammar.net"
  type       = "A"
  ttl        = each.value.ttl
  ip_address = each.value.ip
}

# ---------------------------------------------------------------------------------------------------
# App service records — the published apps served by the apps Caddy (10.10.100.35). These give every
# app vhost an EXPLICIT A record so the `*.aliammar.net` wildcard can be retired: each resolves to the
# same IP the wildcard hands out today, so adding them is a no-op on resolution.
# SOURCE OF TRUTH is the apps Caddyfile (compose/caddy-apps/Caddyfile) — keep this list in lockstep
# with the vhosts there (add a vhost → add its name here; a name missing here falls through to public
# DNS once the wildcard is gone).
# ---------------------------------------------------------------------------------------------------
locals {
  apps_caddy_ip = "10.10.100.35"
  apps_service_names = toset([
    "karakeep",
    "aiostreams",
    "aiometadata",
    "marinara",
    "obsidian",
    "calibre",
    "sillytavern",
    "speed",
    "auth",
  ])
}

resource "technitium_record" "apps_service" {
  for_each = local.apps_service_names

  domain     = "${each.key}.aliammar.net"
  type       = "A"
  ttl        = 300
  ip_address = local.apps_caddy_ip
}
