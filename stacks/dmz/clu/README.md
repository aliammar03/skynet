# clu

- **Purpose:** Comic Library Utilities for P8. It finds the issues missing from the series it
  follows on Usenet (NZBGeek, downloaded by SABnzbd) and then GetComics, whose search runs on a
  local index of GetComics' sitemap and scores every result against the wanted issue (with Download
  Packs on, the pack holding a missing issue is taken once and the rest of its range skipped). It
  unpacks, converts to CBZ, renames and files what it gets into series folders in its own library,
  and has a pull list, bulk CBR→CBZ, a CBZ editor and ComicInfo tools. On trial against Mylar3 for
  Usenet (Ali, 2026-10-30); a series is followed in one app, not two.
- **URL:** https://clu.aliammar.net (caddy-apps → `clu:5577` on `door-clu`). Inside and over
  Tailscale; not public.
- **Auth mode:** forward: the apps' Authelia, group `admins`, a password (`one_factor`). CLU itself
  stays single-user, which has no login: whoever passes Authelia runs it.
- **Network:** `door-clu`, an internal bridge it shares with caddy-apps alone (from
  `hosts/docker-dmz`); the stack's own `egress` (GetComics, MEGA, Pixeldrain, Metron, NZBGeek,
  ComicVine); and `mylar3_backend`, SABnzbd's internal network in `stacks/dmz/mylar3`, where it
  calls `http://sabnzbd:8080`.
- **Data:**
  - `/opt/appdata/clu/config` → `/config`: its database (settings, library index, wanted list,
    the metadata and indexer keys) and its own backups of it (backup class: data);
  - `/var/cache/clu/thumbnails` → `/cache` and `/var/cache/clu/downloads` → `/downloads`: covers,
    and downloads (`temp/`) with their processed copies (`processed/`) before filing; on the host's
    ext4, outside `/opt/appdata`'s snapshots and the backup (`hosts/docker-dmz` makes both,
    `99:100`);
  - `/var/cache/sabnzbd/clu` → `/usenet` in CLU and SABnzbd: SABnzbd's `clu` category, where its
    finished jobs wait for CLU to move them into `temp/` (CLU looks for a job at the path SABnzbd
    reports, so the path is the same in both);
  - its library `/data` = Unraid's `Books/Comics/clu` (`hosts/docker-dmz`: `/mnt/storage`), as
    `<publisher>/<series>/`. It runs as `99:100` (`PUID`/`PGID`), Unraid's `nobody:users`.
- **Secrets:** none in git. Ali's Metron account, ComicVine key and NZBGeek key, and SABnzbd's API
  key, live in its database.
- **Setup:**
  - Ali: Settings → Metadata providers: Metron (needed by its Wanted list, pull list and
    subscriptions) and the ComicVine key; Settings → Download & API → Indexers: NZBGeek
    (`https://api.nzbgeek.info`, his API key).
  - The agent (D16), through its API: Download Packs and CBR→CBZ on; timezone `5` (an hour offset);
    folder monitoring on; sources in the order `usenet`, `getcomics`; SABnzbd as its Usenet client
    (`sabnzbd`, 8080, SABnzbd's API key, category `clu`); in SABnzbd, a category `clu` with the
    folder `/usenet`; the schedules: the GetComics index at 00:30, the auto-download at 03:30 and
    the library index at 04:30 (Pakistan time; CLU takes them in UTC).
- **Upstream:** [CLU](https://github.com/allaboutduncan/clu-comics) · [docs](https://clucomics.org)

**Gotchas**
- A series page's "check for missing issues" is a real search and download, not a count.
- With its index empty, its GetComics searches go live, several variants an issue: GetComics
  answered 429 (too many requests) 213 times in 20 minutes on 2026-10-30. Usenet first keeps that
  down; the index fills for followed series, 300 posts a night.
- It scores TPBs, annuals and other variants down unless accepted (Search Variant Settings), and
  same-named spin-offs can slip through: for Ultimate Spider-Man (2000) it took Ultimate
  Spider-Man – Infinity Comic #17 and Incursion #3 (2025), and GetComics has that run only as
  collections. That series is unmonitored in CLU.
- Its GetComics downloads use the file hosts' free tiers (MEGA, Pixeldrain, GetComics' own server):
  no Premiumize. Mylar3's GetComics goes through JDownloader and Premiumize instead.
