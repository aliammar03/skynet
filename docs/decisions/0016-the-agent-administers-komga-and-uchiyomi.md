---
status: accepted
date: 2026-10-29
decision-makers: Ali
---

# The agent administers Komga and Uchiyomi through their APIs

## Context and Problem Statement

Ali asked (2026-10-29): "configure the services for me". Komga's and Uchiyomi's settings live in
their own databases, not in files git could hold, and both do everything their web apps do over
documented APIs.

## Decision Outcome

Chosen option: the agent **administers Komga and Uchiyomi** through their APIs, with an admin
account of its own in each: libraries, sources, extensions, series, settings, users' roles. The
passwords are agent-generated, encrypted to Ali and ops (`hosts/ops/komga.sops.yaml`,
`hosts/ops/uchiyomi.sops.yaml`), and rendered on ops for its calls. What can live in git (their
environment) still does. Deleting a series' files, a library or an account asks Ali each time.

### Consequences

- Good, because Ali asks in chat and the agent does it.
- Bad, because what the agent sets lives in the apps' databases: it comes back with their data,
  not from git.
- Neutral, because the library's day to day (adding and filling series) is the comics agent's
  (ADR-0017). This agent keeps the admin.

## More Information

Ali, 2026-10-29, with the comics and manga plan (#118). The accounts: `hosts/ops/README.md`,
`stacks/dmz/komga/README.md`, `stacks/dmz/uchiyomi/README.md`.
