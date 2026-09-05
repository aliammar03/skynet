---
date: 2026-09-06
time: 01:39:17
kind: session
title: SKY-023 final independent close-out audit — reopened
tier_touched: [T1]
grants: []
refs: [SKY-023, PR #202]
thread_status: open
---

# 2026-09-06 · session · SKY-023 final independent close-out audit — reopened

<!-- RAW EPISODE. Preserve concrete audit evidence here. Current-state fixes belong in their owning
     live files; do not rewrite older journal/history entries to make the repository look clean. -->

## What happened

Performed an independent close-out review from current `main` at merge commit
`f6bd03e6269df303681f1e45cd822dd70f8e6090` without accepting prior phase-complete claims as proof.
Read `AGENTS.md`, authoritative `docs/system-design.md`, the full SKY-023 directive, the current
planning lifecycle, the runbook catalog and representative deploy/provision/restore procedures, the
hygiene/drift gates, CI/pre-commit wiring, and the retained migration/compatibility candidates.

No repository-backed `[[SKY-023-progress]]` file exists; the journal and directive remain the durable
repository evidence. No infrastructure command, credential access, T2 write, root grant, firewall
change, or autonomy change was used by this audit.

The verdict is **NOT READY**. SKY-023 had already been archived by PR #202, but the live tree still
contains temporal archaeology that its own deterministic gate does not detect, and a proof-only
`deploy.nodes.lxc-proof` target still points at the old proof address with no current operational
consumer found. The directive is therefore reopened at one bounded Phase 10 rather than being accepted
as complete.

## Blocking findings

| Path / surface | Current evidence | Desired end state | Exact next action |
|---|---|---|---|
| `tests/temporal-hygiene-test.sh`, `.githooks/pre-commit`, `.github/workflows/checks.yml`, `.github/workflows/nix.yml` | The temporal scanner omits `.githooks/` and `.github/workflows/`; those omitted live gate files contain concrete completed directive/phase provenance. The narrative regex also misses demonstrated forms such as `replaces`, `historically`, Before/After migration narration, and proof wording. | CI/pre-commit wiring is part of the current operational surface and the gate rejects the actual regression classes without broad false positives. | Add hooks/workflows to the current-surface scan, purge their provenance comments, add focused negative fixtures for the demonstrated false-negative wording, and manually review remaining hits. |
| `bin/ops`, `hosts/lxc-proof/default.nix`, `compose/obsidian-livesync/local.ini`, `nix/modules/ops-user.nix`, `docs/conventions/docs.md`, `README.md`, `scripts/cf-dns-route.sh` | Live current-state files still contain replacement stories, proof/phase narration, historical anecdotes, or rehearsal chronology. `hosts/lxc-proof/default.nix` also names stale `hosts/lxc-adguard-network/`. | Current files state present behavior, safety/compatibility rationale, verification and rollback only. | Rewrite the named passages as timeless present constraints; move no historical evidence into other current files. Preserve functional behavior. |
| `flake.nix` `deploy.nodes.lxc-proof` | The deploy node targets `10.10.90.99`; no current guest, runbook, or non-history caller for that proof target was found. The current OpenTofu CT declarations consume only the uploaded template filename `local:vztmpl/nixos-lxc-proof-26.05.tar.xz`. | Keep the template builder/name while it has a current provisioning consumer, but remove proof-only day-two deployment machinery with no live target. | Remove `deploy.nodes.lxc-proof` unless a current non-history consumer is demonstrated. Retain `nixosConfigurations.lxc-proof`, `lxc-proof-tarball`, and the current template filename; remove proof-only marker/package if it has no bootstrap purpose. Do not rename or mutate the live template in this phase. |

## Validation evidence

Freshly re-ran the GitHub Actions `checks` workflow against PR #202 head commit
`203e6cb5628c19cc2432150b4c15fc8fe9ec2c50`, whose tree is identical to current `main` tree
`20ec6a1ab2c561f87ab52e75872d89e0880e72f8`. Both jobs completed successfully. The deterministic
job reported success for entity, digest, DNS rollback, compose rollback, certificate selection,
OpenTofu rollback, PVE snapshot, provisioning truth, PBS collection, construction, agent, gitignore,
Obsidian hygiene, nightly automerge, nightly sequence, documentation drift, temporal hygiene, and
hygiene tests; the hard-law invariant job also passed.

That green result is not sufficient close-out evidence because manual inspection found inputs the
current temporal gate does not scan and phrases it does not match. The false positive of "all green"
against an observably dirty corpus is itself a blocker for Phase 8/9 acceptance.

Targeted repository searches/manual review covered concrete `SKY-[0-9]{3}` provenance, `historically`,
`earlier`, `removed`, Before/After narration, proof wording, `envsync.sh`, `collect-firewall.sh`,
`cf-dns-route.sh`, `lxc-proof`, `10.10.90.99`, and stale planning/project paths. Every relevant hit was
classified rather than treating zero regex hits as proof.

The connector-only audit did not independently execute a local `bash -n` sweep or
`nix flake check --no-write-lock-file`; prior phase/PR claims about local Nix validation were not used
as independent evidence. Phase 10 must run those checks along with the complete pre-commit-equivalent
suite after the fixes, then repeat the manual corpus review.

## Intentional compatibility retained

- `scripts/collect-firewall.sh`: keep as the explicit offline/DR parser of the git-mirrored OPNsense
  configuration; the live API collector remains the normal T1 path.
- `scripts/cf-dns-route.sh`: keep behavior as the Cloudflare DNS break-glass/immediate executor and
  explicit delete checkpoint because the saved-plan OpenTofu wrapper refuses delete plans; rewrite
  only temporal wording.
- OpenTofu `moved` blocks and imported-CT `ignore_changes`: keep because they preserve current state
  addresses/provider round-trip compatibility.
- `lxc-proof` template artifact/name: keep while `tofu/pool-cts.tf` consumes
  `local:vztmpl/nixos-lxc-proof-26.05.tar.xz`; this does not justify the dead proof deploy node.
- `envsync.sh`: remains deleted; no current steady-state or recovery consumer was found.
- History in `journal/`, `planning/archive/`, `docs/history/`, ADR history, and generated evidence is
  intentionally not rewritten for hygiene.

## Cold-agent usability / authority review

A cold agent can route from `README.md` → `AGENTS.md` / `docs/system-design.md` → `runbooks/README.md`
without loading archived project history. The catalog exposes deploy, VM/LXC provision, publish,
restore, backup, nightly and DR leaves; `runbooks/provision-lxc.md` states the saved-plan OpenTofu
model and current `svc-ops@pve!operate` identity; `README.md` exposes `bin/ops hygiene`; documentation
conventions state that history belongs in history-bearing files.

No authority drift was found in the audited SKY-023 close-out changes: the current design still keeps
human merge for authored changes, generated-only nightly as the narrow self-merge exception, no
standing T3, the existing root-grant boundary, saved-plan OpenTofu/delete refusal, current firewall
boundary, and current recovery guarantees. The blockers are maintenance-hygiene/dead-proof-path
failures, not a reason to change those boundaries.

## Follow-ups / open threads

Continue SKY-023 at Phase 10. Read `AGENTS.md`, `docs/system-design.md`, and
`planning/projects/SKY-023-eliminate-documentation-drift-and-shrink-operational-context.md` in full.
Reproduce the independent audit findings against current HEAD, execute Phase 10 only, preserve all
retained compatibility and authority boundaries, run the complete validation set named in the phase,
and archive only after a second cold review finds no blocker.
