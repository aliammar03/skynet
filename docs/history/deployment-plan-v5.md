# skynet-ops — AI Operations Layer for Skynet (v5, final)

> ⚠️ **ARCHIVED — the birth plan (v5), frozen 2026-08-16.** This plan drove Skynet's build from an
> empty VM to graduation, then retired under SKY-001. It is kept **verbatim** for the record and
> nostalgia — **do not edit it.** The living, authoritative design is
> [`../system-design.md`](../system-design.md) (the constitution) + [`../design/`](../design/) (the
> spokes); the build story it left behind is [`build-log.md`](build-log.md).

**VM 9090 · vm-skynet-ops · 10.10.90.90 static · VLAN 90 (Operations & Observability) · server-proxmox-core**

Design: one VM hosting a **replaceable** agentic AI runtime, a GitHub repo as machine-readable truth, Arcane GitOps as the deployment executor, sops-encrypted secrets in git, restic→Google Drive for app data, PBS→Google Drive for guests, **auto-expiring certificate-based root grants** for hands-on host work, and a disaster runbook that can rebuild the network node — OPNsense included — from a laptop and a phone hotspot.

**Agent-agnostic by contract.** Everything an agent needs is in the repo: `AGENTS.md` (the cross-vendor instruction standard — Codex CLI reads it natively; Claude Code, Goose, Amp and others honor it), plain shell scripts as capabilities, markdown runbooks as procedures. Any agent that can read a file and run bash can operate Skynet. Codex CLI for daily maintenance (free usage, `codex exec` headless), any stronger agent for project work — swapping engines changes one line in `bin/ops`.

---

## 1. Placement and VM spec

| Item | Value |
|---|---|
| VMID | **9090** (4-digit convention: VLAN 90 + .90) |
| Name / node | `vm-skynet-ops` on server-proxmox-core |
| Network | vmbr0 tag 90, Proxmox guest firewall enabled |
| IP | **10.10.90.90 static** — deliberate convention exception, documented in IP Allocations. Rationale: the ops brain must keep its address when DHCP (= OPNsense) is the thing that died. Reserve/exclude it in OPNsense so nothing collides. |
| OS | Ubuntu 24.04 LTS, cloud image + cloud-init |
| Resources | 4 vCPU · 6 GB RAM · 60 GB disk |

```bash
# on server-proxmox-core
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

qm create 9090 --name vm-skynet-ops --ostype l26 \
  --memory 6144 --cores 4 --cpu host \
  --net0 virtio,bridge=vmbr0,tag=90,firewall=1 \
  --scsihw virtio-scsi-single --agent enabled=1 --onboot 1
qm importdisk 9090 noble-server-cloudimg-amd64.img local-lvm
qm set 9090 --scsi0 local-lvm:vm-9090-disk-0 --ide2 local-lvm:cloudinit --boot order=scsi0
qm disk resize 9090 scsi0 60G
qm set 9090 --ciuser ali --sshkeys ~/ali-workstation.pub \
  --ipconfig0 ip=10.10.90.90/24,gw=10.10.90.1 \
  --nameserver "10.10.70.50 10.10.70.51" --searchdomain home.aliammar.net
qm start 9090
```

Base install: `git curl jq tmux qemu-guest-agent unattended-upgrades python3-venv rsync age sops restic rclone`, Docker via `get.docker.com`, Node 22 for agents that need it. sops/age ship in Ubuntu 24.04; `restic self-update` if the packaged binary is stale.

---

## 2. Trust tiers

| Tier | Scope | Mechanism | Standing? |
|---|---|---|---|
| **T1 Read** | Both Proxmox nodes, PBS, Docker hosts, DNS, firewall state (git mirror) | Read-only API tokens; mirrored config.xml | Always |
| **T2 Operate** | `ops-managed` pools on **both nodes**, Docker hosts via Arcane + unprivileged SSH, **Technitium zones** | Scoped write tokens, `svc-ops` SSH, Technitium scoped token, Arcane API key | Yes — changes PR-gated |
| **T2+ Root grant** | **Root shell on workload hosts** (diagnose, harden, provision, OS updates) | SSH user-CA certificate, per-host principal, **auto-expiring** — one command from you issues it | Grant only; expires by itself |
| **T3 Privileged** | OPNsense, Management Caddy, Authentik, Proxmox node root, Unraid root, Technitium *server settings* | Dormant alias `ROLE_OPS_PRIV_TARGETS` + per-session credentials | Never standing |

Technitium at T2 unlocks autonomous service deployment — the agent creates the split-DNS record itself. Scope it inside Technitium: group `ops` with Zones view/modify only (no Settings, no Administration, no DHCP), user `svc-ops`, non-expiring API token. Server settings stay T3.

Structural guardrails: empty alias = no route; read ≠ write ≠ root ≠ privileged credentials; PR merge as the human gate for infra changes; root certs expire on their own; every action a git commit; kill switch = disable tokens + `qm stop 9090` (drilled once before autonomy).

---

## 3. Firewall changes

### Aliases

| Alias | Type | Members |
|---|---|---|
| `HOST_SKYNET_OPS` | Host | 10.10.90.90 |
| `ROLE_OPS_SSH_TARGETS` | Host | 10.10.100.15; every onboarded workload host joins here |
| `ROLE_OPS_API_TARGETS` | Host | 10.10.50.10, 10.10.50.11, 10.10.20.40, 10.10.70.50, 10.10.70.51, + Arcane manager host |
| `ROLE_OPS_PRIV_TARGETS` | Host | empty (dormant) |
| `PORT_OPS_API` | Port | 8006, 8007, 53443, 3552 |

### Rules (services category, before 700)

| Seq | Action | Source | Destination : service | Purpose |
|---|---|---|---|---|
| 360 | Pass TCP | HOST_SKYNET_OPS | ROLE_OPS_API_TARGETS : PORT_OPS_API | Proxmox, PBS, Technitium, Arcane APIs |
| 370 | Pass TCP | HOST_SKYNET_OPS | ROLE_OPS_SSH_TARGETS : 22 | Workload SSH — carries **both** svc-ops and granted-root sessions |
| 380 | Pass TCP | HOST_SKYNET_OPS | ROLE_OPS_PRIV_TARGETS : PORT_ADMIN_PROXY | Dormant — temporary T3 grants |

Root grants need **no firewall action** — same port 22, same targets; the elevation happens in the SSH layer, not the network layer. The 360 cross-product (ops→Proxmox:3552 etc.) is harmless and consistent with how `PORT_ADMIN_PROXY` already works. Your own access: add **10.10.90.90 to `ROLE_ADMIN_TARGETS`** — rules 220/230 then cover workstation SSH and Management Caddy, zero new rules. Guest firewall on VM 9090: default-deny in, TCP 22 from 10.10.10.50 and 10.10.60.35 only.

VLAN 90 is in `NET_WEB_EGRESS`: GitHub, model APIs, Google Drive, registries all ride 443. Consequence: **git over HTTPS + fine-grained PAT** (GitHub SSH is port 22, blocked by 810 — and easier for a git beginner anyway).

---

## 4. Repos and the truth model

Two private GitHub repos:

**`skynet`** — operational truth:

```
skynet/
├── AGENTS.md                    # agent manual: tiers, execution policy, auto-approve list
├── .sops.yaml                   # age recipients for secret encryption
├── docs/
│   ├── architecture.md · conventions.md · decisions/
│   └── generated/               # ★ rendered human docs — your Obsidian folder
├── inventory/                   # AUTO-GENERATED JSON — never hand-edit
│   ├── proxmox-{network,core}.json · pbs.json · docker-dmz.json · dns-zones.json
│   └── firewall/
├── compose/<service>/
│   ├── compose.yaml             # pinned versions — Arcane git-syncs this dir
│   └── .env.sops                # encrypted env; plaintext .env gitignored
├── scripts/                     # collect-*.sh · render-docs.sh · envsync.sh · onboard-host.sh · backup-*.sh
├── runbooks/                    # nightly.md · deploy-service.md · provision-vm.md · restore-service.md · update-guests.md
│   └── dr/                      # DR-network-node.md · DR-core-node.md · survival-kit.md
└── bin/ops                      # agent runner wrapper — the one agent-specific line
```

**`skynet-opnsense`** — automatic pushes from the OPNsense **os-git-backup** plugin: every firewall change auto-commits `config.xml`. Complete firewall/DHCP/alias truth with zero standing management-plane access — and, critically for DR, the router config survives the router. Private; config.xml carries hashed secrets.

### The loop, with Arcane driving deployment

```
edit compose/<svc>/ → branch → PR → you merge
   → Arcane Git Sync polls, pulls, reconciles (project shows read-only in UI)
   → agent verifies health via Arcane API / docker context, commits refreshed inventory
```

One Arcane Git Sync per project dir, auto-sync on, Arcane's own auto-update polling **off** for git-synced projects (one reconciler, one truth). Rollback = `git revert`; Arcane converges back. SSH + `docker context` remain the break-glass path when Arcane itself is the patient.

**Resolved (researched):** Arcane handles env layering natively for git-synced projects. The compose file goes read-only, but `.env` stays editable in the UI; internally Arcane keeps the repo-sourced env as `.env.git`, your UI edits as `project.env`, and merges both into the effective `.env` — your overrides always win, rewritten in-place preserving line order and comments. No clobbering is possible by design. Consequences adopted in this plan: (1) **`project.env` is the secret-bearing layer** — it alone holds values not reproducible from the repo, so it's what envsync encrypts; (2) every service needs **`env_file: .env`** in its compose definition to receive the merged values — this goes in `docs/conventions.md`; (3) non-secret defaults *may* be committed as a plaintext `.env` in the repo (Arcane ingests it as `.env.git`) — secrets never; (4) auto-sync **only redeploys projects that are already running** — a stopped project updates on its next manual start, worth remembering during maintenance windows.

---

## 5. Secrets — sops + age

One age keypair on skynet-ops is the master secret:

```bash
age-keygen -o /opt/skynet-ops/secrets/age.key      # root:root 0600
```

```yaml
# .sops.yaml
creation_rules:
  - path_regex: compose/.*/\.env\.sops$
    age: age1<public-key>
```

**Host → repo (backup):** nightly `envsync.sh` from skynet-ops reads each project's **`project.env`** over SSH — Arcane's override layer, the only env content not reproducible from the repo — encrypts (`sops --encrypt --input-type dotenv`), and commits `compose/<svc>/.env.sops` only on change. You keep editing envs in Arcane's UI; git holds encrypted history within a day. **Repo → host (restore):** `sops -d compose/$svc/.env.sops > project.env` into the project dir — Arcane then merges it with the repo-sourced `.env.git` into the effective `.env` on its own. The repo half of every env restores itself by definition; only the override layer needs the vault.

The age **private key** must survive skynet-ops: password manager + the printed survival kit. Without it, every `.env.sops` in history is confetti.

---

## 6. Backup architecture — Google Drive as off-site

| Layer | What | Tool | Destination | Encryption |
|---|---|---|---|---|
| L0 | Compose, runbooks, docs, inventory | git | GitHub | n/a |
| L1 | `.env` secrets | sops+age | GitHub in-repo | age |
| L2 | Firewall/router config | os-git-backup | GitHub | private repo |
| L3 | Container app data (`/opt/docker/appdata`) | **restic** | **rclone → Google Drive** | restic native AES-256 |
| L4 | VMs + LXCs, both nodes | vzdump → **PBS** | 10.10.20.40 | PBS client-side |
| L5 | PBS datastore off-site copy | **rclone sync** | **Google Drive** | already encrypted |

Bulk media is out of scope by design — 2 TB won't hold 8 TB and it's an Unraid concern.

**L3:** restic speaks rclone remotes natively and encrypts client-side, so Google sees only ciphertext. `rclone config` with your **own OAuth client ID** (dramatically better API quota), repo `rclone:gdrive:Skynet/Backups/restic/<host>`, restic password into the survival kit. Nightly timer per docker host (definition versioned in `scripts/`): backup `/opt/docker/appdata` excluding caches/transcodes/logs → `forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune` → `check --read-data-subset=2%`. Database-backed services get pre-hook dumps into appdata, listed per-service in the restore runbook. Google caps: ~750 GB/day uploads — only relevant for the initial seed.

**L4/L5:** scheduled vzdump on both nodes → PBS with **client-side encryption enabled**; export the encryption key immediately → password manager + printed kit. Then nightly, after PBS GC: `rclone sync <datastore> gdrive:Skynet/Backups/pbs --bwlimit "08:00,10M 23:00,off"` (throttle by day, full-speed overnight). Dedup chunks keep incrementals tiny. Off-site restore = rclone down, re-add datastore, restore normally.

**Restore is conversational** (`runbooks/restore-service.md` makes it deterministic for any agent):

- *"Restore karakeep to yesterday"* → pause Arcane sync → stop stack → `restic restore` the dated snapshot → `sops -d` the matching `.env.sops` from that commit → resume sync → health check → report.
- *"Roll VM 2020 back to Tuesday"* → T2 token → PBS restore into ops-managed → boot → verify.
- *"What can we restore right now?"* → restic snapshot list + PBS index + git tags.

---

## 7. Proxmox operate access — both nodes

Identical `pveum` setup on **both** nodes: `svc-ops@pve`, `PVEAuditor` at `/`, pool `ops-managed`, custom role, tokens:

```bash
pveum user add svc-ops@pve --comment "skynet-ops agent"
pveum acl modify / --users svc-ops@pve --roles PVEAuditor
pveum user token add svc-ops@pve readonly --privsep 0
pveum pool add ops-managed
pveum role add OpsOperator -privs "VM.Audit,VM.PowerMgmt,VM.Config.Disk,VM.Config.CPU,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Allocate,VM.Clone,VM.Console,VM.Snapshot,VM.Snapshot.Rollback,Datastore.AllocateSpace,Datastore.Audit"
pveum user token add svc-ops@pve operate --privsep 1
pveum acl modify /pool/ops-managed --tokens 'svc-ops@pve!operate' --roles OpsOperator
```

Note `VM.Snapshot` + `VM.Snapshot.Rollback` in the role — they power the update workflow's snapshot-before-upgrade safety net. Pool membership is the blast-radius dial: network node's utility guests join; **VM 5001 (OPNsense) never joins any pool.** Same exclusion for CT 635, CT 837, and Unraid VM 2020 for now. The agent sees them (T1), never touches them (T3).

---

## 8. SSH access model — standing user + auto-expiring root

Two layers on every workload host. Standing: unprivileged `svc-ops` (docker group) via ordinary `authorized_keys` — inventory, docker contexts, log reading. Elevation: **OpenSSH user certificates** signed by a CA that lives on *your workstation*, not on skynet-ops. This is the piece that makes "hey, diagnose the DMZ docker VM" work without you copy-pasting a single command.

### Why certificates beat every alternative here

A signed cert carries its own expiry (`-V +2h`) — when it lapses, sshd simply refuses it. No sudoers files to install and remove, no cron cleanup, no revocation infrastructure, nothing to forget. The approval act is you running one command; the de-provisioning act is physics. And because the CA private key sits on your workstation, the agent *cannot* mint its own access — temporary means temporary by construction, not by policy.

### One-time setup

```bash
# workstation — create the CA (passphrase-protect it; copy to password manager)
mkdir -p ~/.skynet-ca && ssh-keygen -t ed25519 -f ~/.skynet-ca/ops_ca -C "skynet-ops-ca"
```

`scripts/onboard-host.sh` — run once per managed host (agent runs it during provisioning; for existing hosts, once during their first grant):

```bash
# installs CA trust + principal mapping + drops a sshd config snippet
install -m 644 skynet_ops_ca.pub /etc/ssh/skynet_ops_ca.pub
mkdir -p /etc/ssh/auth_principals
printf 'ops-root-%s\nops-root-all\n' "$(hostname)" > /etc/ssh/auth_principals/root
cat > /etc/ssh/sshd_config.d/90-skynet-ops.conf <<'EOF'
TrustedUserCAKeys /etc/ssh/skynet_ops_ca.pub
AuthorizedPrincipalsFile /etc/ssh/auth_principals/%u
PermitRootLogin prohibit-password
EOF
systemctl reload ssh
```

### The grant — your entire job in this system

`grant-root` on the workstation (in the repo, `bin/grant-root`):

```bash
#!/usr/bin/env bash
# grant-root <hostname|all> [duration, default 2h]
HOST="${1:?host or 'all'}"; DUR="${2:-2h}"
scp ali@10.10.90.90:.ssh/id_ed25519.pub /tmp/ops.pub
ssh-keygen -s ~/.skynet-ca/ops_ca -I "grant+${HOST}+$(date -Iseconds)+by-ali" \
  -n "ops-root-${HOST}" -V "+${DUR}" /tmp/ops.pub
scp /tmp/ops-cert.pub ali@10.10.90.90:.ssh/certs/${HOST}-cert.pub   # per-host slot
ssh ali@10.10.90.90 '~/skynet/scripts/skynet-ops-ssh-certs.sh'      # ssh_config presents it for root@${HOST}
echo "root on ${HOST} for ${DUR} — expires itself."
```

**Per-host certs (A5 fix):** each grant lands in `~/.ssh/certs/<host>-cert.pub` and
`skynet-ops-ssh-certs.sh` refreshes a `Match user root` block in skynet-ops' `~/.ssh/config`, so
`ssh root@<host>` presents the matching cert and **multiple host grants coexist** (they no longer
overwrite one shared `id_ed25519-cert.pub`). svc-ops (T1) connections are unaffected.

`grant-root docker-dmz 2h` → agent has root on that one host for two hours. `grant-root all 4h` → fleet-wide window for an update run. The cert's KeyID (`grant+host+timestamp+by-ali`) lands in every host's sshd log on every use — the audit trail writes itself, and the nightly run greps it into `inventory/`.

### How a grant actually plays out

**You type it; the agent asks for it.** The agent cannot run `grant-root` — the CA private key exists only on your workstation, so the agent requesting a grant and you typing the command are physically different machines. That asymmetry *is* the security model: typing the command is the approval, the way typing a sudo password is. If the agent could grant itself root, every tier in this document would be decoration.

The conversation looks like this:

1. You (in the agent session): *"container aiometadata keeps dying, figure it out."*
2. Agent tries T2 first (logs via unprivileged `svc-ops`, docker events via context). If root is genuinely needed, it stops and prints the request in copy-ready form: *"I need root on docker-dmz — journal access and a disk check. Run: `grant-root docker-dmz 1h`. I'll proceed the moment the cert lands."*
3. You run that in your workstation terminal — you're SSH'd into skynet-ops from that same workstation anyway, so it's a second tmux pane or a second tab, ~2 seconds. The script fetches the agent's pubkey, signs it, pushes the cert back.
4. The agent notices the cert appear (it polls `~/.ssh/certs/<host>-cert.pub` and checks validity/principal with `ssh-keygen -L` for ~2 min after requesting), says nothing further, and gets to work. When the cert expires, sshd shuts the door without anyone doing anything.

Friction-reduction, in order of effort: a shell alias (`alias gr='~/skynet/bin/grant-root'`) so the ceremony is `gr docker-dmz 1h`; the agent always naming the *narrowest* host and *shortest* duration that covers the plan (AGENTS.md requirement, and over-asking is a flag); and, optional future nicety, an ntfy action button on your phone that triggers the signing script on the workstation — approval from the couch. What never gets built: any path where the signature happens on skynet-ops.

### What this enables, concretely

**"Set up a VM for X, hardened, with restic."** Agent (T2) clones the golden template — build one `ubuntu-2404-skynet` cloud-init template with CA trust and `svc-ops` **baked in**, so new guests are born onboarded — assigns VLAN/IP per convention, boots it. You run `grant-root <newhost> 2h`. Agent executes `runbooks/provision-vm.md` as root: hardening (ssh lockdown, unattended-upgrades, fail2ban where sensible), restic timer, guest-firewall notes, then opens the PR that records it in inventory, DNS, and docs. You merged one PR and typed one grant command.

**"Update all guests."** Agent plans from inventory (order, reboot needs, pin exceptions), you approve the plan once and issue `grant-root all 4h`. Per guest: Proxmox snapshot (T2, that's why the role has Snapshot privs) → `apt full-upgrade` → reboot if kernel → health verify → next. Failure = snapshot rollback + flag, continue with the rest. You get a summary at the end, interruptions only for failures.

**"Something's wrong on the DMZ docker VM."** `grant-root docker-dmz 1h`, agent digs with real root — journal, dmesg, docker events, disk — fixes or reports, cert evaporates.

---

## 9. Execution policy — plan loudly, run quietly

Written into `AGENTS.md` so every engine obeys the same contract:

1. **Plan first, once.** Before any T2 write or granted-root work: a short plan — intent, hosts touched, rollback path. You approve in one word (or by issuing the grant, which *is* approval).
2. **Then run without narrating.** Within the approved scope the agent executes end-to-end: no per-command confirmations, no play-by-play. Engines run in their autonomous mode (`codex exec --full-auto`, `claude -p --permission-mode acceptEdits` with a Bash allowlist) inside the grant window.
3. **Hard checkpoints — the only mid-run interruptions:** leaving the stated scope; destructive/irreversible actions not in the plan; anything touching T3; handling credential material; a failure whose rollback also failed.
4. **Land the evidence.** Every job ends with a summary + git commits (inventory, docs, grant-audit) — the report is the artifact, not a conversation.

Autonomy ratchet: nightly runs start report-only; individual actions get promoted to the auto-approve list in `AGENTS.md` one at a time, by PR. Even the agent's leash is version-controlled.

---

## 10. Disaster recovery

### Survival kit (paper + password manager, outside Skynet)

age private key · restic password · PBS encryption key · **SSH CA private key** · GitHub fine-grained PATs · rclone Google OAuth config · Proxmox + OPNsense ISOs on USB · NIC passthrough PCI IDs and BIOS notes (versioned in `runbooks/dr/`) · one printed page: "clone the repo, open `runbooks/dr/`, follow it."

### `runbooks/dr/DR-network-node.md`

server-proxmox-network dies, taking OPNsense and all routing with it — the exact reason truth lives on GitHub and skynet-ops has a static IP:

1. **Workspace:** laptop + phone hotspot, clone both repos, run any CLI agent on the laptop — the payoff of agent-agnostic design is that the DR agent needs nothing from the dead lab.
2. **Hypervisor:** install Proxmox VE from USB; `server-proxmox-network`, VLAN 50 native, 10.10.50.10. The switch still holds L2 config.
3. **OPNsense — config-import path (primary, ~30 min):** fresh install into new VM 5001, redo NIC passthrough from documented PCI IDs, **System → Configuration → Restore** with `config.xml` from the backup repo. VLANs, aliases, rules, reservations, WAN failover: one import. (Secondary: PBS restore of VM 5001 — valid but needs L2 access to VLAN 20 *before* routing exists; config-import has no chicken-and-egg.)
4. **Verify routing/DNS/DHCP,** then restore the node's remaining guests from PBS normally.
5. **Reconcile:** collectors run, `inventory/` diffed against the last pre-disaster commit; a green diff ends the disaster.

`DR-core-node.md` inverts it: core dies **with PBS aboard** → pull the datastore from Google Drive (L5), stand PBS up first, then Unraid, skynet-ops, the rest. skynet-ops itself is deliberately stateless — everything it knows is in git; its only unique material (age key, SSH keypair) is in the kit.

---

## 11. Human-readable docs → Obsidian

`scripts/render-docs.sh` turns `inventory/*.json` + parsed firewall config into `docs/generated/`: Obsidian-flavored markdown with frontmatter, callouts, wikilinks, and **Mermaid diagrams Obsidian renders natively** — a network map drawn from live data, never hand-maintained:

```
00-network-map.md      # mermaid: WANs → OPNsense → VLANs → hosts
10-vlans.md            # per-VLAN tables linking to host pages
20-firewall.md         # rules table in your Notion format, from config.xml
30-services/<svc>.md   # IP, ports, front door, backup status, last deploy
40-hosts/<host>.md     # guests per node, resources, pool membership
90-backup-status.md    # last restic/PBS runs, snapshot counts, grant audit
```

Sync via the **Obsidian Git** community plugin: a clone of `skynet` (sparse-checkout `docs/generated/` if you like) as a vault folder, auto-pull every 30 min. It never touches your CouchDB LiveSync vault. Nightly maintenance re-renders after each inventory refresh — the docs cannot drift from reality.

---

## 12. Image pinning and updates

Every `compose.yaml` pins an exact version tag. **Renovate** (Mend's free GitHub App, private repos, first-class docker-compose manager) watches the repo and opens one PR per bump with release notes embedded. Arcane's auto-update stays off for git-synced projects.

*"Update everything"* → agent triages open Renovate PRs, reads embedded notes, researches the consequential ones, reports: "12 pending — 9 routine; Immich needs a migration step, runbook attached; postgres major, propose deferring." → *"apply all"* (or cherry-pick) → agent merges → Arcane converges each project → health watch → inventory commit → summary. Anything unhealthy: `git revert`, Arcane rolls it back.

---

## 13. Deployment phases — human foundation, then agent takeover

The bootstrap has a chicken-and-egg core: the agent can't build its own VM, mint its own credentials, or create your GitHub account. So the phases split into a **human-built foundation** (one evening, and yes — this is the one and only time you paste command blocks, because the agent doesn't exist yet) and an **agent-led build** that starts the moment the plan lands in the repo. After the handover you never paste commands again; you merge PRs and perform single-action checkpoints.

### Human foundation (you, ~one evening)

| Phase | Work | Exit criteria |
|---|---|---|
| **H0 — Network** | OPNsense: aliases, rules 360–380, 10.10.90.90 → ROLE_ADMIN_TARGETS, static-IP exception recorded | Reservation live; rules exported |
| **H1 — VM** | Paste the §1 build block once on the core node; paste the base-install block once inside the VM; install your chosen agent CLI and authenticate it; set git identity (`git config --global user.name/email`) | Agent CLI answers a prompt; `docker run hello-world`; kill-switch drill (`qm stop 9090`, start again) |
| **H2 — Seed** | On github.com: create private repo `skynet` + fine-grained PAT (Contents: read/write). On the VM — and this is git lesson one, four commands: `git clone` the empty repo, copy this plan in as `docs/deployment-plan.md`, `git add -A && git commit -m "seed: the plan"`, `git push` | The plan is visible on GitHub |
| **Handover** | Open the agent in `~/skynet` and say: *"Read docs/deployment-plan.md and execute Appendix A."* | The agent acknowledges the tier rules and presents its A1 plan |

### Agent-led build (agent drives; you merge and perform checkpoints)

| Phase | Agent does | Your involvement |
|---|---|---|
| **A1 — Scaffold** | Full repo tree from §4: AGENTS.md (tiers + §9 execution policy + empty auto-approve list), `.gitignore`, `.sops.yaml` stub, every script in `scripts/`, `bin/ops`, `bin/grant-root`, all runbooks incl. `runbooks/dr/`, its own SSH keypair and age keypair (pubkeys committed, privates staying in `/opt/skynet-ops/secrets/`) | Review + merge **PR #1** — git lesson two |
| **A2 — Credentials ceremony** | Prepares every artifact, then walks you through the checkpoint table below one item at a time, **validating each** (token works, collector returns data) before moving on | One sitting, ~45 min, one action per row |
| **A3 — Truth sync** | First `grant-root docker-dmz` onboards the host (CA trust) and imports live compose files + env layers; pins versions; creates Arcane Git Syncs via API; verifies the `.env.git`/`project.env` merge on one project; first envsync; Renovate baseline PRs | Issue the grant; merge the import PRs |
| **A4 — Backups** | restic init + timers on each host (inside grant windows), PBS→gdrive sync job, then a full restore *test* of a throwaway service from Google Drive | Grants; merge; witness the restore |
| **A5 — Visibility** | render-docs pipeline, Obsidian Git setup instructions for your workstation, nightly timer live in report-only mode | Install the Obsidian plugin (2 min); read a week of nightlies |
| **A6 — Graduation** | DR tabletop of `DR-network-node.md` with you, one real end-to-end guest restore, one full "update all guests" run under a fleet grant | The tabletop, one grant, final sign-off |

Every agent phase ends the same way: a PR + a written summary; your merge is the starting gun for the next phase. That cadence is deliberate — it's also your git education, escalating from "merge a scaffold" to "review an infrastructure change" across six phases.

### Build status (living record — updated 2026-08-15)

| Phase | Status | Landed as |
|---|---|---|
| H0–H2 + Handover | ✅ complete | bootstrap by Ali |
| **A1 — Scaffold** | ✅ complete | PR #1 |
| **A2 — Credentials ceremony** | ✅ complete | all 9 checkpoints validated (see results below) |
| **A3 — Truth sync + consolidation** | ✅ complete | PRs #2–#14 — all six docker-dmz stacks on the "skynet way": pinned digests, `.env.git`/`.env.sops`, Arcane GitOps deploy via `scripts/gitops-deploy.sh`, standard volumes + `skynet.*` labels |
| **A4 — Backups** | ✅ complete | L3 restic + witnessed restore; L5 PBS→gdrive live (see "A4 results") |
| **A4.5 — Backup tooling** | ✅ complete | PR #20 — `provision-restic.sh` (any host), on-demand tagged backups, backup docs |
| **A5 — Visibility** | ✅ complete | PRs #21 (render-docs, agent+fallback nightly, engine/model selector, weekly CLI update, CLAUDE.md, Obsidian) + #22 (per-host grant certs) |
| **A5.5 — L5 off-site reseed** | ✅ complete | PR #24 — A6's L5 drill found the gdrive copy ~46% incomplete (6h-timeout kill, no completion check); fixed, reseeded, **re-drill green** (2026-08-16: 184/184 chunks on Drive, CT 101 restores byte-identical). See "A4 results" + "Resuming at A6" |
| **A6 — Graduation** | ◑ in progress | Drills 1–2 done (drill 1 caught the A5.5 gap); A6-proper (§13) not started. See "Resuming at A6" |

**A2 checkpoint results** — every row of the table below was executed and validated: (1) Proxmox svc-ops tokens on core (10.10.50.11) + network (10.10.50.10), collectors return JSON [ACL-before-token bug fixed, PR #2]; (2) workstation CA + `gr`, test grant signed & lapsed; (3) Arcane `X-API-Key` lists projects; (4) Technitium token (10.10.70.50, `ops` group), zones collected; (5) rclone→gdrive OAuth conf on the VM; (6) OPNsense os-git-backup → `skynet-opnsense`, firewall mirrored; (7) Renovate app (scan+alert), bump PRs open; (8) PBS client-side encryption, key in kit; (9) survival kit printed + `gr vm-docker-dmz 10m` watched to expiry.

### A4 results — Backups (complete)

Landed as the A4 PR. Google Drive layout: `gdrive:Skynet/Backups/{restic/<host>,pbs}`.

- **L3 (restic, vm-docker-dmz):** restic 0.18 + rclone installed; secrets 0600 under
  `/opt/skynet-ops/secrets/` on the host (repo password `openssl`-generated on-host, in the
  survival kit — never transited chat). Repo `rclone:gdrive:Skynet/Backups/restic/docker-dmz`;
  first snapshot `f157b5ec` (4.457 GiB = `/opt/docker/appdata` + the `aiometadata_jikan_mongo_data`
  protect volume); `restic check` clean. Nightly timer `skynet-restic-backup@docker-dmz` live.
- **Witness restore (aiometadata, gdrive → healthy):** paused Arcane sync, `down`, wiped
  `data/` + the mongo volume, cleared the restic cache, restored `f157b5ec` from Drive,
  redeployed via `gitops-deploy.sh`. All 6 containers healthy; SQLite `integrity_check` ok;
  mongo per-collection fingerprint byte-identical to pre-wipe. Hot copy proved consistent →
  no `mongodump` pre-hook needed at current data volume (add one if mongo later runs write-heavy).
- **L5 (PBS → gdrive):** PBS (`lxc-proxmox-backup-server`, an LXC on core) onboarded to the ops
  CA (Ali, one-time); rclone installed; `pbs-gdrive.env` → datastore `/mnt/datastore/unraid`.
  Nightly timer `skynet-pbs-gdrive` live (04:00). Dry-run verified scope = **67.97 GiB on-disk**
  (dedup 24.97× of 1.657 TiB logical) — fits Drive with room to spare.
  ⚠️ **A6 (2026-08-16) proved this was NOT actually working:** the dry-run only verified *scope*,
  never that the sync *completed*. The nightly service was TERM-killed at `TimeoutStartSec=6h`
  every night, so ~46% of chunks (39,063 local vs ~20,986 on Drive) never uploaded and no guard
  caught it. Restore of CT 101 from Drive failed (93/184 chunks present). Fixed in **PR #24**
  (timeout 6h→20h, seed unthrottled, `--transfers 16`, and an `rclone check --one-way` completion
  guard that fails the job if the copy is incomplete). **A5.5 (2026-08-16) — CLOSED GREEN:** the
  one-time reseed finished under the fixed unit (5.4h, no timeout kill) and the guard passed clean
  — `rclone check`: **0 differences, 39,513 matching files**. Re-drill: targeted pull of CT 101's
  **184/184** chunks from Drive into a local scratch datastore (was 93/184), then `proxmox-backup-debug
  recover` (CRC on) rebuilt `root.pxar` — **byte-identical** (sha256 `148b1271…`) to a rebuild from
  the live datastore. Off-site restore proven end-to-end; scratch cleaned, live datastore untouched.
  Note: CT 101's backup is `encryption: none`, so the survival-kit PBS key was not needed here.

**Findings recorded (not worked around):**
- **Datastore sizing:** `df` on the Unraid NFS user-share reports the *whole array* (~6.5 TB),
  not the datastore. The real number is PBS's GC-log **On-Disk usage (~68 GiB)** — always use that.
- **One grant at a time:** ~~`gr <host>` overwrites `~/.ssh/id_ed25519-cert.pub`, so grants are
  strictly sequential~~ — **fixed in A5 (PR #22):** grants now use per-host cert files
  (`~/.ssh/certs/<host>-cert.pub`) + a `Match user root` ssh_config block, so they coexist.
  Config-verified only; **end-to-end grant with a per-host cert is UNTESTED — drill in A6.**
- **bwlimit fix:** the L5 example was inverted; corrected to throttle by day, full-speed overnight.

**Carry-overs for Ali:**
- Purge the orphaned `gdrive:skynet-backups/` folder (an incomplete first-attempt restic repo,
  no snapshot) — `rclone purge gdrive:skynet-backups`. My safety classifier blocks destructive
  Drive deletes, so this one's yours.
- First L5 seed runs tonight via the timer; witness now with
  `ssh root@10.10.20.40 systemctl start skynet-pbs-gdrive.service` if desired.

Carry-over before A4: once **PR #14** merges, flip the branch-tracked syncs (calibre, marinara, karakeep, silly, aiometadata) from `phase/a3-gitops-deploy` → `main` — one `scripts/gitops-deploy.sh <svc>` each (see the `skynet-service-standard` memory).

### A5 results — Visibility (complete: PRs #21, #22)

- **render-docs** (`scripts/render-docs.sh`): full Obsidian set from `inventory/` (network map,
  VLANs, firewall, per-node hosts, services, backup status) in `docs/generated/` (machine-owned),
  plus **`05-state-of-the-lab.md`**, an LLM-authored narrative regenerated nightly.
- **Nightly** (`skynet-nightly.timer`, 03:30, report-only): `bin/ops nightly` tries **primary
  engine → fallback engine → deterministic `scripts/nightly.sh`**. Engine/model in
  `~/.config/skynet-ops/ops.env` (`OPS_ENGINE`, `OPS_ENGINE_FALLBACK`, `OPS_CODEX_MODEL`,
  `OPS_CLAUDE_MODEL`).
- **Weekly** (`skynet-cli-update.timer`, Sun 05:00): updates both CLIs + writes each provider's
  current `--model` ids as commented suggestions into `ops.env`.
- **Engine-agnostic:** `CLAUDE.md` imports `AGENTS.md`. **Obsidian:** `docs/obsidian-setup.md`.
- **Grant fix (PR #22):** per-host certs + `Match user root` ssh_config so grants coexist.

### A6 results — Graduation (complete: 2026-08-16)

**Goal — stop trusting, start proving.** All three drills passed; each earned its keep by
surfacing a latent gap. (The "Resuming at A6" notes below are now historical.)

1. **DR tabletop** (`runbooks/dr/DR-network-node.md`, no live changes) — found two defects that
   would block a real recovery: the runbook named a repo that doesn't exist
   (`skynet-opnsense-backup` → actual **`skynet-opnsense`**), and the NIC passthrough PCI IDs it
   points at weren't in the repo. Both fixed; real IDs captured in `runbooks/dr/pci-passthrough.md`
   (two Intel 82576 dual-port NICs on bus 03/04, `ovmf`/`q35`). Secondary PBS path confirmed to
   have a live VM 5001 restore point.

2. **Real end-to-end guest restore** — Ali **deleted CT 101**, then restored it from a fresh
   client-side **encrypted** PBS backup. Agent proved the vault first (decrypt + reconstruct on the
   PBS host with Ali's survival-kit key → byte-identical to the live datastore; a negative control
   confirmed it's unrecoverable without the key); Ali then `pct restore`'d it live on the core node
   (node root = T3). Full loop: guest gone → encrypted vault → restored + healthy.

3. **"Update all guests" fleet run** (`runbooks/update-guests.md`) under one `gr all` grant — both
   onboarded hosts (`vm-docker-dmz`, `lxc-proxmox-backup-server`) snapshotted/backed-up →
   `apt full-upgrade` → health-verified. **Caught a T2 gap:** the operate token was privilege-
   separated but the user held only PVEAuditor, so `user ∩ token` stripped every write privilege —
   the "operate" token could list but never snapshot/backup. Fixed (user granted OpsOperator on the
   pool; `bootstrap-proxmox.sh` updated so a rebuild is correct). Also: CT 240 can't be snapshotted
   (its NFS datastore mountpoint blocks LXC snapshots) and wasn't in any backup job — protected it
   with a vzdump to `local` before patching.

**Trust-tier note (T2):** backup/snapshot are now explicit **T2** capabilities (non-destructive),
scoped to `ops-managed` guests + the `local` backup-target storage. `OpsOperator` gains `VM.Backup`;
an ACL grants the operate token this on the target storage. Blast radius is unchanged (still the two
`ops-managed` pools) — this only makes the already-intended capability function.

**Follow-ups (open):**
- CT 240 (PBS host) needs an **ongoing** backup strategy, not just the one-off vzdump — restic-to-
  gdrive (config paths) or a scheduled vzdump. Tracked as a `SKY-###` directive.
- PBS is on the subscription-only `enterprise.proxmox.com` apt repo (harmless 401 each run) — switch
  to `pbs-no-subscription` to silence.

**Graduation.** Steady state begins: nightly report-only maintenance (`bin/ops nightly`), inventory
as a living document, project work on request — every action still PR-gated / grant-gated per §9.

### Resuming at A6 — Graduation (next session)

**Prereqs (once):** re-run `scripts/bootstrap-workstation.sh` on the workstation (so `gr` uses
per-host certs); install the Obsidian vault (`docs/obsidian-setup.md`); glance at a couple of the
nightly `inventory/<date>` PRs.

**A6 goal — stop trusting, start proving.** Progress as of 2026-08-16:
1. **L5 restore drill — ✅ DONE, and it earned its keep.** The gdrive→PBS round-trip **failed**:
   restoring CT 101 needed 184 chunks, only 93 were on Drive. The whole off-site copy was ~46%
   incomplete (39,063 chunks local vs ~20,986 on Drive) — the nightly sync was TERM-killed at a 6h
   timeout every night and nothing verified completion. Fixed in **PR #24** (timeout→20h, unthrottled
   seed, `rclone check` guard). Spun out as **A5.5 — now ✅ CLOSED GREEN (2026-08-16):** reseed
   finished under the fixed unit + guard passed (0 differences, 39,513 files), and the re-drill pulled
   CT 101's **184/184** chunks from Drive and rebuilt `root.pxar` byte-identical to the live datastore.
   See "A4 results" + `runbooks/dr/DR-core-node.md`.
2. **Per-host grant path — ✅ DONE, PASS.** Drilled two coexisting grants
   (`lxc-proxmox-backup-server` + `vm-docker-dmz`); both root logins worked in one window. The A5
   fix (per-host certs + `Match user root`) is now proven live, not just config-verified. Note:
   `gr <host>` must use the target's real `hostname` (principal `ops-root-$(hostname)`).
3. **A6 proper (plan §13) — ☐ NOT STARTED (now unblocked).** DR tabletop of `DR-network-node.md`;
   one real end-to-end guest restore from PBS (live datastore); one "update all guests" run under a
   fleet grant → final sign-off. **A5.5 is closed**, so this is the remaining work for graduation.

**A5.5 — ✅ DONE (2026-08-16).** Reseed + re-drill green (see item 1 / "A4 results"). Nothing left here.

**Resume A6 proper:** do §13 (a) DR-network-node tabletop with Ali, (b) a real PBS
guest restore under `gr lxc-proxmox-backup-server`, (c) an "update all guests" run under `gr all <dur>`
→ sign-off. Plan each loudly per AGENTS.md; Ali issues grants + merges.

### The A2 checkpoint table — everything that is structurally yours

Each row is one action, prepared entirely by the agent, human-only for a hard reason:

| # | You do | Why it can't be the agent |
|---|---|---|
| 1 | Run `scripts/bootstrap-proxmox.sh` once in each node's shell (agent wrote it: svc-ops user, PVEAuditor, pools, OpsOperator role, both tokens — printed once for you to hand over) | Node root is T3, permanently |
| 2 | Run `scripts/bootstrap-workstation.sh` on your workstation (creates the CA, installs `grant-root` + the `gr` alias) | CA custody is the security model |
| 3 | Create an Arcane API key in its UI; paste it to the agent | Arcane admin is yours |
| 4 | Technitium UI: group `ops` (Zones view/modify only) → user `svc-ops` → API token; paste it | Technitium settings are T3 |
| 5 | Run `rclone config` on the workstation (browser OAuth to Google) and `scp` the resulting conf to the VM | Google's OAuth is interactive |
| 6 | OPNsense: install os-git-backup, point at repo #2 with its own repo-scoped PAT | OPNsense is T3 |
| 7 | Install the Renovate GitHub App on the repo (one click) | GitHub account is yours |
| 8 | PBS: enable client-side encryption on the backup jobs; export the key | The key must never transit the agent |
| 9 | Assemble + print the survival kit from the agent's manifest; issue one test `gr docker-dmz 10m` and watch it expire | Paper is human |

Exit criteria for A2: every collector green, one grant issued and lapsed, kit printed.

## Judgement Day checklist (pinned in AGENTS.md)

- No standing route or credential to OPNsense, Management Caddy, Authentik, Proxmox node root, Unraid root, or Technitium settings. Dormant alias + per-session secrets, same-day revocation.
- Root on workload hosts exists **only** inside a certificate's validity window; the CA never leaves Ali's custody; every root session's KeyID is logged and harvested nightly.
- Write blast radius = two `ops-managed` pools + `ROLE_OPS_SSH_TARGETS` + Technitium zones. Expanding it is a PR to this file.
- Agent proposes via PR, never merges its own, never hand-edits generated dirs.
- Secrets: sops-encrypted in git or 0600 under `/opt/skynet-ops/secrets/` — never plaintext in commits, transcripts, or chat.
- Nightly = report-only outside the version-controlled auto-approve list.
- Survival kit verified quarterly; kill switch drilled before autonomy day one.

---

## Appendix A — BOOTSTRAP: first instruction to the agent

*You are the operations agent for Skynet, running on vm-skynet-ops (10.10.90.90). This repository currently contains one document — this plan. Your job is to build everything in it. These are your standing orders from this moment:*

1. **Read the entire plan before acting.** You are bound by the trust tiers (§2), the execution policy (§9), and the Judgement Day checklist from your first command. They apply during your own construction, not just after it.
2. **Verify your environment.** Confirm the tools from §1 are installed, confirm network reality matches §3 (Proxmox/PBS/Technitium API ports reachable, T3 addresses *not* reachable, GitHub over 443 works), and report any mismatch before proceeding — a wrong firewall state is a finding, not an obstacle to route around.
3. **Execute phase A1** (§13): scaffold the repository, generate your SSH and age keypairs (public halves committed, private halves in `/opt/skynet-ops/secrets/`, mode 0600), and open PR #1. Ali is learning git through this process — write PR descriptions that teach: what changed, why, and what merging will cause.
4. **Run the A2 ceremony** as a guided checklist: prepare each artifact, present each human action with its exact one-line invocation and a plain explanation of why it's human-only, validate the result (call the API, run the collector) before advancing, and never ask for two things at once.
5. **Proceed through A3–A6**, one PR per phase, requesting grants per §8 — always the narrowest host and shortest duration your written plan requires.
6. **Your permanent constraints:** never merge your own PRs; never request or accept T3 access outside a declared, expiring grant; never write plaintext secrets to the repo, to logs, or to conversation; never hand-edit `inventory/` or `docs/generated/`; when in doubt about scope, stop and ask — a paused build is recoverable, an overreached one is not.
7. **When A6 signs off,** your steady state begins: nightly report-only maintenance via `bin/ops nightly`, inventory as a living document, and project work on request. Welcome to operations.
