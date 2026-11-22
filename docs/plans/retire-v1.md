# Retire v1, and prove disaster recovery `[outline]`

An outline: it is fleshed out into steps, in a PR, before any of it runs. v1's guests are gone
(Ali, 2026-10-25); what's left of it is access, and the recovery isn't proven end to end.

**Why:** no orphaned access, and a recovery that has actually been proven.

## v1's credentials, revoked

- Proxmox, on both nodes (read 2026-11-22): user `svc-ops@pve` with its tokens `operate` and
  `readonly`; its role `OpsOperator` (on core, granted on `/`: VM.Allocate, VM.Config.*,
  VM.GuestAgent.FileWrite, VM.Snapshot.Rollback and more); its pool `ops-managed` (HAOS and athena).
- The Technitium, Cloudflare and Authentik tokens.
- OPNsense's `svc-skynet-recon`; Omada's viewer; the v1 GitHub PAT; v1's healthchecks.io checks;
  v1's rclone client.
- Cloudflare: v1's tunnel `b5171e13…` (ADR-0012: v2's tunnel is new).

## v1's OPNsense entries, removed

Read through `skynet-read` on 2026-11-16 (Ali applies; the PR names each):
- rule 240 (Authentik, disabled), `HOST_AUTHENTIK` (also nested in `ROLE_ADMIN_TARGETS`) and
  `PORT_AUTHENTIK`;
- v1's ops, 10.10.90.90, in `HOST_SKYNET_OPS`;
- v1's docker-dmz, 10.10.100.15, in `ROLE_NFS_CLIENTS` and `ROLE_OPS_SSH_TARGETS`;
- what only v1 used, if nothing else does: `ROLE_OPS_PRIV_TARGETS` and rule 380 (dormant),
  `ROLE_DNS_UPSTREAMS`, rules 360 and 370 (v1's ops reads and SSH; rule 390 covers v2's ops), and
  the descriptions that still name v1 (`PORT_OPS_API`'s Arcane, `HOST_CLOUDFLARED`'s VLAN 40).

## Disaster recovery

- The final survival kit (`runbooks/survival-kit.md`).
- The runbooks:
  - a host rebuilt from git: `runbooks/new-vm.md` → Rebuild, from docker-dmz's rebuild; its data
    from Drive with `skynet-restore drive --all` is not yet drilled (`runbooks/restore.md` → Last
    done, case 3);
  - ops rebuilt from scratch (`hosts/ops/README.md` → Rebuild): not drilled; its first install's
    key was v1's, so the steps use the installing machine's own key;
  - PBS rebuilt (`runbooks/restore.md`, case 5) and everything from Drive (case 6, all of it): not
    yet drilled;
  - OPNsense restored from the `skynet-opnsense` repo (os-git-backup, unchanged);
  - the recovery order after losing a node.
- A quarterly kit check and restore drill, run as a scheduled agent task.

## Exit criteria

- The credential checklist is ticked, and OPNsense holds no v1 entry.
- One Docker host rebuilt from git plus backup in a drill.
