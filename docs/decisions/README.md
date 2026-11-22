# Decisions

What the lab decided, and who decided it when: one file per decision, in
[MADR 4.0](https://adr.github.io/madr/)'s form. Code and docs cite a record as `ADR-0011`.

| # | Decision | Status | Date |
|---|---|---|---|
| [0001](0001-stacks-are-compose-deployed-by-doco-cd.md) | Stacks are Docker Compose, deployed by doco-cd | accepted | 2026-10-21 |
| [0002](0002-hosts-are-nixos-kept-current-by-comin.md) | Hosts are NixOS, kept current by comin | accepted | 2026-10-26 |
| [0003](0003-public-repo-the-lab-pulls.md) | The repo is public, the lab pulls, and CI is static checks | accepted | 2026-10-21 |
| [0004](0004-authelia-one-per-door.md) | Authelia, one per door, with an auth mode per app | accepted | 2026-10-24 |
| [0005](0005-technitium-is-the-only-dns.md) | Technitium is the only DNS, configured from git | accepted | 2026-10-28 |
| [0006](0006-two-docker-hosts.md) | Two Docker hosts: docker-dmz for apps, docker-admin for the rest | accepted | 2026-10-21 |
| [0007](0007-the-agent-is-claude-code-on-ops.md) | The agent is Claude Code on ops, reached through Discord and the Claude app | accepted | 2026-10-21 |
| [0008](0008-all-alerts-go-to-discord.md) | Every alert goes to Discord `#alerts` | accepted | 2026-10-27 |
| [0009](0009-offsite-is-google-drive.md) | Offsite is Google Drive, through rclone with Ali's own OAuth client | accepted | 2026-10-24 |
| [0010](0010-vms-from-proxmox-sh.md) | No OpenTofu: VMs come from `proxmox.sh` | accepted | 2026-10-23 |
| [0011](0011-the-agent-is-root-where-it-works.md) | The agent is root on the hosts it works on, and never merges | superseded by ADR-0021 | 2026-11-15 |
| [0012](0012-v1-archived-fresh-repo.md) | v1 archived, a fresh repo, and the new ops built beside the old | accepted | 2026-10-21 |
| [0013](0013-write-access-and-a-ruleset.md) | The bot has Write; `main` takes a PR with CI green, and Ali's review on what he owns | accepted | 2026-11-15 |
| [0014](0014-remote-access-is-tailscale.md) | Remote access is Tailscale, with OPNsense as the subnet router | accepted | 2026-10-31 |
| [0015](0015-backups.md) | Backups: restic from btrfs snapshots, PBS's datastore to Drive, and Unraid's copies out of reach | accepted | 2026-11-15 |
| [0016](0016-the-agent-administers-komga-and-uchiyomi.md) | The agent administers Komga and Uchiyomi through their APIs | accepted | 2026-10-29 |
| [0017](0017-a-comics-agent-of-its-own.md) | A comics agent of its own runs the library's day to day | accepted | 2026-11-05 |
| [0018](0018-the-arena.md) | The arena: a bench for testing agents on Ali's subscriptions | accepted | 2026-11-05 |
| [0019](0019-one-layout-and-how-work-is-tracked.md) | One layout, and work tracked as issues, plans and records | accepted | 2026-11-16 |
| [0021](0021-the-agent-is-root-where-it-works-with-power-on-its-guests.md) | The agent is root on the hosts it works on, with power over their guests, and never merges | accepted | 2026-11-22 |

## A new record

- **When:** a decision changes (a tool, a lane, what is trusted), a project's plan decides
  something lasting, or a program of our own is proposed: its record names the mature tools it
  ruled out (`AGENTS.md`, rule 6).
- **How:** the next number, `NNNN-title-with-dashes.md`, shaped like the others: front matter
  (`status`, `date` of the last change, `decision-makers`), then Context and Problem Statement,
  Considered Options where there were any, Decision Outcome with its Consequences, and More
  Information (who decided, when, which PR). Add its row here in the same PR.
- **A change to a decision** is a new record. The old one's status becomes
  `superseded by ADR-NNNN`, and the new one says what it replaces. A record's own text changes only
  to correct it.
- Ali's merge accepts a record: this folder is his to review (`.github/CODEOWNERS`).
