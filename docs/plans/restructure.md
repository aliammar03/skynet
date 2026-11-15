# Restructure: one layout, no build plan

**Goal**
- The build is over, so `skynetv2.md` goes. What's still true in it gets a home an agent finds by
  path; the build's steps stay in git history.
- One rule per kind of thing: a machine is one folder, a stack is one folder, a decision is one
  file, a procedure is one file, a project in flight is one file.
- New work has a fixed route from idea to done, with no phases.
- Established conventions only (below). Nothing here is deployed differently.

**Why now:** no agent PR is open, and P6's next PR (the merges) adds scripts, CI checks and code-owner
paths that should land in the final layout, not be moved after.

## Decided (Ali, 2026-11-15)

| Question | Answer |
|---|---|
| The build steps in `skynetv2.md` | Deleted from `main` once every still-true fact has a home. Git keeps them; `README.md` names the last commit with the file |
| Work that takes several PRs | `docs/plans/<slug>.md`: the agent PRs the plan, Ali's merge approves it, the closing PR deletes it |
| Machines | `hosts/<name>/` for every machine git configures, NixOS or not, its secrets beside it |
| Comics, the arena | Stay as stacks. Platform docs stop describing them; each keeps its README |
| P7 | Not done. It becomes `docs/plans/retire-v1.md` |
| Unscheduled ideas | GitHub Issues, one each |
| Ali's review (code owner) | `docs/decisions/` and `docs/plans/`, with what is guarded today apart from `skynetv2.md` (the root `AGENTS.md` and `CLAUDE.md`, `.claude/`, `.mcp.json`, `.github/`, P6's gates and aliases). Reference pages, READMEs and runbooks are the agent's to keep current |
| The Glue budget | The table goes. Rule 6 stays, and a new program of our own needs a decision record naming the mature tools ruled out |

## Conventions adopted

| For | Convention | Here |
|---|---|---|
| Decisions | [MADR 4.0](https://adr.github.io/madr/): `docs/decisions/NNNN-title-with-dashes.md`, a `status` that a later record supersedes | D1–D18 become `0001`–`0018`, same numbers; `D11` in a comment becomes `ADR-0011` |
| The agent's contract | [AGENTS.md](https://agents.md/): one root file; the nearest one to a file wins | Root only: the rules and a map. The folder contracts are READMEs, so any tool and any reader finds them |
| Nix | The flake folders most configs use and [blueprint](https://numtide.github.io/blueprint/main/getting-started/folder_structure) names: `hosts/`, `modules/`, `packages/` | The names only, not the library |
| Secrets | sops: every encrypted file is `<what>.sops.<ext>`, beside what reads it | Hosts as stacks already do |
| Backlog | GitHub Issues | The phases' Open lists |
| Titles | `<area>: <sentence>`, as nixpkgs and the kernel do | Area = the plan's slug, else the stack, host or top folder. Branch `<area>/<slug>` |

## Layout

```
skynet/
├ AGENTS.md  CLAUDE.md  README.md
├ flake.nix  flake.lock
├ hosts/README.md            the host contract: addressing, NICs, keys, install
├ hosts/<machine>/           every machine git configures, with its README.md and *.sops.yaml
│   ops · docker-admin · docker-dmz · technitium-core · technitium-network   (NixOS:
│       default.nix · net.nix · disk.nix · hardware.nix · proxmox.sh · ssh_host.pub)
│   pbs · pve · unraid       (not NixOS: setup.sh · etc/ · what Ali installs)
├ modules/                   NixOS modules, and the data they import
├ packages/<name>/           our own programs a host runs, one folder each
├ stacks/README.md           the stack contract: folder, routing, auth modes, data, networks
├ stacks/<target>/<stack>/   compose.yaml · *.sops.* · README.md · its own config and code
├ dns/                       the zone and Technitium's settings
├ runbooks/<job>.md          procedures, one file each
├ docs/README.md             index
├ docs/lab.md                the lab on one page: nodes, VLANs, every guest (ours and Ali's), change flow
├ docs/credentials.md        who holds what
├ docs/decisions/NNNN-*.md   decision records
├ docs/plans/<slug>.md       projects in flight; empty when nothing is
└ .doco-cd.<target>.yml  .sops.yaml  renovate.json  .mcp.json  .claude/  .github/
```

What moves:

| Now | Then |
|---|---|
| `pbs/`, `pve/`, `unraid/` | `hosts/pbs/`, `hosts/pve/`, `hosts/unraid/` |
| `secrets/<host>.yaml` | `hosts/<host>/secret.sops.yaml` |
| `secrets/<host>.oidc.yaml`, `secrets/ops.komga.yaml`, `secrets/ops.uchiyomi.yaml` | `hosts/<host>/oidc.sops.yaml`, `hosts/ops/komga.sops.yaml`, `hosts/ops/uchiyomi.sops.yaml` |
| `modules/skynet-restore.sh`, `technitium-sync.sh`, `technitium-stats.sh` | `packages/<name>/`, each also a flake package (`nix build .#<name>` runs shellcheck) |
| `runbooks/dns-speed-test/` (a runbook, a 450-line tool and its config) | `runbooks/dns-speed-test.md` and `packages/dnsbench/` |
| P6's planned `opnsense/`, `modules/window/` | `hosts/opnsense/`, `packages/skynet-*/`; `infra/proxmox/` as planned (it spans both nodes) |

`stacks/`, `dns/`, `runbooks/` and the root dotfiles stay where they are: doco-cd, the DNS sync and
the unattended runs read them by path.

`skynetv2.md`'s sections:

| Section | Goes to |
|---|---|
| How to use, Rules | `AGENTS.md` (there already; reworded for a lab without phases) |
| Status | Gone |
| Target state, Lab facts | `docs/lab.md` |
| Decisions | `docs/decisions/` |
| Repo layout | `AGENTS.md` → Map |
| Conventions → Stack folder | `stacks/README.md` |
| Conventions → Hosts and git | `hosts/README.md`; the git flow to `AGENTS.md` |
| Credentials ledger | `docs/credentials.md` |
| P0–P5, P8 | Read against the READMEs. What is still true and written nowhere else moves to the README of the host or stack it describes; the PR lists each move. The rest is history |
| P6 | Built parts: the READMEs. What's left (steps 5–10 with their design, exit criteria, Open): `docs/plans/autonomy.md` |
| P7 | `docs/plans/retire-v1.md` |
| Every Open list | GitHub issues |
| Glue budget | Gone |

## How work happens afterwards

| Ali wants | It starts as | What lands |
|---|---|---|
| An idea kept for later | A GitHub issue | Nothing in git |
| A new app | `runbooks/new-stack.md` | One PR: the stack folder, its route, its Gatus row |
| A new machine | `runbooks/new-vm.md` | One PR: `hosts/<name>/` |
| A stack or machine gone | `runbooks/retire.md` (new) | One PR: its folder, route, row, records and `docs/lab.md` line removed. Destroying the guest or its data stays Ali's |
| A decision changed (a tool, a lane, what is trusted) | A decision record | `docs/decisions/NNNN-*.md`, superseding the old one |
| Anything taking several PRs | `docs/plans/<slug>.md` | The plan PR; after Ali merges it, its PRs; the last one deletes the plan and leaves the truth in READMEs and decisions |

`AGENTS.md` changes to match: branches are `<area>/<slug>`; the hard checkpoint "leaving the current
phase's scope" becomes "work of several PRs without a merged plan, or against a decision without a
new record"; rule 6 loses the budget and gains the decision record.

**Example: Home Assistant into Skynet, the HAOS VM retired.**
1. An issue holds the idea until Ali says go.
2. Plan PR, `docs/plans/homeassistant.md`: what HAOS does today (add-ons, radios, VLAN 30), the
   options, the steps, the cutover and the way back. Its decision (a stack on a Docker host, or an
   HAOS VM that Skynet provisions and backs up as `hosts/haos/`) is a decision record in the same
   PR. Ali's merge approves both.
3. The work, each PR a runbook: `new-vm.md` if it needs a host on VLAN 30, `new-stack.md` for
   `stacks/<target>/homeassistant/` (its route exists: `caddy-apps/conf/sites/homeassistant.conf`),
   the data moved as the plan says.
4. `retire.md` for VM 3050: its records and `docs/lab.md` line go in a PR; Ali destroys the VM.
5. The closing PR deletes the plan; the issue closes.

## PRs and order

1. **This plan**, with the code-owner lines for `docs/plans/` and `docs/decisions/`.
2. **Docs:** `skynetv2.md` split as above and deleted; `AGENTS.md`, `README.md`, `CODEOWNERS`; every
   reference to the plan repointed (98, in 78 files) and the phase tags removed; the Open lists
   filed as issues. Comments change in files that hosts and stacks read; nothing they do changes.
3. **Moves:** the folders and files in "What moves", `.sops.yaml`'s rules, the Nix paths, PBS's drift
   check. Proof in the PR: each host's system built before and after, differing only in the moved
   paths; every moved sops file still opens with its host's key. A moved file keeps its recipients,
   so there is no `updatekeys` and no step for Ali.
4. **Crud and checks:** stack READMEs to the contract's labels, in its order; dated attributions out
   of READMEs and comments (what they record is in a decision or git); `runbooks/retire.md`; CI: every
   stack has `compose.yaml` and `README.md`, every host a `README.md`, every `*.sops.*` file is
   encrypted, relative links resolve (lychee, offline). For Ali, as exact commands in that PR: the
   merged remote branches deleted (about 185 today), auto-delete of merged branches turned on, and
   which of ops's old worktrees go.

P6 continues after PR 3, from `docs/plans/autonomy.md`.

## Exit criteria

- `git grep -E 'skynetv2|\bP[0-8]\b'` finds nothing outside `docs/plans/`.
- Every machine git configures has `hosts/<name>/README.md`; no secret file sits outside the folder
  of the host or stack that reads it, `secrets/shared/` apart (P6).
- CI fails a stack without its files, an unencrypted `*.sops.*` file and a dead relative link.
- A fresh session, given "add app X" or "retire machine Y", reaches the right runbook from
  `AGENTS.md` in one hop.
- This file is deleted.

**Open:**
- Only the root `AGENTS.md` and `CLAUDE.md` are code-owned today. Claude Code also reads a
  `CLAUDE.md` in any folder it works in, so one added deeper would instruct the agent without Ali's
  review. Guarding both names at any depth closes that; it also puts the comics agent's contract
  (`stacks/dmz/comics-agent/agent/AGENTS.md`) under his review. Ali's call, in PR 2.
