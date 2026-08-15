# ca/ — SSH user-CA **public** key (trust anchor for auto-expiring root grants)

`skynet_ops_ca.pub` is the public half of the CA that lives ONLY on Ali's workstation
(`~/.skynet-ca/ops_ca`). Hosts trust it via `scripts/onboard-host.sh`, which installs it
to `/etc/ssh/skynet_ops_ca.pub`. Public material — safe in git. The **private** CA key is
never here; it is the whole root-grant security model (plan §8) and lives only on the
workstation + the survival kit.
