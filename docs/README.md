# docs

What isn't one host's or one stack's. Each machine's own facts are in its folder's README; each
stack's in its folder.

- [`lab.md`](lab.md): the lab on one page: the nodes, the VLANs, every guest (ours and Ali's), the
  change flow, and what only Ali applies (OPNsense, Cloudflare, Tailscale).
- [`credentials.md`](credentials.md): who holds what, and the credentials still planned.
- [`decisions/`](decisions/README.md): what was decided, by whom and when, one record each.
- [`plans/`](plans/): projects in flight, one file each; the folder is empty when nothing is.
  - [`restructure.md`](plans/restructure.md): this layout; its last PR deletes it.
  - [`autonomy.md`](plans/autonomy.md): the agent merges, verifies and rolls back by itself.
  - [`retire-v1.md`](plans/retire-v1.md): v1's last credentials, and disaster recovery proven.

The contracts: `stacks/README.md` (a stack), `hosts/README.md` (a machine), `AGENTS.md` (the
agent). Procedures: `runbooks/`.
