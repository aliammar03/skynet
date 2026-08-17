# Spoke · Observability

> How Skynet turns machine state into things a human can read, and how the nightly run keeps the
> picture current. Governed by [`../system-design.md`](../system-design.md). Sourced from plan §11
> (render-docs / Obsidian) and the A5 visibility work.

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
20-firewall.md         # rules table from config.xml
30-services/<svc>.md   # IP, ports, front door, backup status, last deploy
40-hosts/<host>.md     # guests per node, resources, pool membership
90-backup-status.md    # last restic/PBS runs, snapshot counts, grant audit
```

`inventory/` and `docs/generated/` are **machine-owned — never hand-edited** (a constitution
invariant). The docs cannot drift from reality because they're re-rendered after each inventory
refresh.

**Sync to Obsidian** via the Obsidian Git community plugin: a clone of `skynet` (sparse-checkout
`docs/generated/` if desired) as a vault folder, auto-pull every 30 min. It never touches the
CouchDB LiveSync vault. Setup: [`../obsidian-setup.md`](../obsidian-setup.md).

## The nightly run

`bin/ops nightly` (`skynet-nightly.timer`, 03:30, **report-only**) tries **primary engine →
fallback engine → deterministic `scripts/nightly.sh`**. Engine and models come from
`~/.config/skynet-ops/ops.env` (`OPS_ENGINE`, `OPS_ENGINE_FALLBACK`, `OPS_CODEX_MODEL`,
`OPS_CLAUDE_MODEL`). A weekly timer (`skynet-cli-update`, Sun 05:00) updates both CLIs and writes
each provider's current `--model` ids into `ops.env` as commented suggestions.

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

## What "observability" covers today vs. next

Today this spoke is **descriptive**: state, rendered, nightly. It answers *what is the lab right
now* and *what changed*. It is not yet *alerting* — there's no live signal that pages when
something breaks between nightlies.

## Planned expansion — from description to monitoring

- **A monitoring / alerting stack** (metrics + a notifier) is the named growth direction: live
  health, thresholds, and push alerts (an ntfy channel already fits the grant-approval pattern).
  This becomes its own `SKY-###`, and likely deepens this spoke rather than adding a new one.
- **Richer nightly reasoning** — the report-only run graduating individual, well-understood
  actions onto the auto-approve list, one PR at a time (the autonomy ratchet).
