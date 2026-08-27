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
