# kapowarr

- **Purpose:** Western comics for P8: searches GetComics for the issues of a volume Ali adds, downloads
  whole issues and collections (CBR/CBZ as published), and files them as publisher and series folders
  with ComicVine's metadata. Komga (library Downloads) and Uchiyomi (library Comics) read them.
- **URL:** https://kapowarr.aliammar.net (caddy-apps → `kapowarr:5656` on `door-kapowarr`). Inside and
  over Tailscale; not public.
- **Auth mode:** forward: the apps' Authelia, group `admins`, a password (`one_factor`). Its own
  authentication stays at None: whoever passes Authelia runs it.
- **Network:** `door-kapowarr`, an internal bridge it shares with caddy-apps alone (from
  `hosts/docker-dmz`), and its stack's own `egress` (GetComics, ComicVine, the file hosts).
- **Data:**
  - `/opt/appdata/kapowarr/db` → `/app/db`: its database (library, settings, the ComicVine key;
    backup class: data);
  - `/var/cache/kapowarr` → `/app/temp_downloads`: downloads in progress, on the host's ext4, outside
    `/opt/appdata`'s snapshots and the backup;
  - root folder `/comics` = Unraid's `Books/Downloads/Kapowarr` (`hosts/docker-dmz`: `/mnt/storage`).
    It runs as `99:100` (`PUID`/`PGID`), Unraid's `nobody:users`.
- **Secrets:** none in git. Ali's ComicVine API key (free account,
  https://comicvine.gamespot.com/api/) goes into Settings → General, and lives in its database.
- **Setup (Ali, once):** Settings → General → ComicVine API key; Settings → Media Management → root
  folder `/comics`. Then add a volume (search by name) and its issues download.
- **Upstream:** [Kapowarr](https://casvt.github.io/Kapowarr/) ·
  [GitHub](https://github.com/Casvt/Kapowarr)

**Gotchas**
- It logs its API key at its first start, and settings it saves with their values, at INFO, so they
  reach VictoriaLogs. The API answers only behind Authelia here.
- GetComics' links lead to file hosts (Mega, MediaFire, Pixeldrain…), each with its own limits; a
  download that a host refuses is retried from another link when the post has one.
- No FlareSolverr: Kapowarr logs it when Cloudflare blocks it; its URL then goes in Settings →
  General.
