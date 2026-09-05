---
summary: "Triage internal Technitium and public Cloudflare DNS failures, then repair records through the scoped declarative path."
trigger: "A name won't resolve / service unreachable by hostname / ACME DNS-01 failing"
tier: "T1/T2"
executor: "DNS queries and the scoped declarative DNS path"
rollback: "restore the prior DNS declaration through its approved path"
---

# Diagnose — DNS failure

**Tier:** T1 queries; T2 PR-gated record changes. Technitium settings and the Cloudflare account/zone settings are T3.

## Preconditions

- Know the affected name and whether it should resolve internally, publicly, or both.

## Steps

1. Query an actual internal resolver and a public resolver. Resolver addresses are `ROLE_DNS_RESOLVERS` in [`../../docs/generated/20-firewall.md`](../../docs/generated/20-firewall.md); do not query a proxied Technitium admin hostname.
   ```bash
   TDNS=10.10.70.51
   dig +short <name> @"$TDNS"
   dig +short <name> @1.1.1.1
   dig <name> @"$TDNS"
   resolvectl status
   ```
2. Classify the result:

   | Signal | Action |
   |---|---|
   | public works, internal fails | repair Technitium zone record |
   | internal works, public fails | repair Cloudflare DNS record |
   | `NXDOMAIN` | add the record on the required side |
   | `SERVFAIL` | inspect forwarder health; settings work is T3, so stop |
   | wrong address | compare the generated host map and correct the declared record |
   | missing ACME TXT | check scoped Cloudflare token and propagation |

3. Change the declared source on a branch, attach a speculative plan, and wait for its merge. From merged source, create/show the saved plan and apply only after approval:
   ```bash
   eval "$(scripts/tofu-env.sh)"
   tofu -chdir=tofu plan -out=/tmp/dns-fix.tfplan
   tofu -chdir=tofu show -no-color /tmp/dns-fix.tfplan
   TOFU_APPLY_SCOPE=<technitium-dns|cloudflare-dns> scripts/tofu-apply.sh /tmp/dns-fix.tfplan
   ```
   Internal records are declared in `tofu/dns-aliammar-net.tf`; public tunnel CNAMEs derive from `compose/cloudflared/config.yml` into `tofu/cloudflare-dns.tf`. Do not hand-run a provider token call. The Technitium token cannot yet delete records; deletion requires its documented grant or human UI action.

## Verify

- Both required resolver paths return the expected record and status after propagation; DNS-01 TXT is visible where ACME queries it.

## Rollback

- Revert the declaration and use the corresponding approved saved plan. Do not broaden provider access to delete a record.

## Evidence

- Record the resolver, status, affected side, declaration change, and verification in the incident journal.
