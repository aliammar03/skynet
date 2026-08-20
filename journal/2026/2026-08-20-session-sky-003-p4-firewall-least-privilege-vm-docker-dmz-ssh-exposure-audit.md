---
date: 2026-08-20
kind: session
title: SKY-003 P4 — firewall least-privilege + vm-docker-dmz SSH-exposure audit
tier_touched: [T1]
grants: []
refs: [SKY-003, vm-docker-dmz, 10.10.100.15]
---

# 2026-08-20 · session · SKY-003 P4 — firewall least-privilege + vm-docker-dmz SSH-exposure audit

## What happened
Read-only audit (T1) over a freshly re-collected firewall mirror + host-layer reads on
vm-docker-dmz via svc-ops. No changes applied — this episode produces the findings + a proposed
delta for Ali to apply (firewall = T3 on OPNsense; sshd = host).

## Findings — ingress least-privilege (the proxy path)
- **Core segmentation holds.** Only rule 250 (src = HOST_PROXY_APPS) targets app origins; there is NO
  client→origin rule. Client VLANs (NET_APP_CLIENTS = 10.10.10/20/30/40.0/24) reach only the proxy
  .35 via rule 200. Clients cannot reach origins directly. ✓
- **Rule 250 governs almost nothing (intra-VLAN reality).** Every real app origin is on VLAN 100 DMZ,
  same subnet as Caddy .35 → L2-switched, never traverses OPNsense. So rule 250 / PORT_APP_BACKENDS
  do NOT filter Caddy→origin for them. This corrects the P3 note: the "karakeep on :3000 vs
  PORT_APP_BACKENDS=8080" mismatch is a NON-issue — that path isn't firewalled. Narrowest fix = none.
- **ROLE_APP_ORIGINS inaccurate.** Members: 10.10.20.63, .100.53/.65/.66/.69/.75/.85.
  - 10.10.20.63 (VLAN 20) is the ONLY cross-VLAN entry — so the only one rule 250 actually enforces
    (opens Caddy→a client-VLAN host:8080). It appears ONLY in this alias + docs derived from it; not
    in DNS, not in any compose, not in the Caddyfile. **Stale** (pre-staged leftover). Prune candidate.
  - obsidian 10.10.100.95:5984 IS proxied but MISSING from the alias (functionally moot, intra-DMZ,
    but the alias should be accurate).
- **Rule 240 / PORT_AUTHENTIK ✓** = {9000,9443}; outpost forward-auth is :9000; covered.
- **Rule 830 (Caddy→any:53).** apps Caddy (HOST_PROXY_APPS) is a source but doesn't need :53 — ACME
  rides the Cloudflare API on 443 (rule 810); Caddy's only real DNS need (resolve api.cloudflare.com)
  goes to Technitium and is covered by rule 100 (NET_SKYNET→resolvers:53; NET_SKYNET includes
  10.10.100.0/24). So HOST_PROXY_APPS can be removed from 830's source. CAVEAT: Caddy ACME DNS-01 does
  a propagation check; certmagic defaults to recursive resolvers (rule 100), but if it ever queries
  authoritative NS on :53 directly it'd need 830. Low-risk optional narrowing; verify a renewal after.

## Findings — vm-docker-dmz (10.10.100.15) SSH exposure
Network layer — rules whose destination expands to include .15 on :22:
- seq 220 (breakglass): HOST_ADMIN_WORKSTATION + **ROLE_ADMIN_CLIENTS** → ROLE_ADMIN_TARGETS:PORT_ADMIN_BREAKGLASS (incl 22). Broader than the single workstation the plan expected.
- seq 270: HOST_SKYNET_OPS → ROLE_SKYNET_OPS_TARGETS:22 (BROAD: proxmox/firewall/resolvers/unraid/authentik/pbs/docker-dmz).
- seq 370: HOST_SKYNET_OPS → ROLE_OPS_SSH_TARGETS:ssh (NARROW: 10.10.100.15 + HOST_PBS).
- **270 and 370 are redundant** for ops→.15:22, and 270 is far broader than the design's intended ops-SSH surface (ROLE_OPS_SSH_TARGETS). Candidate: retire 270 / narrow ROLE_SKYNET_OPS_TARGETS, leaving ops SSH governed by the narrow 370 — pending confirmation nothing relies on 270's reach.

Host layer (sshd on .15; effective values inferred from Include first-match-wins, sshd -T needs root):
- Main /etc/ssh/sshd_config: line 12 `Include sshd_config.d/*.conf`; line 33 `PermitRootLogin yes`; line 57 `PasswordAuthentication yes`.
- Drop-in /etc/ssh/sshd_config.d/90-skynet-ops.conf: `AuthorizedPrincipalsFile /etc/ssh/auth_principals/%u`; `PermitRootLogin prohibit-password`.
- Include sits at line 12 (before 33/57) → drop-in wins: **effective PermitRootLogin = prohibit-password ✓**. The `PermitRootLogin yes` at line 33 is DEAD but a latent footgun (remove/comment it).
- **PasswordAuthentication = yes** (only set in main; drop-in doesn't override) → password login enabled for non-root users. svc-ops + aliammar are both in the docker group (docker-group ≈ root), so a password becomes a ≈root path. Recommend `PasswordAuthentication no`.
- TrustedUserCAKeys /etc/ssh/skynet_ops_ca.pub ✓; auth_principals/root = `ops-root-vm-docker-dmz`, `ops-root-all` (the granted-root cert mechanism) ✓.
- docker group = {aliammar, svc-ops} — known/accepted docker-group≈root surface.
- ROLE_OPS_PRIV_TARGETS **empty** ✓ (dormant T3 alias).

## Actions & outcomes
- re-collected firewall mirror (now reflects Ali's rule 240 HOST_SKYNET_OPS amendment)
- ingress path analyzed → segmentation holds; rule 250 intra-VLAN-moot; ROLE_APP_ORIGINS drift (stale .20.63, missing .95); rule 830 over-broad for apps Caddy
- .15:22 reach mapped (rules 220/270/370) → 270⇄370 redundancy + 270 over-broad
- host sshd audited → PasswordAuthentication=yes (finding); PermitRootLogin effective prohibit-password (dead `yes` footgun); CA/principals correct

## Graveyard — tried & abandoned
- `sshd -T` for effective config → needs root (sudo -n failed as svc-ops); inferred effective values
  from Include order instead. A short root grant would confirm definitively.

## Follow-ups / open threads — PROPOSED DELTA (Ali applies)
Firewall (T3, OPNsense):
- LP-1: prune 10.10.20.63 from ROLE_APP_ORIGINS (stale); add 10.10.100.95 (obsidian) for accuracy.
- LP-2 (optional): remove HOST_PROXY_APPS from rule 830 source (apps Caddy needs no :53).
- LP-3: retire rule 270 / narrow ROLE_SKYNET_OPS_TARGETS (redundant with 370, over-broad) — confirm nothing relies on it first.
Host sshd (vm-docker-dmz):
- H-1: PasswordAuthentication no (drop-in).
- H-2: remove stray `PermitRootLogin yes` from main sshd_config.
Then re-collect the mirror; confirm docs regen clean + drift green.

## Update — delta applied & verified (same session)
Ali applied the firewall delta on OPNsense and granted `gr vm-docker-dmz` for the sshd work.
- **Firewall (verified via a fresh `gh` clone of skynet-opnsense → collect-firewall.sh; the root mirror
  at /opt/skynet-ops/mirror lags and its https pull has no creds in-context):** rule 250 + the whole
  `ROLE_APP_ORIGINS` alias + `PORT_APP_BACKENDS` **deleted** (Ali chose full removal — the rule guarded
  nothing real since all origins are intra-DMZ); rule 270 + `ROLE_SKYNET_OPS_TARGETS` **deleted**; rule
  830 source trimmed to `HOST_PROXY_ADMIN, ROLE_DNS_RESOLVERS` (no `HOST_PROXY_APPS`). rule 240 keeps
  the ops amendment; rule 370 remains the sole (narrow) ops-SSH rule.
- **Host sshd (under the grant, applied by the agent):** added `PasswordAuthentication no` to
  `/etc/ssh/sshd_config.d/90-skynet-ops.conf`; commented the stray `PermitRootLogin yes` / `PasswordAuthentication yes`
  in the distro main config; `sshd -t` OK; `systemctl reload ssh`. `sshd -T` confirms:
  `passwordauthentication no`, `permitrootlogin without-password`, `pubkeyauthentication yes`,
  `kbdinteractiveauthentication no`. No lockout — fresh svc-ops (pubkey) + root (cert) both authenticate.
  Timestamped backups left on the host.
- Re-collected the mirror + regenerated the firewall-derived docs (00/10/20); `check-invariants` green.
- **Mirror-lag gotcha (reusable):** the collector's default source `/opt/skynet-ops/mirror/skynet-opnsense/config.xml`
  only refreshes when os-git-backup pushes AND the mirror pulls; the in-context git pull fails (https, no
  creds). Fastest fresh read: `gh repo clone aliammar03/skynet-opnsense` then
  `collect-firewall.sh <clone>/config.xml`.
