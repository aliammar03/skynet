terraform {
  required_version = ">= 1.11.0"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.111.0"
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
