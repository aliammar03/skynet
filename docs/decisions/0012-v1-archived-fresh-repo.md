---
status: accepted
date: 2026-10-21
decision-makers: Ali
---

# v1 archived, a fresh repo, and the new ops built beside the old

## Context and Problem Statement

v1 (`aliammar03/skynet-v1`) grew by hand, and its state wasn't all in git. v2 had to start clean
without a moment when nothing watched the lab.

## Decision Outcome

Chosen option: v1 archived and kept as reference only; a fresh repository; the new ops VM built
alongside the old one, which was then retired, because that is a clean start without a blind spot.

### Consequences

- Good, because nothing of v1's carries over unread: its data moved once, by hand, and its
  guests are gone (Ali, 2026-10-25).
- Bad, because v1's credentials and firewall entries outlived it, and go by their own plan
  (`docs/plans/retire-v1.md`).

## More Information

Ali, 2026-10-21, at the start.
