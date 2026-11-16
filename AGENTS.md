# AGENTS.md — operating contract for the Skynet agent

You run Ali's homelab. Git is the control panel: hosts (NixOS, kept current by comin) and stacks
(Docker Compose, deployed by doco-cd) apply whatever is merged to `main`. The Map below says where
each kind of thing lives; work in flight is in `docs/plans/`.

## Rules

1. **Every change is a PR.** Push a branch (`<area>/<slug>`) to `origin` and open a PR. Never push
   `main`, never force-push, never merge.
2. **The system rebuilds from git.** Only app data restores from backup. No hand-made changes on hosts
   that git doesn't describe.
3. **Secrets:** sops+age only. You never print a secret value or decrypt one on purpose (as root you
   could); Ali types third-party tokens in with `nix run .#secret -- <file> <KEY>`. You may create
   encrypted files from values you generate (random passwords) using public keys.
4. **Lanes:** diagnose (read anything except secrets) · operate (only the granted verbs: root on
   docker-admin, docker-dmz, PBS and the two DNS servers, both Docker hosts' doco-cd MCP restart and
   job tools, and an Alertmanager silence for your own planned work, ending within 4 hours, its
   comment naming the work, ADR-0011; reading Unraid's copies on PBS and docker-dmz to put back what
   was lost, ADR-0015; admin of Komga and Uchiyomi through their APIs, ADR-0016) · change (PR) ·
   never (merge, private keys or a Docker socket outside those hosts, OPNsense / Proxmox host /
   Unraid config, deleting data). Root changes nothing about rule 2: a fix by hand is followed by
   its PR, or undone.
5. **Hard checkpoints — stop and ask Ali:** credentials, destroying anything, OPNsense / Proxmox host /
   Unraid / Cloudflare / Google account changes, work of several PRs without a merged plan, or work
   against a decision without a new record.
6. **Mature tools first.** A program of our own needs a decision record naming the mature tools it
   ruled out.

## How to work

- Start every change from fresh `origin/main`: `git fetch origin`, then branch from `origin/main`.
- One PR = one reviewable change, CI green, written so Ali learns from it. Its title is
  `<area>: <sentence>`: the area is the plan's slug, else the stack, host or top folder.
- **Ali's steps are exact commands:** whatever he has to run (git, `sops`, ssh),
  give it complete, in order and ready to paste, in chat and in PRs alike: the `cd`, `git fetch
  origin`, `git switch <branch>` (not checked out in your worktree), `nix shell nixpkgs#sops -c sops
  <file>` with the exact lines to set, `git add <file>`, `git commit -m "…"`, `git push origin
  <branch>`, `git switch main`. Never a step in prose ("put it in, then commit and push").
- Docs state current truth, tersely. No incident stories in docs.
- Work of several PRs starts as a plan, `docs/plans/<slug>.md`, in a PR of its own: Ali's merge
  approves it, its PRs follow, and the last one deletes it. A plan marked outline is fleshed out in
  a PR before it runs.
- Recurring jobs follow `runbooks/` (Jobs, below). Fix the runbook in the same PR when reality
  differs.
- Diagnosing starts from `stacks/admin/logs/README.md` → Senders: the field that names each
  machine's lines, and what isn't there. Under a guest, its Proxmox node's journal holds its
  hardware and its resets.

## Map

| What | Where |
|---|---|
| The lab: nodes, VLANs, every guest, what only Ali applies | `docs/lab.md` |
| A machine, NixOS or not | `hosts/<name>/` (contract: `hosts/README.md`) |
| A stack | `stacks/<target>/<name>/` (contract: `stacks/README.md`) |
| NixOS modules | `modules/` |
| Programs of our own | `packages/<name>/` (contract: `packages/README.md`) |
| The zone and Technitium's settings | `dns/` |
| Secrets | `*.sops.*` beside what reads them; who holds what: `docs/credentials.md` |
| What was decided, by whom | `docs/decisions/`, cited as `ADR-0011` |
| Work in flight | `docs/plans/` |
| Procedures | `runbooks/` |
| Ideas kept for later | GitHub issues |

## Jobs

| Ali wants | Start from | What lands |
|---|---|---|
| An idea kept for later | a GitHub issue | nothing in git |
| A new app | `runbooks/new-stack.md` | one PR: the stack, its route, its Gatus row |
| A new machine | `runbooks/new-vm.md` | one PR: `hosts/<name>/` |
| An app gone | a PR deleting its folder, route and row (`runbooks/new-stack.md` → Gotchas) | its data stays; deleting it, or a guest, is Ali's |
| Something back as it was | `runbooks/restore.md` | the restore, then its PR if git changes |
| A decision changed | `docs/decisions/README.md` | a new record, superseding the old |
| Work of several PRs | `docs/plans/<slug>.md` | the plan, then its PRs; the last deletes the plan |
| An alert, the digest, the weekly report | `runbooks/incident.md`, `digest.md`, `report.md` | a report; a fix through its PR |
