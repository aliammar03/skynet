# comics-agent

- **Purpose:** the comics agent (P8, D17): Codex on Ali's ChatGPT subscription, in Discord's `#comics`
  through OpenAB, runs comics and manga day to day. It adds and fills series (comics through CLU, manga
  through Uchiyomi), judges every issue filed, finds and grabs the right post when CLU misses it,
  patrols the wanted list every 6 hours, reports each morning and offers upgrades weekly. Swapping or
  trashing what's in the library waits for Ali's ✅.
  - `comics-agent`: OpenAB 0.10 with Codex CLI 0.159 and its ACP adapter. A Codex session per Discord
    thread, two at a time; the model is `gpt-6.1-terra` (Ali, 2026-11-03), set by OpenAB at each
    session. It runs in Codex's full-access mode: the container is the boundary.
  - `comics-tools` (`tools/comics_tools.py`, Python's standard library): the agent's only way to the
    apps, and the only holder of their keys. A fixed list of verbs (`GET /` lists them) over CLU,
    SABnzbd, Komga and Uchiyomi; anything else is refused, and it answers only the agent's container
    (by its name on `backend`), not the others on its networks. Grabs are capped at 360 an hour. A trash is
    a proposal first: it runs only once Ali's ✅ on the agent's proposal (a reaction, or a ✅ reply to
    it) in `#comics` is read back from Discord. Its answers carry no link (an indexer's NZB link holds
    its API key) and no key.
- **Discord:** only `#comics` and the threads in it, and only Ali (config.toml). The desk is Ali's
  standing thread there: once the bot has answered in it, no @mention is needed; an @mention in the
  channel opens a thread of its own. The patrol (00:00, 06:00, 12:00, 18:00), the morning report
  (08:00) and the weekly upgrades (Sundays 11:00) post into the desk. CLU's own alerts arrive in the
  channel through its webhook (CLU → Settings → Notifications) and are ignored by the bot.
- **URL / auth mode:** none: no door, no DNS name, no Gatus row (Ali, 2026-11-03). Its containers'
  health checks make doco-cd restart a dead one, and a morning report that doesn't come says the rest.
- **Network:**
  - `comics-agent`: the stack's `egress` (OpenAI, Discord) and its internal `backend`, nothing else.
  - `comics-tools`: `backend`; CLU's `clu_backend` (CLU and SABnzbd by name: CLU's port has no login,
    hence D17's exception to Networks); `edge`, for Komga and Uchiyomi through caddy-apps (its `edge`
    aliases `komga.aliammar.net`, `uchiyomi.aliammar.net`) and for Discord.
- **Data:**
  - `/opt/appdata/comics-agent/home` → `/home/node`: Codex's login (`.codex/auth.json`) and sessions,
    OpenAB's thread map and caches (`.openab`) (backup class: data). Owner 1000, the image's user
    (`hosts/docker-dmz`).
  - From git, read-only: `config.toml` (OpenAB), `agent/AGENTS.md` (the agent's standing
    instructions, in its working directory) and `agent/skills/comics` (its skill, at
    `~/.agents/skills/comics`).
  - `comics-tools` keeps nothing on disk: its search results, proposals and grab count are in memory,
    gone at a restart (a proposal is made again).
  - It reads, read-only: SABnzbd's `sabnzbd.ini` (its API key), CLU's library (`/data`) and downloads
    (`/downloads`) at CLU's own paths, for `inspect`.
- **Secrets:**
  - `secret.sops.env`: `DISCORD_BOT_TOKEN`, the comics bot's (Ali; not Skynet's bot), for both
    containers: OpenAB's login, and comics-tools reading Ali's ✅.
  - `tools.sops.env`, comics-tools only: `KOMGA_API_KEY` (Ali's Komga account → API keys,
    `comics-tools`) and `UCHIYOMI_TOKEN` (Ali's Uchiyomi → Profile → Connections → API tokens,
    `comics-tools`: read + write + admin; admin for Rescan everything).
  - Codex's login is in its home, made once by `codex login --device-auth` (below).
- **Setup (once, after the deploy):**
  - Codex's login: `ssh skynet@10.10.100.10 sudo docker exec -it comics-agent codex login --device-auth`,
    Ali enters the code at the address it prints (device-code login allowed in ChatGPT → Settings →
    Security), then `sudo docker restart comics-agent`.
  - Ali @mentions the bot once in the desk; it answers, and from then on it's in.
- **Upstream:** [OpenAB](https://github.com/openabdev/openab) ([config](https://github.com/openabdev/openab/blob/main/docs/config-reference.md),
  [Codex](https://github.com/openabdev/openab/blob/main/docs/codex.md)) ·
  [Codex CLI](https://github.com/openai/codex) · [codex-acp](https://github.com/agentclientprotocol/codex-acp)

**Gotchas**
- OpenAB fills every `${NAME}` in `config.toml` from its environment before reading it (the IDs come
  from compose.yaml's `x-discord`), comments and prompts included.
- The bot stays in the desk while one of its messages is among the thread's last 200; the patrol
  sees to that. If it ever stops answering there, @mention it once.
- The model is chosen per session through OpenAB (`[pool] default_config_options`); a model Codex
  doesn't know logs `failed to set default config option` and the session runs on Codex's default.
- The agent can read anything in its own container, the Discord token included (OpenAB's
  environment): that's why no app key is there.
- `comics-tools` names Komga and Uchiyomi by their public names: on `edge`, only caddy-apps' aliases
  make those resolve (the host can't reach its own macvlan address, 10.10.100.35).
- Uchiyomi refuses a POST that says JSON but carries no body, and rescans at most once a minute
  (`rate_limited`).
- SABnzbd's history names a job by what it was given, which can be an indexer's NZB link: hence the
  scrub of every answer.
