#!/bin/sh
# Fetches the upstream boards from grafana.com at their pinned revisions into upstream/. A data
# source input that no template variable stands for is pointed at our VictoriaMetrics, since
# provisioning has no import step to fill it in. Run it from anywhere, then commit the result.
set -eu
cd "$(dirname "$0")/upstream"
fetch() { # <file> <grafana.com id> <revision>
  curl -fsS "https://grafana.com/api/dashboards/$2/revisions/$3/download" | jq '
    [.templating.list[]?.name] as $vars
    | ([.__inputs[]? | select(.type == "datasource") | .name] - $vars) as $ins
    | reduce $ins[] as $n (.; walk(if type == "string" and . == "${\($n)}" then "victoriametrics" else . end))
    | del(.__inputs, .__elements) | .id = null' >"$1.json"
}
fetch node-exporter-full 1860 45
fetch cadvisor 19792 6
fetch proxmox 10347 5
fetch victoriametrics 10229 60
fetch victorialogs 22084 12
fetch vmalert 14950 22
fetch alertmanager 9578 4
