# stacks

A stack is one folder, `stacks/<target>/<name>/`, deployed by its Docker host's doco-cd from
`main` (ADR-0001): `stacks/admin/` on docker-admin, `stacks/dmz/` on docker-dmz. A new one follows
`runbooks/new-stack.md`; its route and its Gatus row land in the same PR.

## The folder

| File | When | Content |
|---|---|---|
| `compose.yaml` | always | `container_name: <name>` (not compose's `<project>-<service>-1`); images pinned `tag@sha256:…`; a healthcheck; `restart: unless-stopped`; network `edge` (the doors also join their macvlan; the exceptions are in Networks) |
| `secret.sops.env` | it has secrets | dotenv, sops-encrypted for that host only; used through `env_file` |
| `README.md` | always | purpose · URL · auth mode · data paths + backup class · secret key *names* · upstream link · gotchas |

A scheduled job (a doco-cd `one_off` job) has no `restart` and no healthcheck, and its folder's
`.doco-cd.yml` turns reconciliation off (`runbooks/new-stack.md`, step 5).

## Routing

- Each door has **one wildcard site**, `*.aliammar.net`. It imports the app snippets and ends with a
  catch-all `404`.
- The wildcard cert comes through Cloudflare's DNS-01, so no app's name appears in the certificate
  transparency logs.
- A routed app's site file lives in its door: `conf/sites/<name>.conf` (`@x host x.aliammar.net` +
  `handle @x { [import authelia] reverse_proxy <container>:<port> }`); the door reloads it in place.
- Every app gets a row in Gatus's `config/admin.yaml`: Gatus runs on docker-admin and checks every
  host.
- No container mounts a stack's folder itself, because doco-cd writes the decrypted secrets into
  it. Mount single files, or subfolders without `*.sops.*` files.

## Auth modes

- **`own`** (the default): a plain proxy; the app has its own login.
- **`oidc`:** the client goes in its door's Authelia, `stacks/<target>/authelia/oidc-clients.yml`.
  That one file holds the whole list, because Authelia replaces a repeated key rather than
  appending to it. The client secret's digest goes there, and the plaintext in the app's own
  `oidc.sops.env`, which the agent generates whole and the compose file lists after
  `secret.sops.env`, so it wins. The provider's keys are in that Authelia's `oidc.sops.yml`.
- **`forward`:** `import authelia` in the app's site file. Each door's snippet asks its own
  Authelia, and the app's access rule goes in that Authelia's `configuration.yml`.

## Data

- Everything that persists is a bind mount at `/opt/appdata/<stack>/<role>`, databases included
  (their images fix file ownership at start). A host's state is then one folder to back up or move.
  No named volumes.
- Docker creates a missing folder as root and copies none of the image's files into it, as it would
  into a new named volume. An image that runs as a fixed non-root user and doesn't fix its own
  folder gets that folder from the host's config (`systemd.tmpfiles`, with its owner), in the
  stack's PR.
- The README gives each path a backup class: **data**, or **cache** (it rebuilds itself; its path
  joins the host's `stacks/<target>/backup/excludes.txt`).
- The nightly backup copies `/opt/appdata` hot, on both Docker hosts from a read-only btrfs
  snapshot taken a moment before: every file at one instant, as after a power cut, which the apps'
  databases restart from. Databases need no dumps, nothing stops, and a restore is the files put
  back (ADR-0015, `runbooks/restore.md`).

## Networks

- The host's Nix config creates the shared networks, not the stacks:
  - `edge`: a bridge shared by the apps and the doors;
  - a macvlan for the doors (`dmz`, `adm60`);
  - `door-<app>`: an internal bridge for a door and one app alone (`skynet.docker.doorNetworks`).
- A stack with helpers (a browser, a database, a search engine) gives them a network of its own in
  its compose file (`backend`), so nothing outside the stack reaches them. Only the app joins
  `edge`.
- Apps get no LAN address. The doors reach them by container name.
- The exception is an app that a firewall rule must name (its own egress, e.g. usenet). It joins
  only the macvlan, with a fixed address, so its traffic leaves with that address. Its door is on
  the macvlan too and reaches it there; no app on `edge` can.
- Every app on `edge` reaches every other. So an app with no login of its own (auth mode
  `forward`) stays off it, and only its door reaches it:
  - on the macvlan (a firewall rule names it), it admits only its door's address;
  - otherwise it joins `door-<app>`, plus a network of its own if it needs the internet.
- `comics-tools` is the one other exception: it sits on CLU's network as well (ADR-0017).
