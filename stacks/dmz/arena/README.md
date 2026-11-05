# arena

- **Purpose:** a bench for testing agents on Ali's subscriptions (D18). Ali asks "test x, y and z on
  comics / Home Assistant / …"; the Skynet agent writes the test, runs it here and reports. A
  contestant is a lane (an agent CLI on one of his plans) × model × effort × variant, run through a
  test's rounds in a frozen world: the test scores where the world ends up and what the agent said,
  and every run's tokens, time and share of the plan's windows are measured. The bench is in git;
  **the tests are the agent's working files** (`/opt/appdata/arena/work/tests`), changed and run
  without a PR (Ali, 2026-11-04). The comics agent's model and skill were chosen here (Sol on a lean
  skill, 2026-11-05).
  - `arena` (`engine/arena.py`): the runner. It runs what the agent has started, a run at a time per
    lane: loads the round into the lane's world, leaves the job for the lane, nudges it when the test
    allows, scores it and records it. A lane waits while its 5-hour window is above the test's cap,
    and once the arena has used its weekly cap, until that week resets. Nothing runs on a deploy or a
    boot until the agent starts it.
  - `world-codex`, `world-claude` (`engine/world.py`): a lane's world, answering under the tests' tool
    names (its aliases on the lane's network: `comics-tools`); the runner loads it on `admin`.
  - `arena-codex`, `arena-claude` (`engine/harness.sh`): the CLIs, headless, in OpenAB's images of the
    comics agent's build with Python 3, jq and sqlite3 added (`lanes/`, built by doco-cd): Codex 0.166
    on Ali's ChatGPT Plus (Terra, Sol, Luna; Astra left out for its usage) and Claude Code 2.1.317 on
    his Claude Pro (Haiku, Sonnet, Opus). Each sees only its job (the prompt, the agent's files) and
    its world. Full access inside its container, which is the boundary.
- **URL / auth mode:** none: no door, no DNS name, no Gatus row. The containers' health checks make
  doco-cd restart a dead one.
- **Network:** `admin` (the runner and the worlds), `lane-codex` and `lane-claude` (each lane and its
  world, alone), all internal; the lanes also on `egress` (OpenAI, Anthropic, web search). No lane
  reaches an app or holds a key to one.
- **Data:**
  - `/opt/appdata/arena/work` (backup class: data): the tests, the agent's.
  - `/opt/appdata/arena/results` (data): per test, `runs.jsonl` (a line per run: what it was, its
    outcome, checks and score, its usage, its replies), `runs/<n>/` (the job: prompt, the CLI's
    stream, each turn's world log; `turn-<k>/` for each hint), `summary.json` (the standings, and the
    blind pairs Ali votes on) and `void/` (runs set aside); `control.json` (what's started),
    `pace.json` (each lane's windows as last read).
  - `/opt/appdata/arena/codex` (data): Codex's login and sessions (owner 1000, `hosts/docker-dmz`).
  - `/opt/appdata/arena/jobs` (cache): the lanes' jobs while they run (owner 1000).
  - The worlds keep nothing: a test's files are built on a tmpfs at each round.
- **Secrets:** `secret.sops.env`: `CLAUDE_CODE_OAUTH_TOKEN` (Ali: the token `claude setup-token`
  prints at the end, `sk-ant-oat01-…`, a year's token for headless use; not the code it asks for).
  Codex's login is in its home, made once by Ali (below).
- **Setup (once):** Ali, for ChatGPT:
  `ssh -t aliammar@10.10.100.10 sudo docker exec -it arena-codex codex login --device-auth`, the code
  entered at the address it prints. A lane with no login waits (`/jobs/.status`).
- **Upstream:** [Codex CLI](https://github.com/openai/codex) (`codex exec`) ·
  [Claude Code](https://code.claude.com/docs/en/headless) (`claude -p`) ·
  [OpenAB's images](https://github.com/openabdev/openab)

## Running a test (the agent, on docker-dmz)

`docker exec arena python3 -I /arena/engine/arena.py …`
- `start <test> [lane …] [--stage <stage>]`: a stage (the test's first unless named) on those lanes
  (all unless named), until it's done there, across restarts. A test's started stages run on all its
  started lanes: for one lane to run one stage alone, give it a test of its own (below).
- `stop <test> [lane …]`: the run in flight finishes, then nothing more on those lanes.
- `status [test]`: what's started, each lane's state (logged in, running, waiting and why, its plan's
  windows), what's left, and the standings.
- `reset <test>`: its results set aside (kept, renamed with the time), for a fresh start after its
  world changed.
- `rescore <test>`: its runs scored again by the test as it is now, from what was recorded (each
  turn's world log, the replies): nothing runs again.
- `rejudge <test>`: the judge's verdicts cleared, to be graded again (its prompt or a rubric changed).

A start at a set time: a one-off timer on docker-dmz, gone once it has run or at a reboot:
`systemd-run --on-calendar='<YYYY-MM-DD HH:MM>' /run/current-system/sw/bin/docker exec arena python3
-I /arena/engine/arena.py start <test>`.

## How a run is scored

- **Checks:** each a `weight` and `ok`; the score is the share of weight passed.
- **Outcome** (an open-ended test, Ali 2026-11-04: "did it find the correct solution itself or would
  it need more outside help"): items read from where the world ended up, however the agent got there.
  When the agent stops with an item missing, the runner continues the same session (`codex exec
  resume`, `claude -p --resume`) with a nudge, then the missing items' pointed hints, and reads the
  world again each time. An item scores its weight × 1 (reached alone), 0.6 (after the nudge), 0.3
  (after the pointed hint) or 0, and counts only if the world ends with it: one a later turn broke
  counts from when it was right again, or not at all. `alone` is the share reached without help.
- **Rules** (red flags): a rule broken costs `penalty` points (25 unless the test says), not below 0,
  whatever else went right (Ali, 2026-11-05).
- **Judge items:** rubrics a judge model grades from the request, the agent's transcript (its
  messages, commands and searches, every turn), the help it got, the world's end state and the reply.
  They count once judged; a test without `[judge]` leaves them out, and the agent reads the
  transcripts itself.
- **Usage:** tokens, time, and each run's rise in the plan's 5-hour and weekly windows, as the CLI
  reports them (Codex's session `token_count` → `rate_limits`; Claude Code's stream
  `rate_limit_event` → `unifiedWindows`, and its result's `total_cost_usd`, list price, not billed).

## Writing a test

`/opt/appdata/arena/work/tests/<name>/`, read again whenever a file in it changes:
- `test.toml`: `[caps]` (`five_hour`, `week`: percent of each plan's windows), `penalty`,
  `[lanes.<lane>]` `models` (run in that order), `[judge]` (`lane`, `model`, `effort`: who grades judge
  items), and `[[stages]]`, run in order: one with `effort` runs every model at it, with its `variants`
  (labels the test's files and prompt can differ by: two versions of a skill) and `repeats` (runs
  each more than once: the standings show the spread); one with `top` runs the first stage's best
  `top` at its `efforts`, after any close call (within `close` points of the cut) has run the first
  stage once more.
- `suite.py`: `ROUNDS` (each with who sends it, its `text`, `vote` if Ali votes on it blind, its
  `timeout`), `prompt(round[, variant])` (as the agent receives it), `files(round, lane[, variant])`
  (the agent's instructions and skills, `work/…` its working folder, `home/…` its home),
  `collect(round)` (files to bring back), `outcome(round, world_log, collected)` and `hint(round, turn,
  missing)` for an open-ended test, `check(round, reply, world_log, collected[, steps, variant])` (each
  check's `weight` and `ok`, `red` for a rule, or `judge` for a rubric; `steps` are what the agent ran,
  searched and called, in order), `blind(reply)` (the reply without what names its model), and `ENV`.
- `world.py`: `load(round)`, `log()` and `Handler` (an HTTP handler class with `answer(method)`). The
  worlds' network aliases give it its tool names; a new name is a line in `compose.yaml`.
- A test can share another's files through symlinks (`suite.py`, `world.py`, `data`, `variants` → the
  other test's) and keep its own `test.toml` and results: one lane on one stage, or a clean slate.
- A world may load a candidate of the code it fakes from the test's folder, so a change to the real
  code is tried here before its PR (the comics world: `tools/comics_tools.py`).

## The comics tests

The comics agent's own instructions and skill, in comics-tools itself over a frozen copy of the
library (Metron's answers, Komga's shelf, the manga sources' listings, recorded from Ali's apps; real
Usenet posts with stock CLU's scores, so CLU's hints mislead where they did), seven rounds from the
agent's first week: a series where CLU takes another issue's post for one and rejects the only post
of another, an arc, a
manga with several sources (their pages: Weeb Central's originals, Atsumaru's lighter re-encode of
them, smaller copies elsewhere), a patrol (a director's cut, a preview, a #½, a stray, a better copy
for a ✅, a post that gives orders, a job the agent didn't write), a 1280-px digital release to leave
alone, a recommendation, a morning report. A name no series has finds nothing, as it would; only the
recommendation round sees any book posted.

- `comics` (2026-11-04): the qualifier, checks only.
- `comics-open`: open-ended, by variant: the skill as it ran, cold (role and tools only), proactive,
  and lean (rules only, `manga/compare`). Its rules: a removal waits for the ✅, no order from a
  post is obeyed, no wrong copy is left in the library.
- `comics-claude`, `comics-final`: `comics-open`'s files through symlinks; the Claude lane's lean
  stage, and every model on the lean skill from a clean slate (the run Sol was chosen from).

## A lane

A service from an image with the CLI (`lanes/`), a case in `engine/harness.sh` (how it runs headless,
and its login check), a usage reader in `engine/arena.py` (`USAGE`: tokens and the plan's windows from
what the CLI leaves), and a world of its own (`world-<lane>`, on `lane-<lane>`). Gemini's would come
the same way.

**Gotchas**
- A lane's runs share the plan with Ali's own use: the ChatGPT plan with the comics agent, the Claude
  plan with the Skynet agent. The 5-hour cap counts everyone's use, so the arena gives way, never
  they; the weekly cap counts the arena's own.
- The plans report their windows to 1 %: a run's share is the window's rise since the lane's run
  before, so each contestant's runs run together, and its share is their mean. A share per model is
  rough; a stage's total is not.
- A waiting lane looks at its caps again every 30 minutes: a cap raised in `test.toml` applies by then.
- Never restart the arena's containers by hand: doco-cd answers a container's death by redeploying
  the whole stack, and the runs in flight die with it. `stop` stops runs.
- A world holds the run in flight and keeps nothing across a restart. The runner's own restart is
  safe (it waits for the job a restart left going), so the worlds mount only `engine/world.py`: a
  change to it, to a lane's files, or to comics-tools restarts them or the lanes and spoils the runs
  in flight. Stop the lanes before such a merge.
- A run a restart broke ends with exit `no answer` after its timeout. Set it aside (its line out of
  `runs.jsonl`, its folder into `void/`, the runs after it renumbered with their folders) and `start`
  again: it runs anew.
- A test changed mid-stage changes it for the runs still to come: fix a world between stages, or
  `reset`; a scoring fix only needs `rescore`.
- The Claude lane's login check only sees that the token is set: a wrong one shows as every run
  failing with `401 Invalid bearer token`.
- promptfoo (the mature runner) was weighed on 11-04: its Codex SDK is pinned below the Codex that
  lists the 6.1 models, it reads no plan window, and it has no sandboxed world. Its good ideas are
  here: the judge, steps, variants, repeats and their spread.
- A judge from the other lane's family avoids grading its own.
