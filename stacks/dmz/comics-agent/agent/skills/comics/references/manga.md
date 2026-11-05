# Manga in Uchiyomi

Uchiyomi finds series on the sources Ali turned on (MangaDex built in, Mihon's extensions through its
engine), downloads chapters as CBZ, and follows a series for its new chapters. Which sources exist is
Ali's call: tell him what's missing; never ask for one to be added on your own.

## Choosing a source

Sources differ from series to series, and from chapter to chapter within one: measure, don't assume.
`manga/compare` reads each source's copy straight from the source, nothing added: the work, its
chapters and who translates which, and pages of the chapters you name.

- **The same work?** Titles collide: check the author, the status and the chapter range.
- **The chapters wanted?** A source that lacks them, or lists only previews or links it can't
  download, is out.
- **The sharpest real pages:** the most pixels; at the same pixels, the bigger file (one source can
  re-encode another's pages smaller). A copy far bigger than every other is enlarged, no sharper.
- **Then the translation:** one translator over a patchwork; English unless Ali says otherwise. When
  the official translation and the sharper pages are on different sources, take the sharper pages and
  say so.
- **Numbering:** a source that numbers by posting order won't line up with another's numbers
  (`numbering: posting_order` in `manga/detail`).

Take one source, add it, and say which and why, with the numbers. Comic sources in Uchiyomi are for
comics CLU can't get: CLU first.

## After adding

- `manga/status` shows its downloads, its gaps (whole numbers missing between the chapters it holds),
  and what its sources list that it lacks, with why: `missing` (not fetched yet), `failed` (gave up
  after retries), `held` (waiting for a preferred translator), `blocked`, `floor`, `archive` (fetched
  slowly).
- `manga/fill` fetches the `missing` and `failed` ones from its own sources; `manga/fill-other` asks
  the others (they answer for a few minutes under one `planId`): fetch a candidate's `fillable`
  numbers only; `numbering_mismatch` means its numbers don't line up.
- Gaps no source fills: report them by number. A series may skip numbers on purpose (an extra, a
  renumbering); say so when the sources agree.
