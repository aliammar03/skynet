# SKY-024 P3 — core-managed NixOS CTs as DATA. A new container is one entry in one of the maps
# below + a `hosts/lxc-<name>/` flake host + a merged PR → explicitly approved saved plan →
# supervised `scripts/tofu-apply.sh` create. These live core service CTs are intentionally
# unpooled; the core-node operate ACL manages their envelopes. A create has no automatic rollback
# and stays below A4; never auto-destroy a partial failure. Then: envelope (API-only) → Option C key
# inject → `deploy .#lxc-<name>` (inside). tofu owns the envelope, nix owns the inside (SKY-021/024).
# See runbooks/provision-lxc.md.
#
# Each entry:
#   vmid  — MUST satisfy the VMID<->IP law (VLAN + last octet); the entity audit (check-invariants #4)
#           enforces it. Core self-provisions new VMIDs; a NEW network-node CT needs a human (that node
#           is pool-scoped — OPNsense lives there). NEVER add a T3-excluded guest here.
#   vlan/octet — the address is 10.10.<vlan>.<octet>/24, gateway 10.10.<vlan>.1.
#   mac   — REQUIRED and pinned in code, so a reprovision reuses it and never churns the gateway ARP
#           (the SKY-021 lesson). New guest? pick BC:24:11:XX:YY:00 from the vlan/octet hex, or any free
#           unicast MAC. An imported guest keeps its existing MAC (adguard-core below).
locals {
  # Imported state keeps the historical pool_ct resource address. The live guest is unpooled;
  # its pool binding is audited from Proxmox inventory, not managed by this imported declaration.
  imported_core_cts = {
    "adguard-core" = {
      vmid   = 731
      node   = "server-proxmox-core"
      vlan   = 70
      octet  = 31
      mac    = "BC:24:11:69:9E:4D"
      cores  = 1
      memory = 1024
      swap   = 512
      disk   = 8
      tags   = ["adblock", "nixos", "skynet"]
    }
  }

  # Native-created core guests deliberately have no import compatibility ignores. In particular,
  # CPU, initialization, VMID, and the bootstrap template remain declarative for these resources.
  native_core_cts = {
    # Obsidian vault librarian on the DMZ (VLAN 100): coding-agent box (Claude Code / Codex /
    # opencode) that curates Ali's vault, with NO lab authority — it tends the vault, not the lab.
    # VMID 10030 → 10.10.100.30 (canonical VMID↔IP law). MAC from the vlan/octet hex: 100=0x64, 30=0x1E.
    "athena" = {
      vmid   = 10030
      node   = "server-proxmox-core"
      vlan   = 100
      octet  = 30
      mac    = "BC:24:11:64:1E:00"
      cores  = 4
      memory = 8192
      swap   = 2048
      disk   = 64
      tags   = ["obsidian", "nixos", "skynet"]
    }
    # Migration candidates (SKY-021 follow-ups) — each becomes a one-block add here + a flake host:
    #   "technitium-core" = { vmid = 751, node = "server-proxmox-core", vlan = 70, octet = 51, mac = "…", … }
    #   "omada"           = { … }
    #   "authentik"       = { … }   # (837 is T3 today — graduates only if it leaves the excluded set)
  }
}

resource "proxmox_virtual_environment_container" "pool_ct" {
  # Keep this address for the already-imported adguard-core state; see the moved block below.
  for_each = local.imported_core_cts

  node_name    = each.value.node
  vm_id        = each.value.vmid
  unprivileged = true
  started      = true
  tags         = each.value.tags

  cpu {
    architecture = "amd64"
    cores        = each.value.cores
  }

  memory {
    dedicated = each.value.memory
    swap      = each.value.swap
  }

  disk {
    datastore_id = "local-lvm"
    size         = each.value.disk
  }

  network_interface {
    name        = "eth0"
    bridge      = "vmbr0"
    vlan_id     = each.value.vlan
    mac_address = each.value.mac
  }

  features { nesting = true }

  # Match bpg's read-back console (cmode=console) — an absent block reads as "remove console".
  console {
    enabled   = true
    tty_count = 2
    type      = "console"
  }

  operating_system {
    type = "nixos"
    # Unreadable on a live CT (source template gone) → placeholder + ignored below. On a fresh create
    # this is the real bootstrap rootfs; deploy-rs specializes it afterwards.
    template_file_id = "local:vztmpl/nixos-lxc-proof-26.05.tar.xz"
  }

  initialization {
    hostname = "lxc-${each.key}"
    ip_config {
      ipv4 {
        address = "10.10.${each.value.vlan}.${each.value.octet}/24"
        gateway = "10.10.${each.value.vlan}.1"
      }
    }
  }

  lifecycle {
    ignore_changes = [
      operating_system, # template_file_id unreadable on a live CT
      cpu,              # bpg's import doesn't populate cpu for raw-API-created CTs → would drift forever
      initialization,   # pct-set network (ip/hostname) isn't round-tripped by bpg on import
      description,      # not managed declaratively
      pool_id,          # unpooled by design; bpg doesn't read pool membership back on import
      vm_id,            # import populates `id`, not the vm_id attribute → state-only phantom
      timeout_clone,
      timeout_create,
      timeout_delete,
      timeout_start,
      timeout_update,
    ]
  }
}

# Native-created core guests are kept separate from imported guests. The imported adguard resource
# above needs compatibility ignores because bpg cannot round-trip several fields from a raw API
# container. A native create has complete provider state, so broad ignores here would silently turn
# day-two CPU/network/identity changes into no-ops.
resource "proxmox_virtual_environment_container" "core_ct" {
  for_each = local.native_core_cts

  node_name    = each.value.node
  vm_id        = each.value.vmid
  unprivileged = true
  started      = true
  tags         = each.value.tags

  cpu {
    architecture = "amd64"
    cores        = each.value.cores
  }

  memory {
    dedicated = each.value.memory
    swap      = each.value.swap
  }

  disk {
    datastore_id = "local-lvm"
    size         = each.value.disk
  }

  network_interface {
    name        = "eth0"
    bridge      = "vmbr0"
    vlan_id     = each.value.vlan
    mac_address = each.value.mac
  }

  features { nesting = true }

  console {
    enabled   = true
    tty_count = 2
    type      = "console"
  }

  operating_system {
    type             = "nixos"
    template_file_id = "local:vztmpl/nixos-lxc-proof-26.05.tar.xz"
  }

  initialization {
    hostname = "lxc-${each.key}"
    ip_config {
      ipv4 {
        address = "10.10.${each.value.vlan}.${each.value.octet}/24"
        gateway = "10.10.${each.value.vlan}.1"
      }
    }
  }
}

# adguard-core was a standalone resource (P2); it retains the historical `pool_ct` state address.
# `moved` tells tofu to rename it in state — no destroy/recreate of the live CT. Athena was created
# under the original shared map and receives the same state-only move into the native resource.
moved {
  from = proxmox_virtual_environment_container.adguard_core
  to   = proxmox_virtual_environment_container.pool_ct["adguard-core"]
}

moved {
  from = proxmox_virtual_environment_container.pool_ct["athena"]
  to   = proxmox_virtual_environment_container.core_ct["athena"]
}
