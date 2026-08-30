> Agent-generated position note, written after auditing the actual pipeline (`collect-*.sh`,
> `render-docs.sh`, `invariants.json`, `tofu/`, `nix/`, `compose/`). Companion to the
> [NetBox vs Nautobot note](2026-08-28-netbox-vs-nautobot.md) — that one answers "which product",
> this one answers the question underneath it. Raw, no commitment; feeds SKY-004 / SKY-011 / SKY-015.

# What should be the source of truth for this lab?

*Compiled 2026-08-28, against the tree at `claude/netbox-vs-nautobot-apdxof`.*

## 0. The answer up front

**Git, as it already is.** The store is not the problem and no product will fix what's actually
weak. The system has the right *shape* — three kinds of truth, cleanly separated, all in git — and
three concrete defects, none of which is "we need a database":

1. **No identity spine.** Every generated view is a fuzzy join on *IP address*. Nothing has a
   stable key. **The lab's own naming convention is already that key and nothing reads it** (§2).
2. **No controller.** Observed truth is committed nightly and never *asserted* against intended
   truth. The nightly PR proves something changed, never whether it was supposed to. (SKY-004's
   "plant, two sensors, no controller" — still open.)
3. **Coverage holes**, in both directions: ~2 of 21 guests have declared desired state, and the
   live switch/AP estate is collected by nothing at all (§3).

Fixing #1 is a few dozen lines and unlocks the other two. That is the whole recommendation.

## 1. What we already have (and it's more than it looks)

Four truths, each with a different direction of flow — this separation is the system's real asset:

| Truth | Lives in | Direction | Consumer |
|---|---|---|---|
| **Intended** | `tofu/`, `compose/`, `hosts/` + `nix/`, `.env.sops` | git → reality | tofu, Arcane, nixos-rebuild |
| **Observed** | `inventory/*.json`, `inventory/firewall/` | reality → git | `render-docs.sh` |
| **Constraint** | `invariants.json` | authored, asserted | `check-invariants.sh` (deterministic gate) |
| **Episodic** | `journal/`, `docs/decisions/`, `planning/` | authored | a cold agent, at read time |

Against the standard SoT checklist this scores well: versioned, diffable, reviewable, revertible,
offline-readable, no service to keep alive, no backup obligation, survives the loss of every host.
NetBox and Nautobot each give you *one* store with a web UI and take most of that away.

## 2. Defect 1 — the identity spine that already exists and isn't read

`render-docs.sh` builds its host table by merging three sources **keyed on IP**, with a hardcoded
priority ladder (DHCP reservation > single-IP alias > unique-target DNS A record) and a bash `case`
statement for VLAN names. A host, to this system, is *an IP that several sources happen to agree on*.
That's why a reverse-proxy front door reads as a host (the SKY-015 bug) — there's no key to hang
"this is a vhost, not a machine" on.

But **ADR 0001 already defines a primary key**: VMID = VLAN with its trailing zero dropped, followed
by the two-digit last octet. Nothing in the repo consumes it. Deriving the expected IP from VMID
alone and joining against the rendered host table, with no authored mapping whatsoever:

| Result | Count | Detail |
|---|---|---|
| ✅ Derived IP matches a known host/alias | **14** | 240→`HOST_PBS`, 525→`HOST_OMADA`, 635→`HOST_PROXY_ADMIN`, 751→`tdns-core`, 837→`HOST_AUTHENTIK`, 1035→`HOST_PROXY_APPS`, 10015→`HOST_DOCKER_DMZ`, … |
| ⚠️ No match — **stopped** guest | **4** | 101 `debian`, 231 `lxc-adguard-core`, 720 `lxc-adguard-network`, 999 `vm-skynet-ops` — all dead, all still on disk |
| 🔴 No match — **running** guest | **1** | **526 `lxc-unifi-os-server`** — live, and invisible to every generated view: no reservation, no alias, no DNS record |

That table is an audit the current system cannot produce, it needed no new service, and it separates
"healthy" from "stale" from "genuinely unmapped" in one pass. The 4 stopped guests are a retirement
list. The 1 running miss is a real hole.

**What to build:** teach `render-docs.sh` to join on VMID-derived identity instead of guessing by IP,
and add the derivation as a `check-invariants.sh` assertion (a guest whose address contradicts its
VMID is either misconfigured or an intentional exception, and exceptions belong in `invariants.json`
next to 5001/635/837/2020 — which are already listed there by VMID, so the file is halfway to being
the entity registry). This satisfies **ADR 0003** cleanly: it schematizes only what a deterministic
consumer reads, and the consumers already exist.

**Corollary, same doctrine:** the VLAN-name map and the proxy-alias set are *authored knowledge*
currently living inside a bash `case` in the renderer. They're data with a non-LLM consumer. They
belong beside the invariants, read by the script — not baked into it.

## 3. Defect 2 & 3 — the controller, and the holes

**No controller.** Nothing computes `intended − observed`. The layers to diff already exist or are
landing: `tofu plan -detailed-exitcode` (exit 2 = drift), `nixos-rebuild dry-activate`,
`docker compose --dry-run`, and firewall-mirror-vs-baseline. This is SKY-004 Phase 1 and it stays
report-only. With §2's spine it gets sharper: drift can be attributed to an *entity*, not an IP.

**Coverage, honestly measured:**

- **Intended state covers ~2 of 21 guests** — `vm-docker-dmz` (tofu) and `vm-skynet-ops` (nix).
  Everything else exists only as observed truth. That's fine as a position, but it should be a
  *chosen* position, not an accident: the cheap next takes are Technitium zone records (already T2,
  already collected, a provider exists) and the rest of the `ops-managed` pool.
- **The switch/AP estate is collected by nothing.** `ROLE_INFRASTRUCTURE_SWITCHES` and
  `ROLE_INFRASTRUCTURE_APS` exist in the firewall, an EAP683 shows up in DHCP, and both controllers
  run as guests (525 Omada, 526 UniFi) — but no collector reads either controller. Ports, VLAN
  assignments, PoE state, AP inventory: all invisible. This is the largest observed-truth hole in
  the lab and the one place a SoT product would genuinely have had something to hold.
- **Reverse-proxy routes** (hostname → which Caddy → real backend) still live only in Caddyfiles —
  SKY-015 Phase 3, and the prerequisite for any view that resolves a vanity name to a machine.

## 4. The plan, ranked by leverage per hour

1. **VMID identity spine** — join key + invariant + move the VLAN/proxy maps into data. Unblocks
   SKY-015's canonical host map and sharpens SKY-004's drift signal. *Highest leverage in the repo
   right now.* Ships the stale-guest and unmapped-guest audits for free.
2. **Drift diff, report-only** (SKY-004 P1) — start with compose + firewall baseline; tofu/nix light
   up as those layers grow.
3. **A UniFi/Omada collector** (T1, read-only) — close the biggest observed-truth hole.
4. **Caddy route collector** (SKY-015 P3) — the last join needed to resolve a name to a backend.
5. **Widen intended state deliberately** — Technitium records, then the ops-managed pool, one PR at
   a time. Not a sprint; a ratchet.

Nothing on that list adds a service, a credential, or a backup obligation.

## 5. Entirely other methods — what I'd reject, and the one worth stealing from

- **NetBox / Nautobot** — see the companion note. Beyond the fit problems there: they'd become a
  *fourth* place identity lives without retiring any of the other three. Adding a SoT to a system
  whose defect is *un-joined* truth makes the joining problem worse, not better.
- **Infrahub** — right model (branch/diff/merge in the data layer), wrong maturity and weight for
  ~20 guests. Watch it.
- **Ansible inventory + group_vars** — genuinely a decent identity spine, and the YAML-inventory
  shape is close to what §2 wants. But it drags in a whole config-management paradigm we've
  deliberately not adopted, and nix already owns host definition. Take the *idea* (an entity file),
  leave the runtime.
- **✅ Worth stealing: a rebuildable SQLite view.** The renderer is doing relational work in `jq`,
  `awk` and `sort` — that's what the fuzzy IP joins actually are. Build `inventory.db` from
  `inventory/*.json` on every render: git stays truth, the DB is a **cache, never committed as
  truth, always regenerable** (same rule the memory spoke already applies to a semantic index).
  Renderers query SQL; the agent gets real joins and ad-hoc questions ("which running guest has no
  DNS record, no alias, and no backup job?") instead of grep. Costs one file and no service.
  Warranted *after* §2 — a spine first, then joins over it.

## 6. Verdict

Git is the right source of truth and should stay it. The lab doesn't need a better store — it needs
a **key**, a **controller**, and two missing **collectors**. The key already exists as a convention
nobody reads; that's where to start, and it's the cheapest item on the list.

---
### Referenced
- ADR 0001 (static addressing / VMID convention) — `docs/decisions/0001-static-ip-addressing.md`
- ADR 0003 (ambiguity layering; format follows enforcement) — `docs/decisions/0003-*.md`
- SKY-004 (drift-as-signal), SKY-011 (machine-enforced invariants), SKY-015 (renderer overhaul)
- The 2026-08-17 declarative-future thesis — `planning/scratchpad/2026-08-17-declarative-future-and-agent-cognition.md`
