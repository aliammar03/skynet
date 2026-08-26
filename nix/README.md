# nix/ — declarative host definitions (SKY-007)

Pushes the declarative boundary *below* Docker: a whole host as a reproducible flake. Piloted on
`vm-skynet-ops` only — the agent's own box, lowest blast radius. The design lives in
[`docs/system-design.md`](../docs/system-design.md); the directive in
[`planning/projects/SKY-007-…`](../planning/projects/SKY-007-nixos-host-definition-piloted-on-the-ops-vm.md).

## Layout

```
flake.nix                    inputs (nixpkgs 26.05, disko, sops-nix, deploy-rs), the
                             nixosConfiguration, and the deploy-rs node
hosts/vm-skynet-ops/
  default.nix                the host: imports + hostname + static network identity
  hardware.nix               qemu-guest profile + systemd-boot (UEFI/OVMF, q35)
  disko.nix                  declarative disk layout (VirtIO disk, GPT, ESP + root)
nix/modules/
  base.nix                   nix settings, the ops toolchain, docker daemon, firewall
  ops-user.nix               aliammar + svc-ops, and the narrowed sudo (SKY-007's thesis)
  ssh-ca.nix                 sshd + TrustedUserCAKeys (grant-root cert trust)
  timers.nix                 skynet-nightly + skynet-cli-update as systemd units
  secrets.nix                sops-nix wired to the lab age key
```

## The decisions baked in (locked at Phase-1 scoping)

- **Fresh VM, not a clone** as the `nixos-anywhere` target — the flake is the sole source of
  truth, no snowflake carryover.
- **sops-nix via `sops.age.keyFile`** = the one lab age key (survival kit), not a host-SSH-key
  identity. One age key lab-wide ([secrets](../docs/design/secrets.md)).
- **Agent CLIs stay npm-global** in `~aliammar`; Nix owns nodejs/git/gh/sops/age/rclone/restic/docker.
  The repo is checked out in `~aliammar` too — Nix defines the machine, the runtime is replaceable.
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
- **1d:** human-approved cutover — PBS-snapshot the old box, then the twin took the live `.90`
  identity (`deploy .#vm-skynet-ops`). **DONE** — the old VMID 9090 is kept **stopped** as instant
  rollback. The temp twin (`vm-skynet-ops-nix`) is retired and removed from the flake.

## Building / deploying (post-cutover)

The box now **runs NixOS**, so it builds and deploys itself — Nix is native here. Day-2 changes are a
reviewed flake diff, merged, then applied:

```bash
# validate any change (no switch)
nixos-rebuild build --flake ~/skynet#vm-skynet-ops

# apply — either path works now that the box has password sudo + the agent key:
sudo nixos-rebuild switch --flake ~/skynet#vm-skynet-ops        # local, host-agnostic
nix run github:serokell/deploy-rs -- .#vm-skynet-ops            # deploy-rs, magic-rollback
```

The original provisioning (kexec + `disko` via `nixos-anywhere`, from a throwaway `nixos/nix`
container so Nix never touched the old Ubuntu box) is history now — see the git log if you ever
reprovision from scratch.
