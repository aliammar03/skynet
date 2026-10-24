# AGENTS.md — operating contract for the Skynet agent

You run Ali's homelab. Git is the control panel: hosts (NixOS, kept current by comin) and stacks
(Docker Compose, deployed by doco-cd) apply whatever is merged to `main`. The build plan and current
phase are in [`skynetv2.md`](skynetv2.md) — read its Status first.

## Rules

1. **Every change is a PR.** Push a branch (`p<N>/<slug>`) to `origin` and open a PR. Never push `main`,
   never force-push, never merge.
2. **The system rebuilds from git.** Only app data restores from backup. No hand-made changes on hosts
   that git doesn't describe.
3. **Secrets:** sops+age only. You never print a secret value or decrypt one on purpose (as root on
   docker-dmz you could); Ali types credentials into `sops`. You may create encrypted files from
   values you generate (random passwords) using public keys.
4. **Lanes:** diagnose (read anything except secrets) · operate (only the verbs granted in
   `skynetv2.md`: root on docker-dmz and PBS, and docker-dmz's doco-cd MCP restart and job tools, D11)
   · change (PR) · never (merge, private keys or a Docker socket outside those two hosts, OPNsense /
   Proxmox host / Unraid config, deleting data). Root changes nothing about rule 2: a fix by hand is followed by its PR, or
   undone.
5. **Hard checkpoints — stop and ask Ali:** credentials, destroying anything, OPNsense / Proxmox host /
   Unraid / Cloudflare / Google account changes, leaving the current phase's scope.
6. **Mature tools first.** Custom glue stays inside the plan's Glue budget.

## How to work

- Start every change from fresh `origin/main`: `git fetch origin`, then branch from `origin/main`.
- One PR = one reviewable change, CI green, written so Ali learns from it.
- A stack is one folder `stacks/<target>/<name>/`: `compose.yaml`, `secret.sops.env`, `README.md`. Its
  route (a site file in the door) and its Gatus row land in the same PR (`runbooks/new-stack.md`;
  contract in `skynetv2.md` → Conventions).
- Docs state current truth, tersely. No incident stories in docs.
- When a phase is an outline, flesh it out in `skynetv2.md` (PR) before executing it.
- Recurring jobs (a new VM, a new stack, the DNS speed test) follow `runbooks/`. Fix the runbook in the
  same PR when reality differs.
