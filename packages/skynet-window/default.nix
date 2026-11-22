# skynet-window: the night's merge window (docs/plans/autonomy.md → Merges); a dry run until
# step 6. modules/window.nix builds it with ops's values, skynet-merge and skynet-verify, and runs it
# at 05:00; `nix build .#skynet-window` checks the script with shellcheck.
{
  writeShellApplication,
  coreutils,
  findutils,
  gh,
  skynet-merge,
  skynet-verify,
  runtimeEnv ? { },
}:
writeShellApplication {
  name = "skynet-window";
  runtimeInputs = [
    coreutils
    findutils
    gh
    skynet-merge
    skynet-verify
  ];
  inherit runtimeEnv;
  text = builtins.readFile ./skynet-window.sh;
}
