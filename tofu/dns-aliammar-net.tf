# aliammar.net vanity A records under tofu (T2, Technitium zones-only).
# aliammar.net is a Forwarder zone that also holds authoritative A overrides for the lab's admin
# vanity names. It is UNSIGNED (no DNSKEY), so kevynb/technitium v0.4.0 reads it fine — unlike the
# DNSSEC-signed resolver zone tdns.home.aliammar.net, deferred until a release carries b2f6b89c.
#
# The named admin hosts front onto the Management Caddy (10.10.60.35). The record-scoped provider
# manages ONLY these records and leaves the zone's SOA / FWD / DNSSEC-none machinery untouched.
# Every app vhost has its own explicit record below; there is no catch-all.
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
# App service records — the published apps served by the apps Caddy (10.10.100.35). Every app vhost
# gets an EXPLICIT A record → the apps Caddy — these replaced the retired `*.aliammar.net` wildcard
# (each resolves to the same IP the wildcard used to hand out).
#
# SINGLE SOURCE OF TRUTH = the apps Caddyfile (compose/caddy-apps/Caddyfile). The record set is
# DERIVED from it, never hand-listed: every site-address line ("<host>.aliammar.net {") becomes a
# record. Add a vhost there → its A record appears on the next `tofu plan`. Nothing to keep in sync.
# ---------------------------------------------------------------------------------------------------
locals {
  apps_caddy_ip  = "10.10.100.35" # the caddy-apps front door (compose/caddy-apps)
  apps_caddyfile = file("${path.module}/../compose/caddy-apps/Caddyfile")
  # Match only site-address lines: a bare "<host>.aliammar.net" at column 0 (reverse_proxy/forward_auth
  # lines are indented; the global-options block starts with "{"), so no false positives.
  apps_service_hosts = toset(regexall("(?m)^[a-z0-9-]+\\.aliammar\\.net", local.apps_caddyfile))
}

# Guard the derivation — a Caddyfile that parses to zero hosts would otherwise propose deleting every
# app record. Refuse that (this is the layer's "checker"; the derivation above is the writer).
check "apps_ingress_parsed" {
  assert {
    condition     = length(local.apps_service_hosts) > 0
    error_message = "No app vhosts parsed from ${abspath("${path.module}/../compose/caddy-apps/Caddyfile")} — refusing to wipe app DNS records."
  }
}

resource "technitium_record" "apps_service" {
  for_each = local.apps_service_hosts

  domain     = each.key # already the FQDN (e.g. karakeep.aliammar.net)
  type       = "A"
  ttl        = 300
  ip_address = local.apps_caddy_ip
}
