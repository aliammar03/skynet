{ pkgs, ... }:
# The ops operator (ali) + the T2 SSH principal (svc-ops), and the narrowed sudo that is
# SKY-007's thesis: collapse the ops VM's *standing passwordless root* into a reviewed diff.
{
  users.users.ali = {
    isNormalUser = true;
    description = "Skynet ops agent + operator";
    # docker-group ≈ root (SKY-003 caveat) — a known trade-off kept for now so the ops
    # scripts run unchanged; tightening it belongs to a later hardening phase. "wheel" is
    # retained for password-gated escalation only (blanket NOPASSWD is removed below).
    extraGroups = [ "docker" "wheel" ];
    openssh.authorizedKeys.keys = [ ]; # operator key added at provision (1b)
  };

  # svc-ops: the unprivileged T2 operate principal (AGENTS.md §1). deploy-rs connects as this.
  # In "wheel" only so it may exec sudo (execWheelOnly below); it has NO password, so
  # password-gated sudo is impossible for it — it is confined to its NOPASSWD rules below.
  users.users.svc-ops = {
    isNormalUser = true;
    description = "Skynet T2 operate SSH principal";
    extraGroups = [ "wheel" ];
    hashedPassword = "!"; # locked — deploy activation is its only sudo path
    openssh.authorizedKeys.keys = [ ]; # deploy key added at provision (1b)
  };

  # --- Narrowed sudo ---------------------------------------------------------------------
  # Before: wheel held blanket NOPASSWD:ALL — a standing root path on the agent's own box.
  # After: wheel needs a password; only the specific commands ops actually runs are NOPASSWD.
  security.sudo.wheelNeedsPassword = true;
  security.sudo.execWheelOnly = true;

  security.sudo.extraRules = [
    {
      # ali manages only its own skynet-* units without a password.
      users = [ "ali" ];
      commands = [
        { command = "${pkgs.systemd}/bin/systemctl start skynet-*"; options = [ "NOPASSWD" ]; }
        { command = "${pkgs.systemd}/bin/systemctl stop skynet-*"; options = [ "NOPASSWD" ]; }
        { command = "${pkgs.systemd}/bin/systemctl restart skynet-*"; options = [ "NOPASSWD" ]; }
        { command = "${pkgs.systemd}/bin/systemctl status skynet-*"; options = [ "NOPASSWD" ]; }
      ];
    }
    {
      # deploy-rs activation: it SSHes as svc-ops, then sudo-activates the new system profile.
      # sudoers '*' does not cross '/', so the store-hash wildcard matches one path component.
      # The exact command set is proven + tightened during the 1c magic-rollback round-trip.
      users = [ "svc-ops" ];
      commands = [
        { command = "/nix/store/*/bin/switch-to-configuration"; options = [ "NOPASSWD" ]; }
        { command = "${pkgs.nix}/bin/nix-env -p /nix/var/nix/profiles/system --set *"; options = [ "NOPASSWD" ]; }
        { command = "/run/current-system/sw/bin/systemd-run *"; options = [ "NOPASSWD" ]; }
      ];
    }
  ];
}
