# mylar3

- **Purpose:** Western comics for P8. Mylar3 follows the series Ali adds (ComicVine) and looks for
  each issue on NZBGeek (Usenet: SABnzbd downloads it from Easynews) and then on GetComics (its
  file-host links go to JDownloader 2, which downloads them through Ali's Premiumize); then it
  renames and tags the issue and files it as publisher and series folders. Komga and Uchiyomi
  (library Comics) read them. Kapowarr stays for GetComics: a series is followed in one of the two,
  not both.
- **URLs:** https://mylar3.aliammar.net (caddy-apps → `mylar3:8090` on `door-mylar3`),
  https://sabnzbd.aliammar.net (→ `sabnzbd:8080` on the `dmz` macvlan) and
  https://jdownloader.aliammar.net (→ `jdownloader:5800` on `door-jdownloader`: its desktop in the
  browser). Inside and over Tailscale; not public.
- **Auth mode:** forward, all three: the apps' Authelia, group `admins`, a password (`one_factor`).
  Their own logins stay off: whoever passes Authelia runs them.
- **Network:**
  - SABnzbd: on the `dmz` macvlan at 10.10.100.66, in OPNsense's `ROLE_USENET_CLIENTS` (rule 820:
    usenet ports 119/563), so it alone leaves on the usenet ports (`skynetv2.md` → Conventions →
    Networks); and on the stack's internal `backend`. caddy-apps reaches it on the macvlan by name,
    and SABnzbd shows its pages to that address only: `local_ranges` 10.10.100.35, `inet_exposure`
    3 (from anywhere else, its API with its key and nothing more), `verify_xff_header` 0 (the
    client's address in `X-Forwarded-For` is Ali's, not the door's).
  - Easynews: `news.us.easynews.com`, port 119, no SSL (Ali, 2026-10-29). Its US hosts, not its EU
    ones: from here the EU host gave 0.25 MB/s, the US one 17–25 MB/s (2026-10-29).
  - Mylar3: `door-mylar3` (internal, with caddy-apps alone, from `hosts/docker-dmz`), the stack's
    `egress` (ComicVine, NZBGeek, GetComics) and `backend` (`http://sabnzbd:8080`,
    `http://jdownloader:3128`).
  - JDownloader: `door-jdownloader`, `egress` (file hosts, Premiumize, its own updates) and
    `backend`, where its local API (3128, no login) answers Mylar3.
- **Data:**
  - `/opt/appdata/mylar3/config` → Mylar3's `/config`: its database and settings, the ComicVine and
    NZBGeek keys (backup class: data); `mylar/cache` and `mylar/logs` (cache:
    `stacks/dmz/backup/excludes.txt`);
  - `/opt/appdata/mylar3/sabnzbd` → SABnzbd's `/config`: its settings with Easynews' login and its
    API key, queue and history (data); `logs` (cache);
  - `/opt/appdata/mylar3/jdownloader` → JDownloader's `/config`: its settings with Premiumize's login,
    and the JDownloader it keeps updated (data); `logs` and `tmp` (cache);
  - `/var/cache/sabnzbd` → `/downloads` in SABnzbd and Mylar3, `/var/cache/jdownloader` → `/jd2` in
    JDownloader and Mylar3: downloads in progress and finished, on the host's ext4, outside
    `/opt/appdata`'s snapshots and the backup (`hosts/docker-dmz` makes both, `99:100`);
  - comic location `/comics` = Unraid's `Books/Comics/mylar3` (`hosts/docker-dmz`: `/mnt/storage`).
    All three run as `99:100`, Unraid's `nobody:users`.
- **Secrets:** none in git. Ali's Easynews login lives in SABnzbd's settings, the ComicVine and
  NZBGeek keys in Mylar3's, his Premiumize login in JDownloader's; SABnzbd's API key in SABnzbd's
  and Mylar3's.
- **Setup (agent, right after the deploy):**
  - SABnzbd, through its API: `sabnzbd.aliammar.net` added to `host_whitelist`; folders
    `/downloads/incomplete` and `/downloads/complete`; a category `comics`; `verify_xff_header` 0;
    Easynews' host and port above, 20 connections, 5 articles per request (SABnzbd's advice at this
    ~230 ms latency). Its API refuses the two protected ones, so `local_ranges =
    10.10.100.35/32,` and `inet_exposure = 3` go into `sabnzbd.ini` while it's stopped.
  - JDownloader, after its first start and while it's stopped: its local API on, in
    `cfg/org.jdownloader.api.RemoteAPIConfig.json`:
    `{"deprecatedapienabled": true, "deprecatedapiport": 3128, "deprecatedapilocalhostonly": false}`.
  - Mylar3, while it's stopped, `[DDL]` in `mylar/config.ini`: `enable_ddl`, `enable_getcomics`
    and `jd2_enable` true, `jd2_url = http://jdownloader:3128`, `jd2_dest_dir = /jd2`.
- **Setup (Ali, once):**
  1. sabnzbd.aliammar.net, its wizard: the Easynews username and password.
  2. mylar3.aliammar.net → Settings:
     - Web Interface: ComicVine API Key (Kapowarr's); Comic Location Path `/comics`;
     - Download settings: SABnzbd; host `http://sabnzbd:8080`, SABnzbd's API key (its Config →
       General), category `comics`; Enable Completed Download Handling;
     - Search providers: Use Newznab; add NZBGeek, `https://api.nzbgeek.info`, Ali's API key,
       category `7030` (Comics);
     - Quality & Post Processing: Enable Post-Processing, Enable Metadata Tagging (ComicInfo for
       Komga);
     - Advanced Settings: Folder Format `$Publisher/$Series ($Year)`, as Kapowarr's.
  3. jdownloader.aliammar.net → Settings → Account Manager → Add → premiumize.me: the customer ID
     and API key from premiumize.me → Account.

  Then add a series (search by name) and mark its issues Wanted (the series menu's "Change All
  Skipped to Wanted" takes every issue; ticking all takes only the page shown).
- **Upstream:** [Mylar3](https://github.com/MylarComics/mylar3) ·
  [SABnzbd](https://sabnzbd.org/wiki/) ·
  [JDownloader 2 image](https://github.com/jlesage/docker-jdownloader-2)

**Gotchas**
- SABnzbd refuses a name it doesn't know ("Hostname verification failed"): its own hostname is
  admitted at its first start, so compose sets it to `sabnzbd`; the door's name is the agent's step
  above. A rebuilt config needs that step again.
- Mylar3's pages check that it can make a folder under its comic location; if it can't (not
  `99:100`), its home page fails with a Python error rather than its warning.
- Mylar3's "Convert CBR to CBZ" means convert *only*: it switches tagging off. Tagging converts CBR
  to CBZ anyway.
- JDownloader's settings file, written before its first start, makes the image's setup fail; written
  while it runs, JDownloader overwrites it when it exits.
- JDownloader unpacks the archives it downloads (GetComics' packs) next to them; Mylar3 then files
  the issues from that folder.
- Mylar3 searches its providers one minute apart, several queries per issue: a whole old run takes
  hours, and NZBGeek has few single issues of runs older than its uploaders' digital releases.
