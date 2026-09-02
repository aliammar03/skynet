# SKY-014 public path → tofu. The per-host tunnel CNAMEs in the PUBLIC aliammar.net zone (Cloudflare),
# replacing the imperative scripts/cf-dns-route.sh upsert. T2, scoped Zone:DNS:Edit token.
#
# SINGLE SOURCE OF TRUTH = the cloudflared ingress (compose/cloudflared/config.yml). Every `hostname:`
# there is a published host, so its public CNAME → the tunnel is DERIVED, never hand-listed: add an
# ingress line → its CNAME appears on the next `tofu apply`. Same shape as the apps Caddyfile → DNS
# derivation. (Non-tunnel records — the `minki` ChatGPT custom domain, Google/OpenAI verification TXTs
# — are external/manual and deliberately NOT managed here; the provider only touches declared records.)
locals {
  cloudflared_config = file("${path.module}/../compose/cloudflared/config.yml")
  # regexall with a capture group returns [["host"], ...] → take the first group of each match.
  public_hosts = toset([
    for m in regexall("(?m)^\\s*-\\s*hostname:\\s*(\\S+)", local.cloudflared_config) : m[0]
  ])
}

# Guard the derivation — a config that parses to zero hosts would otherwise propose deleting every
# public CNAME. Refuse that (the writer is the resource below; this is its checker).
check "cloudflared_ingress_parsed" {
  assert {
    condition     = length(local.public_hosts) > 0
    error_message = "No hostnames parsed from compose/cloudflared/config.yml — refusing to wipe public CNAMEs."
  }
}

resource "cloudflare_dns_record" "tunnel" {
  for_each = local.public_hosts

  zone_id = var.cloudflare_zone_id
  name    = each.key # FQDN, e.g. karakeep.aliammar.net
  type    = "CNAME"
  content = "${var.cloudflare_tunnel_id}.cfargotunnel.com"
  ttl     = 1 # 1 = automatic — required for proxied records
  proxied = true
}
