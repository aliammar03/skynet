---
date: 2026-08-28
kind: session          # session | incident | decision
title: seed jikan anime index for aiometadata
tier_touched: [T2]      # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: ["compose/aiometadata", "vm-docker-dmz 10.10.100.15", "aiometadata-jikan_rest-1"]
---

# 2026-08-28 · session · seed jikan anime index for aiometadata

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Task: "setup jikan in aiometadata." Turned out the self-hosted Jikan stack
(jikan_rest/jikan_mongo/jikan_redis/jikan_typesense) was ALREADY fully wired in
compose/aiometadata/compose.yaml, secrets in .env.sops, config under ./jikan, and running
healthy 11 days per inventory (docker-docker-dmz.json, collected 2026-08-27). aiometadata already
points at it: .env.git JIKAN_API_BASE=http://jikan_rest:8080/v4, ANIME_API_OVERLAY_ENABLED=true.

So the real gap was DATA, not infra. Nothing in the jikan_rest container auto-indexes (no cron/
supervisor/schedule:work baked in), so Mongo had only grown via aiometadata's on-demand microcaching.
Counted via `php artisan tinker` over the app's own mongodb connection (had to set HOME=/tmp +
XDG_CONFIG_HOME=/tmp — container runs as uid 10001 with home /nonexistent, so psysh refused to write
its config; also tinker here has no --execute, must pipe PHP on stdin). Initial state:
anime=216, manga=0, genres=0, producers=908, magazines=0.

Ran the fast/bounded indexers foreground via `docker --context docker-dmz exec -e HOME=/tmp
aiometadata-jikan_rest-1 php artisan <cmd> --no-interaction`:
- indexer:genres  → parsed anime+manga genres/themes/demographics, "Indexing complete"
- indexer:common  → magazines parsed 1493 (+producers refresh)
Verified: `wget -qO- http://127.0.0.1:8080/v4/genres/anime` now returns Action(count 5013), etc.

indexer:anime-schedule was started foreground but exceeded the 2-min tool timeout; the in-container
exec process (PID 11553) KEPT RUNNING after the client was killed (docker exec without -t survives
client interrupt). Confirmed via /proc/<pid>/cmdline scan.

Rather than block on the multi-minute seasonal + multi-hour full index, wrote a chained,
resumable runner (scratchpad/jikan-seed.sh), copied it into the container, launched detached with
`docker exec -d`. It: waits (via /proc scan, no pgrep dependency) behind any already-running
`artisan indexer:` to respect the shared MAL rate limit, then runs indexer:anime-current-season,
then `indexer:anime --resume --delay 1` (the full ~all-of-MAL scrape; resumable). Delay started at
the default 3s, dropped to 1s mid-session at Ali's request (killed the still-waiting runner PID 11708,
patched the script, relaunched as PID 11937 — the big index had not started yet, so nothing was lost).
1 req/s is still under MAL's ~3/s ceiling but more likely to draw throttling than 3s.
Logs to /tmp/jikan-seed.log in the container. Confirmed both PID 11553 (schedule) and PID 11708
(jikan-seed.sh, in its wait loop) alive at hand-off.

Verified end-to-end path from the aiometadata container itself:
`wget -qO- http://jikan_rest:8080/v4/anime/1` → Cowboy Bebop JSON. Wiring is good.

## Actions & outcomes
- inventory + compose read → jikan stack already deployed/healthy 11 days; gap is unseeded DB
- tinker count (HOME=/tmp) → anime=216 manga=0 genres=0 producers=908 magazines=0
- indexer:genres → complete; /v4/genres/anime serves data (Action count 5013)
- indexer:common → magazines 1493
- indexer:anime-schedule → started foreground, timed out client-side, PID 11553 still running in-container
- detached scratchpad/jikan-seed.sh via `docker exec -d` → queued behind 11553, will run current-season then `indexer:anime --resume --delay 1`; log /tmp/jikan-seed.log
- aiometadata → jikan_rest /v4/anime/1 = Cowboy Bebop → path verified

## Graveyard — tried & abandoned
- `php artisan ... --execute='...'` → this jikan-rest's tinker has no --execute option; piped PHP on stdin instead.
- tinker without HOME override → "Writing to directory /nonexistent/.config/psysh is not allowed" (uid 10001 home=/nonexistent); fixed with -e HOME=/tmp -e XDG_CONFIG_HOME=/tmp.
- foreground `indexer:anime-schedule` → exceeded 2-min tool timeout; not a failure (process survived), but proved foreground is wrong shape for these — switched to `docker exec -d` runner.
- mongosh direct count (no creds) → auth error ("err" for every collection); counted via the app's configured mongodb connection instead.

## Outcome (seed complete)
Full index finished FAST at delay=1 (well under a session): log "SEED COMPLETE" 2026-08-29T00:33:49Z.
- indexer:anime → 30393 entries indexed/updated, 4 failed; `indexer:anime --failed --delay 1` requeue → 0 failed.
- Mongo anime 216 → 30389. producers 909, magazines 1493.
- genres collection still counts 0, but /v4/genres/anime serves the full list (Action count 5013) —
  jikan serves genres from elsewhere, not the `genres` table; the count is a red herring, ignore it.
- Typesense search live: /v4/anime?q=naruto → Naruto / The Last / Boruto, 46 total. aiometadata's
  anime overlay + search now backed by a full local index.

## Follow-ups / open threads
- No persistent scheduler: the DB will go stale again without one. Proper fix is a compose change
  (a `schedule:work` sidecar or cron running indexer:incremental / seasonal refreshes) — that's an
  authored compose PR, out of scope for this seed. Worth a SKY directive or a small PR.
- Consider whether manga is wanted (aiometadata is anime-only today; left manga=0 unseeded).
