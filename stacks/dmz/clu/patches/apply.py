"""Thirteen fixes to CLU v7.0 until CLU ships its own (stacks/dmz/clu/README.md → Patches).

The container runs this as root before CLU's entrypoint. Each fix replaces one exact piece of
CLU's code. A file is rewritten only when all its fixes apply and the result compiles; when CLU's
code has changed (an update), the fix is reported in the log and that file runs as shipped.
"""

import os

USENET = "/app/models/usenet.py"
APP = "/app/app.py"
SCORER = "/app/models/getcomics.py"
SERIES_ROUTES = "/app/routes/series.py"
DOWNLOAD_ROUTES = "/app/routes/download_clients.py"

# 1. A Usenet download is filed like any other: CLU runs its filing pass once WATCH empties after
#    a direct download, and never after a Usenet import. A failed download's leftover in WATCH
#    doesn't count: two from GetComics held The Lost Years #3-#5 unfiled.
FILE_AFTER_IMPORT = (
    "file-usenet-downloads",
    '        app_logger.info(f"{source} import: moved {moved} file(s) into WATCH for {filename}")\n'
    "        return True\n",
    '        app_logger.info(f"{source} import: moved {moved} file(s) into WATCH for {filename}")\n'
    "        _skynet_file_when_watch_empty(watch)\n"
    "        return True\n",
)
FILE_AFTER_IMPORT_HELPER = (
    "file-usenet-downloads",
    "def _move_into_watch(src_file, watch) -> int:\n",
    '''def _skynet_file_when_watch_empty(watch):
    """Skynet patch: CLU's filing pass once WATCH has emptied, as after a direct download."""
    import threading
    import time

    def run():
        from core.download_utils import is_temporary_download_file

        for _ in range(90):  # 15 minutes
            time.sleep(10)
            busy = False
            for _root, dirs, files in os.walk(watch):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                # A failed download's leftover (.part, .crdownload) is no comic on its way.
                if any(not f.startswith((".", "_")) and not is_temporary_download_file(f) for f in files):
                    busy = True
                    break
            if not busy:
                from app import process_incoming_wanted_issues

                process_incoming_wanted_issues()
                return
        app_logger.warning("Skynet patch: WATCH did not empty within 15 minutes; not filing")

    threading.Thread(target=run, name="skynet_file_after_import", daemon=True).start()


def _move_into_watch(src_file, watch) -> int:
''',
)

# 2. Among results with the same score, the bigger post wins: CLU kept the first one the indexers
#    returned, often a small, low-resolution copy.
BIGGER_WINS = (
    "bigger-post-wins-ties",
    '        if decision == "ACCEPT":\n'
    "            if best_accept is None or score > best_accept[1]:\n"
    "                best_accept = (r, score)\n",
    '        if decision == "ACCEPT":\n'
    "            # Skynet patch: among equal scores, the bigger post (the better copy) wins.\n"
    "            if best_accept is None or score > best_accept[1] or (\n"
    "                score == best_accept[1] and (r.size or 0) > (best_accept[0].size or 0)\n"
    "            ):\n"
    "                best_accept = (r, score)\n",
)

# 3. An issue with no on-sale date is out by its cover date: CLU's sweep skipped it as unreleased
#    (Metron lacks on-sale dates for many older issues), while its filing pass accepts it.
UNDATED_SEARCHED = (
    "search-undated-issues",
    "                status = issue_status.get(issue_num, {})\n"
    '                store_date = issue.get("store_date")\n',
    "                status = issue_status.get(issue_num, {})\n"
    "                # Skynet patch: no on-sale date -> its cover date.\n"
    '                store_date = issue.get("store_date") or issue.get("cover_date")\n',
)

# 4. A filed issue is named from CLU's own record of it (the series' start year), not from the
#    release's name, whose year is the cover year: CLU renamed from metadata only when it fetched
#    some, and it fetches none for a release that arrives tagged.
NAME_FROM_SERIES = (
    "name-from-series",
    "                new_filename = get_renamed_filename(filename, file_path=temp_dest)\n",
    "                new_filename = _skynet_series_filename(issue, filename) or get_renamed_filename(\n"
    "                    filename, file_path=temp_dest\n"
    "                )\n",
)
NAME_FROM_SERIES_HELPER = (
    "name-from-series",
    "@app_state.single_flight_target_sweep\ndef process_incoming_wanted_issues():\n",
    '''def _skynet_series_filename(issue, filename):
    """Skynet patch: the custom pattern filled from the wanted issue's own series record."""
    try:
        from cbz_ops.rename import (
            _format_issue_month,
            _pad_issue_number,
            apply_custom_pattern,
            apply_filename_cleanup,
            load_custom_rename_config,
            load_issue_pad_width,
        )

        enabled, pattern = load_custom_rename_config()
        if not enabled or not pattern:
            return None
        cover = str(issue.get("cover_date") or "")
        month_name, month_num = _format_issue_month(cover[5:7] or None)
        number = _pad_issue_number(str(issue.get("number") or ""), load_issue_pad_width())
        stem = apply_custom_pattern(
            {
                "series_name": issue.get("series_name") or "",
                "volume_number": "",
                "volume_year": str(issue.get("volume_year") or ""),
                "year": cover[:4],
                "issue_year": cover[:4],
                "issue_month_M": month_name,
                "issue_month_m": month_num,
                "issue_number": number,
                "issue_title": "",
            },
            pattern,
        )
        return apply_filename_cleanup(stem) + os.path.splitext(filename)[1] if stem else None
    except Exception as e:
        app_logger.warning(f"Skynet patch: no series-based name for {filename}: {e}")
        return None


@app_state.single_flight_target_sweep
def process_incoming_wanted_issues():
''',
)

# 5. A hyphen is a space when a release's series name is compared with the wanted one: CLU scored
#    "All-Star Superman" 0 against Metron's "All Star Superman" and took the scans named the
#    other way. Tried only when the names don't match as written.
HYPHEN_IS_SPACE = (
    "hyphen-is-space",
    "    # Series name matching — must happen before range rejection logic\n"
    "    delta, series_match, sub_series_type, remaining, used_the_swap, detected_variant = \\\n"
    "        _score_series_match(title_lower, title_normalized, search)\n",
    "    # Series name matching — must happen before range rejection logic\n"
    "    delta, series_match, sub_series_type, remaining, used_the_swap, detected_variant = \\\n"
    "        _score_series_match(title_lower, title_normalized, search)\n"
    '    # Skynet patch: a hyphen is a space ("All-Star Superman" is "All Star Superman").\n'
    '    if not series_match and "-" in title_lower + search.series_name:\n'
    "        import dataclasses\n"
    "\n"
    "        delta, series_match, sub_series_type, remaining, used_the_swap, detected_variant = (\n"
    "            _score_series_match(\n"
    '                title_lower.replace("-", " "),\n'
    '                title_normalized.replace("-", " "),\n'
    '                dataclasses.replace(search, series_name=search.series_name.replace("-", " ")),\n'
    "            )\n"
    "        )\n",
)

# 6. When the download client fails a post (articles missing), CLU records it, never takes it again,
#    and grabs the next-best accepted post for the issue; and "REPOST" in a title no longer costs it
#    the match (CLU scored All Star Superman #1 and #4's complete reposts 30 and gave up on both).
FAILOVER_HELPERS = (
    "failover",
    "def try_download_for_issue(\n",
    '''_SKYNET_FAILED_FILE = "/config/skynet_failed_posts.json"
_skynet_failed_lock = threading.Lock()


def _skynet_failed_keys():
    """Skynet patch: posts a download client has failed, as (title, size)."""
    import json

    try:
        with open(_SKYNET_FAILED_FILE, encoding="utf-8") as f:
            return {tuple(k) for k in json.load(f)}
    except (OSError, ValueError):
        return set()


def _skynet_failed_before(r):
    return (r.title, r.size or 0) in _skynet_failed_keys()


def _skynet_mark_failed(title, size):
    import json

    with _skynet_failed_lock:
        keys = _skynet_failed_keys() | {(title, size or 0)}
        try:
            with open(_SKYNET_FAILED_FILE, "w", encoding="utf-8") as f:
                json.dump(sorted(keys), f)
        except OSError as e:
            app_logger.warning(f"Skynet patch: could not record failed post {title}: {e}")


def _skynet_scoring_title(title):
    """Skynet patch: a trailing "REPOST" says nothing about which issue a post is; a scene-style
    name is read with spaces (_skynet_scene_spaces)."""
    import re

    title = re.sub(r"\\s*[\\[(]?\\bre-?post\\b[\\])]?\\s*$", "", title or "", flags=re.IGNORECASE)
    return _skynet_scene_spaces(title)


def _skynet_remember_alternates(download_id, res, chosen, series_name, issue_num):
    """Skynet patch: the other accepted posts, best first, for when this one fails."""
    ranked = sorted(
        (r for r in res["all_results"] if r["decision"] == "ACCEPT" and r["nzb_url"] != chosen.nzb_url),
        key=lambda r: (-r["score"], -(r["size"] or 0)),
    )
    with _jobs_lock:
        job = usenet_downloads.get(download_id)
        if job is not None:
            job["skynet_post"] = (chosen.title, chosen.size or 0)
            job["skynet_alternates"] = ranked
            job["skynet_issue"] = (series_name, issue_num)


def _skynet_try_next(download_id):
    """Skynet patch: a post the client failed is recorded, and the next-best one grabbed."""
    with _jobs_lock:
        job = dict(usenet_downloads.get(download_id) or {})
    post = job.get("skynet_post")
    if not post:
        return  # a manual grab: nothing to fall back to
    _skynet_mark_failed(*post)
    failed = _skynet_failed_keys()
    left = [a for a in job.get("skynet_alternates") or [] if (a["title"], a["size"] or 0) not in failed]
    series_name, issue_num = job["skynet_issue"]
    if not left:
        app_logger.warning(f"Skynet patch: {post[0]} failed at the client; no other post for {series_name} #{issue_num}")
        return
    nxt = left[0]
    app_logger.info(f"Skynet patch: {post[0]} failed at the client; trying {nxt['title']} ({len(left) - 1} more left)")
    filename = _make_filename(series_name, issue_num, None, "direct match")
    new_id = grab_nzb(nxt["nzb_url"], filename, series=series_name, issue=issue_num)
    if new_id:
        with _jobs_lock:
            new_job = usenet_downloads.get(new_id)
            if new_job is not None:
                new_job["skynet_post"] = (nxt["title"], nxt["size"] or 0)
                new_job["skynet_alternates"] = left[1:]
                new_job["skynet_issue"] = (series_name, issue_num)


def try_download_for_issue(
''',
)
FAILOVER_REMEMBER = (
    "failover",
    "    download_id = grab_nzb(result.nzb_url, filename, series=series_name, issue=issue_num)\n",
    "    download_id = grab_nzb(result.nzb_url, filename, series=series_name, issue=issue_num)\n"
    "    if download_id:\n"
    "        _skynet_remember_alternates(download_id, res, result, series_name, issue_num)\n",
)
FAILOVER_ON_FAILED = (
    "failover",
    '            elif status.status == "failed":\n'
    '                _set_status(download_id, "failed", error="Download failed at client")\n',
    '            elif status.status == "failed":\n'
    '                _set_status(download_id, "failed", error="Download failed at client")\n'
    "                _skynet_try_next(download_id)\n",
)
FAILOVER_SCORING_TITLE = (
    "failover",
    "        score, is_range, series_match, issue_matched = score_getcomics_result(\n"
    "            r.title, series_name, issue_num, issue_year,\n",
    "        score, is_range, series_match, issue_matched = score_getcomics_result(\n"
    "            _skynet_scoring_title(r.title), series_name, issue_num, issue_year,\n",
)
FAILOVER_SKIP_FAILED = (
    "failover",
    '        if decision == "ACCEPT" and not issue_matched:\n            decision = "REJECT"\n',
    '        if decision == "ACCEPT" and not issue_matched:\n            decision = "REJECT"\n'
    "        # Skynet patch: a post the download client failed before is not taken again.\n"
    '        if decision == "ACCEPT" and _skynet_failed_before(r):\n'
    '            decision = "REJECT"\n',
)

# 7. A series' search aliases are searched on Usenet too, not only used to score: Metron's
#    "TMNT: The Last Ronin" is posted as "Teenage Mutant Ninja Turtles - The Last Ronin", and CLU
#    found nothing for #2-#5 under the short name.
ALIASES_SEARCHED = (
    "aliases-searched",
    "    queries = _build_queries(series_name, issue_num)\n",
    "    queries = _build_queries(series_name, issue_num)\n"
    "    # Skynet patch: the series' search aliases are searched too.\n"
    "    for _alias in series_aliases or []:\n"
    '        queries += [q for q in _build_queries(" ".join(_alias.split()), issue_num) if q not in queries]\n',
)

# 8. Filing waits while CLU is still converting a CBR in TARGET: it converts after the move into
#    TARGET, and a file filed mid-conversion stayed a CBR while its CBZ was orphaned in TARGET.
FILE_AFTER_CONVERSION = (
    "file-after-conversion",
    "    # Load rename pattern\n    enabled, pattern = load_custom_rename_config()\n",
    "    # Skynet patch: wait (at most 10 minutes) while a CBR that just arrived in TARGET, or a\n"
    "    # conversion's .temp_ folder, is still fresh, so a CBR is filed as its CBZ.\n"
    "    for _ in range(120):\n"
    "        _now = time.time()\n"
    "        try:\n"
    "            _busy = any(\n"
    "                (e.name.startswith('.temp_') or e.name.lower().endswith(('.cbr', '.rar')))\n"
    "                and _now - max(e.stat().st_mtime, e.stat().st_ctime) < 120\n"
    "                for e in os.scandir(target_folder)\n"
    "            )\n"
    "        except OSError:\n"
    "            _busy = False\n"
    "        if not _busy:\n"
    "            break\n"
    "        time.sleep(5)\n"
    "\n"
    "    # Load rename pattern\n    enabled, pattern = load_custom_rename_config()\n",
)

# 9. A series' search aliases are filled from ComicVine (the local copy), on subscribing and before
#    the scheduled search first searches it (a series mapped any other way): its volume's name when
#    it differs from Metron's, and its aliases. Each name is offered once, so one deleted on the
#    series page stays deleted. ComicVine lists "Teenage Mutant Ninja Turtles: The Last Ronin" for
#    Metron's "TMNT: The Last Ronin", the name the releases are posted under.
SEED_ALIASES = (
    "aliases-from-comicvine",
    "        save_series_mapping(series, path)\n"
    '        app_logger.info(f"Subscribed series {series_id} to {path}")\n',
    "        save_series_mapping(series, path)\n"
    '        app_logger.info(f"Subscribed series {series_id} to {path}")\n'
    "        _skynet_seed_aliases(series)\n",
)
SEED_ALIASES_HELPER = (
    "aliases-from-comicvine",
    '@series_bp.route("/api/series/<int:series_id>/subscribe", methods=["POST"])\n'
    "def subscribe_series(series_id):\n",
    '''_SKYNET_OFFERED_FILE = "/config/skynet_offered_aliases.json"
_skynet_offered_lock = threading.Lock()


def _skynet_seed_aliases(series):
    """Skynet patch: ComicVine's name and aliases for the series' volume, added to its aliases;
    each only once (kept by series id), so one deleted on the series page stays deleted."""
    try:
        import sqlite3

        from models.comicvine_sqlite import get_connection_params
        from models.getcomics import get_series_aliases, update_series_aliases

        name, cv_id = series.get("name") or "", series.get("cv_id")
        db = (get_connection_params() or {}).get("database_path")
        if not (name and cv_id and db and os.path.exists(db)):
            return
        with _skynet_offered_lock:
            try:
                with open(_SKYNET_OFFERED_FILE, encoding="utf-8") as f:
                    offered_all = json.load(f)
            except (OSError, ValueError):
                offered_all = {}
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            row = con.execute(
                "SELECT name, aliases FROM cv_volume WHERE id = ?", (int(cv_id),)
            ).fetchone()
            con.close()
            if not row:
                return
            found = [a for a in (row[1] or "").splitlines() + [row[0] or ""] if a.strip()]
            clean = lambda a: " ".join(a.replace(",", " ").replace(":", " ").split())
            norm = lambda a: clean(a.lower().replace("-", " "))
            offered = set(offered_all.get(str(series["id"]), []))
            if {norm(a) for a in found} <= offered:
                return
            current = [a for a in (get_series_aliases(name) or "").split(",") if a.strip()]
            have = {norm(a) for a in current} | {norm(name)} | offered
            new = [clean(a) for a in found if norm(a) not in have]
            if new:
                update_series_aliases(name, ",".join(current + new))
                app_logger.info(f"Skynet patch: search aliases for {name} from ComicVine: {new}")
            offered_all[str(series["id"])] = sorted(offered | {norm(a) for a in found})
            with open(_SKYNET_OFFERED_FILE, "w", encoding="utf-8") as f:
                json.dump(offered_all, f)
    except Exception as e:
        app_logger.warning(f"Skynet patch: no ComicVine aliases for {series.get('name')}: {e}")


@series_bp.route("/api/series/<int:series_id>/subscribe", methods=["POST"])
def subscribe_series(series_id):
''',
)
SEED_ALIASES_BEFORE_SEARCH = (
    "aliases-from-comicvine",
    "            series_aliases = get_series_alias_list(series_name)\n",
    "            try:  # Skynet patch: ComicVine's names for the series first (routes/series.py)\n"
    "                from routes.series import _skynet_seed_aliases\n"
    "\n"
    "                _skynet_seed_aliases(series)\n"
    "            except ImportError:\n"
    "                pass\n"
    "            series_aliases = get_series_alias_list(series_name)\n",
)

# 10. An issue's search window searches and scores Usenet under the series' aliases too, as the
#     scheduled search does: it searched "TMNT: The Last Ronin" alone and showed nothing posted as
#     "Teenage Mutant Ninja Turtles - The Last Ronin".
ALIASES_IN_SEARCH_WINDOW = (
    "aliases-in-search-window",
    "            res = search_usenet_for_issue(\n"
    "                series, issue,\n"
    "                issue_year=_as_year(data.get('issue_year')),\n"
    "                series_volume=data.get('series_volume'),\n"
    "            )\n",
    "            # Skynet patch: the series' search aliases, as the scheduled search uses them.\n"
    "            from models.getcomics import get_series_alias_list\n"
    "\n"
    "            res = search_usenet_for_issue(\n"
    "                series, issue,\n"
    "                issue_year=_as_year(data.get('issue_year')),\n"
    "                series_volume=data.get('series_volume'),\n"
    "                series_aliases=get_series_alias_list(series),\n"
    "            )\n",
)

# 11. A format keyword (TPB, one-shot, omnibus, ...) counts as a whole word in the collected-edition
#     check, as CLU's title parser already reads it: the "os" of one-shot inside "Lost Years" took 30
#     points off every post of The Last Ronin - The Lost Years, and the Usenet ones below acceptance.
FORMAT_WORDS = (
    "format-words-whole",
    "    for kw in get_format_variants() + [r'\\bcompendium\\b',\n",
    "    # Skynet patch: a format keyword as a whole word, as the title parser reads it.\n"
    "    for kw in [rf'(?<![a-zA-Z]){_keyword_pattern(v)}\\b' for v in get_format_variants()] + [r'\\bcompendium\\b',\n",
)

# 12. The scheduled search dates an issue by its cover year, the year its posts carry: it used the
#     on-sale year, and took 30 points off any other, so an issue on sale in October to December was
#     rejected (Ultimate Spider-Man (2000) #15, on sale 2001-11, cover 2002-01, posted as "(2002)").
COVER_YEAR = (
    "cover-year",
    '                    "issue_year": int(store_date[:4]) if store_date else series_year,\n',
    "                    # Skynet patch: the cover year, as posts carry it.\n"
    '                    "issue_year": int((issue.get("cover_date") or store_date)[:4]) if store_date else series_year,\n',
)

# 13. A scene-style post name ("Absolute.Batman.001.2024.Webrip.The.Last.Kryptonian-DCP") is read
#     with spaces, as the scorer needs; a decimal issue ("001.5") keeps its dot. CLU matched none.
SCENE_NAMES = (
    "scene-names",
    "def _make_filename(series_name, issue_num, chosen_result, tier) -> str:\n",
    '''def _skynet_scene_spaces(title):
    """Skynet patch: a name with no spaces and dots between its words reads with spaces."""
    import re

    if " " in title or title.count(".") < 2:
        return title
    return re.sub(r"(?<!\\d)\\.|\\.(?!\\d{1,2}(?!\\d))", " ", title)


def _make_filename(series_name, issue_num, chosen_result, tier) -> str:
''',
)

FIXES = {
    USENET: [
        FILE_AFTER_IMPORT,
        FILE_AFTER_IMPORT_HELPER,
        BIGGER_WINS,
        FAILOVER_HELPERS,
        FAILOVER_REMEMBER,
        FAILOVER_ON_FAILED,
        FAILOVER_SCORING_TITLE,
        FAILOVER_SKIP_FAILED,
        ALIASES_SEARCHED,
        SCENE_NAMES,
    ],
    APP: [
        UNDATED_SEARCHED,
        NAME_FROM_SERIES,
        NAME_FROM_SERIES_HELPER,
        FILE_AFTER_CONVERSION,
        SEED_ALIASES_BEFORE_SEARCH,
        COVER_YEAR,
    ],
    SCORER: [HYPHEN_IS_SPACE, FORMAT_WORDS],
    SERIES_ROUTES: [SEED_ALIASES, SEED_ALIASES_HELPER],
    DOWNLOAD_ROUTES: [ALIASES_IN_SEARCH_WINDOW],
}


def patch(path, fixes):
    with open(path, encoding="utf-8") as f:
        text = original = f.read()
    for name, old, new in fixes:
        if new in text:
            continue  # applied at an earlier start of this container
        if text.count(old) != 1:
            print(f"clu-patch: {path}: {name} doesn't match CLU's code; the file runs as shipped")
            return
        text = text.replace(old, new)
    names = ", ".join(dict.fromkeys(name for name, _, _ in fixes))
    if text == original:
        print(f"clu-patch: {path}: {names} (already applied)")
        return
    try:
        compile(text, path, "exec")
    except SyntaxError as e:
        print(f"clu-patch: {path}: the patched code doesn't compile ({e}); the file runs as shipped")
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"clu-patch: {path}: {names}")


for path, fixes in FIXES.items():
    try:
        patch(path, fixes)
    except Exception as e:
        print(f"clu-patch: {path}: {e}; the file runs as shipped")
