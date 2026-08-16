# Skynet — Build Log (A1 → A6)

> How Skynet was built, from an empty VM to graduation on **2026-08-16**. This is the distilled,
> past-tense record — the readable story, PR numbers preserved. The original birth plan verbatim is
> [`deployment-plan-v5.md`](deployment-plan-v5.md); the living design that replaced it is
> [`../system-design.md`](../system-design.md).
>
> The build ran in two acts: a **human foundation** (one evening — the only time Ali pasted command
> blocks, because the agent didn't exist yet) and an **agent-led build** of six phases, each landing
> as a PR that Ali merged. That cadence was also Ali's git education, escalating from "merge a
> scaffold" to "review an infrastructure change."

## Human foundation (H0–H2 + handover)

| Phase | Work | Done |
|---|---|---|
| **H0 — Network** | OPNsense aliases, rules 360–380, `10.10.90.90` in `ROLE_ADMIN_TARGETS`, static-IP reservation | ✅ |
| **H1 — VM** | Built VM 9090 from the §1 block; agent CLI installed + authed; kill-switch drilled (`qm stop 9090`) | ✅ |
| **H2 — Seed** | Private repo `skynet` + fine-grained PAT; the plan pushed as `docs/deployment-plan.md` | ✅ |
| **Handover** | *"Read docs/deployment-plan.md and execute Appendix A."* | ✅ |

## Agent-led build

### A1 — Scaffold · PR #1
Full repo tree: `AGENTS.md` (tiers + execution policy + empty auto-approve list), `.gitignore`,
`.sops.yaml` stub, `scripts/`, `bin/ops`, `bin/grant-root`, all runbooks incl. `runbooks/dr/`,
the agent's own SSH + age keypairs (public halves committed, privates 0600 on the host).

### A2 — Credentials ceremony
All **9 checkpoints** prepared, then walked with Ali one at a time, each validated before moving on:
1. Proxmox `svc-ops` tokens on core (`10.10.50.11`) + network (`10.10.50.10`); collectors return
   JSON *(ACL-before-token bug fixed, PR #2)*.
2. Workstation CA + `gr`; a test grant signed and lapsed.
3. Arcane `X-API-Key` lists projects.
4. Technitium token (`10.10.70.50`, `ops` group), zones collected.
5. rclone → gdrive OAuth on the VM.
6. OPNsense `os-git-backup` → `skynet-opnsense`, firewall mirrored.
7. Renovate app (scan + alert), bump PRs open.
8. PBS client-side encryption, key in the kit.
9. Survival kit printed + `gr vm-docker-dmz 10m` watched to expiry.

### A3 — Truth sync + consolidation · PRs #2–#14
First `grant-root docker-dmz` onboarded the host (CA trust) and imported live compose files + env
layers. All six docker-dmz stacks moved onto the "skynet way": pinned digests, `.env.git` /
`.env.sops`, Arcane GitOps deploy via `scripts/gitops-deploy.sh`, standard volumes + `skynet.*`
labels, Renovate baseline PRs.

### A4 — Backups · witnessed restore + L5 live
- **L3 (restic, vm-docker-dmz):** repo `rclone:gdrive:Skynet/Backups/restic/docker-dmz`; first
  snapshot `f157b5ec`, `restic check` clean; nightly timer live.
- **Witness restore (aiometadata):** wiped data + mongo volume, restored from Drive, redeployed —
  all containers healthy, SQLite `integrity_check` ok, mongo fingerprint byte-identical.
- **L5 (PBS → gdrive):** PBS onboarded to the CA; nightly `skynet-pbs-gdrive` timer (04:00).
- **A4.5 — backup tooling · PR #20:** `provision-restic.sh` (any host), on-demand tagged backups, docs.

### A5 — Visibility · PRs #21, #22
`render-docs.sh` produces the full Obsidian set from `inventory/` + an LLM-authored
`05-state-of-the-lab.md`. Nightly `bin/ops nightly` (03:30, report-only) with primary → fallback →
deterministic engine chain; weekly CLI-update timer. `CLAUDE.md` imports `AGENTS.md`. **PR #22**
switched grants to per-host certs + a `Match user root` ssh_config block so grants coexist.

### A5.5 — L5 off-site reseed · PR #24, PR #29 · CLOSED GREEN
The A6 L5 drill exposed that the nightly PBS→Drive sync had been **TERM-killed at a 6h timeout
every night** — ~46% of chunks never uploaded, and nothing checked. Restoring CT 101 from Drive
failed (93/184 chunks). **PR #24** fixed it (timeout 6h→20h, unthrottled seed, `--transfers 16`,
and an `rclone check --one-way` completion guard that fails the job if the copy is incomplete). The
reseed finished under the fixed unit (5.4h, no kill), the guard passed clean (**0 differences,
39,513 files**), and the re-drill pulled CT 101's **184/184** chunks and rebuilt `root.pxar`
byte-identical to the live datastore. Off-site restore proven end-to-end.

### A6 — Graduation · 2026-08-16
**"Stop trusting, start proving."** Three drills, each of which earned its keep by surfacing a
latent gap:

1. **DR tabletop** (`DR-network-node.md`) — found the runbook named a repo that didn't exist
   (`skynet-opnsense-backup` → real `skynet-opnsense`) and that the NIC passthrough PCI IDs weren't
   in the repo. Both fixed; real IDs captured in `runbooks/dr/pci-passthrough.md` (two Intel 82576
   dual-port NICs, bus 03/04, `ovmf`/`q35`). *(PR #30)*
2. **Real encrypted-guest restore** — Ali deleted CT 101, then restored it from a fresh
   client-side-encrypted PBS backup. The agent proved the vault first (decrypt + reconstruct with
   Ali's survival-kit key → byte-identical; a negative control confirmed it's unrecoverable without
   the key); Ali then `pct restore`'d it live on the core node (node root = T3).
3. **"Update all guests" fleet run** (`update-guests.md`) under one `gr all` grant — both onboarded
   hosts snapshotted/backed-up → `apt full-upgrade` → health-verified.

**The privsep gap A6 caught.** The operate token was privilege-separated but the *user* held only
`PVEAuditor`, so `user ∩ token` stripped every write — the "operate" token could list but never
snapshot/backup (403s). Fixed: user granted `OpsOperator` on the pool, `VM.Backup` added to the
role + a `/storage/local` ACL, so **backup/snapshot became standing T2**; `bootstrap-proxmox.sh`
updated so a rebuild is correct. Blast radius unchanged. *(PR #31)*

**Findings recorded, not worked around:**
- **Datastore sizing:** `df` on the Unraid NFS share reports the whole array (~6.5 TB), not the
  datastore — use PBS's GC-log **On-Disk usage (~68 GiB)**.
- **CT 240 (PBS host)** can't be snapshotted (its NFS datastore mountpoint blocks LXC snapshots)
  and was in no backup job — protected with a one-off vzdump during the run; ongoing strategy
  tracked as **SKY-002**.
- **PBS apt repo:** on subscription-only `enterprise.proxmox.com` (harmless 401 each run) — switch
  to `pbs-no-subscription` to silence.

**Graduation.** Sign-off landed as **PR #31**. Steady state began: nightly report-only maintenance,
inventory as a living document, project work on request — every action still PR-gated / grant-gated.

---

## Epilogue

The deployment plan's job ended here. It was retired whole under **SKY-001** and replaced by the
[system-design constitution + spokes](../system-design.md). This log is what it left behind.
