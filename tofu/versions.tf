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
    # SKY-014 public path → tofu. PUBLIC DNS records in aliammar.net only (the per-host tunnel CNAMEs),
    # via the scoped Zone:DNS:Edit token. Same T2 scope as scripts/cf-dns-route.sh — account / Access /
    # tunnel config / zone settings stay T3. Per-record: undeclared records (minki, verifications) are
    # left untouched.
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.24"
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
