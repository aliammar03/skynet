# arena

- **Purpose:** models side by side on Ali's subscriptions (D18): each contestant is a lane (an agent
  CLI on one of his plans) × model × effort, run through a suite's rounds in a frozen world. A
  round's checks score what the agent did and said, Ali votes blind on the rounds that are taste, and
  every run's tokens, time and share of the plan's windows are measured. Reusable: a suite is one
  kind of task (`suites/comics` today; Skynet's summaries or media recommendations later), a lane
  one CLI (Gemini's later).
  - `arena` (`engine/arena.py`): the runner. It runs `plans/*.toml`, a run at a time per lane: loads
    the round into the lane's world, leaves the job for the lane, scores it with the suite's checks
    and records it. A lane waits while its 5-hour window is above the plan's cap, and once the arena
    has used its weekly cap, until that week resets.
  - `world-codex`, `world-claude` (`engine/world.py`): a lane's world, answering under the suite's
    tool names (`comics-tools`) on the lane's network; the runner loads it on `admin`.
  - `arena-codex`, `arena-claude` (`engine/harness.sh`): the CLIs, headless, from OpenAB's images:
    Codex 0.166 (as the comics agent) and Claude Code 2.1.317. Each sees only its job: the prompt,
    the agent's files, and its world. Full access inside its container, which is the boundary.
- **URL / auth mode:** none: no door, no DNS name, no Gatus row. The containers' health checks make
  doco-cd restart a dead one.
- **Network:** `admin` (the runner and the worlds), `lane-codex` and `lane-claude` (each lane and its
  world, alone), all internal; the lanes also on `egress` (OpenAI, Anthropic, web search). No lane
  reaches an app or holds a key to one.
- **Data:**
  - `/opt/appdata/arena/results` (backup class: data): per plan, `runs.jsonl` (a line per run: what
    it was, its checks and score, its usage, its reply), `runs/<n>/` (the job: prompt, the CLI's
    stream, the world's log) and `summary.json` (the standings, and the blind pairs Ali votes on).
    `pace.json`: each lane's windows as last read.
  - `/opt/appdata/arena/codex` (data): Codex's login and sessions (owner 1000, `hosts/docker-dmz`).
  - `/opt/appdata/arena/jobs` (cache): the lanes' jobs while they run (owner 1000).
  - The worlds keep nothing: the frozen library is built on a tmpfs at each round.
- **Secrets:** `secret.sops.env`: `CLAUDE_CODE_OAUTH_TOKEN` (Ali, `claude setup-token` on his Claude
  account; a year's token for headless use). Codex's login is in its home, made once by Ali (below).
- **Setup (once, after the deploy):** Ali, for ChatGPT:
  `ssh -t aliammar@10.10.100.10 sudo docker exec -it arena-codex codex login --device-auth`, the code
  entered at the address it prints. A lane with no login waits (`/jobs/.status`).
- **Upstream:** [Codex CLI](https://github.com/openai/codex) (`codex exec`) ·
  [Claude Code](https://code.claude.com/docs/en/headless) (`claude -p`) ·
  [OpenAB's images](https://github.com/openabdev/openab)

## Plans

`plans/<name>.toml`: the suite, the caps, the lanes' models (and a lane's `not_before`), and stages,
run in order. A stage with `effort` runs every model at it; one with `top` runs the first stage's
best `top` at its `efforts`, after any close call (within `close` points of the cut) has run the first
stage once more. `repeats` runs a stage more than once. A finished plan does nothing more; a new
plan, or a new stage, is a PR.

## A suite

`suites/<name>/`:
- `suite.py`: `ROUNDS` (each with who sends it, its text, `vote` if Ali votes on it blind, its
  `timeout`), `prompt(round)` (as the agent receives it), `files(round, lane)` (the agent's
  instructions and skills, `work/…` its working folder, `home/…` its home), `collect(round)` (files
  to bring back), `check(round, reply, world_log, collected)` (each check's weight, pass, and `red`
  for a rule broken), `blind(reply)` (the reply without what names its model), and `ENV`.
- `world.py`: `load(round)`, `log()` and `Handler` (an HTTP handler class with `answer(method)`).
  The worlds' network aliases give it its tool names.

The comics suite's world is comics-tools itself (the comics agent's own code) over a frozen copy of
the library: Metron's answers, Komga's shelf and the manga sources' listings recorded from Ali's apps
(read-only, 2026-11-04), and real Usenet posts with stock CLU's scores, so its hints mislead where
they did (`data/`). Seven rounds from the agent's first week: Mister Miracle (2017), the Court of
Owls, Monster, a patrol, Long Halloween's judging, a recommendation and a morning report.

## A lane

A service from an image with the CLI, a case in `engine/harness.sh` (how it runs headless, and its
login check), a usage reader in `engine/arena.py` (`USAGE`: tokens and the plan's windows from what
the CLI leaves), and a world of its own (`world-<lane>`, on `lane-<lane>`).

**Gotchas**
- A lane's runs share the plan with Ali's own use: the ChatGPT plan with the comics agent, the Claude
  plan with the Skynet agent. The caps count everyone's use, so the arena gives way, never they.
- The plans report their windows to 1 %: a run's share is the window's rise since the lane's run
  before, so each contestant's runs run together, and its share is their mean.
- Codex's session holds its plan's windows (`token_count` → `rate_limits`); Claude Code's stream
  (`rate_limit_event` → `unifiedWindows`) and its result's `total_cost_usd` (list price, not billed).
- The skill's usage line reads Codex's sessions; a Claude lane can't, and it isn't scored.
