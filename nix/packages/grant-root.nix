{ writeShellApplication, openssh, coreutils }:
# Ali's workstation runs grant-root from the flake (`nix run <repo>#grant-root -- <host> <dur>`),
# never from a copied file, so it cannot drift from git. The CA key stays in ~/.skynet-ca.
# Not installed on the ops VM: the agent must never hold a signer.
writeShellApplication {
  name = "grant-root";
  runtimeInputs = [ openssh coreutils ];
  text = builtins.readFile ../../bin/grant-root;
}
