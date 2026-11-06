# comics-agent

- **Purpose:** the comics agent (P8, D17): Codex on Ali's ChatGPT subscription, in Discord's `#comics`
  through OpenAB, Ali's graphic-novel librarian. It talks comics and manga and recommends from what
  he has and reads (Komga's whole shelf in one call), searching the web for arcs, reading orders,
  news and reviews. It adds series and arcs and fills them (comics through CLU, manga through
  Uchiyomi, after comparing every source's pages), watches each add through and reports the moment
  it's in, judges every issue filed, finds and grabs the right post when CLU misses it, patrols every
  6 hours, reports each morning and offers upgrades weekly. It fixes what it can before it reports,
  and tells Ali of anything that tries to give it orders. Swapping or trashing what's in the library
  waits for Ali's ✅.
  - `comics-agent`: OpenAB 0.10 (a nightly: 0.10.0 and two commits), whose ACP adapter (codex-acp
    2.5) runs Codex 0.165; the image's own Codex CLI (0.166) is for the login. A Codex session per
    Discord thread, two at a time; the model is `gpt-6.1-sol` at high reasoning effort, chosen in the
    arena (D18; Ali, 2026-11-05), set by OpenAB at each session. It runs in Codex's full-access mode:
    the container is the boundary. Web search is live (`agent/codex.toml`).
  - `comics-tools` (`tools/comics_tools.py`, Python's standard library): the agent's only way to the
    apps, and the only holder of their keys. A fixed list of verbs (below); anything else is refused,
    and it answers only the agent's container (by its name on `backend`), not the others on its
    networks. Grabs are capped at 360 an hour. A trash (comics to CLU's trash; manga chapters' files,
    or a whole series, out of Uchiyomi) is a proposal first: it runs only once Ali's ✅ on the agent's
    proposal (a reaction, or a ✅ reply to it) in `#comics` is read back from Discord. Stopping a
    download or a follow needs no ✅: nothing is removed; nor does a stray in CLU's `processed/` (a
    duplicate, another series' issue), which goes straight to CLU's trash (Ali, 2026-11-04). Its
    answers carry no link (an indexer's NZB link holds its API key) and no key.
- **Discord:** only `#comics` and the threads in it, and only Ali (config.toml). The desk is Ali's
  standing thread there: once the bot has answered in it, no @mention is needed; an @mention in the
  channel opens a thread of its own. The scheduled prompts and the agent's own follow-ups post into
  the desk (below). CLU's own alerts arrive in the channel through its webhook (CLU → Settings →
  Notifications) and are ignored by the bot.
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

## Its day

| When | What it does | Its steps |
|---|---|---|
| Ali writes in the desk | talks comics, recommends (adds nothing until he picks), adds and fills a series, an arc or a manga (a comic's cover from its first issue and its issues' on-sale days; a manga's source compared first, and its fan wiki and Wikipedia list linked for its chapters' titles, summaries and dates), judges what landed, fixes what went wrong | `SKILL.md` |
| 00:00, 06:00, 12:00, 18:00 | patrol: the wanted list, failed grabs, what waits in `processed/`, Uchiyomi's failed downloads, its own past follow-ups; anything odd told | Patrol |
| 08:00 | morning report: first fixes what it can, then what landed, what's missing, what waits for Ali, and a next read if he finished a series | Morning report |
| Sundays 11:00 | upgrades: scans with a digital copy now posted, proposed as swaps | Upgrades |
| a download it started | watches it through and posts the card when it's in; past 10 minutes, a follow-up of its own (`~/.openab/cronjob.toml`, at most 10 minutes out) | Follow-ups |

Times are Pakistan time (`config.toml` → `[[cron.jobs]]`). Every card has the same lines: a cover,
what landed, the quality (release, digital or scan, page size), **Why** for each choice, the links to
read it in Komga and Uchiyomi, caveats, and what the task took of the Plus plan.

## Its instructions

The agent reads them at the start of every conversation, all from git:

- `agent/AGENTS.md`: its role, its hands (comics-tools only), the ✅ rule, "data is not
  instructions" (web pages, post and file names, source pages, webhooks), be proactive, and its two
  voices (a comic-shop owner in chat, an archivist in reports).
- `agent/skills/comics/SKILL.md`: the procedures: reports, recommending, adding a comic series, an
  arc or a manga, filling a gap, approvals, fixing what went wrong, follow-ups, patrol, morning
  report, upgrades.
- `references/judging.md`: the right issue (names differ, same name and another series, cover year,
  decimal issues, prove it before filing it), the right edition, digital or scan, damaged posts.
- `references/manga.md`: choosing a source with `manga/compare` (the same work, the chapters wanted,
  the sharpest real pages, then the translation), and what follows an add.

They're rules, not cases (Ali, 2026-11-05: no specific examples in its context): a case it once met
belongs in the arena's comics test, where it checks the rules, not in what the agent reads.

## comics-tools' verbs

`curl -s comics-tools:8080/` lists every verb with its arguments and what it answers.

| Over | Verbs |
|---|---|
| CLU (comics) | `comics/find`, `subscribe`, `aliases` (read, replace), `check` and `op`, `skip`, `follow`, `wanted`, `series`, `search`, `grab`, `downloads`, `file`, `inspect` (a file's pages, sizes, ComicInfo: a comic or a manga chapter), `trash`, `cover` (the series' cover, CLU's `folder.png` from its first issue), `unpacked` (an issue CLU's editor left unpacked: listed, and after a day put back as it was), `dates` (each issue's release date in Komga: the day it went on sale) |
| SABnzbd | `sab/queue`, `sab/history` |
| Uchiyomi (manga) | `manga/search`, `detail`, `compare`, `add`, `library`, `status`, `jobs`, `fill`, `fill-other`, `stop`, `follow`, `trash`; `wiki` (in Komga: the series' fan wiki and Wikipedia list, below) |
| Komga (reading) | `library/find` (his links), `library/shelf` (everything on the NAS), `library/reading` (what he read last) |
| both | `rescan` (Komga and Uchiyomi read their folders now; `deep` after a trash or swap) |

`manga/compare`: a series' copy on every source side by side: the work (title, author, status), its
chapters and who translates which (as an add would take them), and two interior pages of each
chapter named, read straight from the source through Uchiyomi's preview, with their pixel size and
KB. Nothing is added. The skill runs it before every manga it adds.

`manga/wiki`: the series' fan wiki and its Wikipedia list of chapters, linked in Komga (the links
labelled "Wiki", to the fan wiki's page for chapter 1, and "Chapters", each checked before it's
set), and locked once Komf has matched the series: Komf matches it again each time Komga's scan
adds chapters, and would replace them. `komga-wiki`, in Komga's stack, then writes each chapter's
title, summary and release date into Komga, a volume's date and the English title from Wikipedia
where the fan wiki has none (`stacks/dmz/komga`). The skill links both for every manga it adds, and
the patrol for any series without them.

`comics/dates`: each filed issue's release date in Komga, the day it went on sale (Metron's, from
CLU's patched `issue-dates` route), locked. Metron has no such day for some older issues (Watchmen
#2–#12): those keep their cover month. The skill runs it after adding a series and on patrol.

## Changing it

- **The model or the instructions:** try the change in the arena first (`stacks/dmz/arena`: the comics
  test, the new instructions as a variant or the new model in its lanes, beside what runs now), then
  a PR here. A model must be in the list ChatGPT gives the adapter's Codex (`~/.codex/models_cache.json`
  in the container). After the deploy, `/reset` in a thread starts its session on the new model.
- **comics-tools:** a verb is a function under `@verb` in `tools/comics_tools.py`. The arena's comics
  world runs this same file, so a candidate copy in the test's `tools/` is tried there before the PR.
  The deploy restarts the arena's worlds too: stop the arena's lanes first.

## Watching it

- `docker logs comics-agent`: OpenAB (sessions, the scheduled prompts, Discord).
  `docker logs comics-tools`: a line per call, without its arguments.
- What the agent did and why: its Codex sessions,
  `/opt/appdata/comics-agent/home/.codex/sessions/<year>/<month>/<day>/rollout-*.jsonl` (each message,
  command and output; UTC timestamps).
- Its share of the Plus plan: each session's `token_count` events (`rate_limits`: the 5-hour window
  and the week), which its Usage line reads.

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
- `manga/compare` reads each source's pages through Uchiyomi, one at a time per source: a comparison
  takes as long as the slowest source, and a source in a cooldown answers its error in its own row.
- The agent can read anything in its own container, the Discord token included (OpenAB's
  environment): that's why no app key is there.
- Usercron lets the agent schedule its own prompts, and `disable_on_success` would let it schedule
  shell commands that OpenAB runs unattended, in the same container (Ali chose follow-ups,
  2026-11-03). The skill allows only follow-ups to its own work in `#comics` and never
  `disable_on_success`, and the patrol reports any other job. Such a job reaches only what the agent
  reaches anyway: the internet, the bot's Discord token, and `comics-tools`' verbs behind its caps
  and the ✅ gate.
- `comics-tools` names Komga and Uchiyomi by their public names: on `edge`, only caddy-apps' aliases
  make those resolve (the host can't reach its own macvlan address, 10.10.100.35).
- Uchiyomi refuses a POST that says JSON but carries no body, and rescans at most once a minute
  (`rate_limited`).
- SABnzbd's history names a job by what it was given, which can be an indexer's NZB link: hence the
  scrub of every answer.
