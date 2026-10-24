# paperless

- **Purpose:** the document archive: scans and PDFs, OCR'd and searchable.
- **URL:** https://paperless.aliammar.net (caddy-apps → `paperless:8000` on `edge`). Inside only.
- **Auth mode:** own (Paperless accounts; admin `aliammar`).
- **Containers:** `paperless`, and `paperless-redis` (its task broker, no persistence) on the stack's
  own internal `backend` network.
- **Data:** `/opt/appdata/paperless/` (copied from v1; backup class: data):
  - `data`: sqlite and the search index;
  - `media`: the documents themselves;
  - `consume`: the inbox; a file dropped here is imported and removed;
  - `export`: `document_exporter` output.
- **Secrets** (`secret.sops.env`, from v1): `PAPERLESS_SECRET_KEY` (signs sessions), and
  `PAPERLESS_ADMIN_PASSWORD` (used only to create the admin on an empty database).
- **Upstream:** [Paperless-ngx](https://docs.paperless-ngx.com/configuration/)

**Gotchas**
- The image stays at v1's 3.2.1: Paperless migrates its database at start, so a newer version comes as
  its own Renovate PR, after a backup.
- `PAPERLESS_URL` must be the URL the browser uses, or logins fail Django's CSRF check.
