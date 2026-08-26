{ pkgs, ... }:
# sshd + the ops CA trust that makes bin/grant-root's short-lived certs verify (T2+ root grant).
let
  # The grant-root principals sshd accepts for a root login (grant-root signs `ops-root-<host>`):
  # the twin's name, the post-cutover name, and the fleet-wide principal. A real store *file*
  # (writeText), so the copy below dereferences to content — not a symlink to copy verbatim.
  authPrincipalsRoot = pkgs.writeText "ops-auth-principals-root" ''
    ops-root-vm-skynet-ops-nix
    ops-root-vm-skynet-ops
    ops-root-all
  '';
in
{
  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      # Root only via a CA-signed cert inside a grant window — never a password.
      PermitRootLogin = "prohibit-password";
      # AuthorizedPrincipalsFile maps root logins to the grant-root principals only — a CA cert
      # must carry one of these principals, not just "root". MUST be set via `settings` (not
      # extraConfig): NixOS emits `AuthorizedPrincipalsFile none` as a settings mkDefault, and
      # sshd honors the FIRST occurrence — an extraConfig line lands *after* it and is dead, so
      # principal-scoped grant-root certs silently fail (only "-n root"/empty-principal certs work).
      AuthorizedPrincipalsFile = "/etc/ssh/auth_principals/%u";
    };
    # Trust the ops CA public key (baked from the repo) so grant-root certs authenticate.
    # The CA *private* key never leaves Ali's workstation — the agent cannot mint its own access.
    # (No NixOS default for TrustedUserCAKeys, so extraConfig is fine here — no duplicate to lose to.)
    extraConfig = ''
      TrustedUserCAKeys ${../../ca/skynet_ops_ca.pub}
    '';
  };

  # The AuthorizedPrincipalsFile MUST be a real root-owned file, NOT a symlink into /nix/store:
  # sshd's StrictModes refuses to read one whose realpath passes through a group-writable dir, and
  # /nix/store is `root:nixbld 1775` (group-writable). A store symlink → "bad ownership or modes for
  # directory /nix/store" → sshd reads ZERO principals → every grant-root cert is rejected
  # ("Certificate does not contain an authorized principal"). `environment.etc` only makes store
  # symlinks (and a tmpfiles `C` of one copies the symlink verbatim), so a oneshot `install`s the
  # content to a real file on tmpfs /etc before sshd — re-run every boot (tmpfs wipes /etc).
  systemd.services.ops-auth-principals = {
    description = "Install sshd root AuthorizedPrincipalsFile as a real (non-store) file";
    wantedBy = [ "multi-user.target" ];
    before = [ "sshd.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    # rm first: a prior generation may have left a symlink here, and `install` would follow it
    # into the read-only store instead of replacing it.
    script = ''
      rm -f /etc/ssh/auth_principals/root
      ${pkgs.coreutils}/bin/install -Dm0444 -o root -g root ${authPrincipalsRoot} /etc/ssh/auth_principals/root
    '';
  };
}
