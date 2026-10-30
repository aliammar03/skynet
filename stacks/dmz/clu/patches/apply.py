"""Four fixes to CLU v7.0 until CLU ships its own (stacks/dmz/clu/README.md → Patches).

The container runs this as root before CLU's entrypoint. Each fix replaces one exact piece of
CLU's code. A file is rewritten only when all its fixes apply and the result compiles; when CLU's
code has changed (an update), the fix is reported in the log and that file runs as shipped.
"""

import os

USENET = "/app/models/usenet.py"
APP = "/app/app.py"

# 1. A Usenet download is filed like any other: CLU runs its filing pass once WATCH empties after
#    a direct download, and never after a Usenet import.
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
        for _ in range(90):  # 15 minutes
            time.sleep(10)
            busy = False
            for _root, dirs, files in os.walk(watch):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                if any(not f.startswith((".", "_")) for f in files):
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

FIXES = {
    USENET: [FILE_AFTER_IMPORT, FILE_AFTER_IMPORT_HELPER, BIGGER_WINS],
    APP: [UNDATED_SEARCHED, NAME_FROM_SERIES, NAME_FROM_SERIES_HELPER],
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
