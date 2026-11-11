# unraid

Unraid (VM 2020, 10.10.20.20) as docker-admin sees it (skynetv2.md → P5 → Wider eyes), and the
undo copies it keeps for the lab (P6 → The undo out of reach). Unraid's config is Ali's and isn't in
git; this folder is what Ali applies there, so git describes it.

- **Metrics:** `compose.yaml`, two upstream exporters as Unraid containers, on Unraid's own network:
  node-exporter on :9100 (the host; its mdadm collector off, since Unraid's array is its own md
  driver) and smartctl-exporter on :9633 (each disk's SMART health, wear, temperature). VictoriaMetrics
  scrapes both as `unraid` (`stacks/admin/metrics/scrape.yaml`).
- **Logs:** Unraid's syslog to docker-admin's vlagent, TCP 5515, stamped `source=unraid`
  (`stacks/admin/logs`): the array's events (a disk disabled, a parity check's result), disks'
  errors, NFS. Its own lines can be hours apart, so a User Script logs a heartbeat
  (`log-heartbeat`) every 5 minutes: `SyslogNotArriving` counts those.
- **Network:** Unraid is on VLAN 20, so OPNsense's rules carry both: `HOST_UNRAID` in
  `ROLE_METRICS_TARGETS` (rule 236) with 9633 added to `PORT_METRICS`, and in `ROLE_LOG_SHIPPERS`
  (rule 237) with its port alias `PORT_LOG_INGEST` = 9429, 5515. docker-admin's firewall admits
  10.10.20.20 on 5515 (`hosts/docker-admin/default.nix`).
- **Alerts:** the host rules (`HostDown`, `DiskFull` but for the array disks `/mnt/disk*`, which
  Unraid fills past 90% by design; `MemoryLow`, `OOMKill`), `DiskUnhealthy` / `DiskWearing` from
  smartctl-exporter, and `SyslogNotArriving` when the heartbeat stops. The array's own events (a
  disk disabled or missing, a parity check's errors, a disk too hot) post through Unraid's own
  notifications, to `#alerts` by its Discord agent: Unraid knows its array best.
- **Undo copies:** `undo.sh`, a User Script at 04:00, before the merge window: a dated copy of
  shares `pbs` (PBS's datastore) and `Storage` (the library and media), each in a share of its own
  on the same array disk, `undo-pbs` and `undo-Storage`, 14 nights of each. The lab writes and
  deletes in `pbs` and `Storage` (PBS as root; docker-dmz over NFS); the copies it can only read,
  so whatever it deletes there stays for 14 nights.
  - A copy shares its data with the original and costs space only for what the original later
    deletes or replaces. `pbs` is hard-linked: PBS never rewrites a chunk, so every copy is a whole
    datastore. `Storage` is copy-on-write where the disk's XFS has reflinks, which also keeps a
    file rewritten in place; without them it's hard-linked, which keeps deleted and replaced files
    only. The job's log line says which (`copied (reflink)` or `copied (link)`).
  - It logs to syslog as `skynet-undo`, ending with `done`; a failed copy deletes no older one.
  - Reading them back: `undo-pbs` is exported read-only to PBS and `undo-Storage` to docker-dmz.

## Apply it (Ali)

1. **The containers**, either way:
   - the Docker Compose Manager plugin (Community Apps): a new stack `exporters` with this
     `compose.yaml` pasted in, then Compose Up;
   - or Docker → Add Container, twice, with the same settings: the image (tag and digest), network
     type Host, and for node-exporter `--pid=host` and the path `/` → `/host` read-only (not slave:
     Unraid's root isn't a shared mount) plus the two arguments; for smartctl-exporter Privileged on
     and user `root`.

   Check from the workstation: `curl -s http://10.10.20.20:9100/metrics | head` and
   `curl -s http://10.10.20.20:9633/metrics | grep smartctl_device_smart_status`.
2. **The syslog:** Settings → Syslog Server → Remote syslog server `10.10.50.40`, port `5515`,
   protocol TCP. Apply.
3. **The heartbeat:** the User Scripts plugin (Apps), then Settings → User Scripts → Add New Script
   `skynet-heartbeat`, its script:
   ```sh
   #!/bin/bash
   logger -t log-heartbeat "skynet heartbeat"
   ```
   Schedule: Custom, `*/5 * * * *`. Apply. Within 5 minutes its line is in VictoriaLogs
   (`source:=unraid app_name:=log-heartbeat`).
4. **The array's alerts:** Settings → Notification Settings → Notification entity: Agents on for
   Warnings and Alerts; Notification agents → Discord: enable it, Webhook URL = `#alerts`' webhook
   (`nix shell nixpkgs#sops -c sops -d --extract '["discord_alerts_webhook"]' secrets/docker-admin.yaml`),
   Apply, then Test: a post lands in `#alerts`.
5. **OPNsense:** the aliases above.
6. **The undo copies:**
   1. Settings → User Scripts → Add New Script `skynet-undo`; its script is `unraid/undo.sh`, whole.
      Schedule: Custom, `0 4 * * *`. Apply.
   2. Run Script, once. It ends with `skynet-undo: done`, and Shares now lists `undo-pbs` and
      `undo-Storage`.
   3. Shares → `undo-pbs`: SMB Security Settings → Export `No`, Apply. NFS Security Settings →
      Export `Yes`, Security `Private`, Rule `10.10.20.40(sec=sys,ro,no_root_squash)`, Apply.
   4. Shares → `undo-Storage`: SMB Security Settings → Export `No`, Apply. NFS Security Settings →
      Export `Yes`, Security `Private`, Rule `10.10.100.10(sec=sys,ro,no_root_squash)`, Apply.

   Check, on Unraid's terminal: `ls /mnt/disk1/undo-pbs /mnt/disk1/undo-Storage` shows today's
   date in each, and `exportfs -v | grep undo` shows both with `ro`.

A Renovate PR that bumps an image here changes nothing on Unraid until it's applied again (step 1).

## Gotchas

- The undo copies live on the array disks only. A file still on the pool (`/mnt/cache`) joins the
  copies the night after the mover moves it: a copy made on the pool would keep its data there.
- Unraid's root filesystem lives in RAM, and `/mnt/user` is its FUSE union of the array: neither
  counts for `DiskFull`. The pool (`/mnt/cache`, if any) does.
- smartctl-exporter checks each disk's power mode first and skips one in standby (its default
  `--smartctl.powermode-check=standby`), so it wakes no spun-down disk; such a disk's SMART series
  wait until it spins up.
