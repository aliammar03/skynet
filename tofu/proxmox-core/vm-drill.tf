# SKY-025 P15 live drill guest (D7/D8): a running clone of template 9000 that proves the VM paths of
# `skynet tofu`. Throwaway: the executor defers its delete, Ali destroys it by hand, and this file
# and its entity exception are then removed. VMID 10099 → 10.10.100.99 (VMID↔IP law); the MAC is
# pinned from the vlan/octet hex (100=0x64, 99=0x63) so a re-create never churns the gateway ARP.
resource "proxmox_virtual_environment_vm" "vm_drill" {
  node_name = "server-proxmox-core"
  vm_id     = 10099
  name      = "vm-drill"
  pool_id   = "ops-managed"
  tags      = ["drill", "skynet"] # sorted: Proxmox stores tags sorted
  on_boot   = false
  started   = true
  # Leave a no-hotplug change pending instead of rebooting, so the pending-change path is exercised.
  reboot_after_update = false

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
    floating  = 2048 # DRILL D7b: balloon above assigned memory; Proxmox rejects it
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
