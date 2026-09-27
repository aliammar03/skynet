# Core node (server-proxmox-core, 10.10.50.11). API-native cloud-init only: the SSH transport is
# deliberately unconfigured, so snippet uploads (proxmox_virtual_environment_file) cannot be used.
provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = var.proxmox_api_token
  insecure  = false
}

variable "proxmox_endpoint" {
  description = "Core-node Proxmox VE API URL (https://<host>:8006)"
  type        = string
}

variable "proxmox_api_token" {
  description = "svc-ops@pve!operate on core: root-ACL broadened, bright lines enforced"
  type        = string
  sensitive   = true
}
