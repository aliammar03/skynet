# Skynet

Ali's homelab, declared in git and run by an AI agent.

- **Hosts** are NixOS machines defined in this flake; each keeps itself current from `main` (comin).
- **Apps** are Docker Compose stacks, one folder each under `stacks/`, deployed by doco-cd.
- **The agent** (Claude Code on the `ops` VM) diagnoses problems, fixes the safe ones, and proposes
  everything else as a pull request. Ali merges; the lab converges within about a minute.
- **Talk to it** in Discord `#skynet` or from the Claude app. Alerts land in `#alerts`.

Start with [`AGENTS.md`](AGENTS.md) (the rules and a map) and [`docs/`](docs/README.md) (the lab,
its credentials, the decisions and the plans in flight).

The build's plan, `skynetv2.md`, was retired once every fact still true had a home; its last
version is [`c7fe591`](https://github.com/aliammar03/skynet/blob/c7fe591/skynetv2.md). The previous
lab lives in the archived [`skynet-v1`](https://github.com/aliammar03/skynet-v1).
