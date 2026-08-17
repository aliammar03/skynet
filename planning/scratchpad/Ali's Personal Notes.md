Ali's personal Idea board.
Nothing here needs to read by the agent.
Could contain pr0n for all I care. 

repo being the best possible memory for a mind that boots cold every time.

Legibility — can a cold-booting agent reconstruct full state cheaply? Markdown runbooks + JSON inventory + rendered docs = extremely high. This is your biggest strength and it's not an accident.
- Reversibility — git revert → Arcane converges back. This is huge for an LLM: it lets the agent act boldly because mistakes are cheap. Reversibility is an intelligence multiplier for a non-deterministic operator.
- Low branching factor — compose + Arcane is a small, boring surface. Few abstractions = less for the agent to get wrong.

problems with gen docs
cheap recon

OpenTofu


Fix decision 1

Nix.


# pi

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
redesign the zsh landing page, remove vibeos references, fix the snowflake, delegate tasks as needed.

DR runbook Complete check


templates SKY-000

Read planning/projects/SKY-003-apps-reverse-proxy-authentik-sso-ingress.md and execute Phase 1.

# Admin Netbird
Split dns

# Claude github
Run /install-github-app to tag @claude right from your Github issues and PRs

# Snapshot expansion
Add the scrpt logs to drive
Snapshot containers plus roll back scripts

Show what's happening.
Inventory should include wether a host is ops-managed and what tier access does it have.


# Expand workstation scripts
Time zones 12H

# Vault
Evaluate methods of making a secters vault, then make a mechanism to auto copy secrets e.g the rustic repo password.

# Agent aliasing
Should I alias the agent to frontload it?



plan scratch plus service research

###Future Plans and Brainstorming
We need a system of planning and brain storming for future additions and overhaul of existing features that this Skynet agent has. An example could be i propose a thing, we brainstorm then you come up with an actionable plan we save in a folder that we can then execute whenever. Include a prompt to execute the plan in the doc as well. Also it can be split into multiple phases if needed e.g if it takes more than a 1-2 hour session, generate resume stuff too like commits to memory and a continue prompt after a phase has been successfully completed.

# Logging System
Let's build a logging system to the actions the agent takes, we can categorize them, successful runs of actions, failures need logs. Will be so good for diagnostics.

# Better Readmes
Better readmes, they are so bare bones it hurts. Make them rich and exciting. 

# Better Docs
Improve the renderer. I would like the generated docs to be more rich, starting with the inventory of hosts, could you make it so more data is added for example the specs of the machines running proxmox, their ips, network configs etc. Separate the vms and lxcs, add their provisioned specs too like allocated ram, cpu cores, network config etc. The services docs are pretty barebones too, they should have rich details about the services instead of just dns records. Also pretty the generated documents, they are pretty bare bones. Timestamps need to be more human readable, make it a simple 12hr time and date in PST. Also Move the note to the bottom of documents. 

The Docs generated from the Opnsense config could use some work too. we can add the dhcp reservations. Tables in the vlan doc explaining access. a separate page for holes in the vlans we created using the firewall rules. The network map needs overhauling, it currently takes stuff from dhcp reserve hosts only so it contained many stale entries, maybe combine them with the service docs? 

# Inventory
Inventory should include wether a host is ops-managed and what tier access does it have.

# Script expansionRun doc generation after service deployment.
The nightly script should be able to use a really good writing model to write the state of Skynet, it being good at writing means a better more lively summary. The weekly cli script should also give a good overview of the models that the cli supports. It could even make recommendations of which models to use and where. backup status should contain the status of the last 7 last runs.

# Workstation change
What do I need to do if I'm gonna be changing my workstation, give me checklist plus runbook.

# Proxmox Provisioning
We need to rewamp the provisioning of vms and lxc from proxmox. We don't even have our golden templates yet.

# Memory 
When envoking the agent how much data does it have of skynet? Evaluate token usage, does it only ready machine readable stuff or does it get the generated docs and runbooks too? I'm a noob at agentic coding so i genuinely don't know how much cost overhead it adds.

# Caddy proxy manager VS Agent Caddy.

# Docs push
The newest generated docs should be pushed as soon as they are generated. Maybe have the nightly script push the docs?

# Notification System
Let's add a notification system so that the lab tells me what's going on. Give me some options


# Backup Throttle limits

# Root acces expansion
Keep list of hosts

# git push to hosts
