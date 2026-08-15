---
title: State of the Lab
generated: 2026-08-15
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---
> [!quote] Agent's log
> This page is written by me — the operations agent — during the nightly pass, not by the
> deterministic renderer. It's the human-readable read on where Skynet stands: what's healthy,
> what changed, and what I'm keeping an eye on. The tables elsewhere are the truth; this is the
> story that connects them. Regenerated every night; edit the prompt in `runbooks/nightly.md`,
> not this file.

# Skynet — State of the Lab

**As of 2026-08-15** · foundations complete, backups proven, now getting eyes on everything.

## The one-glance dashboard

| System | State | Note |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`) | 🟢 up | static 10.10.90.90, stateless-by-design |
| 🖧 Routing / OPNsense | 🟢 up | config mirrored to git every change (L2) |
| 🐳 DMZ Docker (`vm-docker-dmz`) | 🟢 up | 6 stacks, all on the "skynet way", all healthy |
| 💾 restic → Google Drive (L3) | 🟢 nightly | witnessed restore ✔ |
| 🗄️ PBS → Google Drive (L5) | 🟡 upload live | restore round-trip **untested** (A6 drill) |
| 👁️ Visibility (these docs) | 🟢 new | you're reading it |

## Where we are in the build

```mermaid
graph LR
  A1[A1 Scaffold]:::done --> A2[A2 Credentials]:::done --> A3[A3 GitOps]:::done
  A3 --> A4[A4 Backups]:::done --> A45[A4.5 Provisioning]:::done --> A5[A5 Visibility]:::now
  A5 --> A6[A6 Graduation]:::next
  classDef done fill:#1f6f43,stroke:#0d3,color:#fff;
  classDef now fill:#8a5a00,stroke:#fb0,color:#fff;
  classDef next fill:#333,stroke:#888,color:#ddd;
```

Six docker stacks are consolidated and deployed by Arcane GitOps from this repo —
**aiostreams, aiometadata, calibre, marinara, silly, karakeep** — every one pinned to a digest,
secrets in sops, health-checked. The credential ceremony is done, the firewall is mirrored, and
off-site backups actually work: I wiped aiometadata down to the metal, pulled it back from
Google Drive, and it came up green with its mongo and SQLite intact.

> [!tip] What's genuinely solid
> - **Truth lives in git.** Compose, secrets (encrypted), firewall, inventory — the lab can be
>   described from the repo alone. That's the whole point of skynet-ops.
> - **Backups are real, not aspirational.** L3 has a *witnessed* restore behind it. That
>   sentence is doing a lot of work — most homelab backups have never been tested.

## What I'm keeping an eye on

> [!warning] Honest open items
> - **The PBS→Drive restore is unproven.** The upload runs nightly; pulling it back has never
>   been drilled. Until A6 proves it, treat off-site guest recovery as *probable*, not *certain*.
> - **App data has a single off-site medium.** L3 is Google-Drive-only. A second target would
>   make it a true 3-2-1.
> - **Grants are one-at-a-time** (a single cert file) — being fixed so multi-host work stops
>   being sequential.

## Commentary

Honestly? For a lab this young, the discipline is holding: nothing gets deployed that isn't in
git, nothing gets root that isn't inside an expiring certificate, and the one destructive test I
ran had a proven way back. The next real milestone isn't more features — it's **A6**, where we
stop trusting the backups and start *proving* them, then run a full guest-update pass under a
fleet grant. That's when Skynet graduates from "built" to "operable".

Until then: the timers run at night, the docs render themselves, and I'll flag anything that
drifts. — _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[90-backup-status]]. This narrative is
regenerated nightly; the deterministic pages are the source of truth._
