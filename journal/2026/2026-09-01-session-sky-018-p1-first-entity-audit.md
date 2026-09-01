---
date: 2026-09-01
kind: session          # session | incident | decision
title: SKY-018 P1 first entity audit
tier_touched: [T1]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [SKY-018, SKY-015, ADR-0001, ADR-0003]  # SKY-###, PR #NNN, ADR NNNN, hosts — anything to cross-link
---

# 2026-09-01 · session · SKY-018 P1 first entity audit

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Started SKY-018 (promoted ideas -> projects, branch `phase/sky-018-p1-entity-spine`). Built L0:
the entity derivation + the first audit. New files: `scripts/entity.sh` (sourceable helper, five
classes), `lab.json` (seed — only the docker host-label -> VMID map so far), `scripts/audit-entities.sh`
+ `bin/ops entities`, `tests/entity-test.sh` (wired into CI + pre-commit). All T1, additive.

`bin/ops entities` exits non-zero (a running entity has no home). Guest buckets came out
**7 matched / 5 stale / 3 running-unmapped / 4 exception** (= 19 guests), services **10 matched /
1 running-unmapped**.

Reconciliation vs the directive's hand-count ("14 matched / 4 stale / 1 running-unmapped"): the
directive folded the 4 declared T3 exceptions (2020, 5001, 635, 837) into "matched" and hand-triaged
CT 101 + VM 999 into the stale list even though both are *running*. The machine can't know 101/999
are known leftovers without that being authored, so the tool honestly reports them as
running-unmapped. Net finding is identical: **CT 526 (UniFi controller) is the one surprise running
hole**; CT 101 and VM 999 are running leftovers; `svc/arcane-manager` is the undeclared service. No
code was bent to hit the directive's numbers.

Two derivation facts that surfaced while writing the parser:
- **VM 999 is not off-convention.** It parses cleanly as legacy VLAN 90 (`9`->90), octet 99 ->
  `10.10.90.99`. It's valid-but-unmapped (that IP is in no firewall alias), which is why it's a hole,
  not a parse error. My first test asserted rc1 (off-convention) and was wrong — corrected to assert
  the derived address, and added a synthetic `4001` (VLAN 40 hosts no guest) for the real rc1 case.
- **CT 1035 is genuinely ambiguous by digit parsing** (prefix `10` = VLAN 10 canonical *or* VLAN 100
  legacy, both declared). The audit resolves it by asking which candidate IP the firewall knows:
  `10.10.100.35` is `HOST_PROXY_APPS`, `10.10.10.35` is nothing -> VLAN 100. `vmid_to_ip` itself
  returns rc2 (ambiguous, prints nothing) and leaves the resolution to the caller.

## Actions & outcomes
- `bin/plan start SKY-018` -> projects/, status in-progress, roadmap refreshed.
- `scripts/entity.sh` -> `vmid_to_ip`/`ip_to_vmid`/`vlan_of_vmid`/`guest_id`/`svc_id`/`node_id`/
  `vhost_id`/`net_id`. Canonical (10015=VLAN100) + legacy (240=VLAN20) forms; rc 0/1/2.
- `lab.json` seeded with `docker_hosts` (docker-dmz -> VMID 10015) so `service --hosted_on--> guest`
  is a data lookup, not a `vm-`-prefix string-munge. P2 expands this file.
- `bin/ops entities` -> the audit table above; exit 1 on the running-unmapped set.
- `tests/entity-test.sh` -> 28 passed / 0 failed; added as CI job `entity-derivation` + pre-commit gate 4.

## Proposals raised by the audit (NOT acted on — proposals, not actions)
- **Running-unmapped, needs a decision each:**
  - `guest/unifi-os-server-mgmt-526` (10.10.50.26) — the UniFi controller, invisible to every view.
    Expected to close in **P4** (network-gear collector + its firewall/entity mapping). The directive's
    named surprise hole.
  - `guest/debian-lan-101` (10.10.10.1) — leftover test container. Propose destroy or declare exception.
  - `guest/skynet-ops-999` (10.10.90.99) — the pre-NixOS ops brain, still running alongside 9090.
    Propose shutdown/destroy once the NixOS cutover is confirmed complete (see SKY-007 renumber thread).
  - `svc/arcane-manager` — running compose project with no `compose/arcane-manager/` in git, i.e.
    deployed outside the GitOps loop. Ali's call: bring it into the loop or declare it an exception
    with a `why` (P2's fourth invariant will force the choice).
- **Stale (stopped) cleanup proposals:** CT 231 (retired adguard-core), CT 720 (retired
  adguard-network), VM 9000 (ubuntu-2404-base template), VM 9091 (skynet-ops-nix, stopped — still
  holds firewall alias `10.10.90.91`, awaiting the 9091->9090 renumber), CT 1035 (caddy-dmz).
  - **CT 1035 carries a live dependency ⚠:** its derived address `10.10.100.35` is `HOST_PROXY_APPS`
    and `*.aliammar.net` A-records to it (front door for all apps vhosts), while `caddy-apps` actually
    runs on `guest/docker-dmz-10015` (`.15`). Establish where `.35` lives *now* before any destroy.
    `destroy` is a hard checkpoint at every autonomy level regardless. Not touched this session.

## Graveyard — tried & abandoned
- First `entity-test.sh` asserted `vmid_to_ip 999` returns rc1 (off-convention) -> abandoned: 999 is a
  valid legacy VLAN-90 derivation, not a parse failure. Replaced with an address assertion + a
  synthetic off-convention VMID (`4001`, VLAN 40, no guest).
- Considered string-munging the `vm-`/`lxc-` prefix to resolve `service --hosted_on--> guest` ->
  abandoned per the directive: the label->VMID map lives in `lab.json` so a second docker host is a
  data change, not a code change.

## Follow-ups / open threads
- **P2 next:** move the VLAN display-name map + reverse-proxy front-door alias set out of
  `render-docs.sh` into `lab.json`; add `entity_conventions` (VMID->IP law + declared exceptions) to
  `invariants.json`; add the 4th law to `check-invariants.sh` (every running entity mapped or excepted).
  arcane-manager, 101, 526, 999 must each be triaged (destroy / bring-in / declare) before the law
  can go enforcing rather than report-only.
- lab.json currently holds only `docker_hosts`; P2 owns the rest of its authored content.
- vhost + net classes have no collector yet (P5 Caddy routes, P4 network gear).
