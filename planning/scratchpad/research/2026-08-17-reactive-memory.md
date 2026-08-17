> Agent-generated research (2026-08-17). Feeds SKY-004 (reactive/event-driven ops) and SKY-006 (agent long-term memory), plus a k3s-rejection ADR. Skeptical, decision-oriented; not a design doc.

# Reactive ops, agent memory, and a k3s sanity check

Skynet is BATCH today: nightly report-only cron + Arcane polling git. These three areas ask whether/how to add reactivity and durable memory without breaking statelessness or raising branching-factor. Bias throughout: **the lowest-complexity option that stays regenerable from git.**

---

## A) Reactive / event-driven ops (SKY-004)

**Pattern menu, cheapest first.**

1. **Just a webhook + a script.** A single static Go binary — [`adnanh/webhook`](https://www.teqqy.de/en/gitops-without-komodo/) — exposes one HTTP endpoint, verifies an **HMAC-SHA256 signature** over the payload body (GitHub `X-Hub-Signature-256` / Gitea `X-Gitea-Signature`), and on match runs a shell script. No daemon fleet, no message bus, no new state store. The teqqy writeup uses exactly this to replace compose polling: push → webhook → `git pull && docker compose up -d`. Event-driven in seconds vs. the 5-minute polling delay.
2. **ntfy as the trigger bus.** ntfy is already in-play for grant alerts. It can also be *consumed*: a small `ntfy subscribe <topic> <command>` loop turns a published message into a scoped command run. Good for human-initiated "run job X now" without exposing an inbound HTTP port. One process, no broker.
3. **Lightweight brokers (Redis Streams / NATS).** Only justified by fan-out (many producers/consumers), replay, or backpressure — see the [Kafka vs Redis Streams vs NATS 2026 comparison](https://dev.to/young_gao/real-time-event-streaming-kafka-vs-redis-streams-vs-nats-in-2026-34o1). Skynet has one producer (git/host) and one consumer (the agent run). A broker is a **new standing daemon and a new source of truth** — the opposite of what statelessness wants. Reject for now.

**The right shape for Skynet:** event → *enqueue a job description into git* (or a git-backed queue dir) → the existing agent runner picks it up. The webhook receiver should be dumb: authenticate, validate, drop a signed job file / dispatch a single scoped script. It must never itself become state the agent has to reconstruct — it's a **trigger, not a store**. Flux's [webhook-receiver model](https://fluxcd.io/flux/guides/webhook-receivers/) is the same idea (receiver only nudges reconciliation; git stays authoritative) and is worth mirroring conceptually even without Flux.

**Drift detection as the highest-value event source.** Desired-vs-observed is the natural Skynet signal because desired state already lives in git:
- **OpenTofu/Terraform:** scheduled `tofu plan -detailed-exitcode` — exit `0` = in sync, `2` = drift, `1` = error ([Scalr](https://scalr.com/learning-center/how-to-set-up-scheduled-drift-detection-for-terraform-and-opentofu/), [oneuptime](https://oneuptime.com/blog/post/2026-02-23-how-to-set-up-scheduled-terraform-plans-for-drift-detection/view)). Exit code 2 → publish an ntfy event → graduate to an agent run.
- **NixOS (if adopted):** `nixos-rebuild dry-activate` / `build` and diff the resulting store path against the running system — non-empty diff = drift.
- **docker-compose:** `docker compose config` (canonicalized desired) diffed against running container labels/images, or simply `docker compose up --dry-run`. Arcane already reconciles; the added value is *emitting a signal* when it has to, not silently converging.

Run these on the nightly cron first (report-only), so drift becomes a logged event before it becomes an action.

**Keeping it safe under the ratchet.** The reactive layer inherits, not bypasses, the existing model:
- Every event→action pair starts **report-only**: the trigger fires, the agent produces a PR/report, a human merges. Graduate one pair at a time into the auto-approve list by merged PR — same ratchet as nightly.
- The receiver runs **unprivileged**, holds no T2+/T3 credential, and can only *request* a run within already-granted scope. An inbound webhook must never be able to widen blast radius.
- Signature verification is mandatory (HMAC secret 0600 or sops), payloads are untrusted input, and the dispatched script is a fixed allowlisted capability — not arbitrary command-from-payload.

**Recommendation:** Ship `adnanh/webhook` (HMAC-verified) + ntfy-subscribe as the entire reactive layer; make drift-detectors the first producers, all report-only, graduating one event→action pair at a time. No broker.

---

## B) Agent long-term / episodic memory (SKY-006)

Skynet already has the cheap half right: markdown memory files + git history. The gap is *retrieval at scale* and *not losing episodes*.

**Layered pattern, cheapest first — all regenerable from git:**
1. **Append-only journal** of run outcomes (what ran, what changed, what broke) — one file per run or a dated log. This is **episodic** memory and it's the usual weak spot: an agent that summarizes at write time "collapses distinct episodes into semantic generalizations, destroying the episodic signal before it can be used" ([survey](https://arxiv.org/pdf/2602.06052), [Atlan](https://atlan.com/know/types-of-ai-agent-memory/)). So: **write raw episodes append-only; summarize at read time, never at write time.**
2. **Decision records (ADRs)** — `docs/adr/NNN-*.md` for every non-trivial choice *and every rejected option* (the k3s item below is ADR #1). This is durable **semantic/procedural** memory and it's the highest ROI: cheap, human-readable, diff-able, and it directly answers "why is it this way?" for the next fresh mind.
3. **Rolling state digest** — a regenerated `STATE.md` / inventory snapshot (already partly present) giving a fresh session its **working-memory** seed without reading the whole repo.
4. **Semantic retrieval (only if 1–3 aren't enough).** A **local** embedding index over the repo + journals, stored in [`sqlite-vec`](https://ai.plainenglish.io/embedded-intelligence-how-sqlite-vec-delivers-fast-local-vector-search-for-ai-de6d62936055) — a single-file DB, embeddable, no server. Embeddings via a local model (Ollama / llama.cpp); patterns like [`sqliteai/sqlite-memory`](https://github.com/sqliteai/sqlite-memory) combine vec similarity + FTS5 hybrid search. **Critically: the index is a CACHE, rebuilt from git — never a source of truth.** `rebuild-index` is a capability; if the DB is deleted, `git`+re-embed regenerates it. This preserves statelessness.

**Memory taxonomy & the weak spot.** The 2025–26 consensus is a taxonomy of **working / semantic / procedural / episodic** (plus sensory) memory ([Zylos](https://zylos.ai/research/2026-04-05-ai-agent-memory-architectures-persistent-knowledge/)). Mapping to Skynet: working = the context window (bottleneck — everything competes for it, so retrieve sparingly); semantic = design docs + ADRs (strong); procedural = runbooks/capabilities (strong); **episodic = per-run history (the weak spot)**. Procedural is a known second bottleneck — retrieved text workflows suffer a "text-action disconnect" ([Memp](https://arxiv.org/pdf/2508.06433)) — which is *another* argument for runbooks-as-executable-capabilities over prose.

**Overkill line.** For a single operator, a vector DB is premature until markdown + `git log`/grep + ADRs demonstrably fail to surface the right context. sqlite-vec is the right tool *when* you cross that line ("legitimate choice… not a hack" for single-user local scale) — but a hosted vector DB, an embeddings API, or a memory framework (mem0-style server) is pure branching-factor for one operator. Start with journals + ADRs; add the local index only on felt pain.

**Recommendation:** Formalize an append-only episodic journal + an ADR directory now (raw episodes, read-time summarization); defer the local `sqlite-vec` index until markdown+grep visibly fails, and keep it a git-rebuildable cache.

---

## C) k3s sanity check — write it down as REJECTED (ADR)

**Honest case FOR k3s:** real secret management (vs `.env`/`project.env`), declarative self-healing, network-policy isolation, a single API for multi-host scheduling, and a genuinely lighter footprint than full k8s. If Skynet grows to several nodes needing HA scheduling, it becomes defensible ([TerminalBytes](https://terminalbytes.com/kubernetes-at-home-from-docker-compose-to-k3s/), [Stanislas](https://stanislas.blog/2025/04/moving-to-k8s/)).

**Case AGAINST (decisive for Skynet):** k3s multiplies the branching-factor and failure modes Skynet is explicitly minimizing. For a single-/few-host homelab, compose is "readable YAML, running in seconds" while k8s adds CRDs, an API server, etcd/kine, ingress controllers, CNI, and a much larger surface a *stateless LLM* must reconstruct each session ([DEV: Compose vs k8s](https://dev.to/orthogonalinfo/docker-compose-vs-kubernetes-secure-homelab-choices-4fen)). Community consensus: k3s only earns its keep at **multiple nodes / need real secrets / need network-policy isolation** — none of which Skynet has today; and even seasoned homelabbers call production patterns "increasingly absurd for a three-node homelab." It also *breaks* Skynet's current GitOps loop (Arcane reconciles compose), so adopting it is a rewrite, not an add-on. Secrets — the one real pull — are already solved by sops + 0600 without an orchestrator.

**Recommendation:** Reject k3s now via ADR; revisit only if node count and HA needs cross the compose ceiling — the added branching-factor loses against Skynet's low-moving-parts, regenerable-from-git constitution.

---

### Sources
- Webhook GitOps: <https://www.teqqy.de/en/gitops-without-komodo/> · Flux receivers <https://fluxcd.io/flux/guides/webhook-receivers/>
- Brokers: <https://dev.to/young_gao/real-time-event-streaming-kafka-vs-redis-streams-vs-nats-in-2026-34o1>
- Drift: <https://scalr.com/learning-center/how-to-set-up-scheduled-drift-detection-for-terraform-and-opentofu/> · <https://oneuptime.com/blog/post/2026-02-23-how-to-set-up-scheduled-terraform-plans-for-drift-detection/view>
- Memory taxonomy: <https://atlan.com/know/types-of-ai-agent-memory/> · <https://zylos.ai/research/2026-04-05-ai-agent-memory-architectures-persistent-knowledge/> · survey <https://arxiv.org/pdf/2602.06052> · procedural <https://arxiv.org/pdf/2508.06433>
- Local vector: <https://ai.plainenglish.io/embedded-intelligence-how-sqlite-vec-delivers-fast-local-vector-search-for-ai-de6d62936055> · <https://github.com/sqliteai/sqlite-memory>
- k3s: <https://terminalbytes.com/kubernetes-at-home-from-docker-compose-to-k3s/> · <https://stanislas.blog/2025/04/moving-to-k8s/> · <https://dev.to/orthogonalinfo/docker-compose-vs-kubernetes-secure-homelab-choices-4fen>
