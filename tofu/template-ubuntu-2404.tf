# SKY-008 — permanent Ubuntu 24.04 base cloud-init template (T2, svc-ops!operate). Clone source for guests.
# Base image is placed in local's `import` store out-of-band (URL download needs Sys.Modify/T3); this
# builds the template from the present volume. Trust/onboarding layers go on clones via cloud-init.
resource "proxmox_virtual_environment_vm" "ubuntu_2404_base" {
  node_name   = "server-proxmox-core"
  vm_id       = 9000
  name        = "ubuntu-2404-base"
  pool_id     = "ops-managed" # so the token can VM.Clone it (pool ACL) and see it (VM.Audit)
  description = "SKY-008 base cloud-init template — clone source. Managed by OpenTofu."
  tags        = ["template", "skynet", "sky-008"]
  template    = true
  started     = false

  cpu {
    cores = 2
    type  = "host"
  }

  memory {
    dedicated = 2048
  }

  agent {
    enabled = false # role has no VM.GuestAgent.Audit; enabling only stalls bpg on a 403
  }

  operating_system {
    type = "l26"
  }

  serial_device {} # ubuntu cloud image expects a serial console

  scsi_hardware = "virtio-scsi-single"

  disk {
    interface    = "scsi0"
    datastore_id = "local-lvm"
    # a present import-typed volume (image placed out-of-band, see header) — NOT a URL download.
    # Must carry a disk-image extension (.qcow2/.raw/.vmdk): Proxmox classifies a bare .img as ISO,
    # which won't list under the `import` content type. The ubuntu cloudimg is qcow2 → .qcow2.
    import_from = "local:import/noble-server-cloudimg-amd64.qcow2"
    size        = 10
    discard     = "on"
    ssd         = true
  }

  network_device {
    bridge  = "vmbr0"
    model   = "virtio"
    vlan_id = 100 # dmz — clones inherit; override per-guest if needed
  }

  boot_order = ["scsi0"]
}
