# ADR 0006 — OPNsense read is T1; changing OPNsense stays T3, never-standing

- **Status:** accepted
- **Date:** 2026-09-01

## Context

The original hard law (§2a, AGENTS.md §6) was blunt: **"no standing route or credential to
OPNsense."** Not even read. To get any firewall visibility at all, Skynet reads OPNsense **indirectly**
through a git mirror — the `os-git-backup` plugin commits `config.xml` on every change and pushes it to
the `skynet-opnsense` repo, and `collect-firewall.sh` parses that mirror.

That indirection is the source of recurring operational friction. `os-git-backup` **pushes to the
remote nightly by default** ([OPNsense docs](https://docs.opnsense.org/manual/git-backup.html)); a
config change is committed locally at once but does not reach the mirror — and therefore the agent's
inventory and generated docs — until the nightly push or a manual one. In practice this meant the
firewall map was routinely hours stale, drift the agent surfaced could not be re-verified promptly,
and closing the gap required a `*/5` cron on the Remote Backup action plus debugging why a hand-made
change hadn't propagated. The mirror is a clever way to hold "zero credential on the firewall," but it
buys that property with a freshness tax the operator kept paying.

**The safety property the invariant actually protects is that the agent can never *change* the
firewall.** A read-only credential does not grant that. The blanket "no credential, not even read"
was stricter than the threat model requires: it conflated *reading* the device (harmless to the trust
boundary) with *operating* it (the thing that must stay human-only).

Every other T3-adjacent device already resolves this the same way — a **view/modify split**:
Technitium (Zones view/modify T2, server settings T3), Authentik (app+provider T2, admin T3),
Cloudflare (DNS records T2, account T3). OPNsense was the lone device with **no** read tier at all.

## Decision

Split OPNsense the same way, one notch lower because the firewall is the trust boundary itself:

- **OPNsense *read* is T1** — a **standing, scoped, read-only** API credential. The agent reads
  aliases, rules, interfaces, DHCP, and neighbour/ARP state directly and live.
- **Everything that *changes* OPNsense stays T3, never-standing** — rules, aliases, DHCP, settings,
  root shell. Reached only via the dormant alias + per-session credentials, revoked same day. **No
  standing *write* credential to OPNsense, ever.** This half of the old invariant is unchanged.

**The read-only guarantee is real, if configured correctly.** OPNsense's `user-config-readonly`
privilege — shown in the group's Assigned Privileges list as **"System: Deny config write"** (not
"read only", which is why it is easy to miss) — makes `ApiControllerBase::throwReadOnly()` block
every MVC/API write regardless of page privileges, so a user with it can GET firewall config but
cannot POST changes. One caveat, from
advisory [GHSA-p9pr-782r-w2xw](https://github.com/opnsense/core/security/advisories/GHSA-p9pr-782r-w2xw):
that guard is **bypassable if the privilege is assigned directly on the user**, so it must be granted
**via a group**, and OPNsense must be **≥ 26.1.11 / 26.4.1p1**. Exact recipe in
[access-and-trust](access-and-trust.md). This matters: without it, "read-only" would be enforced only
by the collector's good behaviour, not by OPNsense — which would quietly make the credential a
standing *write* path and violate the very invariant this ADR preserves.

Two constraints keep the read half clean:

- **Scoped, secret-stripping reads.** `config.xml` carries secrets (VPN keys, password hashes). The
  collector reads **scoped endpoints** (firewall aliases/rules, interfaces, DHCP leases) via a
  read-only API user and never writes a sensitive field into `inventory/` — the same secret-stripping
  the mirror parser already does. A read credential must not become a secret-exfiltration path.
- **The git mirror stays.** It still satisfies the rebuild-from-git law (§2a: system state
  reconstructable from the repo, `config.xml` included) and disaster recovery. Live API read is for
  **freshness**; the mirror remains the **source-of-truth-in-git**. Belt and suspenders.

## Consequences

- The §2a hard law is reworded from "no standing route or credential to OPNsense" to "no standing
  **write** credential to OPNsense; a scoped read-only credential is T1." The write boundary — the
  load-bearing half — is untouched. `invariants.json` `t3_targets` reflects the read/write split.
- Ali creates the read-only OPNsense API user (a T3 act — the agent cannot mint access to the
  firewall); the key is stored sops-nix (`opnsense.env`), same shape as the Proxmox/Omada creds.
- `collect-firewall.sh` gains a live-API path and keeps the mirror parse as a fallback, so it still
  degrades to the mirror (and to `exit 0` with no creds) — no hard dependency on the new credential.
- This is a **write-boundary-preserving** change, but it *is* a change to a §2a hard law and to
  `invariants.json`, so it is **human-merged** (never agent-self-merged) — like every leash change.
- Trade-off accepted: a standing read credential to the firewall is a small foothold on the most
  sensitive device. It is bounded by read-only scope, secret-stripping, and same-day revocability,
  and it removes a recurring freshness failure that was itself an operational risk (stale firewall
  truth the agent reasons over).

## Alternatives considered

- **Keep the mirror, just tune the cron** (`*/5` Remote Backup). Reduces the lag but doesn't remove
  it, keeps a second moving part (the plugin + its auth) in the read path, and still routes firewall
  truth through GitHub. Rejected as papering over the indirection.
- **A T2 read/write OPNsense token** (like Technitium zones). Rejected outright: the firewall is the
  enforcement boundary for the whole lab; a standing credential that can change it is exactly what the
  invariant exists to forbid, and nothing here justifies moving that line.
