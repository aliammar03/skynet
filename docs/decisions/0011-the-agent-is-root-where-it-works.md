---
status: accepted
date: 2026-11-15
decision-makers: Ali
---

# The agent is root on the hosts it works on, and never merges

## Context and Problem Statement

The agent diagnoses and fixes. Fixing needs hands where the work happens: the apps' host, the
backups, the DNS servers, the admin host. Without them every fix is a step for Ali. And any Nix or
stack file that merges runs as root on its host anyway, so no file in git walls the agent off from
a host.

## Decision Outcome

Chosen option: the agent never merges, and it is **root on docker-admin, docker-dmz, PBS
(VM 2040), technitium-network and technitium-core**:
- on the NixOS hosts, passwordless sudo (`agentRoot` in `modules/base.nix`), every command in the
  host's journal; with it the host's key and secrets, and on the Docker hosts their Docker socket;
- on PBS, root over SSH from ops only;
- on both doco-cd MCP servers, restarting projects and stacks, running jobs and compacting
  mirrors. Destroying a project or removing a stack asks Ali each time, and so does removing a
  backup, namespace or datastore on PBS;
- an Alertmanager silence for its own planned work, ending within 4 hours, its comment naming the
  work.

It never prints a secret value or decrypts one on purpose. Everywhere else it has no sudo, no
Docker socket and no private age key; on ops, its home, it is a plain user. While it installs a
host it is root on the installer, which holds the new host key that `--copy-host-keys` keeps; it
reads only the public half. Because what bounds it is an undo it can't delete (ADR-0015), the
gates every merge passes (ADR-0013) and the credentials it doesn't hold, not a host it can't touch.

### Consequences

- Good, because operate work (a restart, a restore, a capture on a DNS server, PBS's drills) needs
  no step from Ali, and a host installs in one PR (`runbooks/new-vm.md`).
- Bad, because as root it could read every secret on those hosts: admin Authelia's, caddy-admin's
  Cloudflare token, the Drive tokens. It doesn't, and every sudo command is in the journal
  (`journalctl _COMM=sudo`).
- Bad, because "never merge" is a soft wall outside the code owners' files (ADR-0013).

## More Information

- 2026-10-21, at the start: the agent never merges, never holds a private age key, never gets a
  Docker socket.
- 2026-10-24, Ali: root on docker-dmz (#52), where operate work happens, and on PBS (#73), where
  the offsite copy and its drills happen.
- 2026-10-27: the silences, with the alerts PR (#91).
- 2026-10-28, Ali (#107): root on both DNS servers. What they refuse or drop shows only on the host,
  in a capture, and they hold no secret but their own admin password and the `#alerts` webhook.
- 2026-11-12, Ali, with the autonomy plan: root on docker-admin too, which holds admin Authelia's
  secrets, caddy-admin's Cloudflare token and the offsite job's Drive token. Live 2026-11-15, with
  docker-admin's doco-cd restart and job tools (#190).

The verbs still planned (a PVE token for power, merges through the gates) are in
`docs/plans/autonomy.md`.
