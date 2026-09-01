-- host-map.sql — the canonical host map as a JOIN over entity keys (SKY-018 P3), replacing the old
-- jq/awk IP-priority ladder in render-docs.sh. One row per 10.10.0.0/16 IP, best label wins:
--   guest (0) > DHCP reservation (1) > single-IP alias (2) > unique-target DNS (4) > role alias (3+n).
-- A running guest IS the host, so it wins and carries its entity id; a DNS name that resolves to a
-- front-door IP is a vhost, not a host, and is excluded here (shared target) — see vhosts.sql.
-- Output cols (tab): ip \t name \t source \t entity_id \t note
WITH cand(ip, name, prio, source) AS (
  SELECT ip, name, 0, 'guest' FROM guests
    WHERE ip LIKE '10.10.%' AND ip <> '' AND status = 'running'
  UNION ALL
  SELECT ip, host, 1, 'dhcp' FROM reservations WHERE ip LIKE '10.10.%'
  UNION ALL
  SELECT ip, name, CASE WHEN nmembers = 1 THEN 2 ELSE 3 + nmembers END, 'alias'
    FROM aliases WHERE ip LIKE '10.10.%'
  UNION ALL
  SELECT ip, name, 4, 'dns' FROM dns_a d
    WHERE ip LIKE '10.10.%' AND (SELECT COUNT(*) FROM dns_a e WHERE e.ip = d.ip) = 1
),
best AS (
  SELECT ip, name, source, ROW_NUMBER() OVER (PARTITION BY ip ORDER BY prio) AS rn FROM cand
)
SELECT b.ip, b.name, b.source,
       COALESCE(g.entity_id, ''),
       CASE WHEN fd.ip IS NOT NULL THEN 'front door → ' || fd.proxy ELSE '' END
FROM best b
LEFT JOIN guests g ON g.ip = b.ip AND g.status = 'running'
LEFT JOIN front_doors fd ON fd.ip = b.ip
WHERE b.rn = 1;
