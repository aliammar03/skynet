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

    networking.firewall.extraCommands = ''
      iptables -A nixos-fw -p tcp -s ${dockerAdmin} -m multiport --dports ${ports} -j nixos-fw-accept
    '';
  };
}
