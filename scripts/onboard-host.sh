#!/usr/bin/env bash
# onboard-host.sh — make a workload host trust the SSH user-CA (plan §8)
# TIER: T2+ (runs AS ROOT on the target, inside a grant window; or baked into the golden template).
# USAGE: run ON the target host as root, with skynet_ops_ca.pub present in the CWD:
#          sudo ./onboard-host.sh
#        Golden-template path: bake CA trust + svc-ops in so new guests are born onboarded.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "must run as root on the target host" >&2; exit 1; }
[ -f skynet_ops_ca.pub ] || { echo "skynet_ops_ca.pub not found in $(pwd)" >&2; exit 1; }

echo "==> installing CA trust"
install -m 644 skynet_ops_ca.pub /etc/ssh/skynet_ops_ca.pub

echo "==> principal mapping for root"
mkdir -p /etc/ssh/auth_principals
printf 'ops-root-%s\nops-root-all\n' "$(hostname)" > /etc/ssh/auth_principals/root

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
