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
and network observations, identity/proxy publication, backups, secrets, runbooks, planning,
and episodic evidence. The current trust boundary is T1 read, scoped T2 operation, time-limited T2+
root grants, and never-standing T3 access; a construction worker has no production authority.

## Architecture

- Git is operational truth. Declarative Nix, OpenTofu, Compose, Caddy, encrypted secrets, policy,
  inventory, and documentation rebuild from the repository; backups restore payload after the system
  stands.
- The installable Python package under `src/skynet/` provides the CLI, bounded collectors, factual
  and derived Markdown renderers, and read-time recall. Legacy render and recall shell commands are
  compatibility forwarders; Bash procedures, Nix modules, OpenTofu, and Compose retain their other
  declared roles.
- The packaged entity spine derives and audits guest, service, node, vhost, and network identities
  from authored conventions and observations; route resolution uses the same entity functions. The
  packaged cache/query module builds a disposable, validated 14-table SQLite projection for SQL
  views and ad-hoc queries; it is never authority.
- Arcane reconciles Compose projects through Git Sync. `skynet deploy service` is the packaged
  source/environment activation owner: it reports the exact selected branch head and normalized
  repository, binds Compose/environment bytes and executable modes to that revision, requires one
  existing unique sync/project with `autoSync=false`, installs `.env` by stdin-only SSH and atomic
  `0600` replacement before branch repoint/manual sync, then requires complete runtime health. Arcane
  manual sync may redeploy a running project; scheduled sync stays disabled. `--no-deploy` prepares
  environment only. A legacy auto-sync service must be migrated and quiesced while old source and
  environment still agree under the deploy runbook's timed migration check. Its opt-in `--gate` runs
  the separate report-only P10 verifier for exact revision and DMZ/TLS routes. A live deploy plus
  gate has passed for `librespeed`; PR #259 still
  awaits fresh review. `skynet rollback service` is report-only by default and can prepare an
  isolated reviewed inverse; neither path auto-rolls back. The old shell names are temporary
  compatibility forwarders for P22.
- The generated digest is optional recent-activity/episodic/open-thread retrieval and the context map
  is on-demand load-cost routing; packaged rendering also owns factual pages and the runbook catalog.
  Read-time recall ranks canonical Markdown sources. None replaces `agent_docs/` continuity or
  authoritative sources.
- Construction is a native Main-directed Light/Medium/Heavy worker swarm. Main owns internal
  implementation acceptance and PR readiness. External final acceptance belongs only to a fresh
  reviewer manually started by Ali. The reviewer resolves/rechecks target/base SHA + PR-head SHA and,
  on ACCEPT, posts a machine-readable acceptance marker to the PR conversation. Ali never shuttles
  hashes. Ali then tells the original implementation/fix session only `accepted`; Main validates the
  marker and performs bounded closeout on that **same PR before one human merge**. Post-ACCEPT changes
  are restricted to directive/archive/planning state, Main-owned deployment-state `agent_docs`, journal
  closure evidence, and generator-owned closure views. Any substantive post-ACCEPT change, unexplained
  head movement, or reviewed-base movement requires fresh review. Private GitHub Free leaves a final
  recheck-to-merge race window and does not provide an atomic merge-time guarantee.
- `agent_docs/` is compact cross-session memory, not a second infrastructure truth system.

## Main workflows

1. A normal authored change uses one PR: implementation → fresh review → ACCEPT marker → same-PR
   bounded closeout → one human merge. Git revert is the normal rollback for GitOps changes.
2. After a merged Compose revision, `skynet deploy service <service>` resolves the selected local
   branch head, reconciles Arcane and complete runtime health, and optionally runs the separate
   report-only P10 gate; recovery uses `skynet rollback service <service> <deploy-commit> --prepare`
   with a separate authored commit identity and neither path auto-rolls back.
3. A production OpenTofu write is created from an approved revision, inspected as one saved plan,
   and executed through `scripts/tofu-apply.sh` with one declared actuator scope.
4. T1 collectors gather validated observations; freshness-gated factual rendering stages and safely
   replaces the machine-owned page set. Generated output is never hand-edited.
5. A substantive construction session begins with `agent_docs/` plus its active directive, routes
   evidence to bounded workers, performs independent checks, and stops after publishing its open PR.
   Review runs separately; accepted closeout returns to the original session and stays on the same PR.

## Major current decisions

- Autonomy is earned per capability on the A0–A5 ladder; irreversible actions and T3 work remain hard
  checkpoints. GitHub CI and automated tests are embargoed during SKY-025, so every PR is human-merged
  and no A4 capability is active.
- The agent never widens its own leash. Secrets remain encrypted in Git or restrictive local files;
  root access is certificate-grant-only; generated directories are machine-owned.
- The six `agent_docs/` files are distilled memory with explicit Main/Archivist ownership and
  higher-authority conflict handling.
