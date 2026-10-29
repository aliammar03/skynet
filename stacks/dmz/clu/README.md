# clu

- **Purpose:** Comic Library Utilities for P8, for what Usenet lacks: old runs. It searches
  GetComics from a local index of GetComics' sitemap (no slow page walks), scores every result
  against the issue it wants and, with Download Packs on, takes the pack holding a missing issue
  once and skips the rest of its range. It unpacks, converts to CBZ, renames and files what it gets
  into series folders in its own library, and has a pull list, bulk CBR→CBZ, a CBZ editor and
  ComicInfo tools. Mylar3 stays for Usenet; a series is followed in one app, not two.
- **URL:** https://clu.aliammar.net (caddy-apps → `clu:5577` on `door-clu`). Inside and over
  Tailscale; not public.
- **Auth mode:** forward: the apps' Authelia, group `admins`, a password (`one_factor`). CLU itself
  stays single-user, which has no login: whoever passes Authelia runs it.
- **Network:** `door-clu`, an internal bridge it shares with caddy-apps alone (from
  `hosts/docker-dmz`), and the stack's own `egress` (GetComics, MEGA, Pixeldrain, Metron,
  ComicVine).
- **Data:**
  - `/opt/appdata/clu/config` → `/config`: its database (settings, library index, wanted list,
    the metadata keys) and its own backups of it (backup class: data);
  - `/var/cache/clu/thumbnails` → `/cache` and `/var/cache/clu/downloads` → `/downloads`: covers,
    and downloads (`temp/`) with their processed copies (`processed/`) before filing; on the host's
    ext4, outside `/opt/appdata`'s snapshots and the backup (`hosts/docker-dmz` makes both,
    `99:100`);
  - its library `/data` = Unraid's `Books/Comics/clu` (`hosts/docker-dmz`: `/mnt/storage`), as
    `<publisher>/<series>/`. It runs as `99:100` (`PUID`/`PGID`), Unraid's `nobody:users`.
- **Secrets:** none in git. Ali's ComicVine key (and a Metron account, if he wants Metron's data)
  lives in its database.
- **Setup:** its Guided Setup on the first visit (folders and permissions as above). Then, by the
  agent (D16) or Ali: Settings → Download & API: GetComics as the source, Download Packs on, the
  daily auto-download; Ali's ComicVine key under metadata providers.
- **Upstream:** [CLU](https://github.com/allaboutduncan/clu-comics) · [docs](https://clucomics.org)

**Gotchas**
- It scores TPBs, annuals and other variants down unless accepted (Search Variant Settings), so a
  run that GetComics only has as collections (Ultimate Spider-Man 2000, 2026-10-30) yields no
  issues.
- Its GetComics downloads use the file hosts' free tiers (MEGA, Pixeldrain, GetComics' own server):
  no Premiumize. Mylar3's GetComics goes through JDownloader and Premiumize instead.
