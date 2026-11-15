---
status: accepted
date: 2026-10-24
decision-makers: Ali
---

# Authelia, one per door, with an auth mode per app

## Context and Problem Statement

The admin UIs and the apps with no login of their own need one in front of them, two apps need
single sign-on for family members, and a login reachable from the internet must not live beside
the management side.

## Considered Options

- Authelia
- Authentik (v1's)

## Decision Outcome

Chosen option: **Authelia**, one instance per door, because its config lives in git, it needs
about 50 MB, and it does OIDC, forward-auth and passkeys:
- admin Authelia on docker-admin, internal only, portal `auth`, Ali alone with two factors;
- the apps' Authelia on docker-dmz, reachable from the internet through the tunnel, portal
  `login`, with users of its own.

Each app has an auth mode: `own`, `oidc` or `forward` (`stacks/README.md` → Auth modes).

### Consequences

- Good, because the internet-facing login stays in the DMZ with the apps it guards: nothing in the
  DMZ reaches the management VLAN for it, and family accounts never exist on the admin side.
- Bad, because there are two of everything: users, secrets, sessions, and a passkey to register on
  each.
- Bad, because Authelia's login page can't be made our own. A trial of Authentik for that is an
  issue: it would supersede this record and move every OIDC client with it.

## More Information

Ali, 2026-10-21 (Authelia and the auth modes); 2026-10-24, with the apps' plan (#49): one instance
per door.
