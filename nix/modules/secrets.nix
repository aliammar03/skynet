{ ... }:
# sops-nix wired to the ONE lab age key (survival kit), per docs/design/secrets.md — one age key
# lab-wide. The ops VM's token files are decrypted to tmpfs (/run/secrets) at activation and
# symlinked to the paths the collectors already read; owner=aliammar so the ops user reads them
# with NO sudo. Only the master age.key stays a real on-disk file (root 0600, the bootstrap secret).
let
  secretsDir = "/opt/skynet-ops/secrets";
  # each token file: encrypted whole (binary) in git at secrets/<fname>.sops, restored to
  # <secretsDir>/<fname> as an aliammar-owned symlink into the tmpfs store.
  mkFile = fname: {
    format = "binary";
    sopsFile = ../../secrets/${fname}.sops;
    owner = "aliammar";
    mode = "0400";
    path = "${secretsDir}/${fname}";
  };
in
{
  sops.age.keyFile = "${secretsDir}/age.key";

  sops.secrets = {
    "proxmox-core.env" = mkFile "proxmox-core.env";
    "proxmox-network.env" = mkFile "proxmox-network.env";
    "technitium.env" = mkFile "technitium.env";
    "arcane.env" = mkFile "arcane.env";
    "authentik.env" = mkFile "authentik.env";
    "cloudflare-dns.env" = mkFile "cloudflare-dns.env";
    "rclone.conf" = mkFile "rclone.conf";
  };

  # The secrets dir must be traversable (o+x) so aliammar can follow the symlinks to /run/secrets;
  # the age.key inside stays root 0600 (its own file perms), unreadable to aliammar.
  systemd.tmpfiles.rules = [ "d ${secretsDir} 0751 root root -" ];
}
