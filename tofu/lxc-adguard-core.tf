# SKY-024 P2 — adguard-core (CT 731) declared in tofu, the reference for a NixOS pool CT. This is a
# zero-drift IMPORT of the running guest (the SKY-008 CT-240 recipe): tofu owns the envelope, the flake
# host (hosts/lxc-adguard-core/) + deploy-rs own the inside. The MAC is pinned HERE (network_interface
# reads back from net0 hwaddr, so it round-trips) — a reprovision reuses it and never churns gateway ARP.
# Unpooled by design (reachable via the core /vms-root grant, not pool membership — SKY-021).
resource "proxmox_virtual_environment_container" "adguard_core" {
  node_name    = "server-proxmox-core"
  vm_id        = 731
  unprivileged = true
  started      = true
  tags         = ["adblock", "nixos", "skynet"]

  cpu {
    architecture = "amd64"
    cores        = 1
  }

  memory {
    dedicated = 1024
    swap      = 512
  }

  disk {
    datastore_id = "local-lvm"
    size         = 8
  }

  network_interface {
    name        = "eth0"
    bridge      = "vmbr0"
    vlan_id     = 70
    mac_address = "BC:24:11:69:9E:4D" # pinned — declarative, survives reprovision, no ARP churn
  }

  features { nesting = true }

  # Match bpg's read-back console (cmode=console) — an absent block reads as "remove console", a live
  # mutation on the running guest. Declaring it to the read values keeps the guest untouched.
  console {
    enabled   = true
    tty_count = 2
    type      = "console"
  }

  operating_system {
    type = "nixos"
    # template_file_id is unreadable on a live CT (source template gone) → placeholder + ignored below.
    template_file_id = "local:vztmpl/nixos-lxc-proof-26.05.tar.xz"
  }

  initialization {
    hostname = "lxc-adguard-core"
    ip_config {
      ipv4 {
        address = "10.10.70.31/24"
        gateway = "10.10.70.1"
      }
    }
  }

  lifecycle {
    ignore_changes = [
      operating_system, # template_file_id unreadable on a live CT (see above)
      cpu,              # bpg's import didn't populate cpu for this CT → would drift forever; the guest
      # is 1 core/amd64 (declared above as intent), managed via pct if ever needed, not via tofu here
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
