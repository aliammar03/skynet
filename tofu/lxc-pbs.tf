# SKY-008 P3 — declarative import of CT 240 (lxc-proxmox-backup-server), the only ops-managed LXC.
# Core node, running, ops-managed pool. This proves the zero-drift IMPORT technique (import is
# read-only — no live mutation) that SKY-018 P11 (import in-pool guests) and SKY-020 (OPNsense
# provider) both reuse. bpg cannot read some fields back from a live container, so those are pinned
# under ignore_changes (see the per-field notes) — the point is a clean `plan`, not re-declaring
# every byte a community-script set.
resource "proxmox_virtual_environment_container" "pbs" {
  node_name    = "server-proxmox-core"
  vm_id        = 240
  unprivileged = true
  started      = true
  pool_id      = "ops-managed"
  tags         = ["backup", "community-script"]

  cpu {
    cores = 4
  }

  memory {
    dedicated = 8192
    swap      = 1024
  }

  disk {
    datastore_id = "local-lvm"
    size         = 16
  }

  # Bind mount of the host PBS-on-Unraid path — backup excluded (mp0 backup=0).
  mount_point {
    volume = "/mnt/pbs-unraid"
    path   = "/mnt/datastore/unraid"
    backup = false
  }

  network_interface {
    name        = "eth0"
    bridge      = "vmbr0"
    mac_address = "BC:24:11:A7:AC:84"
    vlan_id     = 20
  }

  features {
    nesting = true
    keyctl  = true
  }

  # Match bpg's imported console (its defaults) — an absent block reads as "remove console", a real
  # live mutation on the running PBS. Declaring it to the read-back values keeps the guest untouched.
  console {
    enabled   = true
    tty_count = 2
    type      = "tty"
  }

  operating_system {
    type = "debian"
    # template_file_id is REQUIRED by bpg's schema but is absent from a live container's config
    # (the source template is long gone) — so it is unreadable on import and would drift forever.
    # Give it the placeholder bpg accepts and ignore_changes it below.
    template_file_id = "local:vztmpl/unknown"
  }

  initialization {
    hostname = "lxc-proxmox-backup-server"
    ip_config {
      ipv4 {
        address = "10.10.20.40/24"
        gateway = "10.10.20.1"
      }
    }
  }

  lifecycle {
    ignore_changes = [
      operating_system, # template_file_id unreadable on a live CT (see above)
      description,      # community-script HTML boilerplate — not managed declaratively
      initialization,   # pct-set network (ip/hostname) isn't round-tripped by bpg on import
      pool_id,          # bpg does NOT read pool membership back on import → declaring it would
      # force replacement forever. Pool membership is the blast-radius dial, asserted/verified
      # out-of-band (entity layer, SKY-018); tofu here manages the guest, not its pool binding.
      vm_id, # import populates `id` (="240") but not the vm_id attribute → a state-only phantom +
      # Terraform-level operation timeouts (how long tofu waits) — schema defaults, never sent to
      # PVE, absent from imported state → phantom + with no live meaning. (timeout_start is
      # deprecated in bpg but still emitted with a default, so it must stay ignored → the one
      # expected "Deprecated attribute" warning on plan is benign.)
      timeout_clone,
      timeout_create,
      timeout_delete,
      timeout_start,
      timeout_update,
    ]
  }
}
