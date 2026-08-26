resource "proxmox_virtual_environment_vm" "docker_dmz" {
  node_name = "server-proxmox-core"
  vm_id     = 10015
  name      = "vm-docker-dmz"
  tags      = ["community-script"]
  on_boot   = true
  started   = true

  bios    = "ovmf"
  machine = "q35"

  cpu {
    cores   = 8
    sockets = 1
    type    = "host"
  }

  memory {
    dedicated = 16384
  }

  agent {
    enabled = true
  }

  operating_system {
    type = "l26"
  }

  serial_device {}

  tablet_device = false

  scsi_hardware = "virtio-scsi-single"

  efi_disk {
    datastore_id = "local-lvm"
    type         = "4m"
  }

  disk {
    interface    = "scsi0"
    datastore_id = "local-lvm"
    size         = 256
    discard      = "on"
    iothread     = true
    ssd          = true
  }

  network_device {
    bridge      = "vmbr0"
    model       = "virtio"
    vlan_id     = 100
    mac_address = "BC:24:11:AD:08:8C"
  }

  boot_order = ["scsi0"]

  initialization {
    datastore_id = "local-lvm"
    user_account {
      username = "root"
    }
    ip_config {
      ipv4 {
        address = "10.10.100.15/24"
        gateway = "10.10.100.1"
      }
    }
  }

  lifecycle {
    ignore_changes = [
      initialization[0].user_account[0].password,
      initialization[0].user_account[0].keys,
      description,
    ]
  }
}
