---
status: accepted
date: 2026-10-24
decision-makers: Ali
---

# Offsite is Google Drive, through rclone with Ali's own OAuth client

## Context and Problem Statement

Every backup needs a copy outside the house. Ali has Google Drive (2 TiB).

## Considered Options

- rclone's shared OAuth client: it stops working during 2026;
- a Google service account: it has no storage on a personal Drive;
- Ali's own OAuth client, in Testing: Google expires its refresh tokens after 7 days;
- Ali's own OAuth client, published to production, scope `drive.file`.

## Decision Outcome

Chosen option: Google Drive through **rclone** with Ali's own OAuth client, scope **`drive.file`**,
**published to production**, because Drive is what Ali has, a published client's token doesn't
expire, and `drive.file` lets rclone see only the files it created.

### Consequences

- Good, because the token reaches nothing else in Ali's Drive.
- Bad, because Drive limits a client to 750 GiB uploaded a day, about 2 new files a second and 10
  requests a second: restic writes 64 MiB packs, and the datastore's copy resumes night after night
  (`--max-transfer 700G`).
- Bad, because the token sits in the backup stacks on both Docker hosts, where the agent is root,
  so Drive isn't out of the agent's reach. The copy that is: ADR-0015.

## More Information

Ali, 2026-10-21 (Drive, a published client of his own); 2026-10-24, with the backups plan (#72):
scope `drive.file`. Making the client, and a new token: `runbooks/drive-access.md`.
