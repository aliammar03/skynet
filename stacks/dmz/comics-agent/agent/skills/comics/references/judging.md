# Judging a copy

Ali wants the best copy of the right issue, filed by itself; a wrong copy in the library is worse
than a gap.

## Is it the right issue?

- **Names differ.** Posts name a series their own way: spelled out or abbreviated, other
  punctuation, dots for spaces. A search that finds nothing, or only wrong posts, usually needs an
  alias, not another issue number.
- **Same name, other series.** Spin-offs, relaunches, companion and digital-first series share a
  name: check the subtitle, the start year and the issue count.
- **The year in a post is the cover year,** often the next year for an issue on sale late in the
  year: search with the cover year (`cover_date` in `wanted`).
- **Decimal issues** are written several ways (½, 0.5, 000.5): match them by value.
- **Prove it before you file it.** A post with no year, a bare abbreviation or sparse ComicInfo proves
  nothing: `inspect` it against the issue (pages, ComicInfo). Unproven is a gap, not a fill.

## Is it the right edition?

Not the issue, unless the series itself is that edition: a director's cut, a preview, a phone
reformat (a panel a page), a noir or black-and-white edition, a facsimile, a variant-cover gallery, a
collected volume standing in for one issue. A variant cover of the same issue is fine. A file far
shorter than the issue is a preview.

## Digital or scan?

Digital, always; among digital copies, the bigger file.

- **Digital** releases say "(Digital)" or "Webrip", or come from a digital-release group (`ComicInfo`
  → `ScanInformation`); their interior pages are all one size, usually about 2000×3000. Older digital
  releases are smaller (some publishers' back catalogue is about 1280 px wide) and still digital:
  judge by the release and the uniform page size, not by pixels alone. Never propose a swap for the
  same release.
- **Scans** of print copies ("c2c") vary by a few pixels from page to page. An issue that exists only
  as scans: the cleanest scan.
- `inspect` samples the cover, page 2, the middle and the last page: judge by the interior pages.

## Damaged and failed posts

- A post damaged at upload fails on every server ("articles were malformed", "cannot be completed"):
  take another post. A REPOST of the same release is often the complete one.
- A post that failed once (`sab/history?failed=1`) fails again.
- CBR is fine: CLU converts it to CBZ when it files.

## GetComics

CLU's fallback after Usenet. Its mirrors die or rate-limit and its search can match the wrong page.
If CLU fell back to GetComics and failed, a Usenet post under another name is the usual fix.
