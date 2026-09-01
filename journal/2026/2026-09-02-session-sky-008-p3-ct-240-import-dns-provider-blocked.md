---
date: 2026-09-02
kind: session          # session | incident | decision
title: SKY-008 P3 — CT 240 import + DNS provider blocked
tier_touched: [T1, T2]  # T1 reads (PVE config, Technitium get); T2 DNS write (add + rollback attempt)
grants: []              # no root grants
refs: [SKY-008, PR #143, SKY-018, SKY-020]
---

# 2026-09-02 · session · SKY-008 P3 — CT 240 import + DNS provider blocked

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Resumed SKY-008 P3 on branch `phase/sky-008-p3-dns-and-lxc-import`. Two parts: Technitium DNS
record via tofu, and a zero-drift LXC import of CT 240. Baseline `tofu plan` was clean.

**Part 2 (LXC import) went first, smoothly.** Pulled CT 240 live config from the PVE API
(`/nodes/server-proxmox-core/lxc/240/config`) with the PVEAuditor token. Wrote
`proxmox_virtual_environment_container.pbs` in `tofu/lxc-pbs.tf`, `tofu import server-proxmox-core/240`.
First `plan` wanted a **destroy+create replacement** — culprit `+ pool_id = "ops-managed" # forces
replacement`: bpg does NOT read pool membership back on import, so declaring it reads as a change.
Added `pool_id` to ignore_changes → dropped to update-in-place. Remaining real diff was a `- console`
block (bpg imported enabled/tty_count=2/type=tty; my config had none → "remove console" = a live
mutation), so I declared a matching `console {}`. Then only state-metadata phantoms remained:
`+ vm_id` (import sets `id` not `vm_id`) and `+ timeout_*` (schema defaults, never sent to PVE).
Added those to ignore_changes → `plan` = No changes. `timeout_start` throws a benign "Deprecated
attribute" warning but must stay ignored or the phantom `+` returns. Zero-drift achieved.

**Part 1 (DNS) proved the write then hit a wall.** Chose test record
`tofu-test.tdns.home.aliammar.net A 192.0.2.1` (RFC 5737) in the Primary zone. Wired provider
`kevynb/technitium` v0.4.0, `url`+`token` vars from `tofu-env.sh`, technitium.crt into the
SSL_CERT_FILE bundle. First `apply` errored: `cannot decode JSON response ... EOF`. Record NOT
created. Cause: I set `url=https://HOST:53443/api` but the provider's client PREPENDS `/api` itself
(`DOMAINS_URL="/api/zones/records"` in client.go) → `.../api/api/...` → 404 → empty body → EOF.
Dropped `/api` from the url → re-apply succeeded, record live (Technitium auto-signed it with
RRSIG/NSEC since the zone is DNSSEC). But the very next `plan` errored on **read**:
`cannot unmarshal number into ... rData.protocol of type string`. The provider's Read does
`GetRecords` with `listZone=true` (whole zone) and the zone has two `DNSKEY` records with numeric
`protocol: 3`. v0.4.0 types that field as string. Fix is on `main` (commit `b2f6b89c`,
"Protocol is number not string", 2026-08-20) but there is NO release with it — v0.4.0 (2026-01-22)
is latest. Our only writable primary zone is DNSSEC-signed → no unsigned zone to dodge it.

Asked Ali: defer DNS / build fixed provider via Nix / switch to restapi. Ali chose **defer DNS,
land LXC now**. Reverted all technitium tofu scaffolding (git checkout the 5 touched files + rm
dns-records.tf), re-init, `plan` = No changes. Committed lxc-pbs.tf + directive → PR #143.

## Actions & outcomes
- `tofu import ... container.pbs server-proxmox-core/240` → imported, then iterated ignore_changes → **zero-drift plan**
- `tofu apply -target=technitium_record.tofu_test` (url with /api) → EOF error, no record
- fixed url (no /api), re-apply → **record created live** (verified via zones/records/get)
- `tofu plan` after → **read crash** on DNSKEY.protocol (v0.4.0 DNSSEC incompatibility)
- attempted rollback: `zones/records/delete` via API → **"Access was denied"** (token lacks record-delete)
- confirmed perm-not-param: delete of a non-existent name also "Access denied"
- `tofu state rm technitium_record.tofu_test` → state clean; reverted scaffolding; PR #143 (LXC only)

## Graveyard — tried & abandoned
- `url = https://HOST:53443/api` for the technitium provider → abandoned: client prepends `/api`, double-path 404/EOF.
- Pinning the technitium cert via a provider cacert arg → none exists; only `skip_certificate_verification`. Used SSL_CERT_FILE bundle instead (worked for the write).
- Deleting the leftover test record with the scoped token → abandoned: token has add/modify but not delete. Needs Ali.
- Using kevynb v0.4.0 against our zone at all → abandoned for now: DNSSEC-signed zone read is broken until a release carries b2f6b89c.

## Follow-ups / open threads
- **Ali action:** delete the leftover live record `tofu-test.tdns.home.aliammar.net A 192.0.2.1`, and add record-delete to the scoped Technitium token (the DNS phase needs it for `tofu destroy`).
- **DNS resume trigger:** kevynb/technitium cuts a release containing `b2f6b89c`, then re-pin + finish (full recipe in [[SKY-008-progress]]). Or Nix-buildGoModule that commit if we want it sooner.
- The CT 240 import recipe (ignore_changes shape + console-match) is the template SKY-018 P11 and SKY-020 reuse.
