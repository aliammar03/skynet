{ ... }:
# sops-nix wired to the ONE lab age key (survival kit), per docs/design/secrets.md — one age key
# lab-wide. The ops VM's token files are decrypted to tmpfs (/run/secrets) at activation; the
# collectors read them (owner=aliammar) with NO sudo. Only the master age.key is a real on-disk
# file (root 0600, the bootstrap secret).
#
# IMPERMANENCE ORDERING (hard-won): sops-install-secrets runs in EARLY (initrd) activation, one
# second BEFORE systemd mounts the /opt/skynet-ops persist bind-mount in stage-2. So:
#   - the age keyFile is read from its REAL backing path on the /nix partition
#     (/nix/persist/...), which is mounted before activation even starts — NOT the /opt bind-mount
#     path, which doesn't exist yet and made sops fail "cannot read keyfile".
#   - secrets decrypt to the sops DEFAULT /run/secrets/<name> (tmpfs, available early) — we do NOT
#     point `path` at the late /opt bind-mount (sops would write onto the pre-mount tmpfs and the
#     mount would then shadow it).
#   - the collectors' read-path /opt/skynet-ops/secrets/<name> is recreated as a symlink to the
#     tmpfs secret by tmpfiles in stage-2, AFTER the mount.
let
  ageKey = "/nix/persist/opt/skynet-ops/secrets/age.key";
  secretsDir = "/opt/skynet-ops/secrets";
  names = [
    "proxmox-core.env"
    "proxmox-network.env"
    "pbs.env"
    "technitium.env"
    "arcane.env"
    "authentik.env"
    "cloudflare-dns.env"
    "omada.env"
    "opnsense.env"
    "rclone.conf"
    "tofu-proxmox.env"
    "tofu-proxmox-network.env"
    "tofu-passphrase"
  ];
  # each token file: encrypted whole (binary) in git at secrets/<fname>.sops, decrypted to
  # /run/secrets/<fname> owned by aliammar.
  mkSecret = fname: {
    name = fname;
    value = {
      format = "binary";
      sopsFile = ../../secrets/${fname}.sops;
      owner = "aliammar";
      mode = "0400";
    };
  };
  # collectors read <secretsDir>/<fname>; link it to the tmpfs secret (stage-2, post-mount).
  mkLink = fname: "L+ ${secretsDir}/${fname} - - - - /run/secrets/${fname}";
in
{
  sops.age.keyFile = ageKey;
  sops.secrets = (builtins.listToAttrs (map mkSecret names)) // {
    # aliammar's login/sudo password hash (SKY-007 1d). neededForUsers → decrypted to
    # /run/secrets-for-users BEFORE users exist (root-owned there, so no owner=), consumed as
    # users.users.aliammar.hashedPasswordFile. Lets Ali password-sudo to root; the agent has no
    # password so its keyless sudo stays blocked (wheelNeedsPassword). Hash set out-of-band by Ali.
    "aliammar-password" = {
      format = "binary";
      sopsFile = ../../secrets/aliammar-password.sops;
      neededForUsers = true;
    };
    # The ops agent's SSH *private* key — the operate identity (reaches svc-ops to deploy, and
    # aliammar@workload-hosts for T2 SSH). Public half is declarative in nix/home/shell.nix. Decrypts
    # to /run/secrets/agent-ssh-key (early, tmpfs); symlinked to ~/.ssh/id_ed25519 in stage-2 below
    # (same reason as the /opt tokens: sops runs before the /home persist mount, so we can't write
    # straight to ~). Folding it here makes the box self-provisioning — no manual key copy on rebuild.
    "agent-ssh-key" = {
      format = "binary";
      sopsFile = ../../secrets/agent-ssh-key.sops;
      owner = "aliammar";
      mode = "0400";
    };
  };

  # The secrets dir must be traversable (o+x) so aliammar can follow the symlinks to /run/secrets;
  # the age.key inside stays root 0600 (its own file perms), unreadable to aliammar.
  systemd.tmpfiles.rules =
    [ "d ${secretsDir} 0751 root root -" ]
    ++ (map mkLink names)
    ++ [
      # ~/.ssh/id_ed25519 → the decrypted agent key (post-mount, stage-2). Ensure the dir first
      # (tmpfiles L+ won't create parents; a fresh reprovision may not have it yet).
      "d /home/aliammar/.ssh 0700 aliammar users -"
      "L+ /home/aliammar/.ssh/id_ed25519 - - - - /run/secrets/agent-ssh-key"
    ];
}
