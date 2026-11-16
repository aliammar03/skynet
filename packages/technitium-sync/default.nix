# technitium-sync: dns/ applied to the local Technitium through its HTTP API (dns/README.md).
# modules/dns.nix runs it on both DNS servers; `nix build .#technitium-sync` checks the script with
# shellcheck.
{
  writeShellApplication,
  curl,
  jq,
}:
writeShellApplication {
  name = "technitium-sync";
  runtimeInputs = [
    curl
    jq
  ];
  text = builtins.readFile ./technitium-sync.sh;
}
