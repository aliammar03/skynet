# T2 scoped Zone:DNS:Edit token for aliammar.net records only. The ops VM has no IPv6 egress; the
# Go client's happy-eyeballs picks IPv4.
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

variable "cloudflare_api_token" {
  description = "Scoped Cloudflare Zone:DNS:Edit token for aliammar.net"
  type        = string
  sensitive   = true
}

variable "cloudflare_zone_id" {
  description = "aliammar.net Cloudflare zone id (a public identifier)"
  type        = string
  default     = "56c76f970190ade4d62262c825272d20"
}

variable "cloudflare_tunnel_id" {
  description = "Public cloudflared tunnel UUID; CNAME target is <id>.cfargotunnel.com"
  type        = string
}
