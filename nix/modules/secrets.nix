{ ... }:
# sops-nix wired to the ONE lab age key (survival kit), per docs/design/secrets.md — NOT a
# host-SSH-key identity, so there is one age key lab-wide.
{
  # The bootstrap secret (chicken-and-egg): the age private key is placed out-of-band at
  # provision time (1b), 0600 root:root. Everything else decrypts from it.
  sops.age.keyFile = "/opt/skynet-ops/secrets/age.key";

  # Declared secrets decrypt to tmpfs (/run/secrets/*), never to the world-readable /nix/store.
  # The ops VM's own 0600 secrets (API tokens, cloudflare-dns.env, …) migrate into in-git
  # *.sops + declarations here incrementally in 1b/1c. None are required for the flake to BUILD:
  # sops-nix decrypts at activation, not at build time. Example:
  #   sops.defaultSopsFile = ../../secrets/vm-skynet-ops.sops.yaml;
  #   sops.secrets."cloudflare-dns" = { path = "/opt/skynet-ops/secrets/cloudflare-dns.env"; };
}
