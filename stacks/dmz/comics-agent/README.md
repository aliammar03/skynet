# comics-agent

- **Purpose:** the comics agent (P8, D17): Codex on Ali's ChatGPT subscription, in Discord's `#comics`
  through OpenAB, Ali's graphic-novel librarian. It talks comics and manga and recommends from what
  he has and reads (Komga's whole shelf in one call), searching the web for arcs, reading orders,
  news and reviews. It adds series and arcs and fills them (comics through CLU, manga through
  Uchiyomi), watches each add through and reports the moment it's in, judges every issue filed,
  finds and grabs the right post when CLU misses it, patrols the wanted
  list every 6 hours, reports each morning and offers upgrades weekly. Swapping or trashing what's
  in the library waits for Ali's ✅.
  - `comics-agent`: OpenAB 0.10 (a nightly: 0.10.0 and two commits), whose ACP adapter (codex-acp
    2.5) runs Codex 0.165; the image's own Codex CLI (0.166) is for the login. A Codex session per
    Discord thread, two at a time; the model is `gpt-6.1-terra` at high reasoning effort (Ali,
    2026-11-03), set by OpenAB at each session. It runs in Codex's full-access mode: the container is
    the boundary. Web search is live (`agent/codex.toml`).
  - `comics-tools` (`tools/comics_tools.py`, Python's standard library): the agent's only way to the
    apps, and the only holder of their keys. A fixed list of verbs (`GET /` lists them) over CLU,
    SABnzbd, Komga and Uchiyomi; anything else is refused, and it answers only the agent's container
    (by its name on `backend`), not the others on its networks. Grabs are capped at 360 an hour. A trash
    (comics to CLU's trash; manga chapters' files, or a whole series, out of Uchiyomi) is a proposal
    first: it runs only once Ali's ✅ on the agent's proposal (a reaction, or a ✅ reply to it) in
    `#comics` is read back from Discord. Stopping a download or a follow needs no ✅: nothing is
    removed; nor does a stray in CLU's `processed/` (a duplicate, another series' issue), which goes
    straight to CLU's trash (Ali, 2026-11-04). Its answers carry no link (an indexer's NZB link holds
    its API key) and no key.
- **Discord:** only `#comics` and the threads in it, and only Ali (config.toml). The desk is Ali's
  standing thread there: once the bot has answered in it, no @mention is needed; an @mention in the
  channel opens a thread of its own. The patrol (00:00, 06:00, 12:00, 18:00), the morning report
  (08:00) and the weekly upgrades (Sundays 11:00) post into the desk, and so do the agent's own
  follow-ups (OpenAB's usercron: `~/.openab/cronjob.toml`, which the agent writes). CLU's own alerts
  arrive in the channel through its webhook (CLU → Settings → Notifications) and are ignored by the
  bot.
- **URL / auth mode:** none: no door, no DNS name, no Gatus row (Ali, 2026-11-03). Its containers'
  health checks make doco-cd restart a dead one, and a morning report that doesn't come says the rest.
- **Network:**
  - `comics-agent`: the stack's `egress` (OpenAI, Discord) and its internal `backend`, nothing else.
  - `comics-tools`: `backend`; CLU's `clu_backend` (CLU and SABnzbd by name: CLU's port has no login,
    hence D17's exception to Networks); `edge`, for Komga and Uchiyomi through caddy-apps (its `edge`
    aliases `komga.aliammar.net`, `uchiyomi.aliammar.net`) and for Discord.
- **Data:**
  - `/opt/appdata/comics-agent/home` → `/home/node`: Codex's login (`.codex/auth.json`) and sessions,
    OpenAB's thread map, caches and the agent's follow-ups (`.openab`, `cronjob.toml`) (backup class:
    data). Owner 1000, the image's user (`hosts/docker-dmz`).
  - From git, read-only: `config.toml` (OpenAB), `agent/AGENTS.md` (the agent's standing
    instructions, in its working directory), `agent/skills/comics` (its skill, at
    `~/.agents/skills/comics`) and `agent/codex.toml` (Codex's settings, as its system config at
    `/etc/codex/config.toml`).
  - `comics-tools` keeps nothing on disk: its search results, proposals and grab count are in memory,
    gone at a restart (a proposal is made again).
  - It reads, read-only: SABnzbd's `sabnzbd.ini` (its API key); for `inspect`, CLU's library (`/data`)
    and downloads (`/downloads`) at CLU's own paths, and Unraid's `Books/Manga` (`/manga`), where
    Uchiyomi downloads.
- **Secrets:**
  - `secret.sops.env`: `DISCORD_BOT_TOKEN`, the comics bot's (Ali; not Skynet's bot), for both
    containers: OpenAB's login, and comics-tools reading Ali's ✅.
  - `tools.sops.env`, comics-tools only: `KOMGA_API_KEY` (Ali's Komga account → API keys,
    `comics-tools`) and `UCHIYOMI_TOKEN` (Ali's Uchiyomi → Profile → Connections → API tokens,
    `comics-tools`: read + write + admin; admin for Rescan everything).
  - Codex's login is in its home, made once by `codex login --device-auth` (below).
- **Setup (once, after the deploy):**
  - Codex's login, by Ali (device-code login allowed in ChatGPT → Settings → Security):
    `ssh -t aliammar@10.10.100.10 sudo docker exec -it comics-agent codex login --device-auth`, the
    code entered at the address it prints, then `ssh aliammar@10.10.100.10 sudo docker restart comics-agent`.
  - Ali @mentions the bot once in the desk; it answers, and from then on it's in.
- **Upstream:** [OpenAB](https://github.com/openabdev/openab) ([config](https://github.com/openabdev/openab/blob/main/docs/config-reference.md),
  [Codex](https://github.com/openabdev/openab/blob/main/docs/codex.md)) ·
  [Codex CLI](https://github.com/openai/codex) · [codex-acp](https://github.com/agentclientprotocol/codex-acp)

**Gotchas**
- OpenAB fills every `${NAME}` in `config.toml` from its environment before reading it (the IDs come
  from compose.yaml's `x-discord`), comments and prompts included.
- The bot stays in the desk while one of its messages is among the thread's last 200; the patrol
  sees to that. If it ever stops answering there, @mention it once.
- The model is chosen per session through OpenAB (`[pool] default_config_options`), from the model
  list ChatGPT gives the adapter's Codex (its version, not the CLI's). A model not in it logs
  `set_config_option not supported, falling back to prompt`: OpenAB then sends `/model …` to Codex as a
  chat turn, and the session runs on Codex's default. It's set only when a session starts, not when
  one resumes: after a change, `/reset` in a thread starts it afresh.
- Renovate can't follow a nightly tag: back to a stable `-codex` tag by hand once one carries codex-acp
  2.5 or later.
- Discord's @ list offers the bot's role beside the bot; `allowed_role_ids` makes either one count.
- Uchiyomi hides the manga sites whose extensions call themselves 18+ (most of the good ones) unless
  asked: `comics-tools` searches sources and the library with `adult=1` (`stacks/dmz/uchiyomi`).
- The agent can read anything in its own container, the Discord token included (OpenAB's
  environment): that's why no app key is there.
- Usercron lets the agent schedule its own prompts, and `disable_on_success` would let it schedule
  shell commands that OpenAB runs unattended, in the same container (Ali chose follow-ups,
  2026-11-03). The skill allows only follow-ups to its own work in `#comics` and never
  `disable_on_success`, and the patrol reports any other job. Such a job reaches only what the agent
  reaches anyway: the internet, the bot's Discord token, and `comics-tools`' verbs behind its caps
  and the ✅ gate.
- The agent reads web pages now as well as post names and source pages: all are data to it
  (`agent/AGENTS.md`), and none can get past `comics-tools`.
- `comics-tools` names Komga and Uchiyomi by their public names: on `edge`, only caddy-apps' aliases
  make those resolve (the host can't reach its own macvlan address, 10.10.100.35).
- Uchiyomi refuses a POST that says JSON but carries no body, and rescans at most once a minute
  (`rate_limited`).
- SABnzbd's history names a job by what it was given, which can be an indexer's NZB link: hence the
  scrub of every answer.
