# Skynet

Ali's homelab, declared in git and run by an AI agent.

- **Hosts** are NixOS machines defined in this flake; each keeps itself current from `main` (comin).
- **Apps** are Docker Compose stacks, one folder each under `stacks/`, deployed by doco-cd.
- **The agent** (Claude Code on the `ops` VM) diagnoses problems, fixes the safe ones, and proposes
  everything else as a pull request. Ali merges; the lab converges within about a minute.
- **Talk to it** in Discord `#skynet` or from the Claude app. Alerts land in `#alerts`.

Start with [`AGENTS.md`](AGENTS.md) (the rules and a map) and [`docs/`](docs/README.md) (the lab,
its credentials, the decisions and the plans in flight).

The build's plan, a Markdown file at the repo's root that ran the build phase by phase, was retired
once every fact still true had a home (ADR-0019). Its last version is in commit
[`c7fe591`](https://github.com/aliammar03/skynet/tree/c7fe591). The previous lab lives in the
archived [`skynet-v1`](https://github.com/aliammar03/skynet-v1).
