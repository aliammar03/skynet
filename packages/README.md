# packages

Our own programs a host runs, one folder each: the program and a `default.nix` that builds it with
`callPackage`. The module that runs one builds it with that host's values; `flake.nix` lists each
under `packages`, so `nix build .#<name>` checks it (shellcheck, for a shell script). A program a
stack runs stays in the stack's folder (`stacks/README.md`). A new program of our own needs a
decision record naming the mature tools it ruled out (`AGENTS.md`, rule 6).

| Package | Run by | What |
|---|---|---|
| `skynet-restore` | both Docker hosts (`modules/docker-host.nix`) | a stack's data back from a local snapshot or from Drive (`runbooks/restore.md`) |
| `technitium-sync` | both DNS servers (`modules/dns.nix`) | `dns/` applied to Technitium (`dns/README.md`) |
| `technitium-stats` | both DNS servers (`modules/dns.nix`) | Technitium's last hour, for node-exporter |
| `dnsbench` | by hand, on ops | Technitium's forwarders chosen by measurement (`runbooks/dns-speed-test.md`) |
