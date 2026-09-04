{ modulesPath, lib, pkgs, ... }:
# Container baseline for pool-able NixOS LXCs (SKY-021). The VM baseline (base.nix) assumes a kernel,
# a bootloader and a disk; a container has none, so this is a separate, leaner spine. The upstream
# proxmox-lxc module already bakes in the historically-broken fixes (boot.isContainer, the
# register-nix-paths profile that lets `nixos-rebuild` find a "system" profile, and the getty@tty1
# start) — so this module adds only the lab conventions on top: nix flakes, the agent's SSH trust,
# the ops timezone, and a minimal toolchain. Reused by every pool CT host (lxc-proof first, then the
# real service hosts). Rationale + the in-place-rebuild verdict live in planning/ + journal/.
let
  # The agent's outbound key (svc-ops@vm-skynet-ops) — same identity ops-user.nix trusts on the VM,
  # so the agent can `nixos-rebuild switch --target-host` into the container to activate day-2.
  agentKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDaJEkEwSMl7iSgXeokZIKSVj4TgE4p8Bljx26LmrK0d svc-ops@vm-skynet-ops";
in
{
  imports = [ (modulesPath + "/virtualisation/proxmox-lxc.nix") ];

  # Unprivileged CT with proxmox owning the network (systemd-networkd picks up the pct-set config).
  # privileged stays off by contract (SKY-021 decision) — no Docker-in-CT; the DMZ Docker host is a VM.
  proxmoxLXC = {
    privileged = false;
    manageNetwork = false; # proxmox/pct owns eth0 addressing (static-first lab, set at pct create)
  };

  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  # deploy-rs / --target-host push locally-built (unsigned) closures as svc-ops → the CT must trust it.
  nix.settings.trusted-users = [ "root" "svc-ops" ];

  time.timeZone = "Asia/Karachi"; # PKT — the operator's timezone (matches base.nix)

  # sshd is on by default from the proxmox-lxc module; pin the agent's key to root so day-2
  # activation over SSH works, and forbid password auth (key-only, same posture as the VM).
  services.openssh = {
    enable = true;
    startWhenNeeded = lib.mkForce false; # a long-lived service host wants sshd always up, not socket-activated
    settings = {
      PermitRootLogin = "prohibit-password";
      PasswordAuthentication = false;
    };
  };
  users.users.root.openssh.authorizedKeys.keys = [ agentKey ];

  environment.systemPackages = with pkgs; [ git vim jq curl ];
}
