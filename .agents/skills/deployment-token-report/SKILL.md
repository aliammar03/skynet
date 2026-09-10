---
name: deployment-token-report
description: Compile recorded per-role Codex rollout and token totals at substantive Medium/Heavy closure. Use only by Archivist after closure is sealed; never estimate cost or missing usage.
---

# Deployment token report

Use this skill only as the Archivist assigned to close a substantive Medium or Heavy deployment.
Finish the assigned documentation, compact checks, and read-only Git handoff first, then seal the
closure: no repository changes or further checks after reporting starts.

Confirm that Main placed this exact hidden marker in its first commentary message for the deployment,
using the supplied unique lowercase underscore-safe deployment ID:

```text
<!-- skynet-deployment-start: <deployment_id> -->
```

Run `python3 -B scripts/report_tokens.py --deployment-id <deployment_id> --format markdown`. Let the script use
`CODEX_THREAD_ID` to identify this Archivist rollout, resolve its parent Main thread, locate the marker
in Main's assistant text, and read recorded metadata and token-count fields under the local Codex
sessions directory. Guardian sessions are outside the descendant set.

Return the script's six-column Markdown table verbatim. Add no pricing, estimates, inferred usage, or
derived statistics. If the script fails or reports incomplete evidence, return that limitation
verbatim instead of manufacturing a report.

```text
| Agent | Quantity | Rollouts | Cached input | Input | Output |
| --- | ---: | ---: | ---: | ---: | ---: |
| <agent role> | <count> | <count> | <tokens> | <tokens> | <tokens> |
```

`Input` includes the cached-input subset. `Rollouts` counts model generations with a recorded
`last_token_usage`. The report cutoff is when the script starts, excluding the Archivist's later
response and Main's final response.
