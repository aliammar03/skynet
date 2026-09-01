-- vhosts.sql — the reverse-proxy vhosts (SKY-018 P3 / SKY-015): DNS names whose target is a declared
-- front-door alias (lab.json). These are NOT hosts — each resolves to a proxy that fans out to many
-- backends — so they are surfaced separately from the host map, with the front door they land on.
-- Output cols (tab): vhost \t front_door_ip \t proxy
SELECT d.name, d.ip, fd.proxy
FROM dns_a d
JOIN front_doors fd ON fd.ip = d.ip
ORDER BY fd.proxy, d.name;
