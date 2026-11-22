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
| `skynet-verify` | ops (`modules/window.nix`), and by hand | whether a stack or a host is well after a change, with its evidence (ADR-0020) |
| `skynet-merge` | ops (`modules/window.nix`) | whether the window may merge a PR now, gate by gate (ADR-0020) |
| `skynet-window` | ops, 05:00 (`modules/window.nix`) | the night's merge window: every open PR through `skynet-merge`, then `skynet-verify all`; a dry run until `docs/plans/autonomy.md` step 6 |

## Our own programs elsewhere

Not every program of ours is a package. A short one is written inside the module that runs it, and
a stack's stays in its folder. So the whole list is this table and the one above:

| Program | Where | What |
|---|---|---|
| `skynet-run`, `skynet-incident`, `skynet-digest`, `skynet-report`, `skynet-post` | `modules/agent-runs.nix` | the agent's unattended runs (`hosts/ops/README.md` → Unattended runs) |
| `skynet-review` | `modules/window.nix` | the evening review of the PRs the window could take (`runbooks/review.md`) |
| the smoke checks, `smoke.sh` | `stacks/dmz/komga/`, `stacks/dmz/uchiyomi/` | a page read through the app, for `skynet-verify` |
| `skynet-claude`, `skynet-attach` | `modules/agent.nix` | the agent's sessions on ops |
| `pbs-drift` | `modules/pbs-drift.nix` | PBS's config against `hosts/pbs/etc/`, every morning |
| the hooks: comin's notice, btrbk's stamp and `latest` link, `storage-keepalive` | `modules/base.nix`, `modules/docker-host.nix`, `hosts/docker-dmz/default.nix` | a few lines each, beside what calls them |
| `setup.sh`, `undo.sh` | `hosts/pbs/`, `hosts/pve/`, `hosts/unraid/` | what is applied to a machine that isn't NixOS (`hosts/README.md`) |
| the backup jobs' `run.sh` | `stacks/admin/backup/`, `stacks/dmz/backup/`, `stacks/admin/pbs-offsite/` | each job's checks before it runs, and the offsite copy's metrics |
| `comics-tools` | `stacks/dmz/comics-agent/tools/` | the comics agent's hands (ADR-0017) |
| CLU's patches | `stacks/dmz/clu/patches/` | fixes applied to CLU at each start, with their tests (ADR-0017) |
| `komga-wiki` | `stacks/dmz/komga/wiki/` | manga chapters' titles, summaries and dates for Komga |
| the arena | `stacks/dmz/arena/engine/` | the bench for testing agents (ADR-0018) |
