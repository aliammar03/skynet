{ pkgs, config, ... }:
# The ops operator (aliammar) + the T2 SSH principal (svc-ops), and the narrowed sudo that is
# SKY-007's thesis: collapse the ops VM's *standing passwordless root* into a reviewed diff.
let
  # The ops agent's SSH key (lives on the current ops box). Baked so the agent reaches the twin
  # as aliammar (operate) and svc-ops (deploy-rs).
  agentKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDaJEkEwSMl7iSgXeokZIKSVj4TgE4p8Bljx26LmrK0d svc-ops@vm-skynet-ops";
  # Ali's workstation key — so Ali logs into the ops box directly (not only via a CA cert).
  aliWorkstationKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMY3q277EOHizg5Ji/WUU7WvUi4X/ezbRPebk65lQVBJ aliammar@RK-W";
in
{
  # Declarative users only — no imperative useradd/passwd drift, enforced every activation. This is
  # also REQUIRED for the sops password below to apply: NixOS writes a declared hash to /etc/shadow
  # for an *existing* user only when mutableUsers=false (update-users-groups.pl). Fits the box's
  # flake-is-truth + impermanence model; change a password via the sops secret + redeploy, not passwd.
  users.mutableUsers = false;

  users.users.aliammar = {
    isNormalUser = true;
    description = "Skynet ops agent + operator";
    # docker-group ≈ root (SKY-003 caveat) — a known trade-off kept for now so the ops
    # scripts run unchanged; tightening it belongs to a later hardening phase. "wheel" is
    # retained for password-gated escalation only (blanket NOPASSWD is removed below).
    extraGroups = [ "docker" "wheel" ];
    openssh.authorizedKeys.keys = [ agentKey aliWorkstationKey ];
    # Ali's login/sudo password (sops, neededForUsers). With wheel + wheelNeedsPassword, this is a
    # full password-gated root for the human; the agent (key-only, no password) can't use it.
    hashedPasswordFile = config.sops.secrets."aliammar-password".path;
  };

  # svc-ops: the unprivileged T2 operate principal (AGENTS.md §1). deploy-rs connects as this.
  # In "wheel" only so it may exec sudo (execWheelOnly below); it has NO password, so
  # password-gated sudo is impossible for it — it is confined to its NOPASSWD rules below.
  users.users.svc-ops = {
    isNormalUser = true;
    description = "Skynet T2 operate SSH principal";
    extraGroups = [ "wheel" ];
    hashedPassword = "!"; # locked — deploy activation is its only sudo path
    openssh.authorizedKeys.keys = [ agentKey ];
  };

  # --- Narrowed sudo ---------------------------------------------------------------------
  # Before: wheel held blanket NOPASSWD:ALL — a standing root path on the agent's own box.
  # After: wheel needs a password; only the specific commands ops actually runs are NOPASSWD.
  security.sudo.wheelNeedsPassword = true;
  security.sudo.execWheelOnly = true;

  security.sudo.extraRules = [
    {
      # aliammar manages only its own skynet-* units. Secrets are now sops-nix decrypt-to-tmpfs,
      # owned by aliammar under /run/secrets (symlinked into the secrets dir) — so the collectors
      # read them with NO sudo, and no secret-reading sudo grant is needed here.
      users = [ "aliammar" ];
      commands = [
        { command = "${pkgs.systemd}/bin/systemctl start skynet-*"; options = [ "NOPASSWD" ]; }
        { command = "${pkgs.systemd}/bin/systemctl stop skynet-*"; options = [ "NOPASSWD" ]; }
        { command = "${pkgs.systemd}/bin/systemctl restart skynet-*"; options = [ "NOPASSWD" ]; }
        { command = "${pkgs.systemd}/bin/systemctl status skynet-*"; options = [ "NOPASSWD" ]; }
      ];
    }
    {
      # deploy-rs activation: it SSHes as svc-ops, then runs `sudo -u root <profile>/activate-rs
      # <cmd> …`. That single Rust binary does the nix-env / switch-to-configuration / systemd-run
      # itself as root, so it is deploy-rs's *entire* sudo surface (svc-ops can do nothing else).
      # A bare command (no args) in sudoers permits any arguments; '*' matches the store-hash
      # component without crossing '/'. Proven in the 1c magic-rollback round-trip.
      users = [ "svc-ops" ];
      commands = [
        { command = "/nix/store/*/activate-rs"; options = [ "NOPASSWD" ]; }
        # magic-rollback confirms by removing its canary file (`sudo -u root rm
        # /tmp/deploy-rs-canary-<hash>`); without this the confirm fails and every deploy rolls back.
        { command = "/run/current-system/sw/bin/rm /tmp/deploy-rs-canary-*"; options = [ "NOPASSWD" ]; }
      ];
    }
  ];
}
