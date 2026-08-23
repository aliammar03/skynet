# nix/ — declarative host definitions (SKY-007)

Pushes the declarative boundary *below* Docker: a whole host as a reproducible flake. Piloted on
`vm-skynet-ops` only — the agent's own box, lowest blast radius. The design lives in
[`docs/system-design.md`](../docs/system-design.md); the directive in
[`planning/projects/SKY-007-…`](../planning/projects/SKY-007-nixos-host-definition-piloted-on-the-ops-vm.md).

## Layout

```
flake.nix                    inputs (nixpkgs 25.05, disko, sops-nix, deploy-rs), the
                             nixosConfiguration, and the deploy-rs node
hosts/vm-skynet-ops/
  default.nix                the host: imports + hostname + static network identity
  hardware.nix               qemu-guest profile + grub (legacy BIOS)
  disko.nix                  declarative disk layout (single virtio disk, GPT)
nix/modules/
  base.nix                   nix settings, the ops toolchain, docker daemon, firewall
  ops-user.nix               ali + svc-ops, and the narrowed sudo (SKY-007's thesis)
  ssh-ca.nix                 sshd + TrustedUserCAKeys (grant-root cert trust)
  timers.nix                 skynet-nightly + skynet-cli-update as systemd units
  secrets.nix                sops-nix wired to the lab age key
```

## The decisions baked in (locked at Phase-1 scoping)

- **Fresh VM, not a clone** as the `nixos-anywhere` target — the flake is the sole source of
  truth, no snowflake carryover.
- **sops-nix via `sops.age.keyFile`** = the one lab age key (survival kit), not a host-SSH-key
  identity. One age key lab-wide ([secrets](../docs/design/secrets.md)).
- **Agent CLIs stay npm-global** in `~ali`; Nix owns nodejs/git/gh/sops/age/rclone/restic/docker.
  The repo is checked out in `~ali` too — Nix defines the machine, the runtime is replaceable.
- **Sudo is a least-privilege module.** The live box grants standing passwordless `sudo ALL`;
  the flake removes wheel's blanket NOPASSWD and scopes it to the commands ops actually runs.
- **Only two timers are the ops VM's.** `skynet-restic-backup@` (docker hosts) and
  `skynet-pbs-gdrive` (PBS host) run elsewhere and are not defined here.

## What each phase does with this

- **1a (this):** author the flake; CI (`.github/workflows/nix.yml`) builds the system closure on
  every PR. No infrastructure touched.
- **1b:** create a fresh twin VM on a temp IP; `nixos-anywhere` kexec+disko installs the flake;
  place the age key; **commit `flake.lock`** (generated on the twin — Nix stays off the live box).
- **1c:** validate on the twin — nightly dry-run, git/gh path, timers, docker, sops decrypt, and a
  **deploy-rs magic-rollback round-trip** (an SSH-breaking change auto-reverts).
- **1d:** human-approved cutover — PBS-snapshot 9090, move `.90`/`.99`+DNS to the twin, retire the
  stray VMID 999. Keep 9090 as instant rollback for a few days.

## Building locally

Nix is deliberately **not** installed on the live ops VM ("never gamble the live VM"). Build in a
throwaway `nixos/nix` container or on the twin:

```bash
nix build .#nixosConfigurations.vm-skynet-ops.config.system.build.toplevel
```
