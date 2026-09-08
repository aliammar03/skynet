# nix/ — declarative host definitions

The ops VM (`vm-skynet-ops`) is a reproducible NixOS flake — the whole host, below Docker, defined
and version-controlled. The design lives in [`docs/system-design.md`](../docs/system-design.md).

## Layout

```
flake.nix                    inputs (nixpkgs 26.05, home-manager, disko, sops-nix,
                             impermanence, deploy-rs), the nixosConfiguration + deploy-rs node
hosts/vm-skynet-ops/
  default.nix                the host: imports + hostname + static network identity
  hardware.nix               qemu-guest profile + systemd-boot (UEFI/OVMF, q35)
  disko.nix                  declarative disk layout (VirtIO disk, GPT, ESP + /nix)
nix/modules/
  base.nix                   nix settings, the ops toolchain, docker daemon, firewall, serial console
  ops-user.nix               aliammar + svc-ops, and the narrowed least-privilege sudo
  ssh-ca.nix                 sshd + TrustedUserCAKeys (grant-root cert trust)
  known-hosts.nix            pinned fleet host keys for the agent's outbound SSH
  timers.nix                 skynet-nightly + skynet-cli-update as systemd units
  secrets.nix                sops-nix wired to the lab age key (decrypt-to-tmpfs)
  impermanence.nix           tmpfs root; only /nix + declared paths persist
  home.nix                   wires home-manager into the system
nix/home/
  aliammar.nix               the operator's home: git identity, agent CLIs (+ mcp-nixos), ops.env
  shell.nix                  zsh + starship + tooling + the login landing board
  docker.nix                 the docker-dmz remote context for collect-docker.sh
nix/packages/
  skynet.nix                 the source-filtered Skynet Python application package
```

## Skynet Python runtime

The `skynet` command is a Nix-owned Python package exposing a runtime diagnostic, core and network
Proxmox observations, default collection and paired Proxmox freshness checks. `bin/skynet` launches the package
from the checkout's tracked Git source using offline, lock-preserving Nix evaluation. It never
falls back to source Python or installs a profile. Build the package and cache its dependencies
before using default callers; a missing Nix/build prerequisite fails the command.

```bash
# source development tools, with no pip installation
nix develop --no-write-lock-file
pytest -q
ruff check src tests/test_*.py
mypy src/skynet

# build the installable command and run it from anywhere
nix build --no-write-lock-file --no-link .#skynet
nix run --no-write-lock-file .#skynet -- doctor --json

# run all packaged behavioral, lint, type, and outside-checkout smoke checks
nix build --no-write-lock-file --no-link .#checks.x86_64-linux.skynet
```

`skynet doctor [--json]` reports the executing package version and Python runtime with
`scope: runtime`. It is not a lab or service health check.

`skynet collect proxmox <core|network> --output <file> [--credentials-file <file>] [--json]` reads
nodes, resources, pools/members, backup jobs and recent vzdump tasks over verified HTTPS. Default
credential files are `/opt/skynet-ops/secrets/proxmox-core.env` and
`/opt/skynet-ops/secrets/proxmox-network.env`; each accepts only
literal `PVE_HOST`, `PVE_TOKEN`, and `PVE_CACERT` assignments plus optional `PVE_TOKEN_OPERATE`
(one per line, optional quotes and comments). Observation requests use only `PVE_TOKEN`;
the shared operate assignment is never a fallback. Shell expressions, duplicate/unknown
assignments and redirects are refused.
Requests use a 15-second socket timeout and the specified CA with hostname verification.

The collector publishes atomically to the explicit destination after every required read and
validation succeeds. Failure retains any previous snapshot and its timestamp; consumers must treat it as
previous evidence. Collection success describes observations, not service or backup health.
JSON reports `outcome`, `target`, `output`, and either `collected`/`counts` or a redacted `reason`.
Exit codes: 0 success, 2 usage error, 3 unavailable credentials/CA/remote evidence, 1 malformed
data or local publication failure. Empty nodes/resources fail; empty pools/jobs/tasks are valid
observations, with absent backup results represented by null fields.

`bin/ops collect` forwards to `skynet collect all --repo <checkout>`, running the Python core and
network collectors once each before the remaining shell readers. Refresh evidence lives in
`inventory/collection-core.json` and `inventory/collection-network.json`: an incomplete marker
precedes each node read, and success records that snapshot's exact hash/time. The nonblocking
`.cache/collection.lock` stores one durable attempt receipt before marker publication. Status
requires that receipt to match both markers, so failed marker setup stops before that node's read
and invalidates either node's previous success without a cutoff.
Missing receipts require a complete refresh. Status briefly locks and durably reaffirms the
existing receipt; storage that cannot persist invalidation is unavailable even if old evidence
is readable. An inability to persist any failure cannot leave a durable diagnosis: repair storage
and complete a refresh before using observations. Snapshot bytes remain intact on setup failure.
Other readers report their
process exits; they do not yet provide the Python core collector's validated evidence contract.
Each runs sequentially in an isolated Linux process group with a 120-second deadline. Before
advancing or releasing the lock, collection kills remaining group members and reaps descendants,
including on interruption or an early leader exit. Cleanup has a five-second deadline; unconfirmed
cleanup stops collection with `recovery-required` and blocks further collections via the receipt.
Readers must remain in that process group; programs that daemonize or create another session
are outside this runner's cleanup contract.
After operator verification that the reader processes are gone, clear that receipt under the
collection lock and run a complete refresh. Do not delete the lock file while a process holds it.

`skynet collect-status --repo <checkout> [--since <timestamp>] [--json]` requires matching
successful core and network observations and operate-token ACL evidence no older than 36 hours,
with timezone-aware timestamps.
Missing, failed, future, stale or mismatched evidence exits 3. Default factual rendering and
`bin/ops query|entities` require this check. Nightly sets `SKYNET_COLLECTION_SINCE` so a prior
success cannot satisfy the current pass. Direct repository invariant/entity/SQLite scripts
operate on historical snapshots for deterministic CI; they do not establish live freshness.
Explicit-output collectors are isolated: use `collect all` to establish default refresh evidence
after an isolated collection changes either snapshot.

## The decisions baked in

- **Fresh VM, not a clone** — the flake is the sole source of truth, no snowflake carryover.
- **sops-nix via `sops.age.keyFile`** = the one lab age key (survival kit), not a host-SSH identity.
  One age key lab-wide ([secrets](../docs/design/secrets.md)).
- **Agent CLIs are home-manager packages** (from nixpkgs-unstable) in `~aliammar`. The repo is
  checked out in `~aliammar` too — Nix defines the machine, the checked-out runtime is replaceable.
- **Agent permission ergonomics follow the OS boundary.** Claude, Codex, and OpenCode may freely
  read, edit, run Nix, commit, push branches, and open PRs as `aliammar`; PR merge and root-grant
  commands still prompt. The unprivileged account and scoped sudo remain the real security wall.
- **Least-privilege sudo, no standing root.** wheel needs a password; only the commands ops actually
  runs are NOPASSWD (aliammar: `systemctl skynet-*`; svc-ops: deploy-activation). Interactive root is
  Ali's password or a grant-root cert.
- **Impermanence** — the root filesystem is tmpfs, wiped every boot; only `/nix` and the declared
  persist paths survive, so drift is structurally impossible.
- **Only two timers are the ops VM's.** `skynet-restic-backup@` (docker hosts) and `skynet-pbs-gdrive`
  (PBS host) run elsewhere and are not defined here.

## Building / deploying

The box runs NixOS, so it builds and deploys itself. Day-2 changes are a reviewed flake diff,
merged, then applied:

```bash
# validate any change (no switch)
nixos-rebuild build --flake ~/skynet#vm-skynet-ops

# apply — either path (the box has password sudo + the agent key):
sudo nixos-rebuild switch --flake ~/skynet#vm-skynet-ops     # local, host-agnostic
nix run github:serokell/deploy-rs -- .#vm-skynet-ops         # deploy-rs, magic-rollback
```

To reprovision from scratch: `nixos-anywhere --flake .#vm-skynet-ops` (kexec + `disko`), with the age
key placed via `--extra-files`.
