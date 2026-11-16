# `nix build .#installer-pbs` → result: Proxmox's PBS ISO with answer.toml built in. VM 2040 boots
# it (proxmox.sh) and installs without a prompt: the boot menu picks "Automated Installation" after
# 10 s, and the answers come from the ISO itself.
{
  runCommand,
  fetchurl,
  proxmox-auto-install-assistant,
  xorriso,
}:
let
  iso = fetchurl {
    url = "https://enterprise.proxmox.com/iso/proxmox-backup-server_4.2-1.iso";
    hash = "sha256-L7KZ3qw5KSU3EsnD38kjftvnCvg8iEhGdha3caHVRT4="; # Proxmox's SHA256SUMS beside it
  };
in
runCommand "pbs-installer.iso"
  {
    nativeBuildInputs = [
      proxmox-auto-install-assistant
      xorriso
    ];
  }
  ''
    proxmox-auto-install-assistant validate-answer ${./answer.toml}
    # It edits a copy that keeps the source's mode, and the store's is read-only.
    install -m 644 ${iso} source.iso
    proxmox-auto-install-assistant prepare-iso source.iso --fetch-from iso \
      --answer-file ${./answer.toml} --output installer.iso
    mv installer.iso $out
  ''
