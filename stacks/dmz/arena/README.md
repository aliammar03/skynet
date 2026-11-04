# arena

- **Purpose:** a bench for testing agents on Ali's subscriptions (D18). Ali asks "test x, y and z on
  comics / Home Assistant / …"; the Skynet agent writes the test, runs it here and reports. A
  contestant is a lane (an agent CLI on one of his plans) × model × effort, run through a test's
  rounds in a frozen world: the test's checks score what the agent did and said, and every run's
  tokens, time and share of the plan's windows are measured. The bench is in git; **the tests are the
  agent's working files** (`/opt/appdata/arena/work/tests`), changed and run without a PR (Ali,
  2026-11-04).
  - `arena` (`engine/arena.py`): the runner. It runs what the agent has started, a run at a time per
    lane: loads the round into the lane's world, leaves the job for the lane, scores it with the
    test's checks and records it. A lane waits while its 5-hour window is above the test's cap, and
    once the arena has used its weekly cap, until that week resets. Nothing runs on a deploy or a
    boot until the agent starts it.
  - `world-codex`, `world-claude` (`engine/world.py`): a lane's world, answering under the tests' tool
    names (its aliases on the lane's network: `comics-tools`); the runner loads it on `admin`.
  - `arena-codex`, `arena-claude` (`engine/harness.sh`): the CLIs, headless, in OpenAB's images of the
    comics agent's build with Python 3, jq and sqlite3 added (`lanes/`, built by doco-cd): Codex 0.166
    and Claude Code 2.1.317. Each sees only its job (the prompt, the agent's files) and its world.
    Full access inside its container, which is the boundary.
- **URL / auth mode:** none: no door, no DNS name, no Gatus row. The containers' health checks make
  doco-cd restart a dead one.
- **Network:** `admin` (the runner and the worlds), `lane-codex` and `lane-claude` (each lane and its
  world, alone), all internal; the lanes also on `egress` (OpenAI, Anthropic, web search). No lane
  reaches an app or holds a key to one.
- **Data:**
  - `/opt/appdata/arena/work` (backup class: data): the tests, the agent's.
  - `/opt/appdata/arena/results` (data): per test, `runs.jsonl` (a line per run: what it was, its
    checks and score, its usage, its reply), `runs/<n>/` (the job: prompt, the CLI's stream, the
    world's log) and `summary.json` (the standings, and the blind pairs Ali votes on); `control.json`
    (what's started), `pace.json` (each lane's windows as last read).
  - `/opt/appdata/arena/codex` (data): Codex's login and sessions (owner 1000, `hosts/docker-dmz`).
  - `/opt/appdata/arena/jobs` (cache): the lanes' jobs while they run (owner 1000).
  - The worlds keep nothing: a test's files are built on a tmpfs at each round.
- **Secrets:** `secret.sops.env`: `CLAUDE_CODE_OAUTH_TOKEN` (Ali, `claude setup-token` on his Claude
  account; a year's token for headless use). Codex's login is in its home, made once by Ali (below).
- **Setup (once):** Ali, for ChatGPT:
  `ssh -t aliammar@10.10.100.10 sudo docker exec -it arena-codex codex login --device-auth`, the code
  entered at the address it prints. A lane with no login waits (`/jobs/.status`).
- **Upstream:** [Codex CLI](https://github.com/openai/codex) (`codex exec`) ·
  [Claude Code](https://code.claude.com/docs/en/headless) (`claude -p`) ·
  [OpenAB's images](https://github.com/openabdev/openab)

## Running a test (the agent, on docker-dmz)

`docker exec arena python3 -I /arena/engine/arena.py …`
- `start <test> [lane …] [--stage <stage>]`: a stage (the test's first unless named) on those lanes
  (all unless named), until it's done there, across restarts.
- `stop <test> [lane …]`: the run in flight finishes, then nothing more on those lanes.
- `status [test]`: what's started, each lane's state (logged in, running, waiting and why, its plan's
  windows), what's left, and the standings.
- `reset <test>`: its results set aside (kept, renamed with the time), for a fresh start after its
  world changed.
- `rescore <test>`: its runs scored again by the checks as they are now: the checks read only what was
  recorded (the reply, the world's log), so nothing runs again.

## Writing a test

`/opt/appdata/arena/work/tests/<name>/`, read again whenever a file in it changes:
- `test.toml`: `[caps]` (`five_hour`, `week`: percent of each plan's windows), `[lanes.<lane>]`
  `models`, `[judge]` (`lane`, `model`, `effort`: who grades judge items), and `[[stages]]`, run in
  order: one with `effort` runs every model at it, with its `variants` (labels the test's files and
  prompt can differ by: two versions of a skill) and `repeats` (runs each more than once: the
  standings show the spread); one with `top` runs the first stage's best `top` at its `efforts`,
  after any close call (within `close` points of the cut) has run the first stage once more.
- `suite.py`: `ROUNDS` (each with who sends it, its `text`, `vote` if Ali votes on it blind, its
  `timeout`), `prompt(round[, variant])` (as the agent receives it), `files(round, lane[, variant])`
  (the agent's instructions and skills, `work/…` its working folder, `home/…` its home),
  `collect(round)` (files to bring back), `check(round, reply, world_log, collected[, steps,
  variant])` (each check's `weight` and `ok`, `red` for a rule broken; or `judge`, a rubric, for the
  judge model to grade from the request, the run's calls and its reply; `steps` are what the agent
  ran, searched and called, in order), `blind(reply)` (the reply without what names its model), and
  `ENV`.
- `world.py`: `load(round)`, `log()` and `Handler` (an HTTP handler class with `answer(method)`). The
  worlds' network aliases give it its tool names; a new name is a line in `compose.yaml`.

**Open-ended tests** (Ali, 2026-11-04: "let the models think … did it find the correct solution
itself or would it need more outside help"): a suite with `outcome(round, world_log, collected)`
(items, each a `weight`, `ok` and a pointed `hint`, read from where the world ended up, however the
agent got there) and `hint(round, turn, missing)` (what Ali would say: a nudge at turn 1, the missing
items' hints at turn 2) is run with a **hint ladder**. When the agent finishes and an item isn't
reached, the runner continues the same session with the hint (`codex exec resume`, `claude -p
--resume`) and reads the world again. A run scores each item's weight times 1 (reached alone), 0.6
(after the nudge), 0.3 (after the pointed hint) or 0; `alone` is the share reached without help. Its
`check()` then holds the rules (red flags) and the judge's items on its approach. The comics test's
open version is `comics-open`, with variants for the skill as it runs, a proactive one, and cold (its
role and tools, no know-how).

The comics test (the first): the comics agent's own `AGENTS.md` and skill, in comics-tools itself
over a frozen copy of the library (Metron's answers, Komga's shelf, the manga sources' listings,
recorded from Ali's apps; real Usenet posts with stock CLU's scores), seven rounds from the agent's
first week.

## A lane

A service from an image with the CLI (`lanes/`), a case in `engine/harness.sh` (how it runs headless,
and its login check), a usage reader in `engine/arena.py` (`USAGE`: tokens and the plan's windows from
what the CLI leaves), and a world of its own (`world-<lane>`, on `lane-<lane>`). Gemini's is next.

**Gotchas**
- A lane's runs share the plan with Ali's own use: the ChatGPT plan with the comics agent, the Claude
  plan with the Skynet agent. The caps count everyone's use, so the arena gives way, never they.
- The plans report their windows to 1 %: a run's share is the window's rise since the lane's run
  before, so each contestant's runs run together, and its share is their mean.
- Codex's session holds its plan's windows (`token_count` → `rate_limits`); Claude Code's stream
  (`rate_limit_event` → `unifiedWindows`) and its result's `total_cost_usd` (list price, not billed).
- A test changed mid-stage changes it for the runs still to come: fix a world between stages, or
  `reset`; a check fix only needs `rescore`.
- promptfoo (the mature runner) was weighed on 11-04: its Codex SDK is pinned below the Codex that
  lists gpt-6.1-terra, it reads no plan window, and it has no sandboxed world. Its good ideas are
  here: the judge, steps, variants, repeats and their spread.
- A judge item's verdict counts once the judge has run (between the judge lane's runs); until then
  the run's score leaves it out, and `status` says how many wait. A judge from the other lane's
  family avoids grading its own.
