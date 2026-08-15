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
2. **Open the vault:** Obsidian → *Open folder as vault* → `~/obsidian-skynet/docs/generated`
   (or the repo root, and navigate into `docs/generated`). The mermaid diagrams, callouts, and
   `[[wikilinks]]` render natively — no plugins needed for viewing.
3. **Auto-pull with the Obsidian Git plugin:**
   - Community plugins → browse → **Obsidian Git** → install + enable.
   - Settings → Obsidian Git → **Pull updates on interval = 30** (minutes); leave auto-commit
     **off** (this vault is read-only — the nightly writes it, you don't).
   Now every merged nightly PR shows up in your vault within half an hour.

## Notes

- **Read-only by contract.** `docs/generated/` is machine-owned. If you want to change what a
  page shows, edit `scripts/render-docs.sh` (factual pages) or the nightly prompt in
  `runbooks/nightly.md` (the narrative) — never the output files; the next render overwrites them.
- **It never touches your other vaults** (e.g. a CouchDB LiveSync vault) — it's just another
  local folder Obsidian opens.
- **Freshness** depends on nightly PRs being merged. Until you merge a night's
  `inventory/<date>` PR, the vault shows the last merged state.
