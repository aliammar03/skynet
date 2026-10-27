# Every host: what docker-admin's VictoriaMetrics scrapes (node-exporter, comin's exporter) and the
# journal, shipped to its vlagent (skynetv2.md → P5). On the host, not in a stack: each exporter
# reads the host itself, and ops and the DNS VMs run no Docker.
{ config, lib, ... }:
let
  dockerAdmin = "10.10.50.40";
  ports = lib.concatMapStringsSep "," toString config.skynet.metricsPorts;
in
{
  options.skynet.metricsPorts = lib.mkOption {
    type = lib.types.listOf lib.types.port;
    default = [ ];
    description = "Ports here that docker-admin's VictoriaMetrics scrapes. The host firewall admits only docker-admin to them.";
  };

  config = {
    skynet.metricsPorts = [
      9100 # node-exporter
      4243 # comin's exporter (comin listens already)
    ];

    services.prometheus.exporters.node = {
      enable = true;
      # systemd: each unit's state, so a failed unit alerts.
      enabledCollectors = [ "systemd" ];
      extraFlags = [
        "--collector.systemd.unit-include=.+[.](service|socket|timer)"
        # Job results (backups, btrbk, the PBS offsite sync), each a *.prom file.
        "--collector.textfile.directory=/var/lib/node-exporter"
      ];
    };
    # Root's jobs write there (the backup containers mount it); the exporter only reads.
    systemd.tmpfiles.rules = [ "d /var/lib/node-exporter 0755 root root -" ];

    # The whole journal, containers' logs included (Docker's journald driver). The upload keeps a
    # cursor, so after an outage it resumes where it stopped; until then the journal holds the logs.
    services.journald.upload = {
      enable = true;
      settings.Upload.URL = "http://${dockerAdmin}:9429/insert/journald";
    };

    # So a loop can't fill the disk or the log store, journald drops what one service logs past
    # about 100 lines a second at each priority, and logs how many it dropped. It scales this burst
    # by the journal's free space (about ×3.5–4 here, so 800 comes to ~3,000 per 30 s); its default
    # of 10,000 lets hundreds a second through. Every container's lines come through dockerd, so
    # containers share docker.service's; the busiest normal 30 s held under 350.
    services.journald.rateLimitInterval = "30s";
    services.journald.rateLimitBurst = 800;

    # A line every 5 minutes, so VictoriaLogs can tell this host's lines still arrive
    # (LogsNotArriving, stacks/admin/logs/rules).
    systemd.services.log-heartbeat = {
      description = "Log a heartbeat line for VictoriaLogs";
      serviceConfig.Type = "oneshot";
      script = "echo log heartbeat";
      startAt = "*:0/5";
    };

    networking.firewall.extraCommands = ''
      iptables -A nixos-fw -p tcp -s ${dockerAdmin} -m multiport --dports ${ports} -j nixos-fw-accept
    '';
  };
}
