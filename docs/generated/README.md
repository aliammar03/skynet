# docs/generated — AUTO-GENERATED, do not hand-edit

`scripts/render-docs.sh` writes this folder from `inventory/*.json` + parsed firewall config.
It is Obsidian-flavored markdown (frontmatter, callouts, wikilinks, native Mermaid).

Sync it into Obsidian via the **Obsidian Git** plugin (clone of `skynet`, optionally
sparse-checkout of `docs/generated/`, auto-pull every 30 min). It never touches the
CouchDB LiveSync vault.

Expected pages once render-docs runs:

```
00-network-map.md      # mermaid: WANs → OPNsense → VLANs → hosts
10-vlans.md            # per-VLAN tables linking to host pages
20-firewall.md         # rules table (Notion format) from config.xml
30-services/<svc>.md   # IP, ports, front door, backup status, last deploy
40-hosts/<host>.md     # guests per node, resources, pool membership
90-backup-status.md    # last restic/PBS runs, snapshot counts, grant audit
```

**Edit the renderer, never the output.**
