---
title: State of the Lab
generated: 2026-08-29
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

**As of 2026-08-29** · foundations long graduated; SKY-008 (OpenTofu) has both Proxmox nodes
provisioning VM/CT lifecycle end-to-end, with DNS + declarative LXC import still to come.

## The one-glance dashboard

| System | State | Note |
|---|---|---|
| 🧠 Ops brain (`vm-skynet-ops`, VMID 9090) | 🟢 up | NixOS flake, static 10.10.90.90, running, `ops-managed` |
| 🖧 Routing / OPNsense | 🟢 up | config mirrored to git every change (L2); 41 aliases, 29 rules, unchanged since 08-27 |
| 🐳 DMZ Docker (`vm-docker-dmz`) | 🟡 up, but check | all 18 containers healthy, but every one shows `Up 11 hours` — points to a host reboot ~08-28 16:30, unexplained in the journal |
| ☁️ Public tunnel (cloudflared, docker container on `vm-docker-dmz`) | 🟢 running | 9+ days up; the *other* cloudflared — a standalone LXC 1033 on the network node — was intentionally destroyed 08-27 as a Tofu proof, doesn't affect this path |
| 🗄️ PBS (LXC 240, `ops-managed`) | 🔴 **stopped** | was running as of 08-27; now down — unconfirmed whether deliberate |
| 💾 restic → Google Drive (L3) | 🟢 nightly | witnessed restore ✔ |
| 🗄️ PBS → Google Drive (L5) | 🟡 at risk | nothing to mirror while PBS itself is stopped — see above |
| 👁️ Visibility (these docs) | 🟢 live | rendered nightly from inventory |
| 🧠 Episodic memory (`journal/`) | 🟢 steady | raw episodes + read-time digest (SKY-006, 2/3) |

## Where we are in the build

SKY-008 (OpenTofu provisioning) picked up two full phases since the last narrative: **Phase 1**
(read-only skeleton + import) and **Phase 2** (throwaway-guest lifecycle) are both done on
**both** Proxmox nodes now — core got a permanent clone-source template (`ubuntu-2404-base`,
VMID 9000) plus a proven clone→destroy round-trip; the network node (previously untouched by
Tofu) got its own provider, its own privilege-separated token, and a clone→destroy round-trip
using the disused `cloudflared` LXC (1033) as the throwaway. **Phase 3** (DNS records +
declarative LXC import) hasn't started yet.

Everything else that graduated earlier is holding steady: convention bedrock (SKY-009),
default-lean context (SKY-010), machine-enforced invariants (SKY-011), Obsidian LiveSync
(SKY-013), the Cloudflare tunnel (SKY-014), and SKY-007 (ops VM as a NixOS flake, closed out
2026-08-26). SKY-005 (recon/diagnosis discipline) and SKY-006 (episodic memory) are both
sitting at 2/3.

> [!tip] What's genuinely solid
> - **Truth lives in git.** Compose, secrets (encrypted), firewall, inventory, and the ops host
>   definition itself — the lab can be rebuilt from the repo alone.
> - **VM/CT lifecycle is now declarative on both nodes.** Tofu proved clone→boot→destroy on
>   core *and* network this week — the standalone-node split (separate ACLs, separate VMID
>   spaces) is handled, not assumed away.
> - **The ops brain is declarative.** SKY-007 turned `vm-skynet-ops` into a NixOS flake — the
>   next full rebuild is `nixos-rebuild`, not a runbook of manual steps.

## What changed since the last render (2026-08-27 → tonight)

- **PBS (VMID 240, `lxc-proxmox-backup-server`) is stopped.** It was running two nights ago.
  Nothing in the journal or recent PRs touches it — no SKY-008 session, no compose change, no
  grant. I didn't start it back up (nightly is report-only, and this is a T2 guest-power action
  outside tonight's scope either way) — **flagging for Ali to confirm**: deliberate maintenance,
  or an unplanned stop that's quietly starving the L5 backup layer of anything to upload.
- **The old pre-NixOS `vm-skynet-ops` (VMID 999) is running again.** Two nights ago I read its
  "stopped" state as the SKY-007 VMID-renumber story closing out clean (999 retired, 9090 is the
  one true ops box). It coming back up isn't explained by anything in the journal since —
  probably intentional (comparing something against the old box?) but worth a one-line
  confirmation so it doesn't quietly become a stray duplicate.
- **`vm-docker-dmz`'s containers all restarted together, ~11 hours before tonight's collect**
  (all 18 containers show `Up 11 hours`, no adds/removes, no image churn beyond routine layer
  diffs). Reads like a host reboot or a full compose/daemon restart, not per-service redeploys.
  No journal entry accounts for it — asking Ali rather than guessing.
- **LXC 1033 (`lxc-cloudflared` on the network node) is gone — expected, not a surprise.** The
  SKY-008 network-node session used it as the Tofu clone/destroy proof: cloned to 1099, then
  both were destroyed on Ali's call. The *actual* public tunnel is a separate `cloudflared`
  Docker container on `vm-docker-dmz`, which never depended on this LXC and has been up 9+ days
  straight through this.
- **A new permanent guest, VMID 9000 (`ubuntu-2404-base`), joined `ops-managed` on core** — the
  Tofu clone-source template from SKY-008 P2. Stopped by design; it's a template, not a running
  service.
- **DNS and firewall**: routine SOA/DNSSEC advances on both zones; the OPNsense mirror is
  byte-for-byte the same content as 08-27 (only the collector timestamp moved) — no drift to
  report there this time.

## What I'm keeping an eye on

> [!warning] Honest open items
> - **PBS is down — needs a human look.** See above; this is the one item tonight that could
>   actually matter if it's not deliberate.
> - **PBS→Drive guest restore is still the standing question** even when PBS itself is up —
>   upload runs nightly when the source is live; the off-site *guest* recovery round-trip is
>   still the thing to keep proving.
> - **Two unexplained state flips** (999 running, docker-dmz uptime reset) — probably both benign
>   and probably both Ali's hands, but I'd rather ask than assume.
> - SKY-008 P3 (DNS + declarative LXC import) is the next phase whenever picked back up.
> - The live, always-current list of what's in flight is in my [[06-agent-digest|agent digest]].

## Commentary

Two solid nights for SKY-008 — the network node going from "untouched by Tofu" to "same
lifecycle proof as core, plus a real destroy of a real (if disused) LXC" is the kind of progress
that de-risks Phase 3. The flip side: three separate unexplained state changes showed up in one
diff (PBS stopped, an old VM back up, a whole docker host's uptime reset), and none of them trace
to a journal entry. Individually they're each plausibly "Ali was poking at something" — together
they're enough that I'd rather hand Ali a clear list than wave it away as noise. Nothing here
needed nightly to act (all report-only, all outside auto-approve scope regardless), so nothing
was touched. — _skynet-ops_

---
_Factual detail: [[README|index]] · [[00-network-map]] · [[90-backup-status]]. Agent orientation:
[[06-agent-digest]]. This narrative is regenerated nightly; the deterministic pages are the truth._
