# Skynet — System Design

> **Skynet became self-aware at 2026-08-16.** The build is over; operations have begun.
> This is the constitution of the system that woke up — the slow-changing law that every
> future change is measured against. It replaces the old birth plan, now archived verbatim as
> [`history/deployment-plan-v5.md`](history/deployment-plan-v5.md).

**The one VM:** `vm-skynet-ops` · **10.10.90.90** static · VLAN 90 · VMID 9090 · on `server-proxmox-core`.

---

## 0. What this document is

The old plan was a *plan to reach a state*. This is a *definition of the state we hold
and intend to grow* — split in two, on purpose:

- **This file is the constitution.** Invariants, the trust model, the agent-agnostic contract,
  and the **extension points** through which the system is allowed to grow. Short enough to read
  in full before any T2+/T3 change.
- **The [spokes](#7-the-spokes-an-open-set) carry the depth.** One `docs/design/*.md` per domain.
  Expansion touches a spoke, not the constitution — so the law stays stable while the detail moves.

**Authority.** When any file conflicts with the system, **the system design wins** and the other
file is the bug — fix the design, don't fork it. [`AGENTS.md`](../AGENTS.md) is the always-loaded,
engine-neutral distillation of this contract; if the two ever disagree, **this file wins** and
`AGENTS.md` is the bug.

## 1. The system, in one breath

One VM hosts a **replaceable** agentic runtime. The GitHub repo `skynet` is machine-readable
truth; **Arcane GitOps** is the deployment executor; secrets are **sops+age**-encrypted in git;
**restic → Google Drive** backs up app data and **PBS → Google Drive** backs up guests. Hands-on
host work uses **auto-expiring, certificate-based root grants** that the agent can request but
*cannot mint for itself*. A disaster runbook can rebuild the network node — OPNsense included —
from a laptop and a phone hotspot. Nothing the agent knows lives only in its own head: it is
stateless by design, and everything it is stands in git.

## 2. Invariants

The invariants come in two kinds, and telling them apart is the whole trick of building a system
that can grow without becoming dangerous.

### 2a. Hard laws — never negotiable, no PR loosens them

- **No standing route or credential to T3.** OPNsense, Management Caddy, Authentik, Proxmox node
  root, Unraid root, Technitium *server settings* — reached only through a dormant alias +
  per-session credentials, revoked the same day. Never a standing path.
- **Root on workload hosts exists only inside a certificate's validity window.** The signing CA
  private key lives on Ali's workstation and **never** enters Skynet. This is the one access
  Skynet cannot mint for itself — temporary is guaranteed by physics, not by policy. Every root
  session's KeyID is logged and harvested nightly.
- **Secrets are sops-encrypted in git, or 0600 under `/opt/skynet-ops/secrets/` — never plaintext.**
  Not in commits, not in logs, not in transcripts, not in chat.
- **The agent proposes; a human disposes.** The agent never hand-edits generated dirs
  (`inventory/`, `docs/generated/`). (*How* a proposal is accepted is a dial — see 2b — but that a
  proposal exists, reviewable, is law.)

### 2b. Version-controlled dials — the settings this document sets, and a PR here can widen

These are deliberately *not* absolutes. They are the current position of a lever, recorded so it
can be moved openly rather than eroded quietly. **Widening any of them is a PR to this file.**

- **Write blast radius** = the `ops-managed` pool **set** + `ROLE_OPS_SSH_TARGETS` +
  Technitium zones. The pool set holds **two** pools today — *a current count, never a fixed law*;
  new pools join by PR here. (Details: [access-and-trust](design/access-and-trust.md),
  [network](design/network.md).)
- **The merge gate** = human merge, today. Merge authority is a *ratcheted grant*, not an eternal
  "never" — the foreseeable first loosening is the agent auto-merging **docs-only** PRs. Any
  widening is a PR here that also updates the [auto-approve list](../AGENTS.md).
- **Autonomy** = nightly runs are **report-only** outside the version-controlled auto-approve
  list. Individual actions graduate to auto-approve one at a time, by PR. Even the leash is in git.
- **Survival & kill switch** — survival kit verified quarterly; kill switch (`disable tokens +
  qm stop 9090`) drilled before autonomy day one, re-drilled on demand.

### 2c. How invariants are enforced — machine-enforced wherever a deterministic check exists

A rule's rigor comes from **who enforces it, not what format it's in**: an LLM reads a schema with
the same latitude it reads prose, so a constraint is binding only once a *deterministic, non-LLM
process* consumes it. The hard laws above should therefore be **machine-enforced wherever such a
check exists** — the machine-checkable ones (excluded guests never pooled, blast radius = the
declared pool set, no plaintext secrets) are extracted into an authored `invariants.json` and
asserted by a gate that fails a violating PR ([SKY-011](../planning/projects/SKY-011-machine-enforced-invariants-and-the-ambiguity-layering-doctrine.md)),
not left to the agent remembering. This is *not* a licence to rewrite this section into a schema:
the constitution's job is to constrain judgment, a natural-language act. The full principle —
ambiguity-tolerance layering; **format follows enforcement** — is [ADR 0003](decisions/0003-ambiguity-layering-and-format-follows-enforcement.md).

## 3. Trust model

Trust is tiered, and the tier decides the mechanism. The deep version — every token, ACL, and
principal — lives in [access-and-trust](design/access-and-trust.md); this is the spine.

| Tier | Scope | Mechanism | Standing? |
|---|---|---|---|
| **T1 Read** | Both Proxmox nodes, PBS, Docker hosts, DNS, firewall state (git mirror) | Read-only API tokens; mirrored `config.xml` | Always |
| **T2 Operate** | `ops-managed` pools (both nodes), Docker hosts via Arcane + unprivileged SSH, Technitium zones; **backup/snapshot** of ops-managed guests | Scoped write tokens, `svc-ops` SSH, Technitium scoped token, Arcane API key | Yes — changes PR-gated |
| **T2+ Root grant** | Root shell on workload hosts (diagnose, harden, provision, OS updates) | SSH user-CA certificate, per-host principal, **auto-expiring** | Grant only; expires itself |
| **T3 Privileged** | OPNsense, Management Caddy, Authentik, Proxmox node root, Unraid root, Technitium *server settings* | Dormant alias `ROLE_OPS_PRIV_TARGETS` + per-session credentials | **Never standing** |

- **Technitium is T2 for Zones view/modify only** — no Settings/Administration/DHCP. Server
  settings are T3.
- **Authentik: server administration is T3; app/provider provisioning is T2 (scoped).** A dedicated
  `svc-skynet` token may CRUD Applications + Providers and bind an existing outpost — nothing else.
  Flows, Policies, Users, System settings, outpost tokens, and signing keys stay T3. Same shape as
  the Technitium split. (Landed by SKY-003 — see [identity-and-proxy](design/identity-and-proxy.md).)
- **Pool membership is the blast-radius dial.** Joining a guest to an `ops-managed` pool hands the
  agent T2 over it; leaving it out keeps it look-but-don't-touch. **VM 5001 (OPNsense) never joins
  any pool** — same for CT 635, CT 837, Unraid VM 2020. Seen at T1, touched never (T3).

## 4. The agent-agnostic contract

Skynet is **agent-agnostic by contract**: any agent that can read a file and run bash can operate
it. Everything an operator needs is in the repo —

- **[`AGENTS.md`](../AGENTS.md)** — the cross-vendor instruction standard (Codex CLI reads it
  natively; Claude Code, Goose, Amp and others honor it). `CLAUDE.md` imports it so the two engines
  cannot drift.
- **Scripts are capabilities** — plain shell in `scripts/` and `bin/`.
- **Runbooks are procedures** — engine-neutral markdown, catalogued in
  [`runbooks/README.md`](../runbooks/README.md).

Swapping the brain is one line in `bin/ops` (`OPS_ENGINE` / `OPS_*_MODEL` in
`~/.config/skynet-ops/ops.env`). The runtime is a replaceable part; the contract is the machine.

## 5. Extension points — how the system is allowed to grow

Growth is legal only when it enters *through* the invariants, not around them. Each kind of
expansion has an admission procedure and a home spoke:

| You want to add… | The admission procedure | Home spoke |
|---|---|---|
| **A new service** | `compose/<svc>/` → the [GitOps loop](design/gitops-loop.md); catalog it in `planning/services/` | gitops-loop |
| **A new managed host** | Onboard to the CA (`onboard-host.sh`), decide pool membership (= its tier), land it in `inventory/` + `ROLE_OPS_SSH_TARGETS` | [access-and-trust](design/access-and-trust.md), [network](design/network.md) |
| **A new `ops-managed` pool** | Widen the blast-radius **dial** by PR here, then create the pool with the operate ACLs | [access-and-trust](design/access-and-trust.md) |
| **A new VLAN / segment** | Firewall aliases + rules, DNS zones, then hosts | [network](design/network.md) |
| **A new capability / trust boundary** | PR here (tier assignment) + a step on the autonomy ratchet in `AGENTS.md` | this file |
| **A new agent engine** | Point `bin/ops` at it — the agent-agnostic contract already fits | this file, §4 |
| **A new spoke** | When a domain outgrows a paragraph, split it into `docs/design/` | this file, §7 |
| **A new convention** | Add the rule to the right [`docs/conventions/`](conventions/) spoke (or add a spoke), tag it testable/manual, surface load-bearing ones in the conventions hub | [conventions](conventions.md) |

## 6. Growth directions

Where Skynet expands next. **Vision lives here; the work lives in `planning/` as `SKY-###`
directives** — this section names the horizon and hands off.

- **Reverse proxy / ingress** — **landing via [SKY-003](../planning/projects/SKY-003-apps-reverse-proxy-authentik-sso-ingress.md)**:
  a T2 apps Caddy at `10.10.100.35` (the everyday-services twin of the T3 Management Caddy), detailed
  in the new [identity-and-proxy](design/identity-and-proxy.md) spoke. The tier decision is made — the
  apps door is T2, the Management door stays T3.
- **A sanctioned public path (Cloudflare Tunnel)** — **landing via [SKY-014](../planning/projects/SKY-014-adopt-cloudflared-as-a-skynet-managed-tunnel-public-path-via-apps-caddy.md)**:
  the hand-run cloudflared LXC (CT 1033) becomes a **T2 Skynet-managed** GitOps service on
  `vm-docker-dmz`, reusing `.33` so it inherits firewall rule 800 (**no OPNsense change**). The
  tunnel is **outbound-only** — it opens no inbound rule, ever — and fronts a **single origin, the
  apps Caddy** (`10.10.100.35`), so publishing a service to the internet is **one reviewed `ingress`
  line + one public DNS record, per hostname**, never a new door. The governing rules: **only
  hostnames with an explicit `ingress` entry are public** (each added by PR), the edge requires the
  service's **own-auth or stronger**, the tunnel credential is **sops**, and — the invariant this
  turns on — the **internal path is unchanged and never transits Cloudflare** (Technitium keeps
  steering internal clients straight to the apps Caddy). See [identity-and-proxy](design/identity-and-proxy.md).
- **A secrets vault beyond sops+age** — an external backend (Vault / Infisical-class) if the
  service count outgrows file-level sops. Migration path sketched in [secrets](design/secrets.md).
- **SSO / authentication** — Authentik graduating out of T3 into something the agent can operate
  under a scoped boundary. **Landing via SKY-003:** server administration stays T3;
  app/provider provisioning becomes T2 via a scoped `svc-skynet` token (flows/users/settings/keys
  stay T3). See [identity-and-proxy](design/identity-and-proxy.md) and
  [access-and-trust](design/access-and-trust.md).
- **More hosts under T2** — the operate model already generalizes; each new host is an onboarding,
  not a redesign.
- **A monitoring / alerting stack** — beyond nightly report-only into live signal. See
  [observability](design/observability.md).
- **Agent memory & retrieval** — the episodic journal + cold-boot digest landed via SKY-006; the
  next swing is a git-rebuildable local semantic index, held until markdown + grep visibly strain.
  See [memory](design/memory.md).
- **The self-hosted service catalog** — `planning/services/` becoming a steady intake pipeline.
- **Multi-agent operations** — more than one engine, or specialized agents, under one contract.

## 7. The spokes — an open set

The depth lives here. **This set is open** — spokes are added by PR as the system grows.

| Spoke | Covers | Sourced from (plan) |
|---|---|---|
| [network](design/network.md) | Placement, VM spec, VLAN 90, firewall aliases/rules | §1, §3 |
| [identity-and-proxy](design/identity-and-proxy.md) | Two-door model, split-DNS, Cloudflare DNS-01, one-Caddy `forward_auth`, Authentik T2/T3 split, the public path (Cloudflare Tunnel) | SKY-003, SKY-014 |
| [access-and-trust](design/access-and-trust.md) | Trust tiers in depth, Proxmox operate tokens, SSH user-CA + grants, T3 dormant aliases | §2, §7, §8 |
| [secrets](design/secrets.md) | sops+age, `.env.git`/`project.env` layering, envsync | §5, §4 |
| [gitops-loop](design/gitops-loop.md) | Arcane deploy loop, rollback, image pinning + Renovate | §4, §12 |
| [disaster-recovery](design/disaster-recovery.md) | Survival kit + DR design (procedures in `runbooks/dr/`) | §10 |
| [observability](design/observability.md) | render-docs, nightly, inventory, generated docs | §11 |
| [memory](design/memory.md) | The four memory kinds; episodic journal + read-time digest + decision ADRs; write-raw/read-summarize; cache-not-truth | SKY-006 |
| [backup-strategy](backup-strategy.md) | The L0–L5 layered backup model | §6 |
| _[conventions](conventions.md)_ | House style **hub** — invariants + an index into `conventions/*.md` spokes (naming, layout, scripts, compose, git, docs, metadata) | — |

## 8. Lineage

Skynet was built in six phases (A1–A6) from an empty VM to graduation on 2026-08-16. That story
— every phase, every drill, every latent gap the drills surfaced — is preserved in
[`history/build-log.md`](history/build-log.md), and the original birth plan verbatim in
[`history/deployment-plan-v5.md`](history/deployment-plan-v5.md). Architectural decisions with
lasting consequence are recorded as ADRs in [`decisions/`](decisions/). The fast orientation map
is [`architecture.md`](architecture.md).
