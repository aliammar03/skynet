# inventory — AUTO-GENERATED JSON, never hand-edit

The `scripts/collect-*.sh` collectors (T1 read-only) write this folder. Every file is
machine truth, refreshed by the nightly run and committed as an `inventory/<date>` change.

Expected files:

```
proxmox-core.json      # guests, resources, pool membership (node: core)
proxmox-network.json   # guests, resources, pool membership (node: network)
pbs.json               # datastores, snapshots, GC status
docker-dmz.json        # compose projects, containers, images, health
dns-zones.json         # Technitium zones/records (view/modify scope)
firewall/              # parsed config.xml → rules, aliases, reservations
```

To change what is collected, **edit the collector**, never the JSON.
