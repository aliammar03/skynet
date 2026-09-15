# arcane-manager — Docker UI and emergency human tool

Arcane is declared here for rebuild-from-git. It can display and inspect Docker projects and may
help a human during an emergency; its Git repositories, Git Sync branch controls, source-sync POSTs,
and scheduled redeploys are not Skynet deployment authority. Existing disabled legacy sync records
may remain during deliberate per-service migration. Any `autoSync=true` record for a target service
blocks direct Skynet generation activation until the documented disable-and-drain procedure completes.

Arcane itself is a bootstrap component on `guest/docker-dmz-10015`. It is not reconciled by its own
Git Sync and remains a separately supervised human operation; do not add it as an Arcane project to
make it manage itself. The Docker socket, host binding, and persistent `/app/data` state define its
current boundary.

Its authored `.env.git` and encrypted `.env.sops` define the effective environment.
`ENCRYPTION_KEY` is load-bearing because it protects stored Arcane state; preserve the encrypted
copy for rebuild. Handle its bootstrap environment under its separate approved procedure and keep
plaintext out of commits, transcripts, and reports. Skynet's P11 Compose generation path is the
owner for Skynet-managed services; this bootstrap exception does not authorize another deployment
engine for those services.
