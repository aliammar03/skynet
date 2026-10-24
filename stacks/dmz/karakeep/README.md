# karakeep

- **Purpose:** bookmarks with full-page archives (screenshot, PDF, single-file HTML, video), OCR,
  full-text search and AI tags and summaries (OpenAI).
- **URL:** https://karakeep.aliammar.net (caddy-apps → `karakeep:3000` on `edge`). Public through
  the tunnel, for the phone apps and the browser extension.
- **Auth mode:** own (karakeep's accounts). Signups are off: new accounts come from the admin
  settings.
- **Containers:** `karakeep` (web, API and workers), `karakeep-chrome` (the headless browser that
  crawls pages), `karakeep-meilisearch` (search). The last two sit only on this stack's networks:
  Chrome on `backend` (its debugging port has no login, so no other container reaches it), and
  Meilisearch on `search`, which is internal: no internet, and out of the browser's reach.
- **Data:**
  - `/opt/appdata/karakeep/data` → `/data`: sqlite, assets, archives, OCR cache (backup class:
    data);
  - `/opt/appdata/karakeep/meili` → `/meili_data`: the search index (backup class: cache; karakeep
    can rebuild it).

  Both copied from v1 (P3 → Data).
- **Secrets** (`secret.sops.env`, from v1): `NEXTAUTH_SECRET` (signs sessions and API keys; keep
  it, or every login and app token breaks), `MEILI_MASTER_KEY`, `PROMETHEUS_AUTH_TOKEN`,
  `OPENAI_API_KEY`.
- **Upstream:** [Karakeep](https://docs.karakeep.app/) ·
  [configuration](https://docs.karakeep.app/configuration/)

**Gotchas**
- Karakeep migrates its database on upgrade, one way: going back needs a copy from before.
- Meilisearch stays at karakeep's own pin (v1.41.0 with karakeep 0.34.1), and Renovate leaves it
  alone (`renovate.json`): a newer one can't open the index without a migration. It moves when
  karakeep's `docker/docker-compose.yml` moves it.
- Chrome (`karakeep-chrome`, Google Chrome stable, from Karakeep) opens whatever pages are
  bookmarked. It sits on `backend` only and leaves as the host (10.10.100.10). OPNsense rule 700
  blocks the host from private networks apart from DNS, NTP and v1's rule 300 (Unraid SMB/NFS); on
  VLAN 100 itself, athena (.30) is its only neighbour.
- Video downloads (`CRAWLER_VIDEO_DOWNLOAD`, up to 1 GB each) and full-page archives grow
  `/opt/appdata/karakeep/data`.
