---
summary: "How machine state becomes human-readable docs, and how the nightly run keeps the picture current."
---

# Spoke · Observability

> How Skynet turns machine state into things a human can read, and how the nightly run keeps the
> picture current. Governed by [`../system-design.md`](../system-design.md).

## Inventory → human-readable docs

`scripts/render-docs.sh` turns `inventory/*.json` + parsed firewall config into
[`../generated/`](../generated/) — Obsidian-flavored markdown with frontmatter, callouts,
wikilinks, and **Mermaid diagrams Obsidian renders natively**, drawn from live data and never
hand-maintained:

```
00-network-map.md      # mermaid: WANs → OPNsense → VLANs → hosts
05-state-of-the-lab.md # human narrative, LLM-authored nightly (surfaced in README)
06-agent-digest.md     # agent cold-boot digest, render-digest.sh (decisions/threads/episodes)
10-vlans.md            # per-VLAN tables linking to host pages
20-firewall.md         # rules/aliases from the LIVE OPNsense API (collect-opnsense.sh); mirror = DR only
30-services/<svc>.md   # IP, ports, front door, backup status, last deploy
40-hosts/<host>.md     # guests per node, resources, pool membership
90-backup-status.md    # last restic/PBS runs, snapshot counts, grant audit
```

`inventory/` and `docs/generated/` are **machine-owned — never hand-edited** (a constitution
invariant). The docs cannot drift from reality because they're re-rendered after each inventory
refresh.

Obsidian sync uses a `skynet` clone (optionally sparse-checking out `docs/generated/`) and never
touches the CouchDB LiveSync vault. Configuration: [`obsidian-setup.md`](../obsidian-setup.md).

## The nightly run

[`nightly.md`](../../runbooks/nightly.md) defines the 03:30 `skynet-nightly.timer` flow:
deterministic preparation and finalization in [`scripts/nightly.sh`](../../scripts/nightly.sh), with
primary then fallback engines available only for the optional narrative and grant-audit stage.
Engine and model selection are in `~/.config/skynet-ops/ops.env`.

Report-only is a constitution dial: the nightly run *observes and proposes*, it does not act
outside the version-controlled auto-approve list.

## Episodic memory — see the memory spoke

Rendered docs answer *what is true now*; they can't answer *how the lab got here, what was tried,
what failed*. That **episodic** memory — the [`journal/`](../../journal/README.md) and the read-time
digest that reconstructs it — is its own domain, designed in the [memory](memory.md) spoke. The
only part that lives here is the *rendering*: `scripts/render-digest.sh` produces the agent digest
[`../generated/06-agent-digest.md`](../generated/06-agent-digest.md) alongside the other nightly
pages (deterministic, content-stable), and the human narrative
[`05-state-of-the-lab.md`](../generated/05-state-of-the-lab.md) is the agent-authored counterpart.

## Scope

Observability is descriptive: rendered state and nightly change detection. It does not provide
live alerting between nightly runs.
