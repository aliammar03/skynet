# dnsbench: Technitium's forwarders chosen by measurement (runbooks/dns-speed-test.md). Run by hand
# on ops, `nix run .#dnsbench -- <mode> …`; nothing deploys it. unbound.conf beside it is the
# throwaway resolver its `recursion` mode measures.
{
  writeShellApplication,
  python3,
}:
writeShellApplication {
  name = "dnsbench";
  runtimeInputs = [
    (python3.withPackages (p: [
      p.httpx
      p.h2
    ]))
  ];
  text = ''exec python3 -I ${./dnsbench.py} "$@"'';
}
