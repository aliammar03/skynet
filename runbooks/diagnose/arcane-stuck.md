---
summary: "Diagnose a legacy Arcane auto-sync writer or an externally managed Compose project visible in Arcane."
trigger: "Arcane scheduling blocks Skynet takeover or Arcane UI disagrees with Docker"
tier: "T1/T2"
executor: "Arcane read API, skynet deploy status, and Docker inspection"
rollback: "No mutation during diagnosis; use retained-generation rollback only on explicit request"
---

# Diagnose — Arcane legacy sync or UI mismatch

**Tier:** T1 observation; T2 only if the separately approved migration disables legacy auto-sync.
Arcane is a useful UI and emergency human tool, but its Git Sync status, `lastSyncAt`, and
`lastSyncStatus` are not Skynet deployment identity or success evidence.

## Inspect

```bash
skynet deploy status <service> --json
skynet verify deployment <service> <expected-full-revision> --json
```

Compare the protected generation release manifest and state pointers with actual Docker Compose
project/config-file/working-directory labels and complete container health. An old Arcane-managed
project may still have config-file/working-directory labels under
`/opt/docker/arcane-projects/<service>`; that is not a Skynet generation and requires deliberate
first takeover. An externally Compose-managed project may or may not be displayed by Arcane; Docker
evidence is authoritative.

If `skynet deploy service` refuses `autoSync=true`, identify that service's legacy Arcane sync through
the scoped read API. Disable scheduling only under an approved T2 migration plan while old source and
effective environment still agree. Wait the deployed maximum sync duration, never less than five
minutes, and verify the old running revision and container/route state. A disabled record can remain.
Do not repoint Arcane branches, manually trigger sync, or delete sync metadata to make deployment
proceed. If the old revision or drain cannot be proved, stop and record the blocker.

## Recovery

A failed Skynet candidate leaves `stable` as the explicit retained rollback candidate. Inspect
`skynet deploy status`, then use `skynet rollback service <service> [--to <full-revision>] --apply`
only under an explicit runtime rollback plan. That action does not change Git; make an authored
correction through the normal reviewed PR path. Record concrete Docker/operation evidence in a raw
`journal/` incident entry.
