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
