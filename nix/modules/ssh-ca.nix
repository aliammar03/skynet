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
    extraConfig = ''
      TrustedUserCAKeys ${../../ca/skynet_ops_ca.pub}
    '';
  };
}
