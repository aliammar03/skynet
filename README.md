# Skynet

Ali's homelab, declared in git and run by an AI agent.

- **Hosts** are NixOS machines defined in this flake; each keeps itself current from `main` (comin).
- **Apps** are Docker Compose stacks, one folder each under `stacks/`, deployed by doco-cd.
- **The agent** (Claude Code on the `ops` VM) diagnoses problems, fixes the safe ones, and proposes
  everything else as a pull request. Ali merges; the lab converges within about a minute.
- **Talk to it** in Discord `#skynet` or from the Claude app. Alerts land in `#alerts`.

Start with [`skynetv2.md`](skynetv2.md) (the plan and status) and [`AGENTS.md`](AGENTS.md) (the rules).
The previous version lives in the archived [`skynet-v1`](https://github.com/aliammar03/skynet-v1).
