terraform {
  required_version = ">= 1.7.0"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.111.0"
    }
    # SKY-008 P3 — DNS records in T2 zones only. Record-scoped provider: manages only the records it
    # declares, leaves undeclared ones untouched (the zones-only fit). Pinned + lock-file'd like bpg.
    # NB: v0.4.0 can't read a DNSSEC-SIGNED zone (numeric DNSKEY.protocol; fix on main @ b2f6b89c,
    # unreleased) → only the UNSIGNED aliammar.net zone is managed here; the signed resolver zone
    # tdns.home.aliammar.net waits for a release. See [[SKY-008-progress]].
    technitium = {
      source  = "kevynb/technitium"
      version = "~> 0.4.0"
    }
  }

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
