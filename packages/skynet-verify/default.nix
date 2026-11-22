# skynet-verify: whether a stack or a host is well after a change, from evidence the agent didn't
# write (docs/plans/autonomy.md → Verify and roll back). modules/window.nix builds it with ops's
# values (runtimeEnv); `nix build .#skynet-verify` checks the script with shellcheck.
{
  writeShellApplication,
  coreutils,
  curl,
  findutils,
  git,
  gnugrep,
  gnused,
  jq,
  openssh,
  systemd,
  yq-go,
  runtimeEnv ? { },
}:
writeShellApplication {
  name = "skynet-verify";
  runtimeInputs = [
    coreutils
    curl
    findutils
    git
    gnugrep
    gnused
    jq
    openssh
    systemd
    yq-go
  ];
  inherit runtimeEnv;
  text = builtins.readFile ./skynet-verify.sh;
}
