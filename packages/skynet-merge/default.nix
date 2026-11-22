# skynet-merge: whether the window may merge a PR now, gate by gate (docs/plans/autonomy.md →
# Merges); a dry run until step 6. modules/window.nix builds it with ops's values and its
# skynet-verify; `nix build .#skynet-merge` checks the script with shellcheck.
{
  writeShellApplication,
  coreutils,
  curl,
  gh,
  git,
  gnugrep,
  gnused,
  jq,
  yq-go,
  skynet-verify,
  runtimeEnv ? { },
}:
writeShellApplication {
  name = "skynet-merge";
  runtimeInputs = [
    coreutils
    curl
    gh
    git
    gnugrep
    gnused
    jq
    yq-go
    skynet-verify
  ];
  inherit runtimeEnv;
  text = builtins.readFile ./skynet-merge.sh;
}
