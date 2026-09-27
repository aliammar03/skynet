terraform {
  required_version = ">= 1.11.0"

  required_providers {
    # Public records in aliammar.net only; undeclared records (minki, verification TXTs) are left
    # untouched. Account, Access, tunnel config, and zone settings stay T3.
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.24"
    }
  }

  # State path comes from `skynet tofu` at init (-backend-config=path=...); the executor mirrors it
  # to the tofu-state branch. State and saved plans are encrypted with the sops-held passphrase.
  backend "local" {}

  encryption {
    key_provider "pbkdf2" "main" {
      passphrase = var.state_passphrase
    }
    method "aes_gcm" "default" {
      keys = key_provider.pbkdf2.main
    }
    state {
      method = method.aes_gcm.default
    }
    plan {
      method = method.aes_gcm.default
    }
  }
}

variable "state_passphrase" {
  description = "PBKDF2 passphrase for state/plan encryption, from sops at runtime"
  type        = string
  sensitive   = true
}
