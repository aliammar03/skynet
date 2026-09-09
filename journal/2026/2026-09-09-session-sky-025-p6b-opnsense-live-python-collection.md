---
date: 2026-09-09
time: 17:40:00
kind: session
title: sky-025-p6b-opnsense-live-python-collection
tier_touched: [T1]
grants: []
refs: [SKY-025]
thread_status: open
---

# 2026-09-09 · session · sky-025-p6b-opnsense-live-python-collection

<!-- RAW EPISODE. -->

## What happened
Executed SKY-025 P6b (the same-phase continuation released by P6a merge #226), directly as Opus —
no Terra High, no Luna workers. Base: origin/main `b7e6f6e8e1dd69f8bbe0f54d91738f9bced4a1b8`
(includes P6a). Branch `phase/sky-025-p6b`. Stashed the pre-existing local worktree again with
`git stash push -u` before branching.

P6b is the biggest collector. Split it: **this slice = the live OPNsense collector**
(`src/skynet/opnsense.py`, replacing `collect-opnsense.sh`); **P6b-ii = the offline config.xml
mirror parser** (`collect-firewall.sh` → `src/skynet/firewall.py`), deferred. This matches the two
shell scripts and the packet phrasing "opnsense.py and an offline firewall parser."

`src/skynet/opnsense.py` produces both files the shell did, from one collection:
- `inventory/firewall/firewall.json` — user-view config: aliases (built-ins `^__.*_network$` +
  bogons/bogonsv6/sshlockout/virusprot dropped; type/content resolved from OPNsense's
  `{key:{selected}}` form or plain string), rules (intersect `firewall/filter/get` UUIDs+sequence
  with `firewall/filter/searchRule` flat fields — internal/auto rules excluded for free),
  reservations (`dnsmasq/settings/searchHost`). Added a top-level `host` for the freshness check.
- `inventory/opnsense.json` — live state: firmware (`core/firmware/status`), ARP
  (`diagnostics/interface/searchArp`), interfaces (`interfaces/overview/interfacesInfo`), and
  declared-host presence (ARP first, then ICMP for ARP-silent 10.10.x hosts). `via` is explicit:
  arp / icmp / no-arp,no-icmp / no-arp,icmp-unavailable (probe couldn't run).
- TLS: reuse `pbs.HTTPSConnection` + `pbs._sni_from_certificate` (genuine second consumer of the
  SNI-pinned transport — connect to OPN_HOST, present the cert-derived SNI, verify against the
  pinned cert as CA). Basic auth from OPN_KEY:OPN_SECRET, key/secret only in the header, fixed
  redacted diagnostics. Only the enumerated GETs + read-only search POSTs; search pages whose
  reported `total` exceeds returned rows fail as incomplete (pagination/completeness).
- Both snapshots fully validated before either is written (failure leaves both files untouched);
  `collect all` publishes both under one receipt with two markers (`collection-firewall.json`,
  `collection-opnsense.json`), both required by default status/query/entity/render + nightly.
- `collect-opnsense.sh` → forwarding shim (P22 owns removal). opnsense dropped from the shell
  `REMAINING`. `collect-firewall.sh` unchanged this slice (owned by P6b-ii).

CLI: `skynet collect opnsense --firewall-output <f> --state-output <f> [--credentials-file <f>]
[--json]`, and `--opnsense-credentials-file` on `collect all`.

Tests: `tests/test_opnsense.py` (19 cases) — full paired projection, read-endpoint allowlist,
built-in drop + type/content resolution, rule intersection, presence arp/icmp/unavailable vantage,
incomplete search page, malformed/unavailable retention of BOTH files, missing/empty/unknown/
duplicate credentials, and three real-TLS cases (SNI-from-pinned-cert read, wrong CA rejected,
missing/invalid CA). Extended test_collection.py: autouse opnsense stub (publishes both files),
both inline runners, a paired failure/recovery test, `collect-opnsense.sh not in calls`, and the
shell-caller offline row. New source/tests/fixtures added to the Nix source filter, installed
check, and pre-commit glob.

## Actions & outcomes
- `nix develop -c pytest -q tests` → 186 passed
- `ruff check src tests/test_*.py` → All checks passed; `mypy src/skynet` → 10 files clean
- `nix build .#checks.x86_64-linux.skynet` → exit 0; `nix flake check --no-build` → all checks passed
- offline doctor → exit 0; disposable status (now requiring firewall+opnsense markers) → exit 3
- opnsense `--help` shows the paired-output flags

## Graveyard — tried & abandoned
- Synthetic secrets first tripped nothing new, but the credentials-rejection test asserted
  `OPN_SECRET=$(bad)` → fail. The OPNsense parser deliberately allows shell-metachar characters in
  KEY/SECRET (base64 secrets, never eval'd — only base64'd into the Basic header), so `$(bad)` is a
  valid literal and the collection succeeded (0, not 3). Fixed the test to exercise real rejection
  paths: empty value, unknown key, duplicate key.
- mypy flagged `get()` returning Any (from `_read -> Any`); typed `_read -> dict[str, Any]` after its
  `isinstance(payload, dict)` narrowing.
- Reused `pbs.HTTPSConnection`/`pbs._sni_from_certificate` by import rather than extracting a shared
  transport module — the packet permits extraction "only where a consumer warrants," and importing
  avoids churning pbs.py + its P5 tests. A clean extraction is a later-phase cleanup if the reviewer
  prefers it.

## Follow-ups / open threads
- **P6b-ii is the remaining same-phase work:** `src/skynet/firewall.py` offline config.xml parser
  (redact sensitive tags, retain source provenance, avoid implicit git pulls, never satisfy live
  freshness), `collect-firewall.sh` → shim, `skynet collect firewall`, tests/fixtures. Detail it
  after this PR merges.
- **After all P6 slices (P6a + P6b-i + P6b-ii) merge**, obtain ONE fresh review of the complete
  numbered P6 before P7. Accepted progress stays 5/24.
- **Unverified live boundary (no live reads this packet):** ICMP presence depends on the ops→
  NET_SKYNET floating rule; without it a silent host reads live:false via no-arp,no-icmp (recorded
  as vantage, not proven-down). Pagination completeness assumes OPNsense returns `total`; if an
  endpoint omits it, completeness isn't enforced — acceptable for the fixed 2000-row budget, noted
  for the live transition.
- Restore the local worktree: `git stash pop` after leaving this branch.
