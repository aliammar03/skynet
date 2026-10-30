# clu

- **Purpose:** Western comics for P8, in one stack (Ali, 2026-10-30, after CLU found 5× Mylar3's
  Usenet hits and pulled the Watchmen pack Kapowarr corrupted, cleanly and 10× faster):
  - **CLU** (Comic Library Utilities) follows Ali's series (Metron) and finds their missing issues on
    Usenet (NZBGeek, downloaded by SABnzbd), then GetComics, whose search runs on a local index of
    GetComics' sitemap and scores every result against the wanted issue (with Download Packs on,
    the pack holding a missing issue is taken once and the rest of its range skipped). It unpacks,
    renames and files what it gets into series folders in its library, and has a pull list, bulk
    CBR→CBZ, a CBZ editor and ComicInfo tools. It tags from Metron and ComicVine, ComicVine first
    from a local copy of its database.
  - **SABnzbd** downloads CLU's NZBs from Easynews.
  - **JDownloader 2** is for Ali's own picks (a GetComics pack, a file-host link): it downloads
    through his Premiumize into CLU's downloads, and CLU processes and files the result.

  Manga stays in Uchiyomi: CLU tags manga but has no manga sources, and its scorer rejects
  volume-numbered releases (2026-10-30).
- **URLs** (caddy-apps; inside and over Tailscale, not public): https://clu.aliammar.net (→
  `clu:5577` on `door-clu`), https://sabnzbd.aliammar.net (→ `sabnzbd:8080` on the `dmz` macvlan),
  https://jdownloader.aliammar.net (→ `jdownloader:5800` on `door-jdownloader`: its desktop).
- **Auth mode:** forward, all three: the apps' Authelia, group `admins`, a password (`one_factor`).
  Their own logins stay off (CLU single-user has none): whoever passes Authelia runs them.
- **Network:**
  - CLU: `door-clu` (internal, with caddy-apps alone, from `hosts/docker-dmz`), the stack's `egress`
    (GetComics, MEGA, Pixeldrain, Metron, NZBGeek, ComicVine) and `backend` (`http://sabnzbd:8080`).
  - SABnzbd: on the `dmz` macvlan at 10.10.100.66, in OPNsense's `ROLE_USENET_CLIENTS` (rule 820:
    usenet ports 119/563), so it alone leaves on the usenet ports (`skynetv2.md` → Conventions →
    Networks); and on the internal `backend`. caddy-apps reaches it on the macvlan by name, and it
    shows its pages to that address only: `local_ranges` 10.10.100.35, `inet_exposure` 3 (from
    anywhere else, its API with its key and nothing more), `verify_xff_header` 0 (the client in
    `X-Forwarded-For` is Ali's, not the door's). Easynews: `news.us.easynews.com`, port 119, no SSL
    (Ali, 2026-10-29); its US hosts, not its EU ones (0.25 MB/s from here against 17–25 MB/s).
  - JDownloader: `door-jdownloader` and `egress` (file hosts, Premiumize, its own updates).
- **Data:**
  - `/opt/appdata/clu/config` → CLU's `/config`: its database (settings, library index, wanted list,
    the Metron, ComicVine and NZBGeek keys) and its own backups of it (backup class: data);
  - `/opt/appdata/clu/sabnzbd` → SABnzbd's `/config`: its settings with Easynews' login and its API
    key, queue and history (data); `logs` (cache: `stacks/dmz/backup/excludes.txt`);
  - `/opt/appdata/clu/jdownloader` → JDownloader's `/config`: its settings with Premiumize's login,
    and the JDownloader it keeps updated (data); `logs` and `tmp` (cache);
  - on the host's ext4, outside `/opt/appdata`'s snapshots and the backup (`hosts/docker-dmz` makes
    them, `99:100`): `/var/cache/clu/thumbnails` → `/cache` (covers); `/var/cache/clu/comicvine` →
    `/comicvine` (`localcv.db`, ComicVine's data as one SQLite file, 3.2 GB, which CLU downloads
    from a public mirror and refreshes every two weeks; a refresh holds about 7 GB for a few
    minutes: the old file, the zip and the new one); `/var/cache/clu/downloads` →
    CLU's `/downloads` (`temp/`, where downloads arrive, and `processed/`, before filing), its
    `temp/` also JDownloader's `/output`; `/var/cache/sabnzbd` → SABnzbd's `/downloads`; and
    `/var/cache/sabnzbd/clu` → `/usenet` in both CLU and SABnzbd: SABnzbd's `clu` category, where
    finished jobs wait for CLU (CLU looks for a job at the path SABnzbd reports, so the path is the
    same in both);
  - CLU's library `/data` = Unraid's `Books/Comics/clu` (`hosts/docker-dmz`: `/mnt/storage`), as
    `<publisher>/<series>/`. Files land there as `99:100` (Unraid's `nobody:users`, all_squash),
    the user CLU runs as (`PUID`/`PGID`).
- **Secrets:** none in git. Ali's Metron account, ComicVine and NZBGeek keys live in CLU's database,
  his Easynews login in SABnzbd's settings, his Premiumize login in JDownloader's; SABnzbd's API key
  in SABnzbd's settings and CLU's database.
- **Setup:**
  - Ali: CLU → Settings → Metadata providers: Metron (its Wanted list, pull list and subscriptions
    need it) and the ComicVine key; → Download & API → Indexers: NZBGeek
    (`https://api.nzbgeek.info`, his API key). SABnzbd's wizard: the Easynews login. JDownloader →
    Settings → Account Manager → premiumize.me: the customer ID and API key.
  - The agent (D16), through CLU's API: Download Packs and CBR→CBZ on; timezone `5` (an hour offset);
    folder monitoring on; sources `usenet`, then `getcomics`; SABnzbd as its Usenet client
    (`sabnzbd`, 8080, SABnzbd's API key, category `clu`); the schedules (CLU takes UTC): the
    GetComics index at 00:30, the auto-download at 03:30, the library index at 04:30, Pakistan time;
    the local ComicVine database: its path `/comicvine/localcv.db`, its two-weekly refresh on, a
    first download (`POST /api/providers/comicvine_sqlite/update`); the library's metadata providers
    in the order ComicVine (local), ComicVine (its API, for issues newer than the copy), Metron
    (Ali, 2026-10-30); file names `{series_name} ({volume_year}) #{issue_number}` (Ali,
    2026-10-30), the issue number padded to three digits (its default):
    `Ultimate Spider-Man (2000) #004.cbz`; series folders `{publisher}/{series_name} ({start_year})`
    (`CUSTOM_MOVE_PATTERN`, Ali, 2026-10-30), which the Subscribe dialog suggests:
    `DC Comics/Watchmen (1986)`. That one through `core.settings.set_setting` in the container and a
    restart: its Settings page saves every field at once, so a partial save resets the rest.
- **Patches:** `patches/apply.py` fixes four things in CLU v7.0 at each start, before CLU's
  entrypoint (its `clu-patch:` lines in the log):
  - a Usenet download is filed once `temp/` empties, as a direct download is (CLU never filed one);
  - an issue with no on-sale date counts as out by its cover date (Metron lacks on-sale dates for
    many older issues, Watchmen #2–#12 among them, and CLU never searched for those);
  - among results with the same score the bigger post wins (CLU took the first: Watchmen #1 came as
    a 29 MB, 1280×1968 copy where a 90 MB, 1988×3056 one scored the same);
  - a filed issue is named from CLU's record of its series, the series' start year (CLU kept the
    release's year whenever it fetched no metadata, which it skips for a release that arrives
    tagged: Watchmen #5–#12 came as `(1987)`).

  A fix whose text CLU's code no longer has (after an update) is left out with a `clu-patch:` line,
  and that file runs as shipped. On a CLU update: read those lines, and drop each fix CLU now has.
  - The agent, in SABnzbd: through its API, `sabnzbd.aliammar.net` in `host_whitelist`, folders
    `/downloads/incomplete` and `/downloads/complete`, the category `clu` → `/usenet`,
    `verify_xff_header` 0, the Easynews server above with 20 connections and 5 articles per request;
    in `sabnzbd.ini` while it's stopped (its API refuses these two), `local_ranges =
    10.10.100.35/32,` and `inet_exposure = 3`.
  - The agent, in JDownloader, after its first start and while it's stopped: archive extraction off
    (`cfg/org.jdownloader.extensions.extraction.ExtractionExtension.json`: `"enabled": false`), so
    CLU alone unpacks what lands in its `temp/`.
- **Upstream:** [CLU](https://github.com/allaboutduncan/clu-comics) · [docs](https://clucomics.org) ·
  [SABnzbd](https://sabnzbd.org/wiki/) ·
  [JDownloader 2 image](https://github.com/jlesage/docker-jdownloader-2)

**Gotchas**
- CLU's entrypoint runs CLU as root (its *Container user* notice) when `/downloads/temp`,
  `/downloads/processed`, `/data` or `/cache` isn't writable by `PUID:PGID`, and makes a missing
  `temp/` or `processed/` as root itself: the host makes both as `99:100` first (`hosts/docker-dmz`).
- CLU dates a wanted issue by Metron's on-sale year, while releases carry the cover year (two or three
  months later), and its scorer takes 20 points off for a wrong year: an issue on sale in October to
  December is rejected (Ultimate Spider-Man #15: 20 by on-sale year, 60 by cover year), and the run
  falls through to GetComics. For a backfill, search such issues by cover year and grab them through
  `/api/usenet/grab`.
- It files once a finished download has emptied its `temp/` (a Usenet one through the patch); a
  straggler waits in `processed/` until the next one, or `POST /api/scan-downloads`. It files only
  issues it still wants: a better copy of an issue it has (a digital release for a scan) stays in
  `processed/` until moved into the series folder by hand.
- Re-packing a CBZ whose pages sit in one subfolder can stop half-way with no error logged, leaving
  a `<name>.zip` and a `<name>_folder` in the series folder. Grab another copy instead.
- A series page's "check for missing issues" is a real search and download, not a count.
- It names a download in `temp/` from the release's name, where `{volume_year}` can only be the year
  in that name (the cover year: `Watchmen (1987) #005`); the patch renames it at filing
  (`Watchmen (1986) #005`). A release's own ComicInfo may carry ComicVine's series id as its
  `Volume` (Marika-Empire's Watchmen: 3622), which CLU's rename from metadata would read as a year.
- With its GetComics index empty, its searches go live, several variants an issue: GetComics
  answered 429 (too many requests) 213 times in 20 minutes on 2026-10-30. Usenet first keeps that
  down; the index fills for followed series, 300 posts a night.
- Its scorer drops TPBs, annuals and other variants unless accepted, rejects scanners' odd names
  (`Ultimate.Spider-Man.064-000`, a title starting with "- ") that are proper issues, and once took
  same-named spin-offs (Ultimate Spider-Man – Infinity Comic #17 and Incursion #3 for Ultimate
  Spider-Man 2000).
- SABnzbd refuses a host name it doesn't know ("Hostname verification failed"): its own hostname,
  `sabnzbd`, is admitted at its first start; the door's name is the agent's step above. A rebuilt
  config needs that step again.
- JDownloader's settings file, written before its first start, makes the image's setup fail; written
  while it runs, JDownloader overwrites it when it exits.
