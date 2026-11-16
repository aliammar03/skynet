# Runbooks

How recurring jobs are done here, step by step. Each states who does what (agent or Ali).

- [`new-vm.md`](new-vm.md): a new NixOS VM of any role (Docker host included), in one PR.
- [`new-stack.md`](new-stack.md): a new Compose stack on any Docker host, in one PR.
- [`restore.md`](restore.md): what comes back from where: an app, a host, a guest, PBS, or all of
  it from Drive.
- [`survival-kit.md`](survival-kit.md): what Ali keeps outside the lab for that last case, a
  template to fill in, and how to check it.
- [`drive-access.md`](drive-access.md): Ali's OAuth client for Drive, and a new token for rclone.
- [`dns-speed-test/`](dns-speed-test/README.md): pick Technitium's forwarders by measurement.
- [`incident.md`](incident.md), [`digest.md`](digest.md), [`report.md`](report.md): what the
  agent's unattended runs do with an alert, each morning and each Monday (`modules/agent-runs.nix`).
  Each run reads one as its instructions.
