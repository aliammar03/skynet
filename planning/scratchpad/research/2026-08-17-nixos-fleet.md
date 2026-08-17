> _Agent-generated research (Claude Code, 2026-08-17), feeding **SKY-007**. Skeptical decision brief; not a design doc. Verify commands against current upstream before acting._

# NixOS as a declarative host-definition layer for Skynet

**Question:** is NixOS worth adopting as the host layer, and is the ops VM the right low-blast-radius pilot? Skynet already has the *service* layer solved (compose + Arcane GitOps). The gap NixOS would fill is the *host* layer — today general-purpose Debian/Ubuntu VMs configured by drift-prone imperative steps. NixOS makes a host a reviewable, atomically-rollbackable artifact in git. The counterweight is branching factor: an LLM operator must run it reliably, and Nix is famously sharp-edged.

## 1. Flakes fundamentals & the LLM-operator learning curve

A single-host flake is small: a `flake.nix` with `inputs` (nixpkgs, plus modules) and one `nixosConfigurations.<host>` output importing `configuration.nix` + `hardware-configuration.nix`. Apply with `nixos-rebuild switch --flake .#host`; every generation is a bootloader entry you can roll back to. That part is genuinely clean and teaches well in PRs.

The honest cost: you must learn the **Nix language** (lazy, functional, its own idioms) and the module system, and *the docs are the weak point* — widely described as confusing, with knowledge scattered across manual, wiki, Discourse, and blogs ([fosslinux 2026](https://www.fosslinux.com/154635/mastering-nixos-immutable-linux.htm); [NixOS & Flakes book](https://discourse.nixos.org/t/an-unofficial-nixos-flakes-book-for-beginners/29561)). For an **LLM operator the specific hazards are**: (a) *cryptic errors* — `infinite recursion`, `attribute missing`, opaque type-mismatch traces that don't point at the offending line; an agent can burn many turns pattern-matching blind. (b) *Packaging friction* — anything not already in nixpkgs (custom binary, odd build) means writing a derivation, a real skill jump. (c) *Flake pinning* — `flake.lock` is a feature (reproducible) but agents must discipline `nix flake update` or silently drift. Mitigation: keep the config boring, pin nixpkgs to a stable release (25.11-class), lean on `oci-containers` so almost nothing needs custom packaging, and treat every rebuild behind a PR + `nixos-rebuild build` (dry) check.

## 2. NixOS as a Proxmox guest + converting an existing VM

Two clean starting paths, both current to **Jan 2026 on PVE 9.1 / NixOS 25.11** ([NixOS wiki: Proxmox VE](https://wiki.nixos.org/wiki/Proxmox_Virtual_Environment); [mtlynch.io](https://mtlynch.io/notes/nixos-proxmox/)):
- **Prebuilt template** — download `nixos-image-lxc-proxmox-*.tar.xz` from Hydra as a CT template, or a VM image; `nixos-generators --format proxmox-lxc` builds a custom one. Gotchas: set container console `tty`→`console` (broken web console otherwise); some PVE UI fields (root password, hostname) are ignored — set them in the Nix config.
- **Convert a running VM in place** — the important one for Skynet's existing hosts. **`nixos-anywhere`** is the mature route: it kexecs the target into a RAM-only NixOS installer, uses **disko** to partition/format, and installs your config over SSH — the original OS is no longer running when it works, which is far safer than editing a live system ([nixos-anywhere repo](https://github.com/nix-community/nixos-anywhere); [Simon Shine](https://simonshine.dk/articles/nixos-anywhere-on-hetzner/)). `nixos-infect` also exists but is explicitly "surgery on a running patient" and fragile — avoid for anything we care about. **Gotchas:** disko wipes disks (destructive by design — snapshot/backup first); need a hardware profile matching the PVE virtio disk/NIC; it's a *reprovision*, not an upgrade, so treat the VM as rebuilt-from-git.

## 3. Fleet deployment: colmena vs deploy-rs vs nixos-anywhere

These solve different phases — pair them, don't pick one for everything.
- **nixos-anywhere** = *bare-metal / first provisioning* (Linux→NixOS). Not a day-2 fleet tool. Hosts can appear in both `nixosConfigurations` (for nixos-anywhere) and a deployer's output.
- **colmena** ([repo](https://github.com/nix-community/colmena), [manual](https://colmena.cli.rs/unstable/)) — *stateless*, flake-first, tag-based parallel push; builds *on the remote* to save bandwidth. Simple mental model, no state file. Weaker automatic post-deploy rollback story.
- **deploy-rs** ([Serokell](https://serokell.io/blog/deploy-rs), [README](https://github.com/serokell/deploy-rs/blob/master/README.md)) — same push idea but with **magic rollback**: after activation it drops a canary and reconnects; if it can't confirm the host in ~30s it auto-reverts the profile. Plus `autoRollback` on failed activation and per-profile health checks. For an **LLM operator this is the decisive feature** — a bad config that kills SSH self-heals instead of bricking the box. Caveat: magic rollback only works if the prior generation was also deploy-rs-deployed; neither colmena nor deploy-rs handles password-protected SSH keys well (use key files / agent). NixOps is legacy/stateful — skip.

**Fit for Skynet:** `nixos-anywhere` to convert/provision, **deploy-rs** for day-2 pushes precisely because auto-rollback shrinks the LLM's blast radius.

## 4. Secrets: sops-nix vs agenix

Both decrypt at boot to a **tmpfs** (`/run/secrets` or `/run/agenix`), so plaintext never hits disk and never lands in the **world-readable `/nix/store`** — the caveat both exist to solve ([NixOS wiki: secret schemes](https://wiki.nixos.org/wiki/Comparison_of_secret_managing_schemes)). Skynet already runs **sops + age**, which is decisive: **sops-nix** rides that setup directly — same `.sops.yaml`, and it can decrypt using the host **SSH host key** as an age identity (`sops.age.sshKeyPaths`), elegant for machines ([Stapelberg 2025](https://michael.stapelberg.ch/posts/2025-08-24-secret-management-with-sops-nix/); [Discourse overview](https://discourse.nixos.org/t/handling-secrets-in-nixos-an-overview-git-crypt-agenix-sops-nix-and-when-to-use-them/35462)). agenix is simpler (one `.age` file per secret) but is its own format and would fork our tooling; it also re-encrypts every affected secret on host/key changes. **Recommend sops-nix** — one secrets format across the whole lab.

## 5. Impermanence ("erase your darlings")

Root on **tmpfs** (or wiped from a ZFS snapshot) each boot; only `/boot`, `/nix`, and explicitly-declared persist paths survive ([impermanence repo](https://github.com/nix-community/impermanence); [wiki](https://wiki.nixos.org/wiki/Impermanence)). Security upside is real and on-theme for a Judgement-Day posture: **it defeats attacker persistence** — anything an intruder drops outside declared paths vanishes on reboot. But it's advanced: you must enumerate *every* stateful path (SSH host keys, machine-id, container data, logs) or lose it; RAM-root risks OOM/disk-full. **Verdict: not in the first pilot.** Note it as a phase-2 hardening goal once the persist set is understood.

## 6. Docker / compose + Arcane on NixOS

No rewrite required. Enable `virtualisation.docker.enable = true;` and the existing compose stacks + Arcane GitOps run **unchanged** — NixOS only manages the daemon, not the workloads. `virtualisation.oci-containers` (with `compose2nix` to convert) is an *optional* alternative that makes containers declarative NixOS units, but it would duplicate what Arcane already owns and **break our GitOps loop** ([NixOS wiki: Docker](https://wiki.nixos.org/wiki/Docker/en); [compose2nix via Discourse](https://discourse.nixos.org/t/docker-compose-oci-container-how-to-migrate-docker-compose-sections/40657)). Keep the split clean: **NixOS owns the host, Arcane owns the services.**

## 7. Honest tradeoffs & the LLM risk profile

**For:** host becomes a reviewable git artifact; atomic generation rollback; "rebuild from git" disaster recovery becomes literal; kills config drift. **Against / risk:** Nix's error surface is exactly where an LLM stalls — opaque traces, packaging detours, and a docs corpus that rewards human intuition over an agent's pattern-matching. Branching factor goes *up* before it goes down. The mitigations that make it operable — pin stable nixpkgs, keep configs boring, `oci-containers`-free (let Arcane run services), `nixos-rebuild build` in CI, and **deploy-rs magic rollback** so a bad push self-reverts — are all things we'd have to actually enforce, not hope for.

## Recommended shape for Skynet (pilot on the ops VM?)

**Yes — pilot on the ops VM, and only there, first.** It's the lowest-blast-radius host (agent's own box, no tenant services), so a botched rebuild hurts nobody but the agent, and it forces us to learn `nixos-anywhere` conversion, sops-nix, and deploy-rs on a target we can afford to rebuild. Concrete pilot:
1. Snapshot the ops VM; convert a *clone* with **nixos-anywhere** + disko (destructive — clone, don't gamble the original).
2. Minimal flake pinned to stable nixpkgs; **sops-nix** wired to our existing age keys via the host SSH key; **docker enabled**, services still Arcane's.
3. Day-2 pushes via **deploy-rs** (magic rollback on) behind the normal PR→merge gate.
4. **Defer impermanence** and any workload-host Nix migration to a later phase, decided only after the ops VM has run on Nix long enough to prove the LLM can operate it without stalling.

Gate the workload-host decision on that evidence. If the agent repeatedly stalls on Nix errors during the pilot, the correct answer is to stop at the ops VM (or back out entirely) — the reproducibility win doesn't pay for a host layer the operator can't reliably drive.
