{ ... }:
# Declaratively trusted fleet host keys, written to /etc/ssh/ssh_known_hosts so the agent's outbound
# SSH (envsync.sh, collect-docker.sh's context, gitops-deploy.sh) VERIFIES remote hosts instead of
# TOFU-prompting — which fails under `ssh -o BatchMode=yes`. A freshly reprovisioned box has no
# accumulated ~/.ssh/known_hosts, so trust has to be declared here to be reproducible.
#
# Keys captured with `ssh-keyscan`; add a block as each new SSH target is onboarded. recon.sh against
# ad-hoc hosts still TOFUs interactively — that's fine, it's a human-driven probe.
{
  programs.ssh.knownHosts = {
    docker-dmz = {
      hostNames = [ "10.10.100.15" ];
      publicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIM3KfY6KO8M3XRi1Np4HAQdE/J1FJMUjHXK4om1B8JFZ";
    };
  };
}
