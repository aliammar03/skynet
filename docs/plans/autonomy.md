# Autonomy: the agent merges, verifies and rolls back by itself

**Goal**
- Ali says "deploy X" or "restore Y to how it was yesterday" in Discord or the Claude app. The agent
  does the rest and reports.
- Updates land by themselves, majors included: reviewed, merged one at a time in a nightly window,
  each just after its own undo point, verified, and rolled back, code and data, if they break.
- A host change proves itself before it merges: activated under a timer that undoes it unless it
  verifies, so a change that cuts a host's network needs no console.
- An alert is investigated before Ali hears of it. What's in the agent's lane is fixed, verified
  and reported; the rest arrives as research, a proposal and a PR.
- The toil goes: ISOs and `proxmox.sh`, editing aliases.
- What bounds a mistake is an undo the agent can't delete, not Ali's review of each change. His
  review stays for the contract, the gates and the perimeter.

**Built** (steps 1–4, and where each is described):
- the leash: code-owner review (ADR-0013, `.github/CODEOWNERS`), root where the agent works
  (ADR-0011, `agentRoot` in `modules/base.nix`), comin pinned (`flake.nix`), comin's testing
  branches off (`modules/base.nix`);
- the undo out of reach: Unraid's dated copies (ADR-0015, `hosts/unraid/README.md`), drilled
  2026-11-15 (`runbooks/restore.md`, cases 7–8);
- operate: root on docker-admin and its doco-cd tools, PBS's security updates
  (`hosts/pbs/README.md` → Updates), `nix run .#secret` (`AGENTS.md`, rule 3);
- incidents, investigated and reported only; the morning digest and the weekly report
  (`hosts/ops/README.md` → Unattended runs, `runbooks/incident.md`, `digest.md`, `report.md`);
- docker-admin's data on a btrfs disk of its own (`hosts/docker-admin/README.md` → Data).

## What Ali still does

| Ali | The agent |
|---|---|
| Decides what no undo reaches: the perimeter (OPNsense's rules and aliases, Cloudflare, the tailnet's policy), and any step on OPNsense, a Proxmox node, Unraid or an account (Merges → C) | Every other update, majors, hosts and comin included: reviewed, merged in the window, verified, rolled back if bad |
| Re-encrypts for a brand-new host: `sops updatekeys`, from the agent's exact commands | The VM, its ISO, the install. A host keeps its key for life, so nothing else needs re-encrypting (Toil) |
| Mints third-party tokens (Google, Cloudflare, healthchecks.io…) and types each in with `nix run .#secret` | Every secret it can generate, written whole into the files that need it |
| Approves anything destructive: deleting data, backups or VMs, replacing a VM | "Deploy X", "restore Y to yesterday", incident fixes within its lane |
| Reviews the contract, the gates and the firewall's aliases (`.github/CODEOWNERS`) | Proposes changes to them; changes everything else through the gates |
| Upgrades PVE, OPNsense and Unraid; physical and account work | Their changelogs and exact steps, in the weekly report |

## Decisions and rules this plan changes

Each lands as a new decision record, superseding the old one, and in `AGENTS.md`, with the PR that
makes it true.

| Now | With this plan | Step |
|---|---|---|
| ADR-0013, rule 1: Ali merges every PR | The agent merges through the gates (Merges). Renovate never merges by itself, so every update gets the same review, verify and rollback. Code owners keep the contract, the gates and the aliases Ali's | 6 |
| ADR-0011: root where the agent works | plus a PVE token for power only, scoped to pool `skynet`, for the window's kernel reboots | 5 |
| ADR-0010: no OpenTofu | OpenTofu creates and changes our VMs (Provisioning) | 8 |
| Rule 3: each file is for one host | a generated value two hosts share lives in a file of its own beside the host it belongs to (`hosts/<name>/<what>.sops.yaml`), encrypted for both | the first such value |
| Rule 4: OPNsense and PVE config are never | aliases Ali approved reach OPNsense through an alias-only key, and PVE tokens are scoped to pool `skynet`. OPNsense's rules, the nodes, and PVE's users, tokens and storage stay never | 8, 9 |

## The leash, still

- **Limits:** one change at a time, an undo point before each, and a daily budget of headless runs
  (they share Ali's Claude plan).
- **What it doesn't do:** hold an agent that chooses to go around it. The bot's token can merge
  anything outside the code owners' files (ADR-0013), and root can change a script on disk. The
  leash bounds a mistake, and a run misled by the text an alert or a release note carries. A filter
  in front of the doco-cd MCP servers would be no wall either: root on both Docker hosts walks
  around it.
- **The ruleset** gains the check `build` beside `nix` once step 5 adds it (Ali).

## Merges

A change merges by itself when a rollback undoes all of it and verify would see it break: the
revert puts the code back, and an undo point the data. What neither reaches is Ali's, whatever the
version number says.

| Change | Undo point | Gate | Merged by |
|---|---|---|---|
| **A:** one stack's images, digest to major; a database engine's major, with its migration | a snapshot of `/opt/appdata` seconds before; for a stack that writes the library (CLU, Uchiyomi, the comics agent), that night's copy of `Storage` too | CI; the release's age; the agent's review; in the window | agent |
| **B:** a host: the weekly `flake.lock`, an image pinned in Nix (doco-cd, Apprise), comin, a NixOS release, a host file | the timed rollback (Verify and roll back → Hosts) | as A, 7 days for Renovate's; every host built; each host verified on the build before the merge | agent |
| **C:** a step on what the agent doesn't hold: OPNsense, a Proxmox node, Unraid, an account | none | the agent's research and a ready PR | Ali |
| What Ali asked for in chat ("deploy X", "a VM for Y") | as A or B | as A or B, without the age; his message, linked in the PR; for a VM, a plan with no destroy or replace | agent |
| The agent's own PR (an incident's fix, a healthcheck, a runbook) | as A or B | as A or B, without the age; reviewed by the evening run, a session that didn't write it | agent |
| A revert of a merge that broke something | | CI | agent |
| A code owner's file; a plan that destroys or replaces | | code-owner review, or Ali | Ali |

- **The library's writers** (CLU, Uchiyomi, the comics agent) are A only while `Storage`'s copies
  are copy-on-write. With hard links a file rewritten in place isn't in the copy, and they are C.
  Unraid's disk has reflinks (2026-11-15), so they are A.
- **`backup` and `pbs-offsite`** are A: what they write to Drive can be made again from PBS's
  datastore and its copies. Their verify runs the job and waits for its exit, so they go last in
  the night. A run goes through doco-cd's own trigger (step 6); until then `skynet-merge` leaves a
  stack of jobs alone, and verify reads doco-cd's counts of each job's runs and failures.
- **Doors and Authelia** are stacks like any other: a broken door shows within minutes, and its
  revert deploys. **comin** and **doco-cd** are B: the timed rollback proves each still fetches and
  deploys before it merges.
- **Renovate** opens one PR per stack (grouped by its folder), so a PR is what verify checks and a
  rollback undoes, and labels each with its tier (`renovate.json`). The agent may raise a tier,
  never lower one.
- **A release's age:** 3 days for a digest or patch, 7 for a minor, 14 for a major, by Renovate
  (`minimumReleaseAge`) where the registry gives a release's time. Most give none: Renovate's lookup
  on 2026-11-22 found no time for any ghcr.io, quay.io or lscr.io image, for several of docker.io's
  (grafana, victoria-metrics, vmalert, cloudflared) or for any digest. Renovate would hold those
  forever, so it takes them as released (`timestamp-optional`). It writes every PR on Mondays only
  and leaves it alone the rest of the week, and `skynet-merge` waits until a Renovate PR's newest
  commit is 3 days old, whatever the update: the week's updates go out from Thursday.
- **The review**, written on the PR by an evening run: the release notes between the two versions,
  and for a major its migration, done in the same PR where it touches git; upstream issues opened
  since the release; the new images pre-pulled on the host. It names the commit it read, and only
  that commit merges. A step on Ali's side raises the PR to C, with the research and a proposal in
  the morning digest.
- **A step on the agent's own hosts** (a database's dump and load, a file moved): the review writes
  it out and labels the PR `steps`. The window's script leaves those; after it, still in the
  window, the agent takes them one at a time: `skynet-merge`, the step, `skynet-verify`, the same
  rollback.
- **The window**, nightly 05:00–06:00, while nobody uses the apps: `skynet-window` (ops, a timer, no
  Claude in it) takes the reviewed PRs oldest first, one at a time: `skynet-merge`, the deploy,
  `skynet-verify`. The first failure is rolled back and ends the night. What Ali asks for goes out at
  once.
- **`skynet-merge <pr>`** (ops) is the agent's only way to merge (`gh pr merge` stays denied): it
  checks the tier, the window, CI, the review and its commit, and the age; takes the undo point;
  merges that commit; and posts what and why to `#alerts`.
- **A rolled-back update isn't tried again as it was.** The agent's next review must name what
  changed (a newer version, a fix in the PR). A second failure goes to Ali with the evidence.
- **Where they live:** `packages/skynet-merge/`, `packages/skynet-verify/` and
  `packages/skynet-window/`, flake packages that `modules/window.nix` runs on ops, with the evening
  review (`skynet-review` there, `runbooks/review.md`). All five paths are code-owned: they stand
  in for Ali's review (ADR-0020).

## Verify and roll back

- **`skynet-verify`** (ops; deterministic, so the agent doesn't grade its own work):
  - a stack: each container runs the image the commit names, and doco-cd counted no failed deploy
    of it; every container healthy for 5 minutes, with no restarts; its Gatus rows green on results
    newer than the deploy; its error lines in VictoriaLogs not well above the same time the day
    before (3 times, plus 10, to begin with); its smoke check passing as it did before the merge;
  - a host: comin reports `main`'s commit (after a merge) and fetches; no failed units; every scrape
    target up; Gatus green. On ops also: the agent's sessions up, a headless `claude -p` answering,
    SSH to every host.

  It prints its evidence for the PR.
- **Nothing merges that verify can't see.** CI fails a long-running service with neither a
  healthcheck nor a stated reason for none, and a routed app with no Gatus row. Where a health
  endpoint doesn't show use, the stack has a smoke check (`smoke.sh` in its folder, run from ops):
  a page read from Komga and Uchiyomi (ADR-0016's accounts), and a login through each Authelia with
  an account of the agent's own (generated; Ali adds it to each users file, with the new verbs).
- **The undo point:** seconds before each merge, `skynet-merge` has btrbk snapshot `/opt/appdata`,
  read-only and instant, on both Docker hosts.
- **A failed stack:** the revert PR merges and deploys; then
  `skynet-restore local <stack> <its undo point> --whole` puts its folder back as it was, caches
  included (`--whole` is new with step 5): an old Redis can't read a newer one's dump. That loses
  only what the new version wrote. It's posted with the evidence.
- **A failure found later**, by use and not by verify: the revert only, and the data stays. If the
  old version can't run on it, the agent restores the stack from its undo point; `skynet-restore`
  first snapshots what it replaces (kept 7 days, as btrbk keeps any), and the digest says what the
  gap holds.
- **Hosts** (B):
  - ops builds every host from the PR; the hosts fetch from its cache;
  - each host in turn, the canaries first (docker-dmz, then technitium-network, while
    technitium-core keeps answering) and ops last, `skynet-activate` (`packages/skynet-activate/`):
    on the host, a 10-minute timer (`systemd-run`) that re-activates the generation running now;
    then the PR's build activated (`switch-to-configuration test`, which leaves the boot entry
    alone); then `skynet-verify`, for doco-cd a poll and a deploy too, for DNS an internal and an
    outside name answered and `technitium-sync` run. Green stops the timer. Anything else, a host
    that can't be reached included, and the timer puts the host back with no console;
  - then the merge. comin switches each host to the build it already runs, which makes it the boot
    default;
  - **what the timer can't undo:** state a new version migrated on the host itself (Docker's,
    Technitium's). That rebuilds from git (rule 2); app data has its snapshot;
  - **kernel reboots** (`comin_need_to_reboot`): one host at a time in the window, each back and
    green before the next, the two DNS VMs on different nights (PVE `operate`: power only). A host
    that doesn't come back from a reboot is the one case left for Ali's console (Open).
- **PBS** takes Debian's security updates by itself already; the agent reboots it in the window when
  one needs it. PVE, OPNsense and Unraid upgrades stay Ali's.

## Chat requests

- **"Deploy X":** the stack, its route, DNS record and Gatus row (`runbooks/new-stack.md`); merged
  once CI passes; deployed, verified, reported.
- **"Restore Y to yesterday":** `skynet-restore` from a local snapshot (7 days) or from Drive, after
  its undo snapshot; on both Docker hosts.
- **The library, or a backup, as it was:** from Unraid's copies (14 nights), read-only on docker-dmz
  and PBS.
- **A config "as it was yesterday":** a revert PR.
- **A VM:** restored from PBS to a spare VMID with its network unplugged, booted and checked; on
  Ali's tap, restored over the original.

## Incidents: the fixes

`skynet-incident` investigates and reports today. With step 6 the agent also fixes what's in its
lane, verifies it and posts it: restarting a container or stack, re-running a job, pruning images on
a full disk, reverting a merge that broke something, restoring a stack from a snapshot, and a PR
through the gates. A fix that touches data takes an undo point first.
- Never by itself: deleting data, a backup or a snapshot, and what's Ali's (What Ali still does).
  Those arrive as research, a proposal and a PR, with one question for Ali.
- An alert that returns within a day of the agent's fix isn't fixed again: it escalates.
- Once the digest has run for a week, warnings wait for it; critical alerts post at once.

## Toil

- **A host keeps its key for life,** so a rebuild re-encrypts nothing: a VM restored from PBS comes
  back with its key. Only a brand-new host, or one reinstalled from scratch, has its files
  re-encrypted: the agent's PR adds its key (`ssh_host.pub`, `.sops.yaml`) and its aliases, and
  gives Ali the `sops updatekeys` commands.
- **Generated secrets** go in files of their own, written whole for every host that needs them (a
  value two hosts share lives beside the host it belongs to, encrypted for both), so nobody copies
  a value.
- **ISOs and VMs:** Provisioning. **Aliases:** OPNsense aliases.

## Provisioning: OpenTofu with bpg/proxmox

- **One source:** each host's `hosts/<h>/vm.nix` replaces `proxmox.sh`: VMID, node, cores, memory,
  balloon, disks, and NICs with the MACs from `net.nix`. Nix exports them as JSON for
  `infra/proxmox/` (it spans both nodes): one module with our VM conventions (q35, OVMF,
  virtio-scsi, serial, guest agent, disk first), one provider per node (they aren't clustered), and
  pool `skynet`.
- **The flow:**
  1. A PR changes a spec. CI checks format and validity (GitHub's runners can't reach the lab), and
     that each NIC's VLAN is the one its VMID names (`hosts/README.md` → Addressing; docker-admin's
     second NIC, on VLAN 60, is listed): a VM's VLAN is firewall policy.
  2. The agent runs `tofu plan` on ops and posts it on the PR.
  3. The gates decide (Merges). Every VM also has `prevent_destroy`, so a plan that destroys one
     fails until that line changes, in a PR.
  4. After the merge, the agent applies the same plan from `main`; a change that needs a reboot
     applies in the window.
  5. A daily plan alerts on drift: anything changed by hand in PVE.
- **A new VM:** the apply uploads its installer ISO (built on ops), creates and boots it; the agent
  records its host key; Ali re-encrypts for it (Toil); the install. A rebuild is a replace: Ali's.
- **What it manages:** our NixOS VMs and PBS (2040, `hosts/pbs/vm.nix`). **What it doesn't:**
  - the passthrough and appliance guests: Unraid, OPNsense, HAOS, Omada, athena;
  - PVE's users, roles and tokens: a tool that grants could grant itself;
  - storage entries (PBS's holds the encryption key), the nodes' networks, upgrades;
  - the backup jobs: managing them takes `Sys.Modify` on `/`, which would let the token change the
    nodes. The stale-backup alert watches their outcome.
- **The token:** `skynet@pve!provision` on each node (`docs/credentials.md` → Planned); Ali mints it
  once into `hosts/ops/secret.sops.yaml`.
- **State** stays on ops, backed up with it, and holds no secrets. If it's lost, `tofu import`
  rebuilds it from the live VMs.
- **The import:** `import {}` blocks for the six VMs. The migration is done when `plan` shows no
  changes.
- **Safety:** a plan runs provider code with the token. So the agent plans only its own branches and
  Renovate's, and CI rejects `local-exec`, `external` and provisioners in `infra/`. The provider is
  pinned in the lock file and updated like any dependency. `packages/skynet-tofu/` runs the specs'
  export, the plan, the apply and the drift check.

## OPNsense aliases

- `hosts/opnsense/aliases.yaml` holds every alias the lab uses, imported from OPNsense
  (`skynet-read`), so the first sync changes nothing.
- On merge, `opnsense-alias-sync` (`packages/opnsense-alias-sync/`, on ops, the `technitium-sync`
  pattern) applies them with the alias-only key, reloads, reads them back, and fails loudly on any
  difference. Aliases not in the file are left alone. Rules stay Ali's, and os-git-backup keeps
  OPNsense's history.
- The folder is code-owned, since an alias is firewall policy. A new host's aliases ride in the PR
  that adds its key (Toil), which Ali reviews anyway.
- **OPNsense on OpenTofu waits:** browningluke/opnsense (v0.26, July 2026) says it isn't for
  production and has no Tailscale coverage, and a bad apply could lock everyone out at once.
  Revisit at its v1.

## Steps

Steps 1–4 are built (above).

5. **Merges PR, as a dry run:** `renovate.json` (one PR per stack, the tiers, the release ages);
   CI: every host built (`build`, which Ali adds to the ruleset), and the healthcheck and Gatus-row
   checks, with the healthchecks, rows and smoke checks they ask for; the evening review;
   `packages/skynet-merge/`, `skynet-verify/` and `skynet-window/` with `modules/window.nix`: the
   undo point, the rollback (`skynet-restore --whole`) and the window, which for a week logs what it
   would merge and verifies what's live; PVE `operate` (Ali mints) and the kernel reboots, which run in the window;
   the incident fixes, logged only.
6. **Live, on Ali's call** after the dry-run week and a drill (a bad update to a real stack, merged
   in a window, rolled back with its data): the window merges and the incident fixes apply; a
   record superseding ADR-0013, rule 1 and `AGENTS.md`.
7. **Hosts PR:** `packages/skynet-activate/`, drilled on each host with a change that cuts its
   network and comes back by the timer; then B merges, and comin's pin goes.
8. **Provisioning PR:** each host's `vm.nix`, `infra/proxmox/`, the `provision` token (Ali), the
   import with no changes, the VLAN check, the drift check; the `proxmox.sh` files go; a record
   superseding ADR-0010.
9. **Aliases PR:** `hosts/opnsense/aliases.yaml`, the alias key (Ali), the sync.
10. **Game day.**

Steps 7–9 can run beside the dry-run week.

## Exit criteria

- The leash holds: a PR touching a code owner's file can't merge without Ali. (Met 2026-11-15,
  proven both ways.)
- The undo out of reach holds: 14 nights of Unraid's copies; a backup deleted on PBS and a folder
  deleted from `Storage`, each put back from them by the agent; a delete on a copy refused. (The
  drill passed 2026-11-15; the 14th night is 2026-11-28.)
- Two weeks of windows: every merge verified, each failure rolled back and reported, nothing for
  Ali but tier C.
- From chat, end to end: a stack deployed, and an app's data put back to yesterday's.
- docker-admin's data on btrfs with snapshots, on the same VM and key. (Met 2026-11-15.)
- A game day passes: a bad image update (rolled back with its data), a killed container, a full
  disk, a host change that cuts the host's network (undone by its timer) and a failed backup
  (re-run), each fixed or PR'd with no step from Ali.

**Open:**
- A host that doesn't come back from a kernel reboot: a PVE snapshot before the reboot, rolled back
  if it stays down, would take `VM.Snapshot` on the `operate` token.
- Root on ops for deep work: time-boxed SSH-CA certificates (the CA on Ali's workstation), if a
  plain user there ever gets in the way.
- PVE's and PBS's own failure notices: the alerts watch the outcome, and a direct webhook would be
  faster (#204).
- Re-encrypting without Ali (a key in a GitHub environment that only `main` can use, and a
  workflow), if new hosts ever come often.
