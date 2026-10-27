# shellcheck shell=bash
# technitium-stats: the local Technitium's last hour (its dashboard: queries by response and by how
# they were answered, clients, cache) as Prometheus text, for node-exporter's textfile collector
# (skynetv2.md → P5 → Wider eyes). modules/dns.nix runs it every 5 minutes, logged in with the host's
# own admin password as technitium-sync is, then moves the file into /var/lib/node-exporter.
set -euo pipefail
api=${API:-http://127.0.0.1:5380/api}
auth=$(mktemp) # the session token as a header file, so it's never on a command line
trap 'rm -f "$auth"' EXIT

# As technitium-sync's: fails with Technitium's message unless its status is ok.
call() {
  local endpoint=$1
  shift
  curl -fsS -m 20 -H @"$auth" "$@" "$api/$endpoint" |
    jq -e 'if .status == "ok" then . else ("\(.status): \(.errorMessage // "")\n" | halt_error(1)) end'
}

pass=$(head -n1 "$PASSWORD_FILE" | jq -Rr @uri)
token=$(printf 'user=admin&pass=%s' "$pass" | call user/login --data @- | jq -r .token)
printf 'Authorization: Bearer %s\n' "$token" >"$auth"
stats=$(call "dashboard/stats/get?type=LastHour")
call user/logout >/dev/null

# A field Technitium no longer sends fails the unit (UnitFailed), rather than a file node-exporter
# would reject.
jq -r --arg now "$(date +%s)" -f /dev/stdin <(printf '%s' "$stats") <<'JQ' >"$RUNTIME_DIRECTORY/technitium.prom"
.response.stats as $s
| def n($k): $s[$k] | if type == "number" then . else error("no \($k) in Technitium's stats") end;
def gauge($name; $help; $lines): "# HELP \($name) \($help)", "# TYPE \($name) gauge", ($lines[] | "\($name)\(.)");
gauge("technitium_queries_last_hour"; "Queries in the last hour."; [" \(n("totalQueries"))"]),
gauge("technitium_responses_last_hour"; "The last hour's queries by response code."; [
  "{rcode=\"no_error\"} \(n("totalNoError"))",
  "{rcode=\"server_failure\"} \(n("totalServerFailure"))",
  "{rcode=\"nx_domain\"} \(n("totalNxDomain"))",
  "{rcode=\"refused\"} \(n("totalRefused"))"]),
gauge("technitium_answered_last_hour"; "The last hour's queries by how they were answered."; [
  "{by=\"authoritative\"} \(n("totalAuthoritative"))",
  "{by=\"recursive\"} \(n("totalRecursive"))",
  "{by=\"cached\"} \(n("totalCached"))",
  "{by=\"blocked\"} \(n("totalBlocked"))",
  "{by=\"dropped\"} \(n("totalDropped"))"]),
gauge("technitium_clients_last_hour"; "Clients that asked in the last hour."; [" \(n("totalClients"))"]),
gauge("technitium_cache_entries"; "Records in the cache."; [" \(n("cachedEntries"))"]),
gauge("technitium_stats_timestamp_seconds"; "When these were read."; [" \($now)"])
JQ
