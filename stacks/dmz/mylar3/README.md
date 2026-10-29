# mylar3

- **Purpose:** Western comics from Usenet for P8. Mylar3 follows the series Ali adds (ComicVine),
  searches NZBGeek for their issues as they come out and hands each to SABnzbd, which downloads it
  from Easynews; Mylar3 then renames and tags it and files it as publisher and series folders.
  Komga (library Comics) and Uchiyomi (library Comics) read them. Kapowarr stays for GetComics: a
  series is followed in one of the two, not both.
- **URLs:** https://mylar3.aliammar.net (caddy-apps → `mylar3:8090` on `door-mylar3`) and
  https://sabnzbd.aliammar.net (→ `sabnzbd:8080` on `door-sabnzbd`). Inside and over Tailscale; not
  public.
- **Auth mode:** forward, both: the apps' Authelia, group `admins`, a password (`one_factor`). Their
  own logins stay off: whoever passes Authelia runs them.
- **Network:** each on its `door-*` network, an internal bridge it shares with caddy-apps alone
  (from `hosts/docker-dmz`), and the stack's own `egress`, where Mylar3 calls SABnzbd as
  `http://sabnzbd:8080`. Easynews answers NNTP over TLS on :443 (`secure-us.news.easynews.com`),
  which the DMZ's web egress already allows (rule 810); its :563 is closed from the DMZ, and
  needing it would mean a rule naming SABnzbd, so a macvlan IP (`skynetv2.md` → Conventions →
  Networks). Its US host, not its EU one: from here the EU host (and `secure.news.easynews.com`, a
  retired name for it) gave 0.25 MB/s, the US host 17–25 MB/s (2026-10-29).
- **Data:**
  - `/opt/appdata/mylar3/config` → Mylar3's `/config`: its database and settings, the ComicVine and
    NZBGeek keys (backup class: data); `mylar/cache` and `mylar/logs` (cache:
    `stacks/dmz/backup/excludes.txt`);
  - `/opt/appdata/mylar3/sabnzbd` → SABnzbd's `/config`: its settings with Easynews' login and its
    API key, queue and history (data); `logs` (cache);
  - `/var/cache/sabnzbd` → `/downloads` in both: SABnzbd's downloads in progress (`incomplete/`) and
    finished (`complete/comics/`), on the host's ext4, outside `/opt/appdata`'s snapshots and the
    backup (`hosts/docker-dmz` makes it, `99:100`);
  - comic location `/comics` = Unraid's `Books/Comics/mylar3` (`hosts/docker-dmz`: `/mnt/storage`).
    Both run as `99:100` (`PUID`/`PGID`), Unraid's `nobody:users`.
- **Secrets:** none in git. Ali's Easynews login lives in SABnzbd's settings; the ComicVine and
  NZBGeek API keys in Mylar3's; SABnzbd's API key in both.
- **Setup (agent, right after the deploy):** SABnzbd through its API: `sabnzbd.aliammar.net` added to
  `host_whitelist` (Special), folders `/downloads/incomplete` and `/downloads/complete`, and a
  category `comics`.
- **Setup (Ali, once):**
  1. sabnzbd.aliammar.net, its wizard: server `secure-us.news.easynews.com`, port 443, SSL on, the
     Easynews username and password, 20 connections; then, in Config → Servers, Articles per
     request 5 (SABnzbd's advice at this ~230 ms latency). Then copy Config → General → API Key.
  2. mylar3.aliammar.net → Settings:
     - Web Interface: ComicVine API Key (Kapowarr's); Comic Location Path `/comics`;
     - Download settings: SABnzbd; host `http://sabnzbd:8080`, the API key, category `comics`;
       Enable Completed Download Handling;
     - Search providers: Use Newznab; add NZBGeek, `https://api.nzbgeek.info`, Ali's API key,
       category `7030` (Comics);
     - Quality & Post Processing: Enable Post-Processing, Convert CBR to CBZ, Enable Metadata
       Tagging (ComicInfo for Komga);
     - Advanced Settings: Folder Format `$Publisher/$Series ($Year)`, as Kapowarr's.

     Save; then add a series (search by name) and Mylar3 searches its missing issues.
- **Upstream:** [Mylar3](https://github.com/MylarComics/mylar3) ·
  [SABnzbd](https://sabnzbd.org/wiki/)

**Gotchas**
- SABnzbd refuses a name it doesn't know ("Hostname verification failed"): its own hostname is
  admitted at its first start, so compose sets it to `sabnzbd`; the door's name is the agent's step
  above. A rebuilt config needs that step again.
- Mylar3's pages check that it can make a folder under its comic location; if it can't (not
  `99:100`), its home page fails with a Python error rather than its warning.
- SABnzbd checks the client caddy-apps passes on (`X-Forwarded-For`) and refuses any outside private
  ranges, a Tailscale `100.x` address too (`inet_exposure` 0; tested 2026-10-29). Tailscale clients
  arrive as OPNsense's own address, so they pass.
