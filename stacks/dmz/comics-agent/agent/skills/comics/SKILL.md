---
name: comics
description: Run Ali's comics and manga library through comics-tools — CLU for Western comics (Usenet, then GetComics), Uchiyomi for manga, Komga for reading. Use for every request in #comics and every scheduled prompt (patrol, morning report, upgrades): adding and filling series, judging copies, finding the right post, swaps that need Ali's ✅.
---

# Comics and manga

Western comics go through CLU; manga, manhwa and webtoons through Uchiyomi. If you can't tell which
a title is, ask. `references/judging.md` is how to tell a right copy from a wrong one; read it
before you judge, grab or swap. `references/manga.md` before manga work.

## comics-tools

Your only way to the apps. `curl -sS comics-tools:8080/` lists every verb with its arguments.

- GET: arguments in the query, `curl -sS --get comics-tools:8080/comics/find --data-urlencode 'q=Saga'`.
- POST: a JSON body, `curl -sS comics-tools:8080/comics/search -d '{"series": "Saga", "issue": "1", "year": 2012}'`.
- Answers are JSON; a refusal is `{"error": ...}` with its status. A search, a check, a filing pass
  or a deep rescan can take minutes: add `--max-time 900` and give the command a long timeout.
- Grabs are capped at 360 an hour (429 past it). Answers never carry links or keys; don't ask for them.

| Verb | Use |
|---|---|
| `GET /comics/find?q=` | Metron's series of a name: id, name, start year, publisher, issue count, subscribed |
| `POST /comics/subscribe {series_id}` | CLU follows it (folder `<Publisher>/<Series> (<year>)`); from `find`'s answer |
| `GET`/`POST /comics/aliases` | the other names CLU searches Usenet under; POST replaces the list |
| `POST /comics/check {series_id}` | CLU searches and grabs that series' missing issues now; `GET /comics/op?id=` until `null` |
| `GET /comics/wanted[?series_id=]` | issues on sale and not in the library: number, cover date, on-sale date |
| `GET /comics/series?series_id=` | every issue's file in the library, or `null` |
| `POST /comics/search {series, issue, year, volume}` | Usenet posts for one issue, scored by CLU, each with an `id` |
| `POST /comics/grab {result}` | download a post by its `id`; CLU files it if the issue is wanted |
| `GET /comics/downloads` | CLU's latest downloads, and the files waiting in `processed/` |
| `POST /comics/file` | CLU files what waits in `processed/` now |
| `GET /comics/inspect?path=` | a file's format, page count, page sizes and ComicInfo |
| `POST /comics/trash` | a proposal for Ali's ✅, then the trash (Approvals) |
| `GET /sab/queue`, `GET /sab/history[?failed=1]` | SABnzbd's downloads; a failed one says why |
| `GET /manga/search?q=`, `GET /manga/detail?source=&source_id=` | the best match on each source; one source's copy |
| `POST /manga/add {source, source_id}` | Uchiyomi adds it, downloads every chapter, follows new ones |
| `GET /manga/library?q=`, `GET /manga/status?series_id=`, `GET /manga/jobs` | the library; one series' gaps and downloads; all downloads |
| `POST /manga/fill {series_id}`, `POST /manga/fill-other` | fetch what its own sources list; or what other sources offer |
| `POST /rescan [{"deep": 1}]` | Komga and Uchiyomi read their folders now; `deep` after a trash or swap |

## The library and the schedule

- CLU files into `/data/<Publisher>/<Series> (<start year>)/<Series> (<start year>) #NNN.cbz` (Unraid's
  `Books/Comics/clu`). Komga reads it within the hour, Uchiyomi within half an hour; `/rescan` now.
- Uchiyomi downloads manga to `Books/Manga/uchiyomi/<source>/<series>/`; Komga reads that too.
- CLU searches every followed series' missing issues at 03:30 (Pakistan time): Usenet first, then
  GetComics. When SABnzbd fails one of CLU's own grabs, CLU takes the next-best post by itself, and
  never takes a failed post again. Your grabs by hand have no such fallback: you watch them.
- CLU files only issues it still wants. A copy of an issue it already has stays in `processed/`
  until a swap (Approvals).

## Add a comic series

1. `find` it. Pick the volume by name, start year, publisher and issue count; Ali's words ("the 2000
   one", "Image") decide. Two equally likely volumes (a relaunch with the same name): ask.
2. `subscribe`, then `aliases`: CLU adds ComicVine's other names by itself. If posts use a name it
   lacks ("Teenage Mutant Ninja Turtles - The Last Ronin" for "TMNT: The Last Ronin"), add it.
3. `check`, follow `op` until `null`, then `downloads` and `sab/queue` until they settle.
4. Judge every filed issue (`series`, then `inspect`): the right issue, the right edition, digital
   over scan. A wrong one goes through Approvals.
5. For each issue still in `wanted`: Fill a gap by hand.
6. `/rescan`, then report: filed N of M, what's missing and why, what needs Ali.

## Fill a gap by hand

1. `search` with the series name, the issue number and the **cover** year (`cover_date` in
   `wanted`; posts carry the cover year, not the on-sale one).
2. Read the results yourself (`references/judging.md`). CLU's score is a hint: it rejects right posts
   under another name, and accepts wrong ones (a preview, a spin-off with the same name).
3. `grab` the best right post. Several right posts: digital before scan, then the bigger file.
4. Watch `sab/queue`. A failed job (`sab/history?failed=1`): grab the next right post; a post that
   failed once fails again. When it lands, CLU files it (`downloads`; `file` if it waits).
5. Nothing right posted: try another alias, then say so. Don't grab a wrong copy to fill a hole.

## Approvals: trash and swaps

Removing or replacing a file in the library waits for Ali's ✅. comics-tools checks the ✅ itself.

1. `POST /comics/trash` with `{"series_id": 537, "issues": ["3"]}` (the issue goes back on the
   wanted list) or `{"paths": ["/downloads/processed/…"]}` (a stray file). It answers a `code` and a
   `post`.
2. Post `post` as its own reply, word for word, with one line before it on why.
3. Ali reacts ✅ to it (you get "✅ — I approve the message I reacted to.") or replies ✅ to it.
4. Call `POST /comics/trash` again with `code` and, from that ✅'s sender context, `message_id`,
   `thread_id` and `channel_id`. The files go to CLU's trash (recoverable).
5. A swap: before proposing, find the better post (`search`); after the trash, `grab` it (or
   `check` the series), `file`, then `/rescan` with `deep`.

## Patrol (every 6 hours)

1. `wanted`: for each issue, `search` (cover year) and grab a right post if there is one. An issue
   with nothing right posted: note it, once a day is enough.
2. `sab/history?failed=1` since the last patrol: for each failed issue still wanted, the next post.
3. `downloads`: files waiting in `processed/` — wanted ones `file`; a better copy of an owned issue →
   a swap proposal; a wrong file → a trash proposal.
4. `manga/jobs`: a failed or stuck download → `manga/fill` for that series.
5. Report in a few lines: what you grabbed and filed, what's still missing and why. Nothing to do:
   one line.

## Morning report (08:00)

What happened since yesterday's report, from the apps: what CLU's 03:30 run downloaded and filed
(`downloads`, `sab/history`), what's still missing per series (`wanted`), Uchiyomi's downloads and
failures (`manga/jobs`), and anything waiting for Ali. Short, by series.

## Upgrades (weekly)

For each followed series, `series`, then `inspect` each filed issue (or a sample of a long run).
Scan-sized pages (`references/judging.md`): `search` what's posted now. A digital copy of the same
issue and edition: propose the swap (Approvals), one proposal per series, each issue named with its
old and new page size. Nothing better: say how many scans are left and that none has a digital copy.

## Manga

1. `manga/search`, then `manga/detail` for the likely sources. Pick by `references/manga.md`; tell Ali
   which source you took and why.
2. `manga/add`. It downloads every chapter and follows new ones.
3. `manga/library` for its id; `manga/status` until its downloads finish. Gaps: `manga/fill`, then
   `manga/fill-other` (take a candidate's `fillable` numbers only), then report what no source has.

## Re-sync

CLU's moves are seen by Komga and Uchiyomi within the hour on their own. After a trash or a swap,
`/rescan` with `deep`: Uchiyomi then marks the chapter whose file left. Never move or rename library
files yourself; you can't, and the apps would list them twice.
