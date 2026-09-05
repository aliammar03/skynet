---
id: SKY-018
title: "Eight-layer reconciliation: entity spine, the Analyze phase, and the verification toolchain"
status: in-progress
horizon: long
created: 2026-08-28
updated: 2026-09-03
phases: 12
current_phase: 6
tier_touched: [T1, T2]   # Mostly T1 (derive, collect, render, check). P4 EXTENDS the T1 read surface
                         # to the UniFi/Omada controllers ⇒ docs/system-design.md §3 PR. P6/P11 touch
                         # existing T2 actuators without widening any dial — no new pool, no new tier.
related:
  - docs/system-design.md
  - docs/decisions/0003-ambiguity-layering-and-format-follows-enforcement.md
  - docs/decisions/0005-full-agent-control-as-terminal-goal.md
  - planning/ideas/SKY-017-the-road-to-full-agent-control-verification-proving-ground-and-an-evidence-earned-ratchet.md
  - planning/ideas/SKY-004-reactive-operations-event-driven-layer-drift-as-signal.md
  - planning/ideas/SKY-015-inventory-renderer-overhaul-proxy-aware-service-annotation-canonical-host-map-reverse-proxy-route-inventory.md
  - planning/scratchpad/research/2026-08-28-complete-system-and-ansible.md
  - planning/scratchpad/research/2026-08-28-full-agent-control-options.md
  - "[[SKY-018-progress]]"
---

# SKY-018 · Eight-layer reconciliation: entity spine, the Analyze phase, and the verification toolchain

> Make the substrate fit to be autonomous. Every layer gets a **writer and a checker**, every fact
> gets **one home**, and the tools the options research settled — conftest/Rego, `tofu test`, a
> health-gated deploy wrapper, SQLite-as-cache, the journal as a replay log — land where they belong.
> SKY-017 buys autonomy with evidence; **this directive builds the thing the evidence is about.**

> **Status: idea.** Long horizon, twelve phases. Promote with `bin/plan start SKY-018`.

## 0. What this directive owns (and what it doesn't)

The roadmap now has four adjacent directives. The boundary, stated once so nobody re-derives it:

| Directive | Owns |
|---|---|
| **SKY-018 (this)** | The **substrate**: the eight layers, their writers and checkers, and the toolchain that gates and verifies them |
| **SKY-017** | The **ladder**: proving ground, change budget, circuit breaker, adversarial review, the per-capability track record, the first graduations |
| **SKY-004** | The **event transport**: the webhook receiver and the batch→reactive shift. *This directive absorbs its Phase 1 (drift-as-signal), which is L4 and cannot be split from the entity spine* — SKY-004 is left owning reactivity |
| **SKY-015** | Superseded in substance: its Phase 1–2 (proxy annotation, canonical host map) fall out of P2–P3 here, its Phase 3 (route table) becomes P5. **Archive it on this directive's close-out** rather than running both |
| **SKY-016** | Service-deployment hardening; **P6 here builds the rollback half**, SKY-016 keeps the reachability half |

Two cross-references to keep honest: SKY-017 P3 names a health-gated compose wrapper — **that is P6
here**, and SKY-017 consumes it rather than building it. SKY-017's proving ground (P2 there) is the
place P6's rollbacks get tested in the failure case.

## 1. Problem / motivation

The architecture note scored the system as **~70% complete**, where complete means *every layer has a
writer and a checker, and every fact has one home*. The missing 30% is not spread evenly — it is two
empty layers and a set of implementations that work but cannot be checked:

- **L0 Identity is empty.** Every generated view is a fuzzy join on **IP address**. `render-docs.sh`
  merges DHCP reservations, firewall aliases and DNS records with a hardcoded priority ladder, so a
  host is *an IP several sources happen to agree on*. That is why a reverse-proxy front door reads as
  a machine. Meanwhile **ADR 0001's VMID convention already is a primary key** and nothing reads it:
  deriving it with no authored mapping matches **14 of 19 guests**, isolates **4 stale stopped
  guests**, and surfaces **one running guest invisible to every view** (CT 526, the UniFi controller).
  The same hole exists one level up and is currently un-nameable: **services** have no key either, so
  `arcane-manager` runs on the DMZ host with no `compose/` directory behind it and nothing notices.
- **L4 Analyze is empty.** In MAPE-K terms the system is a strong Plan phase wired to no error signal:
  observed truth is committed nightly and never *asserted* against intended truth. The nightly PR
  proves something changed, never whether it was supposed to.
- **L3 has one engine and it can't reach the widest actuator.** `check-invariants.sh` enforces three
  hard laws in bash. `tofu apply` — the highest-blast-radius actuator in the system — has **no
  machine gate between plan and apply at all**.
- **L7 mostly cannot roll back.** deploy-rs magic-rollback ✅ and OPNsense's own validate-and-restore
  ✅ pass ADR 0005 §3. Arcane ❌ (converges from git, never rolls back on health failure), `tofu
  apply` ❌, DNS writes ❌. Under §3 that caps all three below A4 no matter how well they work.
- **L2 has three holes**, one of them live: the **UniFi/Omada switch and AP estate is collected by
  nothing** (both controllers run as guests, `ROLE_INFRASTRUCTURE_SWITCHES` and `..._APS` exist in the
  firewall, an EAP683 shows up in DHCP), the **Caddy route table** lives only in Caddyfiles, and
  there is **no certificate inventory**.
- **L5 does relational work in `jq`, `awk` and `sort`.** The fuzzy joins *are* a hand-rolled query
  planner, and authored knowledge (the VLAN-name map, the proxy-alias set) is baked into a bash
  `case` statement inside the renderer — authored data with a deterministic consumer, living in code.
  That is precisely the shape ADR 0003 says to extract.

None of this is a missing product. It is a missing **key**, a missing **controller**, and a set of
implementations that were right when a human was the only verifier and are not right for A4.

## 2. The eight-layer reconciliation

The verdict per layer — improve in place, replace outright, or build from nothing:

| Layer | Today | Verdict | What changes | Phase |
|---|---|---|---|---|
| **L0 Identity** | *nothing* | **BUILD** | A **typed entity model** — five classes, each with its own natural key (guest ⇒ VMID, service ⇒ compose project, vhost ⇒ hostname, node ⇒ node name, netgear ⇒ device id) plus the edges between them; exceptions in `invariants.json`, judgment facts in a new `lab.json` | P1–P2 |
| **L1 Intended** | tofu (1 guest), nix (1 host), compose (10 svcs), sops | **IMPROVE + WIDEN** | Technitium records + remaining in-pool guests under tofu; **keep Arcane** (see §2 decisions) | P11 |
| **L2 Observed** | 5 collectors → `inventory/` | **IMPROVE + FILL** | entity-keyed output; new collectors for network gear, Caddy routes, certificates | P4–P5 |
| **L3 Constraints** | `invariants.json` + bash gate | **IMPROVE + SECOND ENGINE** | keep bash for the hard laws; add **conftest/Rego** for structured artifacts (`tofu plan -json`, `firewall.json`) | P7–P8 |
| **L4 Analyze** | *nothing* | **BUILD** | drift = intended − observed, per layer, **entity-attributed**, report-only | P9 |
| **L5 Views** | `render-docs.sh`, IP-heuristic joins in jq/awk | **REPLACE the join engine** | a **rebuildable SQLite cache** built at render time; renderer queries SQL over entity keys | P3 |
| **L6 Memory** | journal, ADRs, digest | **IMPROVE** | journal becomes the **replay log** — capability runs write structured steps, so a run resumes instead of re-deriving | P10 |
| **L7 Actuation** | Arcane, tofu, grant-root, deploy-rs | **IMPROVE per actuator** | a **named rollback executor** for each: health-gated compose wrapper, snapshot-before-apply, DNS revert files | P6 |

### Decisions worth recording (so they stay decided)

**L5 join engine — `jq`+`awk` vs SQLite vs a real database**
- **Option A — more `jq`.** Zero new tools; but the joins are already the hardest code in the repo
  and every new dataset (routes, certs, network gear) multiplies the join surface.
- **Option B — a rebuildable SQLite cache.** Build `inventory.db` from `inventory/*.json` at render
  time, query it with SQL, never commit it. **Git stays truth; the DB is a cache** — the same rule the
  memory spoke already applies to a future semantic index. Real joins, and the agent gains ad-hoc
  querying ("which running guest has no DNS record, no alias and no backup job?").
- **Option C — a source-of-truth database (NetBox/Nautobot).** Rejected in its own research note: it
  becomes a fourth home for identity without retiring the other three.
- **Decision: B (CHOSEN).** SQLite ships with the toolchain, the file is gitignored and regenerated
  idempotently, and losing it costs one render.

**L7 compose rollback — wrapper vs platform switch**
- **Option A — switch to Komodo.** Deterministic compose GitOps with richer deploy handling.
- **Option B — a health-gated wrapper around the existing loop:** deploy → probe → on failure
  `git revert` + reconcile.
- **Decision: B (CHOSEN).** The wrapper *is* the dumb executor ADR 0005 §3 asks for, costs no
  platform churn, and generalises to actuators Komodo would never cover. Komodo stays the fallback
  only if the wrapper grows into a product.

**L3 second engine — more bash vs Rego**
- **Option A — extend `check-invariants.sh`.** Legible and already trusted; but plan-JSON policy in
  bash is a parser nobody wants to own.
- **Option B — `conftest`/Rego for structured artifacts only.** `tofu plan -json` is identical to
  Terraform's, so the whole policy ecosystem applies unchanged.
- **Decision: B for structured artifacts, A retained for the hard laws (CHOSEN).** Deliberately *not*
  a migration — legibility beats uniformity, and the hard laws are three greps. Cost is honest: Rego
  is a new language; keep the policy set small and `conftest verify`-tested.

**L6 resumability — journal vs a durable-execution engine**
- **Option A — Temporal/Restate/DBOS.** Mature, and the pattern is exactly right.
- **Option B — steal the pattern only:** deterministic outer loop, every step appended to the journal,
  resume from the record.
- **Decision: B (CHOSEN).** Temporal's workflow history is system-class state in **its own database** —
  a direct §2a rebuild-law violation, plus a standing service. The pattern costs a convention.

**L0 scope — a guest key, or a typed entity model**
- **Option A — VMID only.** Simplest, and it fixes the host-map bug. But it identifies *guests*, and
  half the lab the agent actually operates is **compose services**, which have no VMID. Drift on a
  service, a route pointing at a service, or "which guest hosts this" would all stay un-keyed.
- **Option B — a small typed model: one class per kind of thing, each with a natural key already
  present in collected data.** More surface, but every key already exists — nothing new is invented:

  | Class | Key | Where the key already lives | Address |
  |---|---|---|---|
  | **node** | node name | Proxmox API (`server-proxmox-core`) | — |
  | **guest** | **VMID** | Proxmox API; **derives its IP** (ADR 0001) | `10.10.V.O` |
  | **service** | **compose project name** | the `compose/<dir>/` in git, confirmed on the host by the `com.docker.compose.project` label | none of its own — inherits its host guest's |
  | **vhost** | hostname | Caddyfile + DNS | the front door's IP — **and it is not a host** |
  | **netgear** | controller device id / MAC | UniFi/Omada (P4) | DHCP reservation |

  Edges: `service —hosted_on→ guest`, `guest —on→ node`, `vhost —fronted_by→ guest(proxy) —backend→ service`.

  **ID convention (settled 2026-08-28).** `<class>/<key>`, with the guest key descriptive:
  **`guest/<role>-<vlan>-<vmid>`** — e.g. `guest/docker-dmz-10015`, `guest/skynet-ops-9090`,
  `guest/technitium-core-dns-751`. Rules: *role* is the guest name minus its `vm-`/`lxc-` prefix; the
  VLAN slug is appended **only if the role does not already end with it** (no `docker-dmz-dmz`); the
  VMID is last and remains the authoritative key — names collide today (`lxc-adguard-core` is both
  231 and 731; `vm-skynet-ops` is both 999 and 9090), so the slug is decoration and the number is
  identity. Note `-core`/`-network` in existing names denotes the **Proxmox node**, not the VLAN
  (`technitium-core` and `technitium-network` are both VLAN 70), so those stay part of the role.
  Classes with no numeric key use their natural key alone: `svc/karakeep`, `vhost/pbs.aliammar.net`,
  `node/server-proxmox-core`, `net/ap-omada-downstairs` — a service inherits its host's address and a
  vhost's address is the front door's, so neither needs a VLAN token.

  **The ID is self-validating.** The VLAN slug and the VMID's leading digits encode the same fact, so
  the P2 gate asserts they agree — `...-dmz-751` fails, because 751 is VLAN 70. A cosmetic convention
  becomes a checkable invariant for free.
- **Decision: B (CHOSEN).** Three reasons. (1) The service key is **free and verified** — 10 of 11
  running compose projects match a `compose/` directory by name exactly. (2) It fixes SKY-015
  properly: a vhost stops being a *host with a warning annotation* and becomes **a different class of
  entity**, so "front door, not a host" is a type rather than a heuristic. (3) The audit generalises —
  the same query that found CT 526 (running guest, in no view) finds **`arcane-manager`: a running
  compose project with no `compose/` directory in git**, i.e. a service deployed outside the GitOps
  loop. One model, both holes.

**L0 spine — derived vs authored (Ansible inventory)**
- **Option A — an authored YAML inventory + `group_vars`.** Real inheritance, familiar shape.
- **Option B — derive from the VMID convention; author only what is genuinely judgment.**
- **Decision: B (CHOSEN).** Almost everything an authored file would hold is already collected or
  derivable, so authoring it makes a third copy that drifts. Author only the facts that *are*
  judgment: VLAN display names, which alias is a proxy front door, which guests are intentional
  convention exceptions. (Ansible's *dynamic* Proxmox inventory stays available later as another
  rendering of L2 — a view, never a truth.)

## 3. The plan

- **Scope:** the eight layers reconciled — L0 and L4 built, L5's join engine replaced, L2's holes
  closed, L3 given a second engine, L6 upgraded to a replay log, L7 given rollback executors, L1
  widened where it is cheap and gated.
- **Non-goals:** any autonomy promotion (that is SKY-017 — this directive changes **no** dial);
  adopting a source-of-truth product; converting LXC guests to NixOS; adopting Ansible's runtime; any
  new T3 path; touching the excluded guests beyond reading them.
- **Hosts & tiers touched:** ops VM throughout. **P4 extends the T1 read surface** to the UniFi and
  Omada controllers ⇒ **⚠ `docs/system-design.md` §3 PR + access-and-trust spoke**. P6 and P11 change
  *how* existing T2 actuators run, not *what* they may reach — no dial moves, so no constitution PR
  for those.
- **Rollback posture:** every phase is additive. New scripts are new files; the SQLite cache is
  gitignored and regenerable; the renderer keeps its old path until P3's exit criteria pass; policies
  start in report-only before they fail a build. `git revert` restores any phase.
- **Grants / human actions:** none for P1–P3, P5, P7–P10 (all T1, read + render + check). **P4** needs
  Ali to create two read-only controller credentials **and** merge the constitution PR (⚠ hard
  checkpoint — credential handling + tier assignment). **P6/P11** need normal PR merges.

---

### Phase 1 — L0: the derivation and the audit  (~1–2h)   `[x]` done 2026-09-01
The cheapest thing in the directive, and everything downstream keys on it.
Steps:
1. `scripts/entity.sh` — a sourceable helper covering **all five classes**, not just guests:
   - **guest:** `vmid_to_ip` implementing ADR 0001 (VLAN = leading digits with the trailing zero
     restored, octet = trailing two), plus the inverse. VLAN 100 guests carry 4- and 5-digit ids;
     handle both.
   - **service:** key = the compose project name; read from `compose/*/` in git and from the
     `com.docker.compose.project` label in `inventory/docker-*.json`. Both sides already carry it.
   - **vhost / node / netgear:** key passthrough — hostname, node name, device id.
2. **The `hosted_on` edge.** Each `inventory/docker-<label>.json` carries a `host` label
   (`docker-dmz`) that maps to a guest (`vm-docker-dmz`, VMID 10015) by a convention nobody reads.
   Do **not** string-munge the `vm-` prefix: declare the label→VMID map in `lab.json` (P2) and have
   the helper resolve through it, so a second docker host is a data change, not a code change.
3. `bin/ops entities` — run every class and classify each row: **matched**, **unmatched-and-stopped**
   (stale), **unmatched-and-running** (a real hole), **exception** (declared). Guests join against
   firewall/DNS host facts; services join `compose/` against the running project labels in both
   directions.
4. Unit-test the derivation against the known-good set — guests (240→`HOST_PBS`,
   635→`HOST_PROXY_ADMIN`, 751→`tdns-core`, 1035→`HOST_PROXY_APPS`, 10015→`HOST_DOCKER_DMZ`) and
   services (10 of 11 running projects match a `compose/` dir by name; **`arcane-manager` does not** —
   a service running outside the GitOps loop, and the expected first finding).
5. Journal the first audit as an episode — the stale-guest and undeclared-service lists are
   proposals, not actions. Known members of the stale list today: CT 101 `debian`, CT 231 and CT 720
   (retired AdGuards), VM 999 (the pre-NixOS ops brain), and **CT 1035 `lxc-caddy-dmz`, confirmed by
   Ali as stale and to be destroyed**.
   > **⚠ Verify before destroying CT 1035.** Its derived address `10.10.100.35` is `HOST_PROXY_APPS`,
   > and `*.aliammar.net` A-records to it — the front door for all nine apps vhosts — while the
   > `caddy-apps` container actually runs on `guest/docker-dmz-10015` (`.15`). Establish where `.35`
   > lives now before the destroy: if it is a secondary address on the docker VM, the destroy is
   > safe; if it is still the CT's, destroying it breaks every published app until DNS and the
   > firewall alias are moved. `destroy` is a hard checkpoint at every autonomy level regardless.

Exit criteria: `bin/ops entities` reproduces the guest audit (14 matched / 4 stale / 1
running-unmapped) **and** the service audit (10 declared / 1 undeclared-and-running), resolves
`service → guest` through `lab.json`, and exits non-zero only on a *running* entity — of any class —
that is neither mapped nor a declared exception.

### Phase 2 — L0: authored judgment data, and the invariant  (~1–2h)   `[x]` done 2026-09-01
Steps:
0. **The VLAN vocabulary — settled 2026-08-28, display names already corrected in the renderer.**
   The lab had two competing sets and the renderer's was wrong on **10 and 60, which were swapped**:
   VLAN 10 is the trusted client VLAN (workstation, phone, tablet — and OPNsense's own alias text
   calls it "Trusted VLAN 10") while VLAN 60 is admin access (only the Management Caddy front door).
   Collected firewall truth beat the hardcoded map, which is the ADR 0003 argument in miniature —
   authored knowledge living in code drifted from reality and nothing checked it. This phase moves
   the table out of `render-docs.sh` into `lab.json` and adds the **slugs** used in entity IDs:

   | VLAN | Display name | Slug |
   |---|---|---|
   | 10 | Trusted LAN | `lan` |
   | 20 | Servers | `servers` |
   | 30 | IoT | `iot` |
   | 50 | Management | `mgmt` |
   | 60 | Admin Access | `admin` |
   | 70 | Network Services | `netsvc` |
   | 80 | Identity | `identity` |
   | 90 | Operations | `ops` |
   | 100 | DMZ | `dmz` |

   VLAN 30 was missing from the map entirely and rendered as the literal `VLAN 30` despite already
   holding three hosts — it is **IoT**, now named.
1. **`invariants.json`** gains `entity_conventions`: the VMID⇒IP law plus its *declared exceptions*
   (5001 OPNsense, and any guest deliberately off-convention), each with a one-line `why` in the
   file's existing style. Constraint-class data, read by the gate.
2. **`lab.json`** (new, repo root, same `_comment` discipline) holds the **judgment** facts that are
   currently hardcoded in `render-docs.sh`, plus the model's authored edges: VLAN display names, the
   reverse-proxy front-door alias set (which is what makes a **vhost** a vhost), per-entity role
   labels, and the **docker host-label → VMID map** the `hosted_on` edge resolves through. Display-
   and topology-class data, read by the renderer and the entity helper.
3. `check-invariants.sh` gains the fourth law, stated per class: every **running** entity is either
   mapped or a declared exception — for a guest that means satisfying the VMID convention, for a
   **service** it means having a `compose/<project>/` directory in git. Fails the PR otherwise.
   (`arcane-manager` will fail it on day one: either declare it as an exception with a `why`, or bring
   it into the GitOps loop. That choice is Ali's, and the gate is what forces it to be made.)
4. Delete the `vlan_name()` `case` statement and the inline proxy-alias set from `render-docs.sh`;
   both now read `lab.json`.

Exit criteria: the renderer holds no authored knowledge; a PR that adds an off-convention running
guest without declaring it fails CI; `check-invariants.sh` still passes on `main`.

### Phase 3 — L5: replace the join engine with a rebuildable SQLite cache  (~1–2h)   `[x]` done 2026-09-01
Steps:
1. Add `sqlite` to the nix toolchain (`nix/modules/base.nix`).
2. `scripts/build-db.sh` — load every `inventory/*.json` into `.cache/inventory.db` (gitignored):
   tables for guests, hosts, aliases, dns_records, reservations, pools, containers. Keyed on the
   **entity id from P1**, not on IP. Idempotent; rebuilt from scratch each run.
3. Rewrite the `render-docs.sh` host table as SQL over that cache: the canonical host map joins on
   entity, and a DNS record whose target is a `lab.json` front-door alias renders as
   `⚠ front door — not the host` (SKY-015 P1's fix, now with a real key behind it).
4. Add `bin/ops query "<sql>"` so the agent can ask ad-hoc questions instead of grepping.

Exit criteria: `docs/generated/` renders identically-or-better with no IP-priority ladder left in the
renderer; the DB is absent from git and rebuilt by `render-docs.sh`; `bin/ops query` answers "running
guests with no DNS record, no alias and no backup job".

### Phase 4 — L2: the network-gear collector  (~1–2h)   `[x]` done 2026-09-01 (Omada-only)
The largest observed-truth hole, and the only phase that moves a trust surface.
Steps:
1. **⚠ Hard checkpoint — tier assignment:** PR `docs/system-design.md` §3 to add the **UniFi and
   Omada controllers to the T1 read surface**, plus the access-and-trust spoke. This is an extension
   point (§5, "a new capability / trust boundary"), so it is a constitution PR by rule.
2. **⚠ Hard checkpoint — credentials:** Ali creates a **read-only** local account or API key on each
   controller; the agent never holds an admin credential to either. Stored `0600` under
   `/opt/skynet-ops/secrets/`, same shape as `cloudflare-dns.env`.
3. `scripts/collect-network-gear.sh` → `inventory/network-gear.json`: switches, APs, ports, PoE state,
   VLAN/profile assignment, firmware, adoption status. Degrades gracefully with no creds (exit 0),
   like every other collector.
4. Render a `docs/generated/50-network-gear.md` view and join the estate onto the entity map.

Exit criteria: the switch/AP estate appears in inventory and in a generated view; CT 526 is no longer
invisible; the collector is read-only and exits 0 without credentials.

### Phase 5 — L2: routes and certificates  (~1–2h)   `[x]` done 2026-09-01
Steps:
1. `scripts/collect-routes.sh` — parse the Caddyfiles under `compose/` (and the Management Caddy
   mirror) into `inventory/routes.json`: hostname → which Caddy → backend `host:port` → auth mode.
   Static parse of committed config; no live access needed.
   **This collector is the vhost class's only real source — DNS cannot supply it.** There is no
   `karakeep` A record: `karakeep.aliammar.net` resolves through the single `*.aliammar.net`
   wildcard, so DNS knows **one** name where the apps Caddyfile declares **nine** (karakeep,
   aiostreams, aiometadata, marinara, obsidian, calibre, sillytavern, speed, auth). Until this parse
   exists, every wildcard-served vhost is invisible to inventory.
1b. **The `vhost —backend→` edge is not derivable by name**, so the parse must carry it explicitly:
   `obsidian.aliammar.net` → `svc/obsidian-livesync`, `sillytavern.aliammar.net` → `svc/silly`,
   `speed.aliammar.net` → `svc/librespeed`. And a backend need not be a service at all —
   `auth.aliammar.net` fronts Authentik on **`guest/authentik-identity-837`** — so the edge targets
   either class.
2. `scripts/collect-certs.sh` — certificate inventory (issuer, SANs, notAfter) for the internal and
   published names, from the proxies' own stores where readable, otherwise by probing the endpoints.
3. Render the full resolution chain in `30-services`: vanity name → front door → **real backend
   entity**. Emit an expiry table sorted by soonest.

Exit criteria: a vanity hostname resolves end-to-end in the generated docs; every certificate has a
recorded expiry; no manual Caddyfile reading is needed to answer "where does this actually go".

### Phase 6 — L7: rollback executors  (~1–2h)   `[x]` done 2026-09-03
The phase that unblocks A4 for three actuators. Each executor must be **automatic, testable in the
failure case, and independent of the agent** (ADR 0005 §3).
Steps:
1. **Compose:** extend `scripts/gitops-deploy.sh` into a health-gated path — deploy → wait for
   healthy → probe the service's declared endpoint → **on failure `git revert` the deploy commit and
   let Arcane reconcile back**. The wrapper decides; the agent is not in the loop.
2. **Tofu:** `scripts/tofu-apply.sh` — snapshot every in-pool guest the saved plan touches, apply the
   **saved plan** (never a re-planned one), verify, and roll the snapshot back on failure. `destroy`
   remains a hard checkpoint and is refused by the wrapper outright.
3. **DNS:** every Technitium/Cloudflare write first appends the prior record value to a revert file;
   `scripts/dns-revert.sh` replays it. Trivial, and it converts an ❌ into a ✅ on the actuator table.
4. Record each executor in the actuator table SKY-017 P1 owns — name, trigger, tested-in-failure date.

Exit criteria: a deliberately-unhealthy compose deploy auto-reverts with no human action; a failing
tofu apply restores the snapshot; a DNS write can be undone from its revert file. All three
demonstrated in the failure case, not just reasoned about.

### Phase 7 — L3: the second gate (conftest/Rego over `tofu plan`)  (~1–2h)   `[ ]` not started
Steps:
1. Add `conftest` to the nix toolchain.
2. `policy/tofu/*.rego` — deny any plan that: contains a `delete` action; touches a VMID outside the
   declared pool set; touches any excluded guest with anything heavier than the config-only role;
   creates a resource with no `lab.json` entity mapping. Mirror the hard laws rather than replacing
   them.
3. `policy/*_test.rego` + `conftest verify` in CI — the policies themselves get unit tests, or they
   are just more prose.
4. `scripts/check-policy.sh`, wired into `.github/workflows/checks.yml` as a third job **and** into
   `scripts/tofu-apply.sh` as a pre-apply gate. Ship **report-only for one cycle**, then enforce.

Exit criteria: a PR whose plan would destroy an in-pool guest fails CI; `conftest verify` passes; the
pre-apply gate refuses a plan the CI job would have failed.

### Phase 8 — L3: firewall validation as a capability  (~1–2h)   `[ ]` not started
The capability Ali named, built on data already collected.
Steps:
1. `policy/firewall/*.rego` over `inventory/firewall/firewall.json`: no any-any rule; no rule
   sourcing a `ROLE_OPS_*` alias into a T3 target; every rule carries a description; no alias
   references a host absent from the entity map; `ROLE_OPS_PRIV_TARGETS` is empty (the dormant-alias
   law, now machine-checked).
2. Run it in the nightly, **report-only at A1** — findings become a section of the report and a
   proposal, never an edit. OPNsense is T3; the agent reads and argues, it does not touch.
3. Render the findings into `20-firewall.md` with severity, so the human reads a ranked list.

Exit criteria: the nightly reports firewall findings with zero false positives on the current
ruleset; a deliberately-broken test fixture is caught; nothing writes to OPNsense.

### Phase 9 — L4: build the Analyze phase  (~1–2h)   `[ ]` not started
The empty MAPE-K phase. Absorbs SKY-004 Phase 1.
Steps:
1. `scripts/drift.sh` — compute intended − observed per layer: `tofu plan -detailed-exitcode`
   (exit 2 = drift), `nixos-rebuild dry-activate`, `docker compose config` vs running state, and the
   firewall mirror vs its last-approved baseline.
2. **Attribute every drift to an entity** (P1's key), not to an IP or a file path, so the report says
   *what* regressed.
3. Emit drift as a first-class artifact: a `docs/generated/60-drift.md` view, a journal episode when
   non-empty, and a non-zero exit the nightly can act on. **Report-only** — no auto-correction here;
   that is a SKY-017 graduation.
4. Baseline the firewall mirror so "someone changed it by hand" is detectable at all.

Exit criteria: a hand-made change to a declared resource shows up in the next drift run, named by
entity, within one nightly; a clean lab reports zero drift.

### Phase 10 — L6: the journal as a replay log  (~1–2h)   `[ ]` not started
Steps:
1. `scripts/run-capability.sh` — the deterministic outer loop: takes a capability name and arguments,
   appends a **structured step record** (step, intent, command, exit, artifact) to the run's journal
   entry as it goes, and exits with the run's status.
2. Resume: a run that died mid-way can be continued from its record instead of re-derived — the
   durable-execution pattern without the engine.
3. Surface in-flight and recently-failed runs in `06-agent-digest.md`, so a cold agent sees unfinished
   business before it starts new work.
4. Keep episodes **raw** — structured steps are facts, not narrative; summarising still happens at
   read time (memory spoke).

Exit criteria: a capability killed halfway resumes to completion from its journal record; the digest
shows in-flight runs; no episode is rewritten after the fact.

### Phase 11 — L1: widen intended state where it is cheap  (~1–2h)   `[ ]` not started
Gated on P7 — do not widen what tofu may touch until the plan gate exists.
Steps:
1. Technitium **zone records** declared in `tofu/` (already T2, already collected, a provider exists).
   Records only — server settings stay T3.
2. Declare the remaining **in-pool** guests as tofu resources, importing rather than recreating.
   Coverage goes from ~2 of 21 to every guest the agent may already write.
3. Leave everything else observed-only **on purpose**, and say so in the spoke: excluded guests, the
   node config, template bootstrap, and Proxmox credential administration.

Exit criteria: `tofu plan` is clean against reality for every declared resource; the plan gate passes;
no excluded guest appears in any tofu resource.

### Phase 12 — the reconciliation review  (~1–2h)   `[ ]` not started
Steps:
1. Re-score all eight layers against *"has a writer and a checker; every fact has one home"* and
   publish the scorecard in the architecture note.
2. Update `docs/system-design.md` §1a's pointer and the affected spokes (observability, gitops-loop,
   access-and-trust) to describe what now exists — current rule only, no war stories.
3. **Archive SKY-015** (superseded by P2–P3, P5) and re-scope **SKY-004** to the event transport
   alone, noting P9 delivered its Phase 1.
4. Hand off to SKY-017: the actuator table has rollback executors, drift is attributable, and the
   proving ground now has a substrate worth rehearsing against.

Exit criteria: no layer lacks a checker; the roadmap has no duplicate directives; SKY-017 P1 can start
from real data rather than a survey.

## 4. ▶ Execute prompt
```
Read planning/projects/SKY-018-eight-layer-reconciliation-entity-spine-the-analyze-phase-and-the-verification-toolchain.md and execute Phase <N>.
Follow AGENTS.md: plan loudly then run quietly, never merge your own PRs, request the
narrowest host / shortest grant the phase needs, and checkpoint at the listed human/grant
steps. Phase 4 needs a constitution PR and Ali-created credentials before any collection —
stop and wait there. When the phase's exit criteria are met, do the "Phase close-out" below.
```

## 5. Phase close-out (resume material)
- [ ] Land the work via **PR** (agent never merges its own).
- [ ] Write/refresh a memory `SKY-018-progress` (what shipped, what's next, gotchas) + a MEMORY.md pointer.
- [ ] Bump this file's frontmatter (`current_phase`, `status`, `updated`) and flip the phase box to `[x]`.
- [ ] `bin/plan list` to refresh the roadmap index.
- [ ] Paste the **Continue prompt** below to resume in a fresh session:
```
Continue planning/projects/SKY-018-eight-layer-reconciliation-entity-spine-the-analyze-phase-and-the-verification-toolchain.md at Phase <N+1>.
Prereqs carried from the last phase: <…>. Resume context from memory [[SKY-018-progress]].
Follow AGENTS.md as above.
```

## 6. Status log
- 2026-08-28 — created (draft). Derived from the eight-layer architecture note and the full-agent-control
  options research; sequenced against SKY-017 (ladder) and marked to supersede SKY-015 / absorb
  SKY-004 P1 on close-out.
- 2026-08-28 — L0 widened from a guest key to a **typed five-class entity model** after the question
  "is this only Proxmox, or docker services too?". The service key was already there and verified
  (10 of 11 running compose projects match a `compose/` dir); modelling **vhost as its own class**
  turns SKY-015's warning annotation into a type; the audit generalised to find `arcane-manager`,
  a service running outside the GitOps loop.
- 2026-08-28 — entity ID convention settled: `<class>/<key>`, guests as `role-vlan-vmid`, no stutter,
  VMID authoritative. Applying it surfaced a prerequisite: the lab has **two conflicting VLAN
  vocabularies** (renderer vs firewall descriptions), which P2 step 0 now resolves.
- 2026-08-28 — VLAN vocabulary settled (lan/servers/mgmt/admin/dns/identity/ops/dmz). Ali corrected
  the renderer's map: 10 and 60 were **swapped**, so `docs/generated/` had been publishing the wrong
  names for both. Fixed in `render-docs.sh` and re-rendered ahead of this directive, since a shipped
  factual error should not wait twelve phases.
- 2026-08-28 — vocabulary corrected by Ali: VLAN 70's slug is `netsvc` (not `dns`), and **VLAN 30 was
  missing from the renderer entirely** — it is IoT, and already holds three hosts. Also established
  that vhosts cannot be derived from DNS: `karakeep.aliammar.net` has no A record and resolves via
  the `*.aliammar.net` wildcard, so P5's Caddyfile parse is the vhost class's only source, and the
  backend edge must be carried explicitly because the names don't match the projects.
- 2026-08-28 — naming convention finalised into `docs/conventions/naming.md` (entity IDs, VLAN slugs,
  edges, the service-address rule). Writing it corrected the spoke's "VMID = 4 digits" claim: the
  fleet runs **two VMID forms** — VLAN-in-full (2020, 5001, 9090, 10015) and VLAN-trailing-zero-dropped
  (240, 525, 635, 751, 837, 1035) — so the parse matches against the declared VLAN set rather than by
  digit count, `10xx` is the one ambiguous prefix, and new guests use the canonical full form.
  CT 1035 confirmed stale/to-destroy, with the `10.10.100.35` front-door dependency flagged.
- 2026-09-01 — **P1 done.** `scripts/entity.sh` (five classes, VMID⇄IP both forms, rc 0/1/2),
  `lab.json` seeded with the docker host-label→VMID map, `bin/ops entities` → `scripts/audit-entities.sh`,
  `tests/entity-test.sh` (28/28) wired into CI + pre-commit. First audit: guests **7 matched / 5 stale /
  3 running-unmapped / 4 exception**, services **10 matched / 1 running-unmapped (`arcane-manager`)**.
  Reconciled vs the §1 hand-count: the machine reports 101 + 999 as running-unmapped (it can't know
  they're known leftovers); CT 526 is the one surprise hole (closes in P4). Two parser facts: VM 999
  parses as valid legacy VLAN 90 (not off-convention), and CT 1035 is genuinely ambiguous (`10xx`),
  resolved via the firewall fact set. Journal: `2026-09-01-session-sky-018-p1-first-entity-audit`.
- 2026-09-01 — **P1 triage + audit went clean.** VM 9000 was almost destroyed as "stale" but is the
  OpenTofu clone template → made the audit template-aware. arcane-manager → relocation ([[SKY-019]]);
  interim `compose/arcane-manager/` captured (bootstrap, not self-synced). Ali destroyed 101/231/999/
  9091/1035/526 and renumbered the kept AdGuard **720→730** (fixing an off-convention address at the
  source — no exception needed). `bin/ops entities` now **exits 0**: 13 guests, 8 matched / 0 stale /
  0 hole / 4 exception / 1 template; services 11/0.
- 2026-09-01 — **P2 done.** VLAN display names + slugs moved out of `render-docs.sh`'s `vlan_name()`
  case into `lab.json` (`vlans.list`); front-door alias set declared in `lab.json` (`front_doors`, for
  P3's explicit "front door — not the host"); `invariants.json` gained `entity_conventions` (the
  VMID↔IP law + `declared_vlans` + an empty `exceptions` list). `check-invariants.sh` gained the **4th
  law** — reuses `audit-entities.sh` to assert every running entity is mapped or excepted (proven to
  fail on a synthetic rogue guest, clean on `main`). Renderer verified behavior-preserving (VLAN
  headers byte-identical). Tests 36/36. Refreshed inventory + regenerated docs committed alongside so
  the CI gate runs against current truth.
- 2026-09-01 — **P4 done (Omada-only).** Two PRs: **#132** (docs) admitted the Omada controller to the
  T1 read surface (system-design §3 + access-and-trust + network spokes); **#133** the collector.
  Three checkpoints cleared (Ali): merged #132, firewall reachability (found the *port* was missing —
  `HOST_OMADA` was in `ROLE_OPS_API_TARGETS` but 8043 wasn't in `PORT_OPS_API`; verified `.50.25`
  blocked until added), and a read-only **Viewer** account (`svc-ops`). Controller is Omada v6.2.14.11
  (session-login API, verified read-only: a reboot call → `-1007`). `scripts/collect-network-gear.sh`
  → `inventory/network-gear.json` (pinned cert, SNI `Omada` via `--resolve`; degrades exit 0). `net`
  class joined into `audit-entities.sh` (informational, not a hole); `netgear`/`netports` DB tables;
  `docs/generated/50-network-gear.md` with a **reserved-vs-adopted** reconciliation. First run's drift:
  firewall reserves 3 sw + 4 AP slots, only `.2`/`.7` adopted; Ali's EAP772 `.161` adopted-unreserved;
  port 8 `U6-AP` a leftover Ubiquiti trunk. Credential is sops-nix (`secrets/omada.env.sops` +
  `secrets.nix` names[]) — **needs `nixos-rebuild switch`** to materialize. Tests 45/45. CT 526 (UniFi)
  gone → estate Omada-only, 526 resolved by removal.
  `sqlite` in `nix/modules/base.nix`, `scripts/build-db.sh` → `.cache/inventory.db` (gitignored, rebuilt
  each run), entity-keyed tables. `render-docs.sh` host map is now `scripts/sql/host-map.sql` (a running
  guest wins its IP + carries its entity id) — VLAN tables gained an **Entity** column; `vhosts.sql` +
  a 30-services section render every front-door DNS name as "⚠ front door — not a host" (SKY-015 fix,
  real key behind it). `bin/ops query "<sql>"` answers ad-hoc (running guests with no DNS/alias/backup
  = 0, all covered). Degrades gracefully with no sqlite3. Tests 41/41 (P3 skips when sqlite3 absent, so
  the pre-rebuild pre-commit hook stays green; CI on ubuntu runs them). **⚠ Post-merge: `nixos-rebuild
  switch` on the ops VM**, else the nightly render degrades to "Host map pending" until sqlite3 is on PATH.
- 2026-09-01 — **P5 done (PR #141, merged).** L2 routes + certs — the vhost class's only source.
  `scripts/collect-routes.sh` static-parses `compose/caddy-apps/Caddyfile` → `inventory/routes.json`
  (vhost → front door `svc/caddy-apps` → backend **entity** → auth); the backend edge is derived via
  the compose `ipv4_address` map (name-mismatches resolved: obsidian→obsidian-livesync,
  speed→librespeed; `auth`→`guest/authentik-identity-837`), 9/9 resolving. `scripts/collect-certs.sh`
  → `inventory/certs.json` (openssl-probe of reachable infra endpoints; app-vhost ACME certs
  unreachable from VLAN 90, pending). vhost class joined into the audit; routes+certs DB tables;
  `30-services` renders the resolution chain + a soonest-first expiry table. All T1, additive.
- 2026-09-03 — **P6 done** (this branch). L7 rollback executors, one per actuator, each with a
  **deterministic** rollback decision (never the LLM) and a **failure-case test**. (1) **Compose:**
  `gitops-deploy.sh --gate` → `scripts/deploy-gate.sh` (probe: every project container Running / not
  Restarting / healthy-or-none) → on failure `scripts/gitops-rollback.sh` (`git revert` the deploy
  commit → push → Arcane reconciles). (2) **Tofu:** `scripts/tofu-apply.sh <saved-plan>` — refuses
  delete/replace and T3 excluded-guest plans outright, snapshots every touched in-pool guest
  (`scripts/pve-snapshot.sh`, operate token), applies the **saved** plan, verifies (post-apply plan
  clean), rolls the snapshot back on apply-or-verify failure, prunes on success; **fails closed** if a
  guest can't be snapshotted. (3) **DNS:** `scripts/dns-revert.sh` records+replays the inverse of every
  `cf-dns-route.sh` write (landed as commit 1/3). Failure-case demos: `tests/compose-rollback-test.sh`
  7/7, `tests/tofu-rollback-test.sh` 9/9, `tests/dns-revert-test.sh` 5/5 — all inject the failure and
  assert the executor fired (externals stubbed; no production writes). New spoke
  `docs/design/actuators.md` (the executor registry + the deterministic-rollback rule) + §7 row +
  gitops-loop pointer. All three tests wired into CI + pre-commit. No dial moved; destroy/T3 stays a
  hard checkpoint (the tofu wrapper refuses it). **NEXT — P7** (conftest/Rego over `tofu plan`) — do
  NOT start it or SKY-020 in this session.
