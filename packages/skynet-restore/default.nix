# skynet-restore: a stack's /opt/appdata folder back from a local btrfs snapshot or from Drive, with
# doco-cd held (runbooks/restore.md). modules/docker-host.nix builds it for each Docker host with
# that host's Docker, restic and values (runtimeEnv); `nix build .#skynet-restore` checks the script
# with shellcheck.
{
  writeShellApplication,
  docker,
  restic,
  rclone,
  rsync,
  coreutils,
  findutils,
  gnugrep,
  gnused,
  util-linux,
  systemd,
  runtimeEnv ? { },
}:
writeShellApplication {
  name = "skynet-restore";
  runtimeInputs = [
    docker
    restic
    rclone
    rsync
    coreutils
    findutils
    gnugrep
    gnused
    util-linux # flock
    systemd
  ];
  inherit runtimeEnv;
  text = builtins.readFile ./skynet-restore.sh;
}
