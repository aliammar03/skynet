# Manga in Uchiyomi

Uchiyomi finds series on the sources Ali turned on (MangaDex built in; Mihon's extensions through its
engine), downloads chapters as CBZ, and follows a series for new chapters. Which sources exist is
Ali's call: never ask for one to be added on your own, tell him what's missing instead.

## Choosing a source

`manga/search` gives the best match on each source; `manga/detail` one source's copy. Compare:

- **The same work?** A title can name different works: Webtoons' "Blue Period" is not the manga. Check
  the author, the status and the chapter range.
- **How much of it?** `count`, `first`, `last`. MangaDex lists only official previews for a licensed
  series (Blue Period: 6 chapters of 84); say so, and offer the sources that carry the rest.
- **Who translates it?** `groups`: one group carrying the whole run beats a patchwork. Language
  English unless Ali says otherwise.
- **Numbering.** A source that gives many posts one number (webtoon sites) is numbered by posting
  order (`numbering: posting_order`); its chapters won't line up with another source's numbers.

Pick one source, add it, and say which and why. Comic sources in Uchiyomi (BatCave, XOXO Comics,
ComicHubFree, Read Comics Online) are for comics CLU can't get; CLU first.

## After adding

- `manga/add` downloads every chapter and follows the series; `manga/status` shows its downloads,
  its gaps (whole numbers missing between the chapters it holds) and what its sources list that it
  lacks, with why: `missing` (not fetched yet), `failed` (gave up after retries), `held` (waiting for
  a preferred group), `blocked`, `floor`, `archive` (fetched slowly).
- `manga/fill` fetches the `missing` and `failed` ones from its own sources.
- `manga/fill-other` asks the other sources (they answer for a few minutes under one `planId`): fetch
  a candidate's `fillable` numbers only; `numbering_mismatch` means its numbers don't line up.
- Gaps no source fills: report them by number. Some series skip numbers on purpose (a 10.5 extra, a
  renumbered volume); say so when the sources agree.
