{ ... }:
# sshd + the ops CA trust that makes bin/grant-root's short-lived certs verify (T2+ root grant).
{
  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      # Root only via a CA-signed cert inside a grant window — never a password.
      PermitRootLogin = "prohibit-password";
    };
    # Trust the ops CA public key (baked from the repo) so grant-root certs authenticate.
    # The CA *private* key never leaves Ali's workstation — the agent cannot mint its own access.
    # AuthorizedPrincipalsFile maps root logins to the grant-root principals only (same as
    # scripts/onboard-host.sh) — a CA cert must carry one of these principals, not just "root".
    extraConfig = ''
      TrustedUserCAKeys ${../../ca/skynet_ops_ca.pub}
      AuthorizedPrincipalsFile /etc/ssh/auth_principals/%u
    '';
  };

  # grant-root signs certs with principal `ops-root-<host>`; accept the twin's name, the
  # post-cutover name, and the fleet-wide principal.
  environment.etc."ssh/auth_principals/root".text = ''
    ops-root-vm-skynet-ops-nix
    ops-root-vm-skynet-ops
    ops-root-all
  '';
}
