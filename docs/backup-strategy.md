# Backup strategy

**What this is:** the *why and what* of Skynet backups — the layered model, what each layer
protects, where copies live, how they're encrypted, and how long they're kept. The *how*
(day-to-day operation, provisioning, restoring) lives in the runbooks:
[`runbooks/backup.md`](../runbooks/backup.md) and
[`runbooks/restore-service.md`](../runbooks/restore-service.md). The authoritative design is
[`deployment-plan.md` §6](deployment-plan.md); this page is the distilled, current-reality view.

---

## The layered model

Backups are defence in depth: six layers, each protecting a different kind of loss. Losing any
one layer is survivable because the others overlap.

| Layer | Protects | Tool | Destination | Encryption | Status |
|---|---|---|---|---|---|
| **L0** | compose, runbooks, docs, inventory | git | GitHub (private) | — | ✅ |
| **L1** | `.env` secrets | sops + age | GitHub, in-repo (`.env.sops`) | age | ✅ |
| **L2** | firewall / router config | os-git-backup | GitHub (`skynet-opnsense`) | private repo | ✅ |
| **L3** | container app data | **restic** | **rclone → Google Drive** | restic AES-256 | ✅ live (docker-dmz) |
| **L4** | VMs + LXCs (both nodes) | vzdump → **PBS** | PBS datastore (Unraid) | PBS client-side | ✅ |
| **L5** | PBS datastore off-site copy | **rclone sync** | **Google Drive** | already encrypted | ⚠️ upload live, **restore untested** |

Out of scope by design: **bulk media** (an Unraid concern; 2 TB of cloud won't hold it).

---

## Where the copies are (3-2-1 honestly)

**Container app data (L3).** One restic repo per host at
`gdrive:Skynet/Backups/restic/<host-label>`. That single off-site repo holds **many
point-in-time snapshots** — retention `--keep-daily 7 --keep-weekly 4 --keep-monthly 6`
(≈17 restorable versions), deduplicated so they cost far less than 17×. There is **no separate
local backup copy**; the source is the live `/opt/docker/appdata`. So app data is *live + 1
versioned off-site repo* — solid for "the host died", thin on media diversity. (Improvement
noted below.)

**Guests (L4/L5).** Three tiers: the live guest → the **PBS datastore on Unraid** (holds PBS's
own per-guest version history) → a **mirrored off-site copy** on Google Drive
(`gdrive:Skynet/Backups/pbs`). So guests are *source + 2 backup copies on 2 media, 1 off-site* —
a proper 3-2-1.

> ⚠️ **L5 is an `rclone sync` mirror, not independent versioning.** It makes Drive *match* the
> datastore, so a deletion or corruption already written into the datastore propagates to Drive
> on the next run. L5 protects against *losing* the datastore/Unraid, not against corruption
> that has already been synced. PBS's own retention + verify jobs are the guard for the latter.

---

## Encryption — Google never sees plaintext

- **L3 restic** encrypts client-side (AES-256) before rclone uploads; the repo password is the
  only key. Generated on the host, `0600`, and copied into the **survival kit**.
- **L5** ships PBS chunks that are **already** client-side encrypted by PBS; rclone moves
  ciphertext. The PBS encryption key lives only in the survival kit.
- **L1** env secrets are age-encrypted (sops) before they ever touch git.
- The rclone Google Drive OAuth token lives `0600` on each backing-up host — a real standing
  secret on those hosts (see limitations).

So every byte that leaves the LAN is ciphertext, and every decryption key is in the survival
kit, never in git and never in this transcript.

---

## Google Drive layout

```
gdrive:Skynet/Backups/
├── restic/
│   └── <host-label>/        # one restic repo per docker/host (e.g. docker-dmz)
└── pbs/                     # rclone-mirrored PBS datastore (both node namespaces)
```

Remote `gdrive` uses Ali's own OAuth client (better API quota), `scope = drive`. Google caps
uploads at ~750 GB/day — only relevant for an initial seed. Sizes to expect: restic uploads the
*deduplicated* footprint; PBS L5 uploads the datastore's **on-disk** size (dedup ~25×), **not**
its logical size — read it from PBS's GC log, never from `df` (see runbook).

---

## Recovery objectives (informal)

- **App data / a single service:** minutes-to-an-hour. `restic restore` the dated snapshot +
  `gitops-deploy.sh` redeploy. Witnessed end-to-end on aiometadata (mongo + SQLite).
- **A guest:** a PBS restore into `ops-managed` (T2). Fast while PBS is alive.
- **PBS itself gone (core node dead):** pull the datastore back from Drive (L5), stand PBS up,
  restore guests. **This round-trip is UNTESTED** — scheduled as an A6 drill.
- **The whole lab / network node:** `runbooks/dr/` — the router config survives the router
  (L2), truth survives on GitHub (L0/L1), and skynet-ops is stateless. Rebuild from a laptop.

---

## Dependencies — the survival kit is load-bearing

Every off-site restore needs a key that is deliberately **not** in the system:

- **age private key** — without it every `.env.sops` in git history is confetti (L1).
- **restic repo password(s)** — without it the L3 repos are unreadable ciphertext.
- **PBS encryption key** — without it the L4/L5 backups can't be restored.
- **SSH CA private key** — to mint the root grants restores need.
- **rclone Google OAuth config** — to reach the off-site copies at all.

Verify the kit quarterly (Judgement Day checklist). See `runbooks/dr/survival-kit.md`.

---

## Known limitations / roadmap

- **App data has one off-site medium.** L3 is Drive-only; a second target (or an occasional
  local restic copy) would make app data a true 3-2-1.
- **L5 has no independent off-site versioning** (mirror, not additive) — see the warning above.
- **PBS→Drive restore is untested** — prove it in A6 before relying on it in anger.
- **Google OAuth (full-drive scope) sits on each backing-up host.** Acceptable per the plan's
  per-host restic design, but a scoped/service-account credential would shrink blast radius.
- **One root grant at a time** (single cert file) makes multi-host backup work sequential —
  an A5 follow-up (per-host cert filenames).
