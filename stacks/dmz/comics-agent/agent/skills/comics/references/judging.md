# Judging a copy

What this library learned the hard way (2026-10). Ali wants the best copy of the right issue, filed
by itself; a wrong copy in the library is worse than a gap.

## Is it the right issue?

- **Names differ.** Metron names a series one way, posts another: "TMNT: The Last Ronin" is posted as
  "Teenage Mutant Ninja Turtles - The Last Ronin"; "All Star Superman" as "All-Star Superman"; a colon
  becomes a dash; scene posts use dots ("Teenage.Mutant.Ninja.Turtles-The.Last.Ronin.002…",
  "Ultimate.Spider-Man.064-000"). A search that finds nothing, or only the wrong posts, usually needs
  an alias (`POST /comics/aliases`), not a different issue number.
- **Same name, other series.** Spin-offs and relaunches share names: "Ultimate Spider-Man – Infinity
  Comic" and "Ultimate Spider-Man: Incursion" are not Ultimate Spider-Man (2000); "The Last Ronin II
  – Re-Evolution" and "The Last Ronin – The Lost Years" are not The Last Ronin; "Before Watchmen" is
  not Watchmen. Check the series' start year and the issue count.
- **The year in a post is the cover year**, which for an issue on sale in October to December is
  often the next year (Ultimate Spider-Man #15: on sale 2001-11, posted as "(2002)"). Search with the
  cover year (`cover_date` in `wanted`).
- **Decimal issues** are written many ways: "½", "0.5", "000.5". CLU can't file "#000.5" as "#½";
  such a file waits in `processed/` and needs Ali.

## Is it the right edition?

Not the issue, unless the series itself is that edition: a director's cut, a preview, a
"digital-mobile" or DC "W.I.P." reformat (one panel a page, for phones), a noir or black-and-white
edition, a facsimile, a variant-cover gallery, a TPB, omnibus or "collected" volume standing in for one
issue. A variant cover of the same issue is fine. The Last Ronin #1's Director's Cut and a preview of
Absolute Batman #1 were once filed as the issue; don't repeat it.

## Digital or scan?

Prefer digital, always; among digital copies, the bigger file.

- **Digital** releases say "(Digital)" or "Webrip" and come from groups such as Zone-Empire,
  Marika-Empire, Mephisto-Empire or Shadowcat-Empire (`ComicInfo` → `ScanInformation`). Interior
  pages around 1920×2951, 1988×3056 or 2128×3263; the cover may be smaller.
- **Scans** of print copies: interior pages around 1280×1967, or less; "c2c" (cover to cover). Old
  issues may exist only as scans: then the cleanest scan.
- `inspect` samples the cover, page 2, the middle and the last page. Judge by the interior pages, and
  by the page count against the issue's (a 6-page file is a preview).

## Damaged and failed posts

- A post damaged when it was uploaded fails on every server ("articles were malformed", "cannot be
  completed"). Retrying it, or another server, won't help: take another post. A "REPOST" of the same
  release is often the complete one.
- A post that failed once (`sab/history?failed=1`) will fail again; skip it.
- CBR files are fine: CLU converts them to CBZ when it files them, page for page.

## GetComics

CLU's fallback after Usenet. Its mirrors die or rate-limit (MEGA), and its search can match the wrong
page. If CLU fell back to GetComics and failed, a Usenet post under another name is the usual fix.
