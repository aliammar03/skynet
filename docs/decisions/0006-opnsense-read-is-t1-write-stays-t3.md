# ADR 0006 — OPNsense tiered: read+diagnostics T1, config T2 (PR-gated via tofu), self-leash & reboot T3

- **Status:** accepted
- **Date:** 2026-09-01

## Context

The original hard law (§2a, AGENTS.md §6) was blunt: **"no standing route or credential to
OPNsense."** Not even read. To get any firewall visibility at all, Skynet reads OPNsense **indirectly**
through a git mirror — the `os-git-backup` plugin commits `config.xml` on every change and pushes it to
the `skynet-opnsense` repo, and `collect-firewall.sh` parses that mirror.

That indirection is a recurring freshness tax. `os-git-backup` **pushes to the remote nightly by
default** ([OPNsense docs](https://docs.opnsense.org/manual/git-backup.html)); a change is committed
locally at once but does not reach the mirror — and therefore the agent's inventory and docs — until
the nightly push or a manual one. The firewall map was routinely hours stale, and drift the agent
surfaced could not be re-verified promptly.

Two facts reframe how strict the credential rule needs to be:

1. **The box already holds every firewall secret.** `os-git-backup` mirrors the **raw `config.xml`**
   (VPN keys, PSKs, password hashes) into the repo the ops VM clones. So "a credential must not read
   secrets" was guarding a door while the wall was already open — the ops VM has the full config today.
2. **The safety property that matters is not *reading* the firewall, it is *who decides* what it
   enforces.** The firewall is the meta-boundary: its rules define what every other tier can reach.
   The thing to protect is that a *human stays in the loop on changes to that policy* — not that the
   agent is blind to it.

Every other device already resolves access as a **tiered split**: Technitium (Zones T2, settings T3),
Authentik (app+provider T2, admin T3), Cloudflare (DNS records T2, account T3). OPNsense was the lone
device with no read tier and no operate tier at all.

## Decision

Tier OPNsense like the rest, using the mechanisms the lab already runs:

- **T1 — read + non-mutating diagnostics.** A standing, scoped API credential (`svc-skynet-recon`,
  group `skynet-recon`) reads aliases, rules, interfaces, DHCP, and neighbour state live, and runs
  observe-or-probe diagnostics (ping, traceroute, DNS lookup, ARP/route/state tables, logs). "Read"
  here means *changes no state*, which is why non-mutating diagnostics ride this tier.
- **T2 — firewall config, PR-gated, via OpenTofu.** Firewall aliases and rules become `tofu/`
  resources managed through the **OPNsense tofu provider**. A change is a `tofu plan` diff **in a PR**;
  a human merges; `apply` pushes it via the API. This is the **same T2 model as tofu for guests
  (SKY-008)** — a standing write credential, but every change is a human-merged plan. Non-destructive
  maintenance (service restart, apply-config, flush states/leases) is T2 too.
- **T3 — never standing.** OPNsense **node root**; the **account/API-key/cert admin**; **reboot/halt**
  (a lab-wide outage — destructive-class, a hard checkpoint at *every* tier, §9); and — the load-bearing
  carve-out — **the agent's own leash.**

### The self-leash carve-out (the one that makes T2 safe here)

A firewall that the agent can shape is a firewall the agent could use to widen its *own* reach. So,
however autonomous firewall config becomes:

- **The agent may never change the rules/aliases that bound its own access** — `ROLE_OPS_*`,
  `ROLE_OPS_PRIV_TARGETS` (the dormant T3 slot), the "block other DNS" rules, or the `svc-skynet-recon`
  / tofu accounts themselves. This is the §6 "never widen your own leash" invariant applied to the
  firewall: such changes are **human-merged forever**, never eligible for the autonomy ratchet.
- Two things enforce it: (1) *every* T2 firewall change is a human-merged PR, so a human is in the
  loop on any plan touching the leash; and (2) a **machine gate** — the conftest/Rego policy over
  `tofu plan -json` that **SKY-018 P7 already specifies** — hard-denies a plan that touches the
  self-leash set, so a merge-by-mistake still fails closed.

Reboot stays a hard checkpoint because it drops the whole network; it is never auto-approved.

## Consequences

- **§2a hard law reworded** from "no standing route or credential to OPNsense" to "no standing route
  or credential that can **change** OPNsense **beyond PR-gated T2 config**; node root, account/cert
  admin, reboot, and the agent's own leash stay T3/never-standing." `invariants.json` `t3_targets`
  reflects the split, and the self-leash set is named as a never-auto boundary.
- **This is a big, directive-sized build, captured as its own directive** (firewall-as-code): adopt
  the OPNsense tofu provider, import the current 41 aliases / 29 rules as resources, wire the P7
  self-leash gate, and test apply + rollback in the failure case before any of it graduates off
  human-merge. The T1 read credential + live collector is the near-term slice and ships first.
- Two OPNsense credentials, both Ali-minted (the agent cannot mint firewall access): the T1
  `svc-skynet-recon` (read + diagnostics, "System: Deny config write" via a group), and a T2 write
  credential used **only** by `scripts/tofu-apply.sh <saved-plan>` after a merged PR and explicit
  review of that plan. Both sops-nix (`opnsense.env`), same
  shape as the Proxmox/Omada creds.
- **The live API is the collector; the git mirror is retired to DR-only.** `collect-opnsense.sh`
  writes the canonical firewall inventory (`firewall.json` + `opnsense.json`) live — no push lag; the
  mirror parser `collect-firewall.sh` leaves the nightly loop and stays as the offline/DR parser. The
  `config.xml` mirror is retained as the **rebuild-from-git DR source** (§2a: OPNsense reconstructable
  from git), not the observed-truth reader. (Refined 2026-09-01 after P1 proved the live read; Ali's
  call — the mirror already holds every secret the box does, so live-as-primary loses nothing.)
- This changes a §2a hard law + `invariants.json`, so it is **human-merged forever** (never
  agent-self-merged), like every leash change.

## Alternatives considered

- **Keep OPNsense fully T3, read via the mirror only.** The status quo. Rejected: the freshness tax is
  real and recurring, and it keeps the agent unable to help maintain the one device it most often needs
  to reason about — counter to the full-agent-control goal (ADR 0005).
- **Config as raw `config.xml` restore** (edit the mirrored file → push). Rejected: `config.xml`
  restore is an all-or-nothing replace, fragile and unreviewable at the diff level. The tofu provider
  gives resource-level plans that read like every other T2 change.
- **A single T2 read/write token, no self-leash gate.** Rejected: without the P7 gate and the
  human-merge-forever pin on the leash set, a standing firewall-write credential could rewrite the
  rules bounding the agent — the exact thing §6 forbids.
