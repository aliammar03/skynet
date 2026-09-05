# 🗄️ archive — done & abandoned

scratchpad ▸ ideas ▸ backlog ▸ projects ▸ **`archive`**

**The normal end of the line — and the memory.** Completed and killed directives retire here,
because the ID and its history stay meaningful long after the work is over. This is where you
answer "wait, *why* did we do it that way?" six months later.

`bin/plan archive SKY-###` lands a directive here when it ships. Add `--abandon` to mark it
**killed** rather than **done** — a dead-end is data too, and recording *why* we stopped keeps
us from re-litigating it in a year.

Archive is terminal **by default**. A completed maintenance directive may return to `projects/`
only on explicit human instruction when the same maintenance domain needs another bounded phase set.
Reopen the existing ID rather than minting a sequel: preserve completed phases/history, add the new
phases, then `bin/plan promote SKY-### projects` (which stamps `status: in-progress`). Never keep
simultaneous archive/project copies of one ID. Abandoned directives remain historical unless a human
explicitly chooses otherwise.

IDs are never reused: whether active again or archived, `SKY-014` always means the same directive.
