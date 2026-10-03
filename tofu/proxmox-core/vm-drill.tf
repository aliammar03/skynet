# SKY-025 P15 live write-back drill: two running clones of template 9000. One PR moves vm-drill's
# cores (it lands; bpg reboots it) while vm-drill2 gets a value Proxmox rejects, so the failed apply
# must write vm-drill's saved config back and reboot it. Throwaway: their deletes are deferred, they
# are destroyed by an Ali-approved API call, and this file and their entity exceptions are removed.
# VMID↔IP law; MACs pinned from the vlan/octet hex (100=0x64; 99=0x63, 98=0x62).
# Re-run after F3 (#303): the restore restarts a pending guest by a forced shutdown + start.
resource "proxmox_virtual_environment_vm" "vm_drill" {
  node_name = "server-proxmox-core"
  vm_id     = 10099
  name      = "vm-drill"
  pool_id   = "ops-managed"
  tags      = ["drill", "skynet"] # sorted: Proxmox stores tags sorted
  on_boot   = false
  started   = true

  clone {
    vm_id = 9000
    full  = true
  }

  cpu {
    cores = 2 # DRILL write-back: lands (bpg reboots the VM to apply it)
    type  = "host"
  }

  memory {
    dedicated = 1024
  }

  agent {
    enabled = false # the operate role has no VM.GuestAgent.Audit
  }

  operating_system {
    type = "l26"
  }

  serial_device {}

  scsi_hardware = "virtio-scsi-single"

  disk {
    interface    = "scsi0"
    datastore_id = "local-lvm"
    size         = 10
    discard      = "on"
    ssd          = true
  }

  network_device {
    bridge      = "vmbr0"
    model       = "virtio"
    vlan_id     = 100
    mac_address = "BC:24:11:64:63:00"
  }

  boot_order = ["scsi0"]

  initialization {
    datastore_id = "local-lvm"
    ip_config {
      ipv4 {
        address = "10.10.100.99/24"
        gateway = "10.10.100.1"
      }
    }
  }
}

resource "proxmox_virtual_environment_vm" "vm_drill2" {
  node_name = "server-proxmox-core"
  vm_id     = 10098
  name      = "vm-drill2"
  pool_id   = "ops-managed"
  tags      = ["drill", "skynet"] # sorted: Proxmox stores tags sorted
  on_boot   = false
  started   = true

  clone {
    vm_id = 9000
    full  = true
  }

  cpu {
    cores = 1
    type  = "host"
  }

  memory {
    dedicated = 1024
    floating  = 2048 # DRILL write-back: Proxmox rejects it, failing the apply
  }

  agent {
    enabled = false # the operate role has no VM.GuestAgent.Audit
  }

  operating_system {
    type = "l26"
  }

  serial_device {}

  scsi_hardware = "virtio-scsi-single"

  disk {
    interface    = "scsi0"
    datastore_id = "local-lvm"
    size         = 10
    discard      = "on"
    ssd          = true
  }

  network_device {
    bridge      = "vmbr0"
    model       = "virtio"
    vlan_id     = 100
    mac_address = "BC:24:11:64:62:00"
  }

  boot_order = ["scsi0"]

  initialization {
    datastore_id = "local-lvm"
    ip_config {
      ipv4 {
        address = "10.10.100.98/24"
        gateway = "10.10.100.1"
      }
    }
  }
}
