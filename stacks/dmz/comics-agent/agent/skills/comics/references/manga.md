# Manga in Uchiyomi

Uchiyomi finds series on the sources Ali turned on (MangaDex built in; Mihon's extensions through its
engine), downloads chapters as CBZ, and follows a series for new chapters. Which sources exist is
Ali's call: never ask for one to be added on your own, tell him what's missing instead.

## Sources

Measured 2026-11-03 on 17 well-known series: how many each carries whole, how fast its search
answers, and the page width it serves (every one downloads a page in 0.5–0.8 s). Uchiyomi uses the
same order when a series follows more than one source.

| Tier | Source | Whole runs | Search | Pages | Notes |
|---|---|---|---|---|---|
| 1 | Atsumaru | 17 of 17 | 0.5 s | 1067–1200 px | fastest to answer; Weeb Central's pages, re-encoded |
| 1 | MangaFire | 16 | 0.6 s | 1060–1080 px | its own, smaller copies; Chainsaw Man only to #97 |
| 1 | Weeb Central | 16 | 2–4 s | 1067–1200 px | the originals (Vagabond 1–327 at 1200 px); slow to search, quick to download |
| 2 | MangaDot | 15 | 0.5 s | 1200–1500 px | no Vagabond, Berserk #1–7 only; One Piece at 1.4× the others' size, likely enlarged |
| 3 | MangaDex | few | 0.3 s | ~850 px | fan and unlicensed works; a licensed series is previews, or MangaPlus links it can't download |
| 3 | Asura Scans, Flame Comics | manhwa | 1 s | 720 px strips | Korean webtoons only |
| 3 | Webtoons.com | webtoons | 0.5 s | 800 px | official webtoons only |
| 4 | Kagane, OniSaga | 4, 1 | 0.6 s, 4 s | ~850 px | partial runs; last |

Within a tier: the originals over a copy of the same pages (Weeb Central over Atsumaru when both
have the whole run), then the bigger pages, then the faster source.

## Choosing a source

`manga/search` gives the best match on each source; `manga/detail` one source's copy. Compare:

- **The same work?** A title can name different works: Webtoons' "Blue Period" is not the manga. Check
  the author, the status and the chapter range.
- **How much of it?** `count`, `first`, `last`. MangaDex lists only official previews for a licensed
  series (Blue Period: 6 chapters of 84), or chapters that are links to MangaPlus, which can't be
  downloaded (One Piece): take a tier 1 source.
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
