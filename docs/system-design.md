# Skynet — System Design

> **Skynet became self-aware at 2026-08-16.** The build is over; operations have begun.
> This is the constitution of the system that woke up — the slow-changing law that every
> future change is measured against. It replaces the old birth plan, now archived verbatim as
> [`history/deployment-plan-v5.md`](history/deployment-plan-v5.md).

**The one VM:** `vm-skynet-ops` · **10.10.90.90** static · VLAN 90 · VMID 9090 · on `server-proxmox-core` — a **NixOS flake** ([SKY-007](../planning/projects/SKY-007-nixos-host-definition-piloted-on-the-ops-vm.md)).

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

## 1a. The terminal goal — full agent control

Everything below is scaffolding for one end state: **Skynet runs the lab.** A human expresses
intent — *"deploy this service"* — and the system delivers it provisioned, published, backed up,
monitored and documented, with no further input. The agent corrects drift, provisions and optimises
workloads, validates firewall rules, and keeps its own backups honest. **The heart of Skynet is the
AI**; the scripts, gates and runbooks exist to make its judgement *safe to act on*, not to replace
it.

The leash today is not a verdict on that goal — it is a statement about **evidence**. The binding
constraint is that the agent is *unproven*, not that it is untrusted: a confidently-wrong operator
with T2 write can do real damage in a single run, and right now the only thing between a plausible-
but-wrong plan and the lab is **a human reading a diff**. So every widening reduces to one question:
**what replaces the human as the verifier of this loop?** Nothing graduates until something does.

Autonomy is therefore a property of an individual **capability**, not a global setting, and it is
climbed on recorded evidence:

| Level | The agent may… | Verified by |
|---|---|---|
| **A0** Observe | read, render, report | — |
| **A1** Propose | open a PR; a human merges | a human reading the diff |
| **A2** Rehearse | execute against the proving ground, not production | the rehearsal's assertions |
| **A3** Supervised act | act in production, human notified, easy undo | gates + verification, human watching |
| **A4** Auto act | act unattended within its declared scope | gates + verification + **automatic rollback** |
| **A5** Self-direct | choose *when* it is needed, not just how | the above + drift attribution + budget |

A capability climbs only with a track record at the level below, and reaches **A4 only if its
rollback is automatic, tested in the failure case, and performed by a dumb executor that works when
the agent's judgement is the thing that failed.** Actions irreversible by nature — `destroy`, data
deletion, credential rotation, anything crossing into T3 — stay **hard checkpoints at every level,
including the terminal one**. Full agent control means the agent may build, run, repair and revert
unattended; never that it may destroy unattended.

The reasoning, the three classes of verifier that replace the human, and the reversibility test in
full: **[ADR 0005](decisions/0005-full-agent-control-as-terminal-goal.md)**. The road there is
[SKY-017](../planning/ideas/SKY-017-the-road-to-full-agent-control-verification-proving-ground-and-an-evidence-earned-ratchet.md).

## 2. Invariants

The invariants come in two kinds, and telling them apart is the whole trick of building a system
that can grow without becoming dangerous.

### 2a. Hard laws — never negotiable, no PR loosens them

- **No standing route or credential that can *change* T3.** Management Caddy, Authentik, Proxmox node
  root, Unraid root, Technitium *server settings*, Cloudflare *account / Access / tunnel config* —
  reached only through a dormant alias + per-session credentials, revoked the same day. Never a
  standing **write** path. Standing scoped exceptions, by device: **OPNsense** is tiered (ADR
  [0006](decisions/0006-opnsense-read-is-t1-write-stays-t3.md)) — read+diagnostics **T1**, firewall
  **config T2** (PR-gated via OpenTofu), but **node root, account/cert admin, reboot, and the agent's
  own leash rules** stay T3/never-standing; Cloudflare **DNS records** and Technitium **zones** are
  **T2** write (scoped tokens).
- **The agent never widens its own leash — firewall included.** Even with OPNsense config at T2, the
  agent may **never** change the rules/aliases bounding its own reach (`ROLE_OPS_*`,
  `ROLE_OPS_PRIV_TARGETS`, the block-other-DNS rules, its own OPNsense accounts). Human-merged forever,
  never on the autonomy ratchet, and machine-gated on the `tofu plan` (SKY-018 P7). See ADR 0006.
- **Root on workload hosts exists only inside a certificate's validity window.** The signing CA
  private key lives on Ali's workstation and **never** enters Skynet. This is the one access
  Skynet cannot mint for itself — temporary is guaranteed by physics, not by policy. Every root
  session's KeyID is logged and harvested nightly.
- **Secrets are sops-encrypted in git, or 0640 under `/opt/skynet-ops/secrets/` — never plaintext.**
  Not in commits, not in logs, not in transcripts, not in chat. The age private key is readable by
  the agent user (`root:users 0640`) so the agent can encrypt and decrypt T2 secrets without
  escalation.
- **The agent proposes; a human disposes.** The agent never hand-edits generated dirs
  (`inventory/`, `docs/generated/`). (*How* a proposal is accepted is a dial — see 2b — but that a
  proposal exists, reviewable, is law.)
- **The agent never widens its own leash.** Any change to this section, §1a's ladder, §2b's dials,
  [`AGENTS.md`](../AGENTS.md) §3/§6, `invariants.json`, or the gate scripts enforcing them is
  **human-merged, permanently** — at every autonomy level, including the terminal one. The agent may
  propose its own promotion; it may never merge it. This is the counterweight that makes §1a safe to
  state as a goal ([ADR 0005](decisions/0005-full-agent-control-as-terminal-goal.md) §4).
- **The system is reconstructable from git alone — never restored from a backup.** Two classes, and
  the line between them is load-bearing: the **system** (definitions, config, policy, identity,
  encrypted secrets, inventory, docs) rebuilds from git, and a backup of it is a convenience that must
  never become a dependency; the **payload** (service data — documents, libraries, archives) is not
  reconstructable, so it is backed up encrypted and off-site, and restored *after* the system stands
  up. **Rebuilding from git alone must yield a running, correct, empty lab.** If any part of the
  system class can only be recovered from a backup, that is a bug to fix, not a backup to take.

### 2b. Version-controlled dials — the settings this document sets, and a PR here can widen

These are deliberately *not* absolutes. They are the current position of a lever, recorded so it
can be moved openly rather than eroded quietly. **Widening any of them is a PR to this file.**

- **Write blast radius** = the `ops-managed` pool **set** + `ROLE_OPS_SSH_TARGETS` +
  Technitium zones. The pool set holds **two** pools today — *a current count, never a fixed law*;
  new pools join by PR here. (Details: [access-and-trust](design/access-and-trust.md),
  [network](design/network.md).)
- **The merge gate** = human merge, today — with **one** carve-out now taken: the agent
  auto-merges its **own nightly generated-only PRs** (every changed path under `inventory/`,
  `docs/generated/`, `journal/`, or matching `compose/*/.env.sops`) and **only** when CI is green.
  Everything **authored** — design, code, compose, runbooks — stays human-merged. This was the
  dial's foreseeable first loosening ([ADR 0004](decisions/0004-auto-merge-generated-only-nightly-prs.md));
  any further widening is a PR here that also updates the [auto-approve list](../AGENTS.md).
  Off-switch: `OPS_NIGHTLY_AUTOMERGE=0`. No branch protection backstops it (private repo, free
  plan) — the green-gate in `scripts/nightly.sh` is the enforcement.
- **Autonomy** = nightly runs are **report-only** outside the version-controlled auto-approve
  list. Individual actions graduate to auto-approve one at a time, by PR. Even the leash is in git.
  Each graduation is a move on §1a's **A0–A5 ladder**, bought with recorded evidence and — from A4 —
  a rollback that satisfies the reversibility test. Most capabilities sit at **A1** today; the
  nightly's generated-only self-merge is the one at **A4**.
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
| **T1 Read** | Both Proxmox nodes, PBS, Docker hosts, DNS, the **Omada network controller**, **OPNsense (read-only)** | Read-only API tokens; scoped OPNsense read-only API + mirrored `config.xml` | Always |
| **T2 Operate** | `ops-managed` pools (both nodes), Docker hosts via Arcane + unprivileged SSH, Technitium zones, Cloudflare **DNS records** (`aliammar.net` zone); **backup/snapshot** of ops-managed guests; **provisioning** of in-pool guests via OpenTofu; **OPNsense firewall config** (aliases/rules) via OpenTofu + non-destructive maintenance (**minus the self-leash set**) | Scoped write tokens, `svc-ops` SSH, `svc-tofu` pool-scoped API token, Technitium scoped token, Arcane API key, Cloudflare scoped `DNS:Edit` token, OPNsense tofu-write API key | Yes — changes PR-gated |
| **T2+ Root grant** | Root shell on workload hosts (diagnose, harden, provision, OS updates) | SSH user-CA certificate, per-host principal, **auto-expiring** | Grant only; expires itself |
| **T3 Privileged** | OPNsense *node root / account / cert admin / reboot / self-leash rules*, Management Caddy, Authentik, Proxmox node root, Unraid root, Technitium *server settings*, Cloudflare *account / Access / tunnel config / zone settings* | Dormant alias `ROLE_OPS_PRIV_TARGETS` + per-session credentials | **Never standing** |

- **Technitium is T2 for Zones view/modify only** — no Settings/Administration/DHCP. Server
  settings are T3.
- **Authentik: server administration is T3; app/provider provisioning is T2 (scoped).** A dedicated
  `svc-skynet` token may CRUD Applications + Providers and bind an existing outpost — nothing else.
  Flows, Policies, Users, System settings, outpost tokens, and signing keys stay T3. Same shape as
  the Technitium split. (Landed by SKY-003 — see [identity-and-proxy](design/identity-and-proxy.md).)
- **Cloudflare: DNS records are T2 (standing); the account is T3.** A scoped `Zone:DNS:Edit` token
  for `aliammar.net` **only** lets the agent write records (the tunnel's per-host CNAMEs, ACME
  challenges) — records aren't privileged access, exactly as Technitium *zones* are T2. The Cloudflare
  **account, Zero-Trust/Access policies, tunnel configuration, and zone-level settings** stay T3
  (Ali only). Same shape as the Technitium split. Publishing a hostname still needs its `ingress`
  rule **human-merged** (the agent never self-merges an *authored* PR — the merge-gate carve-out in
§2b is generated-only) — that merge is the publish gate, not the
  CNAME. (SKY-014 — see [identity-and-proxy](design/identity-and-proxy.md).)
- **OPNsense is tiered** (ADR [0006](decisions/0006-opnsense-read-is-t1-write-stays-t3.md)) — three
  planes, because the firewall *is* the trust boundary. **T1 read+diagnostics:** a standing scoped
  credential reads aliases/rules/interfaces/DHCP live and runs non-mutating probes (ping/traceroute/
  lookup). **T2 firewall config:** aliases and rules are `tofu/` resources — a `tofu plan` diff in a
  PR, human-merged, applied via API (the same model as `svc-tofu` for guests). **T3, never-standing:**
  node root, account/cert admin, **reboot** (a lab-wide outage — hard checkpoint always), and **the
  agent's own leash** (`ROLE_OPS_*`, the block-other-DNS rules, its own accounts) — human-merged
  forever, machine-gated on the plan (SKY-018 P7). The git mirror stays as rebuild-from-git truth.
  This is a directive-sized build (firewall-as-code); the T1 read slice ships first.
- **Omada is T1 for the switch/AP estate only** — read device inventory, ports, PoE, VLAN/profile
  assignment, firmware, and adoption status. A dedicated **read-only** controller account (never an
  admin credential); controller/site *administration* — adopting devices, pushing profiles, server
  settings — stays **T3**. Same shape as the Technitium Zones-vs-settings split. Reachability is one
  firewall alias membership (add the controller to `ROLE_OPS_API_TARGETS` + its port to
  `PORT_OPS_API`), a T3 OPNsense change. (Landed by SKY-018 P4 — see
  [access-and-trust](design/access-and-trust.md).)
- **Pool membership is the blast-radius dial.** Joining a guest to an `ops-managed` pool hands the
  agent T2 over it; leaving it out keeps it look-but-don't-touch. **VM 5001 (OPNsense) never joins
  any pool** — same for CT 635, CT 837, Unraid VM 2020. Never pooled, destroyed, or stopped by the
  agent (T3); `svc-tofu`'s config-only `/vms` role (both nodes) can config-touch them (name/onboot/
  cloud-init) but nothing heavier — never destroy/stop/re-disk/re-NIC. See [access-and-trust](design/access-and-trust.md).

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
| **A host's OS + config, declaratively** | Define it as a reviewed **NixOS flake** (`hosts/` + `nix/modules/`), `nix build` gated in CI. **In place on the ops VM** (SKY-007); any other host is a fresh directive gated on that evidence | [`nix/README.md`](../nix/README.md), SKY-007 |
| **A managed guest, declaratively** | Declare it in `tofu/` as an OpenTofu resource; `tofu plan` diff reviewed in PR, `apply` after merge. Pool-scoped `svc-tofu` token — **no node root, no SSH** (SKY-008). `destroy` is a hard checkpoint, never auto-approved | [access-and-trust](design/access-and-trust.md), SKY-008 |
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
  hostnames with an explicit `ingress` entry are public** (each added by PR — the **human merge is
  the publish gate**), the edge requires the service's **own-auth or stronger**, the tunnel credential
  is **sops**, and — the invariant this turns on — the **internal path is unchanged and never transits
  Cloudflare** (Technitium keeps steering internal clients straight to the apps Caddy). The per-host
  CNAME is written by the agent under the **T2 Cloudflare `DNS:Edit`** grant (§2), not by hand. See
  [identity-and-proxy](design/identity-and-proxy.md).
- **Declarative host definitions (NixOS)** — **landed for the ops VM via [SKY-007](../planning/projects/SKY-007-nixos-host-definition-piloted-on-the-ops-vm.md)**:
  the box is now a reviewed **flake** (`hosts/` + `nix/modules/`), `nix build` gated in CI, deployed
  with deploy-rs (magic-rollback). Impermanence (tmpfs root), sops-nix secrets, and home-manager own
  the box. The old standing passwordless `sudo ALL` is **gone** — narrowed to least-privilege
  (`aliammar`: `systemctl skynet-*` + password-gated wheel; `svc-ops`: deploy-activation only). Any
  **other** host is still a fresh directive gated on this evidence. Details in [`nix/README.md`](../nix/README.md).
- **Declarative provisioning (OpenTofu)** — **landing via [SKY-008](../planning/projects/SKY-008-opentofu-provisioning-layer-vm-and-ct-lifecycle-plus-dns.md)**:
  in-pool VM/CT lifecycle declared as OpenTofu resources (`tofu/`), driven by a **pool-scoped
  `svc-tofu` API token** (privilege-separated, no node root, no SSH). `tofu plan` is the reviewable
  diff; `apply` runs after human merge; `destroy` is a hard checkpoint. State is local on the ops VM,
  encrypted with OpenTofu native PBKDF2 (passphrase in sops). Provider: `bpg/proxmox` (API-native
  cloud-init only — the SSH-snippet path is deliberately unconfigured). Tofu makes the box exist;
  NixOS (SKY-007) defines what's on it. See [access-and-trust](design/access-and-trust.md).
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
  The first concrete use is **adversarial review**: a second, cold session with no shared context
  reviewing a diff against this constitution — one of the three verifiers §1a requires.
- **The road to full agent control** — **[SKY-017](../planning/ideas/SKY-017-the-road-to-full-agent-control-verification-proving-ground-and-an-evidence-earned-ratchet.md)**:
  build what the ladder in §1a spends — a **proving ground** (an ephemeral replica where A2 rehearsal
  is real but disposable), the **verification layer** (bounded plan diffs, canary scope, health
  probes, automatic rollback), **adversarial review**, and a **per-capability track record** so
  promotion is a measurement rather than a feeling. Plus the containment that unattended action
  needs: a **change budget** per run and a **circuit breaker** that halts on the first unexplained
  failure. This is the directive the rest of the roadmap eventually feeds.

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
