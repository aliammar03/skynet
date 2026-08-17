---
title: State of the Lab
generated: 2026-08-17
author: skynet-ops (agent)
tags: [skynet, generated, narrative, state-of-the-lab]
---
> [!quote] Agent's log
> This page is written by me — the operations agent — during the nightly pass, not by the
> deterministic renderer. It's the human-readable read on where Skynet stands: what's healthy,
> what changed, and what I'm keeping an eye on. The tables elsewhere are the truth; this is the
> story that connects them. Regenerated every night; edit the prompt in `runbooks/nightly.md`,
> not this file. (My own cold-boot orientation lives separately in [[06-agent-digest]].)

# Skynet — State of the Lab

**As of 2026-08-17** · foundations complete and graduated; now in steady-state ops, executing
directives — with memory that finally survives a cold boot.

## The one-glance dashboard

| System | State | Note |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`) | 🟢 up | static 10.10.90.90, stateless-by-design |
| 🖧 Routing / OPNsense | 🟢 up | config mirrored to git every change (L2) |
| 🐳 DMZ Docker (`vm-docker-dmz`) | 🟢 up | stacks on the "skynet way", GitOps-reconciled |
| 💾 restic → Google Drive (L3) | 🟢 nightly | witnessed restore ✔ |
| 🗄️ PBS → Google Drive (L5) | 🟡 upload live | off-site guest restore still the standing question |
| 👁️ Visibility (these docs) | 🟢 live | rendered nightly from inventory |
| 🧠 Episodic memory (`journal/`) | 🟢 new | raw episodes + a read-time digest (SKY-006) |

## Where we are in the build

The foundation arc (A1–A6) is **complete** — scaffold, credentials, GitOps, backups, provisioning,
visibility, and graduation. Skynet is past "built" and into **steady-state ops**, where new work
arrives as `SKY-###` directives rather than plan phases: the conventions bedrock landed (SKY-009),
the Authentik SSO ingress is mid-build (SKY-003), and the agent just grew a memory it didn't have
before (SKY-006 — a journal of what actually happened, and a digest that reconstructs it on a cold
start).

> [!tip] What's genuinely solid
> - **Truth lives in git.** Compose, secrets (encrypted), firewall, inventory — the lab can be
>   described from the repo alone. That's the whole point of skynet-ops.
> - **Backups are real, not aspirational.** L3 has a *witnessed* restore behind it — most homelab
>   backups have never been tested.
> - **Memory is now infrastructure.** Semantic (docs), procedural (runbooks), and — new — episodic
>   (`journal/`) all rebuild from git. A cold agent reconstructs *what was already tried* instead
>   of relearning it.

## What I'm keeping an eye on

> [!warning] Honest open items
> - **PBS→Drive guest restore is the standing question.** The upload runs nightly; the off-site
>   *guest* recovery round-trip is the thing to keep proving, not assuming.
> - **App data has a single off-site medium.** L3 is Google-Drive-only; a second target would make
>   it a true 3-2-1.
> - The live, always-current list of what's in flight is in my [[06-agent-digest|agent digest]].

## Commentary

For a lab this young the discipline is holding: nothing deploys that isn't in git, nothing gets
root outside an expiring certificate, and now nothing that *happened* is lost either — the journal
keeps the episodes and the digest distills them at read time. The timers run at night, the docs
render themselves, and I'll flag anything that drifts. — _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[90-backup-status]]. Agent orientation:
[[06-agent-digest]]. This narrative is regenerated nightly; the deterministic pages are the truth._
