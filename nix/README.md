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
Proxmox observations, PBS backup observations, Docker inventory, Technitium DNS zones, default
collection and receipt-bound
freshness checks. `bin/skynet` launches the package
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

`skynet collect pbs --output <file> [--credentials-file <file>] [--json]` reads complete
datastore status, namespaces and backup snapshots with the literal
`/opt/skynet-ops/secrets/pbs.env` assignments. `PBS_TOKEN` retains PBS's colon separator and
normalizes one PVE-style equals separator. `PBS_CACERT` uses normal CA-file validation; otherwise
the configured fingerprint pins the bootstrap leaf before a verified request, with `PBS_SNI` or
the pinned certificate's DNS name used for hostname verification. Missing/null endpoint data,
partial datastore reads, malformed snapshots, timeout and trust failure are unavailable or failed,
never an empty successful backup result. Empty validated snapshot lists are valid observations;
an explicitly returned root namespace is collected once. Backup rendering distinguishes failed,
absent and unknown latest verification from successful verification.

`skynet collect docker <label> --output <file> [--context <context>] [--json]` runs only
read-only Docker context inspection, `ps --all`, and `image ls` using argument arrays and a
20-second command deadline. Docker and its subprocess descendants are stopped and reaped before
collection continues; uncertain cleanup stops the pass with recovery-required evidence.
JSON lines must contain valid container/image fields consumed by SQLite; a valid
empty host is distinct from a missing context, failed command, or malformed output. Failure retains
the previous snapshot and cannot establish fresh default evidence.

`skynet collect dns --output <file> [--credentials-file <file>] [--json]` reads Technitium zones
and their records over verified HTTPS on port 53443, using literal
`/opt/skynet-ops/secrets/technitium.env` `TECH_HOST`, `TECH_TOKEN`, and `TECH_CACERT` assignments
(the scoped Zones token, never server settings). Only the `zones/list` and `zones/records/get`
read endpoints are called; the token travels solely in the request query and never in a diagnostic.
The snapshot preserves the collection time, host, every zone object, and each zone's
`{zone, records}` with record `name/type/rData` (all record types, not only A/CNAME) consumed by
SQLite and the service renderer. A non-`ok` API status, a null/missing zone list or record list, a
duplicate zone identity, a malformed required record field, timeout or trust failure is unavailable
or failed, never an empty successful result; a validated empty record list is a real observation.
The root zone retains its empty-string identity in inventory and is requested as `.` from the API.
A/AAAA address data and CNAME targets are validated before publication.

`skynet collect opnsense --firewall-output <file> --state-output <file> [--credentials-file <file>]
[--json]` is the live T1 read of OPNsense, producing two paired snapshots: the user-view firewall
configuration (aliases, rules, reservations) and live state the git mirror cannot give (firmware,
ARP, interfaces, declared-host presence). It uses literal `/opt/skynet-ops/secrets/opnsense.env`
`OPN_HOST/OPN_KEY/OPN_SECRET/OPN_CACERT` (optional `OPN_PORT` default 443, `OPN_SNI`, and unused
`OPN_USER` metadata); the SNI is
derived from the pinned certificate's SAN so a stale name cannot break trust, and the key/secret
travel only in the Basic auth header. Only the enumerated GETs (`core/firmware/status`,
`firewall/alias/get`, `firewall/filter/get`, `interfaces/overview/interfacesInfo`) and the
read-only search POSTs (`firewall/filter/searchRule`, `dnsmasq/settings/searchHost`,
`diagnostics/interface/searchArp`) are called — the recon key carries "System: Deny config write",
so this collector only reads. Built-in aliases (`^__.*_network$`, bogons/bogonsv6/sshlockout/
virusprot) are dropped to match the mirror's user view; rules intersect the configured `filter/get`
UUIDs with the flat `searchRule` display fields, excluding internal/auto rules. Every configured
rule must appear once. Missing or malformed configuration sections fail; explicit empty mappings
are observations. Search pages require a nonnegative integer `total` matching the returned rows.
Declared-host presence is ARP
first, then ICMP for ARP-silent hosts from the ops vantage; `via` is explicit (`arp`, `icmp`,
`no-arp,no-icmp`, or `no-arp,icmp-unavailable` when the probe cannot run). Both snapshots are fully
validated before either is written; a read or validation failure leaves both files untouched, and
the default path binds both to one receipt so neither looks fresh without the other. Replacement
is atomic per file, not across the pair: a publication failure can leave one changed file, returns
failure, and cannot satisfy default freshness. The live OPNsense API is the sole producer of
firewall inventory; the `skynet-opnsense` `config.xml` git backup is retained only as
disaster-recovery material (restored as configuration into OPNsense — see
`docs/design/disaster-recovery.md`), never parsed into inventory.

Each collector validates every required read before atomically replacing each explicit destination.
Read/validation failure retains previous snapshots; publication failure cannot establish fresh
evidence, including a partially replaced OPNsense pair. Collection success describes observations,
not service or backup health.
JSON reports `outcome`, `target`, `output`, and either `collected`/`counts` or a redacted `reason`.
Exit codes: 0 success, 2 usage error, 3 unavailable credentials/CA/remote evidence, 1 malformed
data or local publication failure. Empty nodes/resources fail; empty pools/jobs/tasks are valid
observations, with absent backup results represented by null fields.

`skynet collect omada --output <file> [--credentials-file <file>] [--json]` is the T1 read of
the Omada controller through its Viewer account. It parses literal `OMADA_HOST`, `OMADA_PORT`,
`OMADA_SNI`, `OMADA_USER`, `OMADA_PASS`, and `OMADA_CACERT` assignments without shell evaluation,
uses pinned-CA HTTPS, and keeps the password, cookie and CSRF token in memory. The allowlist is
`/api/info`, one login POST, and authenticated site/device/switch-port GETs. Every site page,
device list and switch-port list is validated before the legacy network-gear snapshot is atomically
published; non-switch devices have `ports: null`, while a missing switch-port response fails the
refresh. Default collection binds its snapshot hash/time to `collection-network-gear.json`.

`bin/ops collect` forwards to `skynet collect all --repo <checkout>`, running the Python core,
network, ACL, PBS, Docker, DNS, live OPNsense, and Omada collectors once each before the remaining shell readers. Refresh evidence lives in
the matching `inventory/collection-*.json` markers: an incomplete marker precedes each read, and
success records that snapshot's exact hash/time. The nonblocking
`.cache/collection.lock` stores one durable attempt receipt before marker publication. Status
requires that receipt to match every migrated marker, so failed marker setup stops before that read
and invalidates prior success without a cutoff.
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
successful core and network observations, operate-token ACL, PBS, Docker, DNS, live OPNsense, and Omada evidence no older than 36 hours,
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
