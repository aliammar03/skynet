#!/usr/bin/env bash
# onboard-host.sh — make a workload host trust the SSH user-CA (plan §8)
# TIER: T2+ (runs AS ROOT on the target, inside a grant window; or baked into the golden template).
# USAGE: run ON the target host as root, with skynet_ops_ca.pub (and, to also provision the
#        standing user, skynet_ops_svc.pub) present in the CWD:
#          sudo ./onboard-host.sh
#        Golden-template path: bake CA trust + svc-ops in so new guests are born onboarded.
#        For an existing host with no agent access yet, Ali runs this once as root (bootstrap).
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "must run as root on the target host" >&2; exit 1; }
[ -f skynet_ops_ca.pub ] || { echo "skynet_ops_ca.pub not found in $(pwd)" >&2; exit 1; }

echo "==> installing CA trust"
install -m 644 skynet_ops_ca.pub /etc/ssh/skynet_ops_ca.pub

echo "==> principal mapping for root"
mkdir -p /etc/ssh/auth_principals
printf 'ops-root-%s\nops-root-all\n' "$(hostname)" > /etc/ssh/auth_principals/root

# Standing unprivileged user (T2): docker group + the agent's key — inventory, docker
# contexts, log reading, envsync. Guarded so CA-only onboarding still works without it.
SVC_USER="${SVC_USER:-svc-ops}"
if [ -f skynet_ops_svc.pub ]; then
  echo "==> provisioning standing user ${SVC_USER} (docker group + agent key)"
  id "${SVC_USER}" >/dev/null 2>&1 || useradd -m -s /bin/bash "${SVC_USER}"
  getent group docker >/dev/null 2>&1 && usermod -aG docker "${SVC_USER}"
  install -d -m 700 -o "${SVC_USER}" -g "${SVC_USER}" "/home/${SVC_USER}/.ssh"
  install -m 600 -o "${SVC_USER}" -g "${SVC_USER}" skynet_ops_svc.pub "/home/${SVC_USER}/.ssh/authorized_keys"
else
  echo "==> skynet_ops_svc.pub absent — skipping ${SVC_USER} provisioning (CA trust only)"
fi

echo "==> sshd drop-in"
cat > /etc/ssh/sshd_config.d/90-skynet-ops.conf <<'EOF'
TrustedUserCAKeys /etc/ssh/skynet_ops_ca.pub
AuthorizedPrincipalsFile /etc/ssh/auth_principals/%u
PermitRootLogin prohibit-password
EOF

echo "==> validating sshd config"
sshd -t
systemctl reload ssh 2>/dev/null || systemctl reload sshd

echo "done — this host now honors auto-expiring root certs signed by the ops CA."
echo "principals: ops-root-$(hostname), ops-root-all"
