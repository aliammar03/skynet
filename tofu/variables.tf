variable "proxmox_endpoint" {
  description = "Proxmox VE API URL (e.g. https://10.10.50.11:8006)"
  type        = string
}

variable "proxmox_api_token" {
  description = "svc-tofu@pve!operate=<secret> — pool-scoped, privilege-separated"
  type        = string
  sensitive   = true
}

variable "state_passphrase" {
  description = "PBKDF2 passphrase for state/plan encryption — sourced from sops at runtime"
  type        = string
  sensitive   = true
}

# --- network node (server-proxmox-network, 10.10.50.10) — standalone, separate token ---
variable "proxmox_endpoint_network" {
  description = "Network-node Proxmox VE API URL (https://10.10.50.10:8006)"
  type        = string
}

variable "proxmox_api_token_network" {
  description = "svc-tofu@pve!operate=<secret> on the network node — pool-scoped, privilege-separated"
  type        = string
  sensitive   = true
}

# --- Technitium DNS (T2, zones-only) — sourced from technitium.env via tofu-env.sh ---
variable "technitium_url" {
  description = "Technitium base URL WITHOUT /api (https://10.10.70.50:53443) — the provider prepends /api itself"
  type        = string
}

variable "technitium_api_token" {
  description = "Zones-scoped Technitium API token — Zones view/modify only (never server settings/T3)"
  type        = string
  sensitive   = true
}
