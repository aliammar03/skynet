provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = var.proxmox_api_token
  insecure  = false

  # API-native cloud-init only — the SSH transport is deliberately unconfigured.
  # proxmox_virtual_environment_file (snippet uploads) CANNOT be used; that is
  # the point: the SSH-snippet path breaks the trust model (standing node SSH).
}

# Network node — standalone (not clustered), so its own endpoint + token. Resources on
# server-proxmox-network set `provider = proxmox.network`.
provider "proxmox" {
  alias     = "network"
  endpoint  = var.proxmox_endpoint_network
  api_token = var.proxmox_api_token_network
  insecure  = false
}

# Technitium DNS (SKY-008 P3) — T2, zones-only scoped token. `url` must OMIT the /api suffix: the
# client prepends /api itself (a `.../api` url yields `.../api/api/...` → 404 → EOF). Self-signed
# cert is PINNED, not skipped: tofu-env.sh appends technitium.crt to the SSL_CERT_FILE bundle, so
# the provider's Go client verifies chain + SAN (the same cert collect-dns.sh trusts on this IP).
provider "technitium" {
  url   = var.technitium_url
  token = var.technitium_api_token
}
