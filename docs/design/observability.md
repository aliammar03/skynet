---
summary: "How machine state becomes human-readable docs, and how the nightly run keeps the picture current."
---

# Spoke · Observability

> How Skynet turns machine state into things a human can read, and how the nightly run keeps the
> picture current. Governed by [`../system-design.md`](../system-design.md).

## Inventory → human-readable docs

`skynet render docs` turns validated `inventory/*.json` observations into
[`../generated/`](../generated/) — Obsidian-flavored markdown with frontmatter, callouts,
wikilinks, and **Mermaid diagrams Obsidian renders natively**, drawn from live data and never
hand-maintained:

```
00-network-map.md      # mermaid: WANs → OPNsense → VLANs → hosts
05-state-of-the-lab.md # human narrative, LLM-authored nightly (surfaced in README)
06-agent-digest.md     # recent-activity / episodic / open-thread retrieval, skynet render digest
07-context-map.md      # on-demand load-cost / context-routing index, skynet render context
10-vlans.md            # per-VLAN tables linking to host pages
20-firewall.md         # rules/aliases from the LIVE OPNsense API (skynet collect opnsense); mirror = DR only
30-services/<svc>.md   # IP, ports, front door, backup status, last deploy
40-hosts/<host>.md     # guests per node, resources, pool membership
90-backup-status.md    # last restic/PBS runs, snapshot counts, grant audit
```

`inventory/` and `docs/generated/` are **machine-owned — never hand-edited** (a constitution
invariant). Default rendering requires matching successful core and network observation, ACL, PBS,
Docker, DNS, paired live OPNsense, and Omada evidence no
older than 36 hours and one matching local attempt receipt; the nightly additionally requires an
attempt from its current pass. Missing or unwritable receipt storage is unavailable. A failed node
refresh leaves that snapshot and prior pages intact and records a failure, rather than refreshing their
presentation. PBS status, group, snapshot, and verification fields are complete before rendering;
null data cannot become a zero-backup claim, and failed or unknown verification cannot produce
a successful backup callout. Technitium DNS collection validates the zone listing and every zone's
record list before publishing; a null or missing record list fails rather than becoming an empty
successful snapshot. Live OPNsense collection reads only enumerated GETs and read-only search POSTs,
validates search-page completeness, and binds the user-view firewall config and live
state (firmware/ARP/interfaces/presence) to one attempt receipt. Each file is replaced atomically;
a publication failure can leave a partial pair, which the freshness gate refuses. Neither is
blessed fresh without the other, and
declared-host presence records an explicit ARP/ICMP vantage. The live OPNsense API is the sole
firewall inventory source; the `config.xml` git backup is kept only as disaster-recovery material
(restored as configuration, not parsed into inventory). Omada's Viewer-only HTTPS reads validate
the controller, sites, device and required switch-port responses before its legacy network-gear
schema is atomically replaced and receipt-bound. Collection timestamps
describe observations, not live service-health verification.
Failed initial marker publication also invalidates previous success for default queries and
rendering. Factual pages are built in a staged copy before the generated tree is replaced as one
publication unit; replacement failure rolls the prior tree back, and render/cache/input failure leaves
the previous page set unchanged. Uncertain Docker reader cleanup blocks another collection
pending local process recovery. The package's
[evidence and process contract](../../nix/README.md) defines storage and recovery behavior.

Obsidian sync uses a `skynet` clone (optionally sparse-checking out `docs/generated/`) and never
touches the CouchDB LiveSync vault. Configuration: [`obsidian-setup.md`](../obsidian-setup.md).

## The nightly run

[`nightly.md`](../../runbooks/nightly.md) defines the 03:30 `skynet-nightly.timer` flow:
deterministic preparation and finalization in [`scripts/nightly.sh`](../../scripts/nightly.sh), with
primary then fallback engines available only for the optional narrative and grant-audit stage.
Engine and model selection are in `~/.config/skynet-ops/ops.env`.

Report-only is a constitution dial: the nightly run *observes and proposes*, it does not act
outside the version-controlled auto-approve list.

## Deployment verification

`skynet verify deployment <service> [<revision>]` is the report-only observer `skynet deploy` also
runs after every apply. The expected Compose services come from rendering the service at the
revision (default: the running `skynet.revision` label). Through Docker context `docker-dmz`,
every expected service must have a container, and every container in the project must carry that
exact `skynet.revision`, be running, and report `healthy`; a missing healthcheck, a stray
container, or a missing service fails verification.

Before probing, the verifier validates the complete canonical route snapshot. Duplicate, malformed,
partial, or case-ambiguous route evidence fails closed. Declared routes for the service are probed
from Docker context `docker-dmz` on network `dmz`, resolving the apps front door at
`10.10.100.35` with the immutable image
`curlimages/curl:8.16.0@sha256:463eaf6072688fe96ac64fa623fe73e1dbe25d8ad6c34404a669ad3ce1f104b6`.
TLS must verify and the HTTP response must be 100–499; authentication responses such as 302 or
401 are reachable outcomes. A service with no declared route is reported as `skipped`, not as an
unprobed success.

Routes are read from the Caddyfile at the revision the front door runs (its own
`skynet.revision`), falling back to `origin/main`.

Verification never deploys, restarts, rolls back, edits Git, or changes persistent Docker
configuration. A routed probe creates and removes one ephemeral container and may pull/cache the
pinned image. Acting on a failed verification belongs to `skynet deploy` (see
[gitops-loop](gitops-loop.md)).

## Episodic memory — see the memory spoke

Rendered docs answer *what is true now*; they can't answer *how the lab got here, what was tried,
what failed*. That **episodic** memory — the [`journal/`](../../journal/README.md) and its generated
recent-activity/episodic/open-thread retrieval view — is its own domain, designed in the [memory](memory.md)
spoke. The only part that lives here is the *rendering*: `skynet render digest` produces the agent
digest [`../generated/06-agent-digest.md`](../generated/06-agent-digest.md) alongside the other nightly
pages (deterministic, content-stable), while `skynet render context` produces the on-demand
load-cost/context-routing index [`../generated/07-context-map.md`](../generated/07-context-map.md).
The human narrative
[`05-state-of-the-lab.md`](../generated/05-state-of-the-lab.md) is the agent-authored counterpart.

## Live health and alerts

`skynet watch` passes start every 3 minutes (`skynet-watch.timer`, `OnUnitActiveSec=3m`,
`AccuracySec=1s`; T1 read). For every non-manual service on `origin/main` it runs the
[deployment verifier](#deployment-verification) against the running `skynet.revision`, and alerts
on **state change** only:

| Change | Alert |
|---|---|
| healthy → unhealthy | after 2 consecutive failed passes (< 10 min, budget below); one message. A flap never alerts. |
| still unhealthy | one reminder a day at most |
| unhealthy → healthy | one recovery message, only if the down alert went out; an unsent one is retried |
| monitor cannot observe (no fetch, Docker unreachable, no state, `main` declares no services) | the pseudo-target `monitor`, same rule; every service keeps its state; no per-service storm |
| a pass cannot observe every service within its budget | `monitor` failure, same rule: a coverage gap is never silent |

**Latency budget (< 10 min).** A pass probes Docker once, then observes services least recently
observed first. It starts no new observation after 75 s, caps each at 60 s (`SIGALRM`; an overrun
fails that service), and pushes a service's alert as soon as that service is observed (15 s
timeout). So a pass ends within 150 s plus its final ping, inside the 3-minute interval, and the
next starts ≤ 181 s after it. Worst case: an outage that begins just after a service's healthy
observation gets its first failure in the next pass and its second, which alerts, in the one after
that: ≤ 2 × 181 + 75 + 60 + 15 ≈ 512 s. `tests/test_watch.py` simulates this with slow probes.

While a write holds the lock, only the target it is changing is skipped (a deploy mid-flight is
not an outage); every other service is still checked, so a long write never hides an outage. An
alert that could not be sent is retried next pass; if a needed push is still owed after two passes
(a broken credential or blocked endpoint), the dead-man's switch gets `/fail`, so the independent
channel escalates. State: `/opt/skynet-ops/state/watch.json`.

Write paths alert too: a `rollback-failed` or `unrecorded` outcome pushes a high-priority message,
and whether it went out is a step in the operation record. A write whose final record can't be kept is
`unrecorded` too. A skynet unit that crashes, times out, is killed, or could not send a needed
alert triggers `skynet-alert@` (`skynet alert unit-failed`, at most hourly per unit).

**Channel.** Pushover. **Dead-man's switch.** Every watch pass pings a healthchecks.io check
(`/fail` once the monitor is unhealthy: two failed passes, the same rule as its alert). The check
expects a ping every 3 minutes with a 5-minute grace and alerts through its own Pushover
integration, so a dead ops VM or timer still reaches the phone within about 8 minutes.
`skynet alert test` sends one message and one ping.

**Credential.** `secrets/alerts.env.sops` (`PUSHOVER_TOKEN`, `PUSHOVER_USER`, `HEALTHCHECK_URL`),
materialized `0400 aliammar` at `/opt/skynet-ops/secrets/alerts.env` through the `names` list in
`nix/modules/secrets.nix`. Outbound HTTPS only (`api.pushover.net`, the ping host).

## Scope

Observability covers rendered state, nightly change detection, and live service health with
state-change alerts. It does not collect metrics or logs.
