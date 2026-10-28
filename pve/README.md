# pve

The Proxmox nodes' observability (skynetv2.md → P5 → Wider eyes): server-proxmox-core (10.10.50.11)
and server-proxmox-network (10.10.50.10), PVE 9.2 on Debian 13. The nodes' config is Ali's to apply;
this folder is what Ali applies, so git describes it. As on PBS (`pbs/etc/`):

- **Metrics:** Debian's `prometheus-node-exporter` on :9100, with the systemd collector (a failed
  unit alerts) and the textfile collector, which `prometheus-node-exporter-collectors`' timers fill
  every 15 minutes: SMART health (`smartmon_device_smart_healthy`), NVMe health and wear
  (`nvme_critical_warning`, `nvme_percentage_used_ratio`), pending updates. Each timer skips
  hardware the node lacks (its unit's conditions): smartmon runs only with SATA or IDE disks, so
  core, all NVMe, has the NVMe timer's metrics alone. docker-admin's VictoriaMetrics scrapes it as
  `server-proxmox-core` and `server-proxmox-network` (`stacks/admin/metrics/scrape.yaml`).
- **Logs:** `systemd-journal-upload` sends the journal to docker-admin's vlagent
  (`http://10.10.50.40:9429/insert/journald`): vzdump's results, the kernel, pveproxy. journald
  drops what one service logs past about 100 lines a second, and `log-heartbeat.timer` logs a line
  every 5 minutes (`LogsNotArriving`).
- **Network:** both nodes share VLAN 50 with docker-admin, so no OPNsense rule. docker-admin's
  firewall admits them to vlagent (`hosts/docker-admin/default.nix`). The core node's PVE firewall
  is off; the network node's is on, accepting by default with no rules (2026-10-28), so :9100
  answers. A rule there that drops would need docker-admin (10.10.50.40) on :9100.
- **Alerts:** the host rules, as for every host (`HostDown`, `DiskFull`, `UnitFailed`…), and
  `DiskUnhealthy`, `DiskWearing`, `GuestBackupFailed` (a vzdump job's `ERROR: Backup of VM … failed`
  in a node's journal).

## Run it (Ali, on each node, as root)

From the node's shell (its UI → Shell, or SSH): the repo at `ref`, read, then run. A PR that adds
or changes this folder says to run it from its branch before the merge, so the node's target is up
when VictoriaMetrics starts scraping it:
```sh
ref=main
d=$(mktemp -d) && curl -fsSL "https://codeload.github.com/aliammar03/skynet/tar.gz/refs/heads/$ref" | tar -xz -C "$d" --strip-components=1
less "$d/pve/setup.sh"
sh "$d/pve/setup.sh" && rm -r "$d"
```
It shows each file's change as it installs it, then the services and timers. Check: the node's
`node` target is up in VictoriaMetrics, and its heartbeat reaches VictoriaLogs within 5 minutes.

## Gotchas

- The first upload sends the journal's history too: a burst, with each line's own time.
- Nothing compares the nodes with this folder (the agent has no access to them, unlike PBS), so a
  change made on a node by hand stays invisible until the next run here puts it back.
- A failed unit the node already had shows as `UnitFailed` once node-exporter runs.
