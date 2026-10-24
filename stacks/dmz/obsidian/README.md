# obsidian

- **Purpose:** the sync server for Obsidian Self-hosted LiveSync: one CouchDB node that every
  device's vault replicates with.
- **URL:** https://obsidian.aliammar.net (caddy-apps → `obsidian:5984` on `edge`). Public through
  the tunnel, so phones sync away from home.
- **Auth mode:** own: the CouchDB admin `aliammar` (`COUCHDB_USER`) with `COUCHDB_PASSWORD`, the
  login in the LiveSync plugin. Only `/_up` answers without it. The plugin also encrypts the notes
  end to end, so the server holds ciphertext.
- **Data:** `/opt/appdata/obsidian/couchdb` → `/opt/couchdb/data` (the databases, owner 5984; backup
  class: data). Copied from v1's `obsidian-livesync_data` volume (P3 → Data).
- **Secrets** (`secret.sops.env`): `COUCHDB_PASSWORD`, `COUCHDB_SECRET` (cookie signing). Both carried
  over from v1, so the devices keep syncing without a change.
- **Config:** `local.ini` (CORS for the Obsidian apps, single node, request and document limits),
  copied into `local.d/` at start.
- **Upstream:** [CouchDB](https://docs.couchdb.org/en/stable/config/index.html) ·
  [Self-hosted LiveSync](https://github.com/vrtmrz/obsidian-livesync)

**Gotchas**
- The image's entrypoint chowns everything under `/opt/couchdb` to 5984. So `local.ini` is mounted at
  `/etc/skynet/couchdb/` and copied in, and the checked-out file keeps its owner.
- The image version holds the data format: it stays at v1's 3.5.0 until a Renovate PR moves it.
- Cloudflare caps a request body at 100 MB. LiveSync's chunks are far smaller, but a huge attachment
  syncs only from inside.
