# technitium-stats: the local Technitium's last hour, for node-exporter's textfile collector
# (stacks/admin/metrics/rules/dns.yml). modules/dns.nix runs it every 5 minutes on both DNS servers;
# `nix build .#technitium-stats` checks the script with shellcheck.
{
  writeShellApplication,
  curl,
  jq,
}:
writeShellApplication {
  name = "technitium-stats";
  runtimeInputs = [
    curl
    jq
  ];
  text = builtins.readFile ./technitium-stats.sh;
}
