---
status: accepted
date: 2026-10-27
decision-makers: Ali
---

# Every alert goes to Discord `#alerts`

## Context and Problem Statement

Several tools alert on their own: the deployers, the status page, the dead-man checks, the rules
over metrics and logs. Ali needs one place to look.

## Decision Outcome

Chosen option: every alert posts to Discord **`#alerts`**: doco-cd (through Apprise), comin's
hook, Gatus, healthchecks.io, Alertmanager (the rules in `stacks/admin/metrics/rules/` and
`stacks/admin/logs/rules/`) and Unraid's own notifications, because then there is one place to
look.

### Consequences

- Good, because one channel shows everything, and the agent reads the same alerts from
  Alertmanager's API.
- Neutral, because the rules for the agent alone (`agent_only="true"`) go to Alertmanager's
  `agent` receiver, which posts nowhere: Gatus and doco-cd already post those failures themselves.
- Bad, because Discord is the one path. When it or its webhook fails, `DeliveryWatchdog` stops and
  healthchecks.io reaches Ali through its own integrations (`stacks/admin/alertmanager`).

## More Information

Ali, 2026-10-21, at the start; Alertmanager joined on 2026-10-27, with the alerts PR (#91).
