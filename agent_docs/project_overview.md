# Project Overview

## Authority boundary

This is compact derived agent memory. The constitution, runtime/configuration, current design and
operational documents, active directives, and accepted evidence outrank it; repair this file when it
drifts. It does not define infrastructure authority or replace `docs/system-design.md`.

## Purpose

Skynet is the rebuildable operations repository and runtime for `vm-skynet-ops` (VMID 9090). It
declares infrastructure, service deployment, access boundaries, observability, recovery procedures,
and the Python operations engine so an agent can safely operate the lab through reviewable changes.

## Scope

The repository covers NixOS hosts and modules, Proxmox/PBS envelopes, Docker services, DNS, firewall
and network observations, identity/proxy publication, backups, secrets, runbooks, planning, tests,
and episodic evidence. The current trust boundary is T1 read, scoped T2 operation, time-limited T2+
root grants, and never-standing T3 access; a construction worker has no production authority.

## Architecture

- Git is operational truth. Declarative Nix, OpenTofu, Compose, Caddy, encrypted secrets, policy,
  inventory, and documentation rebuild from the repository; backups restore payload after the system
  stands.
- The installable Python package under `src/skynet/` provides the CLI and bounded collectors. Existing
  Bash procedures, Nix modules, OpenTofu, and Compose retain their declared roles.
- Arcane reconciles merged Compose changes through Git Sync. Health is verified through the scoped
  read paths and inventory is refreshed by machine-owned collectors/renderers.
- The generated digest is optional recent-activity/episodic/open-thread retrieval and the context map
  is on-demand load-cost routing; neither replaces `agent_docs/` continuity or authoritative sources.
- Construction is a native Main-directed Light/Medium/Heavy worker swarm. Main owns decisions and
  acceptance; bounded workers own assigned context, implementation, verification, or documentation.
  `agent_docs/` is compact cross-session memory, not a second infrastructure truth system.

## Main workflows

1. A change is authored on a branch, reviewed in one PR, human-merged, and reconciled by its owning
   subsystem. Git revert is the normal rollback for GitOps changes.
2. A production OpenTofu write is created from an approved revision, inspected as one saved plan,
   and executed through `scripts/tofu-apply.sh` with one declared actuator scope.
3. T1 collectors gather validated observations, publish atomically, and render machine-owned views;
   generated output is never hand-edited.
4. A substantive construction session begins with `agent_docs/` plus its active directive, routes
   evidence to bounded workers, performs independent checks, and leaves a compact handoff.

## Major current decisions

- Autonomy is earned per capability on the A0–A5 ladder; irreversible actions and T3 work remain
  hard checkpoints. Authored changes are human-merged; only the nightly's generated-only green PRs
  may auto-merge.
- The agent never widens its own leash. Secrets remain encrypted in Git or restrictive local files;
  root access is certificate-grant-only; generated directories are machine-owned.
- SKY-026 is the current construction contract and completely supersedes SKY-022. Its six `agent_docs`
  files are distilled memory with explicit Main/Archivist ownership and higher-authority conflict
  handling.
