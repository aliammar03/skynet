# T2 zones-only token. `url` omits /api: the client prepends it. The self-signed cert is pinned,
# not skipped: `skynet tofu` points SSL_CERT_FILE at technitium.crt for this stack only.
provider "technitium" {
  url   = var.technitium_url
  token = var.technitium_api_token
}

variable "technitium_url" {
  description = "Technitium base URL without /api (https://<host>:53443)"
  type        = string
}

variable "technitium_api_token" {
  description = "Zones-scoped Technitium API token (never server settings, which are T3)"
  type        = string
  sensitive   = true
}
