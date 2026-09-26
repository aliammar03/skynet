{ ... }:
# Fleet reachability for the agent's outbound SSH. A freshly reprovisioned box has no accumulated
# ~/.ssh/known_hosts and no /etc/hosts aliases (the old box built both up over time), and the lab
# labels aren't in DNS — so declare both here, reproducibly:
#   - networking.hosts   → resolvable labels, so `skynet recon docker-dmz` (bare label → svc-ops@<label>)
#                          resolves without DNS.
#   - programs.ssh.knownHosts → pinned host keys → /etc/ssh/ssh_known_hosts, so `ssh -o BatchMode=yes`
#                          VERIFIES instead of TOFU-prompting (which fails in batch mode).
# Add a host to both as each new SSH target is onboarded. Keys captured with `ssh-keyscan`.
#
# API collectors (proxmox/pbs/dns) use HTTPS tokens, not SSH, and need nothing here.
{
  networking.hosts."10.10.100.15" = [ "docker-dmz" "vm-docker-dmz" ];

  programs.ssh.knownHosts.docker-dmz = {
    hostNames = [ "10.10.100.15" "docker-dmz" "vm-docker-dmz" ];
    publicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPZi8qYDpILV/frA7oq+SJhRBTZe2eB5NNdK+nGSnCgA";
  };

  # PBS host (CT 240). Pinned for grant-root sessions (root@, user-CA cert). Fingerprint
  # SHA256:QFLLU9m9JUNtguZRPTyPBTwkKOmsdwz+uPTJ/4u8jaU, verified via `pct exec 240` on the core node.
  networking.hosts."10.10.20.40" = [ "lxc-proxmox-backup-server" ];

  programs.ssh.knownHosts.lxc-proxmox-backup-server = {
    hostNames = [ "10.10.20.40" "lxc-proxmox-backup-server" ];
    publicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBOXOpjRJUTG3NiZl2DhRKkTgpNqMjvsR75O7WjFPa9Q";
  };
}
