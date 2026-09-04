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
```

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
