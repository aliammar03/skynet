---
date: 2026-09-04
kind: session          # session | incident | decision
title: SKY-021 P3c — adguard-core cut over to NixOS (live); the .31 stale-ARP saga
tier_touched: [T2]      # self-provisioned/destroyed pool CTs on core; deploy over SSH; OPNsense read (T1)
grants: []
refs: [SKY-021, SKY-007, SKY-008, SKY-020]
---

# 2026-09-04 · session · SKY-021 P3c — adguard-core cut over to NixOS (live); the .31 stale-ARP saga

## What happened
Executed the live cutover of adguard-core (CT 731) from hand-built Debian to the NixOS flake host,
after Ali confirmed "clients use Technitium; adguard is an old leftover, free to experiment, go ahead."

**The clean part.** Snapshot old 731 → stop it → create a NixOS CT (VMID 732) from the base template
on a temp IP (.32) → `ct-age-identity.sh inject` the Option C key → `deploy .#lxc-adguard-core`. First
deploy FAILED: `adguardhome.service` couldn't bind `0.0.0.0:53` — `systemd-resolved`'s stub listeners
(127.0.0.53/54:53) were already there. deploy-rs **auto-rolled-back** (autoRollback+magicRollback did
their job). Fixed with `services.resolved.enable = false` + `networking.nameservers` for the CT's own
lookups; redeploy succeeded. Verified via `dig` (once #164 put it on PATH): resolve, `*.aliammar.net`
→ 10.10.100.35, specific rewrites → 10.10.60.35, `ads.doubleclick.net` → 0.0.0.0 (blocked), admin
auth 401 on bad creds (the sops-injected bcrypt hash enforced). AdGuard 0.107.78, config rendered
verbatim from live 731.

**The VMID↔IP snag.** I'd used VMID 732 to keep old 731 as rollback, but 732@.31 violates the naming
law (732 → .32). Moving 732 to .32 made it convention-correct but then the entity audit went RED
("running-unmapped" — the adguard-core firewall/DNS fact points at .31, not .32). Put it to Ali; he
chose **reclaim to 731/.31**. Destroyed old 731 + 732, recreated the NixOS CT as **731 @ .31**.

**The .31 stale-ARP saga (the real time sink).** The recreated 731 was healthy INTERNALLY (Proxmox
`/lxc/731/interfaces` showed eth0 = 10.10.70.31/24, right MAC, traffic flowing) but **unreachable from
ops** — while .30/.51 on the same VLAN 70 answered fine. Chased it wrong twice: (1) reused the old
Debian MAC via `pct set` + reboot → still dark; (2) suspected networkd `[Match] MACAddress` and
recreated with the MAC at create time → still dark. Ground truth came from the **OPNsense read API**
(`/api/diagnostics/interface/get_arp`): `.31 → bc:24:11:69:9e:4d` **dynamic, valid** — the MAC of the
now-destroyed 732, which OPNsense had cached (and also for .32) and wouldn't re-ARP for ~20 min. My
rapid destroy/recreate churn on the SAME IP had poisoned OPNsense's ARP. `.32` had worked precisely
because it was a fresh IP with no stale entry. **Fix without mutating the live firewall or waiting:**
recreate 731 with the MAC OPNsense already expected (bc:24:11:69:9e:4d) → instant PING/SSH. Pinned
that MAC as adguard-core's stable MAC (in the create recipe + flake comment) so a future reprovision
reuses it and never churns ARP again. inject → deploy → all green. Entity audit now ✓.

Constitution PR'd (docs/system-design.md §5 table + §6 bullet): **new-CT default = NixOS for pool-able
LXCs**, Debian only for T3-excluded/appliance CTs. Also shipped #164 (dig + mtr/nmap/tcpdump/whois/
socat/iperf3 on the ops box) mid-cutover because every DNS check was a `nix run nixpkgs#dnsutils`.

## Actions & outcomes
- snapshot + stop old Debian 731 → create NixOS 732@.32 → inject → deploy: adguardhome bind :53 FAILED
  (resolved) → deploy-rs auto-rollback ✓ (safety net proven live)
- `services.resolved.enable=false` + nameservers → redeploy OK; DNS/rewrites/block/auth all verified ✓
- moved 732 → .32 (VMID↔IP), audit went RED (unmapped) → Ali: reclaim to 731/.31
- destroy 731+732 → recreate 731@.31; unreachable despite healthy internal net
- OPNsense get_arp → stale `.31 → <dead 732 MAC>` dynamic-valid = root cause
- recreate 731 with that MAC (pinned) → reachable; inject + deploy + verify → adguard-core LIVE on NixOS ✓
- entity audit ✓ every running entity mapped; secret-scan + check-invariants + flake check green
- constitution: new-CT default = NixOS for pool LXCs (#163); ops network tools (#164)

## Graveyard — tried & abandoned
- `nix run nixpkgs#dnsutils -- dig` for every check → flaky (download noise, IPv6-first); added dig to
  the ops box as a standing tool (#164). Also: jq's silent null-on-wrong-path (`.net0` vs `.data.net0`)
  wasted a probe — switched to python3 for JSON the rest of the session (Ali's standing gripe).
- Fixing the stale ARP by (a) reusing old MAC via `pct set`+reboot, (b) recreating with old MAC at
  create → both still dark, because OPNsense cached the DEAD 732 MAC for .31, not the old-Debian MAC.
  The winning move was matching the CACHED MAC, not the historical one.
- Considered flushing OPNsense's ARP (whole table) — rejected: mutates the live firewall lab-wide and
  is tier-ambiguous; MAC-adoption is self-contained to my CT.
- VMID 732 (keep-old-as-rollback) → abandoned for 731/.31: the audit maps adguard-core's fact to .31,
  and the naming law ties 731↔.31. Reclaiming (destroy old) was Ali's call.

## Follow-ups / open threads
- **Reprovision hygiene:** pin a stable MAC per pool host at provision (done ad-hoc for adguard-core)
  so destroy/recreate on the same IP never poisons the gateway ARP. Worth folding into the standard
  CT-create recipe / a future tofu resource for these hosts.
- Archive SKY-021 (`bin/plan archive SKY-021`) once #162/#163/#164 merge.
- Migration candidates now unblocked by the proven path: technitium-core (751), omada, authentik —
  each its own directive.
- Old Debian 731 is GONE (reclaimed, per Ali) — rollback now is "rebuild from git" (the NixOS host is
  fully defined), not a stopped CT. Consistent with §6 (rebuild from git, not backup).
