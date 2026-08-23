---
date: 2026-08-23
kind: session          # session | incident | decision
title: librespeed wifi speed-test deploy
tier_touched: [T1, T2]  # tiers this episode ACTUALLY used (not what it could touch)
grants: []              # root grants used this episode: "host KeyID", else empty
refs: [PR #96, compose/librespeed, compose/caddy-apps]
---

# 2026-08-23 · session · librespeed wifi speed-test deploy

<!-- RAW EPISODE. Write what actually happened, in the concrete. Do NOT summarize, generalize,
     or collapse this into a lesson — that destroys the episodic signal before it can be used
     (SKY-006 / journal/README.md). Distillation happens at READ time, never here. -->

## What happened
Ali asked for a LAN speed tester for wifi clients (diagnosis). Chose LibreSpeed over
OpenSpeedTest/speedtest-tracker/iperf3: browser-based, single container, no login, and pointed at
a LAN server so a test measures the wireless link, not the ISP. Scoped internal-only, telemetry ON
(sqlite history), host vm-docker-dmz.

Built compose/librespeed the skynet way. Resolved the image digest from ghcr myself:
`ghcr.io/librespeed/speedtest:6.0.2-alpine@sha256:456389839009c7fdfc14f0840b840f1cce0f57ca7e24bf957cc745c9f2d8b28b`.
Image introspection findings: exposed port is **8080** (not 80), entrypoint hard-codes the sqlite
telemetry DB to **/database/db.sql** (→ bind mount /opt/docker/appdata/librespeed/data:/database),
ships a built-in wget healthcheck. Env vars honored: MODE, WEBPORT, TITLE, TELEMETRY, DB_TYPE,
REDACT_IP_ADDRESSES, ENABLE_ID_OBFUSCATION, PASSWORD, OBFUSCATION_SALT.

Secrets: generated a random stats PASSWORD + OBFUSCATION_SALT, encrypted straight to .env.sops
(sops encrypt only needs the public age recipient from .sops.yaml — no private key on the ops box;
the private key is root:root at /opt/skynet-ops/secrets/age.key, read via sudo by gitops-deploy).
Never printed the plaintext.

Caddyfile: added `speed.aliammar.net { reverse_proxy 10.10.100.72:8080 }` in the NO-AUTH section.
No DNS change (the *.aliammar.net wildcard already A-records to apps-Caddy 10.10.100.35), no firewall
change (container + Caddy share the dmz L2 macvlan). PR #96, Ali merged.

Deployed: `scripts/gitops-deploy.sh librespeed` → running (healthy) in ~9s. Then
`scripts/gitops-deploy.sh caddy-apps` to publish the route — Caddy runs with `--watch`, so the
container was NOT recreated (Up 5 days) and reloaded the new route in place, zero interruption to
other sites. Verified end-to-end from inside the caddy-apps container: GET to
10.10.100.72:8080/backend/getIP.php with Host: speed.aliammar.net → HTTP 200,
`{"processedString":"10.10.100.35",...}`. Loaded Caddy config (admin API :2019) contains the route.

## Actions & outcomes
- introspect ghcr librespeed image → port 8080, sqlite at /database/db.sql, built-in healthcheck
- compose/librespeed/{compose.yaml,.env.git,.env.sops} written; check-invariants OK
- PR #96 opened, merged by Ali
- gitops-deploy librespeed → running (healthy)
- gitops-deploy caddy-apps → route live via --watch reload, container not recreated
- curl from ops VM (VLAN 90) to speed.aliammar.net → TIMEOUT. Not a fault: the ops brain isn't on
  the client ingress path; it manages docker hosts over SSH. Verified from the correct vantage
  (inside caddy-apps container) instead → 200.
- curl from docker HOST (10.10.100.15) to container 10.10.100.72:8080 → connection refused. Also
  not a fault: macvlan host↔own-container isolation. Caddy (also on the macvlan, .35) reaches it fine.

## Graveyard — tried & abandoned
- Tried to make the new `netdiag` role tag (teal) show up in Arcane: redeploy, then explicit
  gitops-sync trigger, then polled the project's tags for ~100s → stayed `[]`. The
  `/environments/0/projects/tags` endpoint is a READ-ONLY union derived from projects' compose
  x-arcane (POST to it 404s). Existing tags (ai/bookmarks/books/media/proxy/tunnel) all pre-existed.
  Conclusion: Arcane does NOT apply a brand-new x-arcane tag to an already-created GitOps project on
  redeploy/sync — abandoned chasing it (cosmetic fleet-view grouping; service is fully functional).
  Contradicts compose/README's "Arcane applies x-arcane.tags automatically on GitOps sync".

## Follow-ups / open threads
- `netdiag` tag not applied to the librespeed project in Arcane. Likely applies only at project
  creation, or needs Ali to add it once in the Arcane UI. Non-blocking. If it's genuinely
  create-only, compose/README's claim about new tags auto-applying needs a caveat.
- Optional: a runbooks/ entry on using speed.aliammar.net to diagnose wifi (client at the AP vs
  across the house; compare to iperf3 for lab-grade numbers).
- Stats password lives in compose/librespeed/.env.sops (key PASSWORD); read with
  `sudo SOPS_AGE_KEY_FILE=/opt/skynet-ops/secrets/age.key sops -d compose/librespeed/.env.sops`.

<!-- Journal entries are APPEND-ONLY history: once written, an episode is not rewritten. A
     correction is a NEW entry that references this one, the same way git never edits a past
     commit. (journal/README.md) -->
