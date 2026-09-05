# Obsidian — read the lab as a live vault

`docs/generated/` is a self-updating, Obsidian-flavored view of the whole lab (network map,
VLANs, firewall, hosts, backups, and the nightly [[generated/05-state-of-the-lab|State of the
Lab]] narrative). Point Obsidian at it and you get a wiki that re-renders itself every night —
never hand-maintained. This is a **workstation** setup; it touches nothing in the lab.

## One-time setup (your workstation)

1. **Clone the repo somewhere for the vault** (separate from any working clone if you like):
   ```bash
   git clone https://github.com/aliammar03/skynet.git ~/obsidian-skynet
   ```
   Optional — pull *only* the generated docs with a sparse checkout:
   ```bash
   cd ~/obsidian-skynet
   git sparse-checkout init --cone
   git sparse-checkout set docs/generated
   ```
2. **Open the repository root as the vault:** Obsidian → *Open folder as vault* →
   `~/obsidian-skynet`, then navigate into `docs/generated`. This preserves the shared vault settings
   committed under `.obsidian/`; a sparse checkout of only `docs/generated` is view-only and does not
   include those settings. The mermaid diagrams, callouts, and `[[wikilinks]]` render natively — no
   plugins are needed for viewing.
3. **Auto-pull with the Obsidian Git plugin:**
   - Community plugins → browse → **Obsidian Git** → install version **2.39.0** (or the current
     compatible release if that version is unavailable) + enable. It is installed locally in this
     vault through Obsidian's Community Plugins UI, not bundled in git.
   - Settings → Obsidian Git → **Pull updates on interval = 30** (minutes); leave auto-commit
     **off** (this vault is read-only — the nightly writes it, you don't).
   Now every merged nightly PR shows up in your vault within half an hour.

## Notes

- **Read-only by contract.** `docs/generated/` is machine-owned. If you want to change what a
  page shows, edit `scripts/render-docs.sh` (factual pages) or the nightly prompt in
  `runbooks/nightly.md` (the narrative) — never the output files; the next render overwrites them.
- **Shared versus local metadata.** The shared `.obsidian` appearance, app, graph, and plugin-enable
  settings are committed. Your open tabs/layout (`workspace*.json`) and installed plugin files are
  intentionally local and ignored; Obsidian recreates them. Removing or recloning this vault never
  loses lab content, only local workspace state and installed plugins.
- **It never touches your other vaults** (e.g. a CouchDB LiveSync vault) — it's just another
  local folder Obsidian opens.
- **Freshness** depends on nightly PRs being merged. Until you merge a night's
  `inventory/<date>` PR, the vault shows the last merged state.
