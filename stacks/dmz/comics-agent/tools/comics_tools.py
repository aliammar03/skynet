"""comics-tools (skynetv2.md → P8 → The comics agent, D17): the comics agent's hands.

A fixed list of verbs over CLU, SABnzbd, Komga and Uchiyomi, for the agent in `comics-agent`, which
reaches this on the stack's `backend` and holds no key: every key is here. `GET /` lists the verbs;
anything else is refused. Grabs are capped at 360 an hour, and a trash waits for Ali's ✅ in #comics,
read back from Discord. Answers carry no URL (an indexer's NZB link holds its API key) and no key.
Python's standard library only.
"""
import collections
import concurrent.futures
import http.server
import json
import os
import re
import secrets
import socket
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

E = os.environ
CLU, SAB = "http://clu:5577", "http://sabnzbd:8080"
KOMGA, UCHIYOMI = "https://komga.aliammar.net", "https://uchiyomi.aliammar.net"  # through caddy-apps on edge
DISCORD = "https://discord.com/api/v10"
AUTH = {
    KOMGA: {"X-API-Key": E.get("KOMGA_API_KEY", "")},
    UCHIYOMI: {"Authorization": "Bearer " + E.get("UCHIYOMI_TOKEN", "")},
    DISCORD: {"Authorization": "Bot " + E.get("DISCORD_BOT_TOKEN", "")},
}
GRABS_PER_HOUR = 360
LOCK = threading.Lock()
SERIES, RESULTS, PROPOSALS, GRABS, ME = {}, {}, {}, collections.deque(), {}
URLS = re.compile(r"\b(?:https?|nntps?)://[^\s\"'<>]+")
IMAGES = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".jxl")


class Refused(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def call(method, url, body=None, timeout=120, raw=False):
    base = next((b for b in AUTH if url.startswith(b)), None)
    headers = {"User-Agent": "DiscordBot (https://github.com/aliammar03/skynet, 1)", **AUTH.get(base, {})}
    if body is not None:  # Uchiyomi refuses a JSON content type without a body
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, None if body is None else json.dumps(body).encode(), headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        raise Refused(e.code, e.read().decode("utf-8", "replace")[:400]) from None
    if raw == "bytes":  # an image
        return data
    return data.decode("utf-8", "replace") if raw else (json.loads(data) if data.strip() else None)


def sab_key():
    """SABnzbd's API key, from its own settings (mounted read-only); a line precedes its first section."""
    section = None
    for line in open("/sabnzbd/sabnzbd.ini", encoding="utf-8", errors="replace"):
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif section == "misc" and line.partition("=")[0].strip() == "api_key":
            return line.partition("=")[2].strip()
    raise Refused(500, "no api_key in sabnzbd.ini")


def scrub(text):
    keys = [E.get(k) for k in ("KOMGA_API_KEY", "UCHIYOMI_TOKEN", "DISCORD_BOT_TOKEN")]
    try:
        keys.append(sab_key())
    except (OSError, Refused):
        pass
    for key in filter(None, keys):
        text = text.replace(key, "<key>")
    return URLS.sub("<url>", text)


VERBS = {}


def verb(method, path, doc):
    def add(fn):
        VERBS[(method, path)] = (fn, doc)
        return fn
    return add


def need(a, *names):
    missing = [n for n in names if a.get(n) in (None, "", [])]
    if missing:
        raise Refused(400, "missing: " + ", ".join(missing))
    return [a[n] for n in names]


def q(text):
    return urllib.parse.quote(str(text), safe="")


# --- comics: CLU -----------------------------------------------------------------------------------

@verb("GET", "/comics/find", "q → Metron's series of that name (id, name, year_began, publisher, issue_count, subscribed)")
def comics_find(a):
    found = call("GET", f"{CLU}/api/series/search?q={q(need(a, 'q')[0])}")["series"]
    with LOCK:
        SERIES.update({s["id"]: s for s in found})
    keys = ("id", "name", "volume", "year_began", "publisher", "issue_count", "status", "subscribed")
    return [{k: s.get(k) for k in keys} for s in found]


@verb("POST", "/comics/subscribe", "series_id (from find) → CLU follows it, filed in <publisher>/<name> (<year>)")
def comics_subscribe(a):
    sid = int(need(a, "series_id")[0])
    s = SERIES.get(sid) or {}
    if not s:
        raise Refused(400, "find the series first")
    call("GET", f"{CLU}/series/s-{sid}", raw=True)  # CLU caches the series and its issues from Metron
    # Its folder pattern (CLU's README → Setup), {publisher}/{series_name} ({start_year}), from CLU's own
    # record of the name: Metron's search answers "Watchmen (1986)". CLU cleans each folder name itself.
    name = call("GET", f"{CLU}/api/series/{sid}/search-aliases")["series_name"]
    folder = re.sub(r"\s*\(\s*\)", "", f"{name} ({s.get('year_began') or ''})")
    lib = call("GET", f"{CLU}/api/libraries")["libraries"][0]["path"]
    return call("POST", f"{CLU}/api/series/{sid}/subscribe", {"path": f"{lib}/{s.get('publisher') or 'Unknown'}/{folder}"})


@verb("GET", "/comics/aliases", "series_id → the names CLU searches Usenet under, besides the series' own")
def comics_aliases(a):
    r = call("GET", f"{CLU}/api/series/{int(need(a, 'series_id')[0])}/search-aliases")
    cur = r.get("current_aliases") or ""
    return {"series": r["series_name"], "aliases": [x.strip() for x in (cur.split(",") if isinstance(cur, str) else cur) if x.strip()],
            "candidates": r.get("candidate_aliases")}


@verb("POST", "/comics/aliases", "series_id, aliases: [names] → replaces the series' aliases")
def comics_set_aliases(a):
    sid, names = need(a, "series_id", "aliases")
    return call("PUT", f"{CLU}/api/series/{int(sid)}/search-aliases", {"aliases": ",".join(n.replace(",", " ") for n in names)})


@verb("POST", "/comics/check", "series_id → CLU searches and grabs that series' missing issues (op_id; see /comics/op)")
def comics_check(a):
    return call("POST", f"{CLU}/api/series/{int(need(a, 'series_id')[0])}/check-missing")


@verb("GET", "/comics/op", "id (op_id) → a CLU operation's progress; null when it has finished")
def comics_op(a):
    return call("GET", f"{CLU}/api/operation/{q(need(a, 'id')[0])}").get("operation")


@verb("POST", "/comics/skip", "series_id, issues: [numbers], [undo] → CLU skips those issues (off the wanted list: an arc's edges), or wants them again")
def comics_skip(a):
    sid, issues = int(need(a, "series_id")[0]), [str(n) for n in need(a, "issues")[0]]
    if a.get("undo"):
        return call("DELETE", f"{CLU}/api/series/{sid}/bulk-manual-status", {"issue_numbers": issues})
    return call("POST", f"{CLU}/api/series/{sid}/bulk-manual-status", {"issue_numbers": issues, "status": "skipped", "notes": "outside an arc (comics agent)"})


@verb("POST", "/comics/follow", "series_id, follow: true|false → whether CLU's nightly search looks for the series' new and missing issues")
def comics_follow(a):
    sid, follow = int(need(a, "series_id")[0]), a.get("follow")
    if follow not in (True, False, "true", "false"):
        raise Refused(400, "follow: true or false")
    return call("POST", f"{CLU}/api/series/{sid}/monitored", {"enabled": follow in (True, "true")})


def collection(sid):
    return call("GET", f"{CLU}/api/series/{sid}/check-collection")


@verb("GET", "/comics/wanted", "[series_id] → issues on sale, not in the library, not marked by hand (CLU's own rule)")
def comics_wanted(a):
    issues = call("GET", f"{CLU}/api/wanted")["issues"]  # every issue on sale of a followed series
    out = []
    for sid in sorted({i["series_id"] for i in issues if not a.get("series_id") or i["series_id"] == int(a["series_id"])}):
        c = collection(sid)
        for i in (i for i in issues if i["series_id"] == sid):
            n = str(i["number"])
            if not c["issue_status"].get(n, {}).get("found") and n not in c["manual_status"]:
                out.append({k: i[k] for k in ("series_id", "series_name", "series_volume", "number", "name", "cover_date", "store_date")})
    return out


@verb("GET", "/comics/series", "series_id → each issue: its file in the library, or missing")
def comics_series(a):
    c = collection(int(need(a, "series_id")[0]))
    st = c["issue_status"]
    return {"found": c["found_count"], "total": c["total_count"], "manual": c["manual_status"],
            "issues": {n: (v.get("file_path") if v.get("found") else None) for n, v in st.items()}}


@verb("POST", "/comics/search", "series, issue, [year (cover year)], [volume], [limit 25] → Usenet posts, scored by CLU (ids)")
def comics_search(a):
    series, issue = need(a, "series", "issue")
    r = call("POST", f"{CLU}/api/usenet/search", {"series": series, "issue": str(issue), "issue_year": a.get("year"),
                                                  "series_volume": a.get("volume")}, timeout=300)
    ranked = sorted(r["results"], key=lambda x: (-(x.get("score") or 0), -(x.get("size") or 0)))
    out = []
    with LOCK:
        for x in ranked[: int(a.get("limit") or 25)]:
            rid = "r" + secrets.token_hex(3)
            RESULTS[rid] = {**x, "series": series, "issue": str(issue)}
            out.append({"id": rid, "title": x["title"], "mb": round((x.get("size") or 0) / 1e6, 1), "score": x.get("score"),
                        "decision": x.get("decision"), "indexer": x.get("indexer_name")})
        while len(RESULTS) > 5000:
            RESULTS.pop(next(iter(RESULTS)))
    return {"total": len(ranked), "errors": r.get("errors"), "results": out}


@verb("POST", "/comics/grab", "result (an id from search) → SABnzbd downloads it for CLU, which files it if wanted")
def comics_grab(a):
    x = RESULTS.get(need(a, "result")[0])
    if not x:
        raise Refused(404, "no such result; search again")
    with LOCK:
        now = time.time()
        while GRABS and GRABS[0] < now - 3600:
            GRABS.popleft()
        if len(GRABS) >= GRABS_PER_HOUR:
            raise Refused(429, f"{GRABS_PER_HOUR} grabs in the last hour; wait")
        GRABS.append(now)
    name = re.sub(r"[/\\#]", " ", f"{x['series']} {x['issue']}").strip() + ".cbz"
    return call("POST", f"{CLU}/api/usenet/grab", {"nzb_url": x["nzb_url"], "filename": name, "series": x["series"], "issue": x["issue"]})


@verb("GET", "/comics/downloads", "→ CLU's latest Usenet downloads (each with the post it took), and the files waiting in processed/ to be filed")
def comics_downloads(a):
    d = call("GET", f"{CLU}/api/usenet/downloads")["downloads"][-int(a.get("limit") or 30):]
    keys = ("filename", "series", "issue", "status", "stage", "percent", "error")
    # skynet_post: the post's title and size, kept by CLU's patch 6; the release a report names.
    return {"downloads": [{**{k: x.get(k) for k in keys}, "post": (x.get("skynet_post") or [None])[0]} for x in d],
            "processed": sorted(os.listdir("/downloads/processed")), "temp": sorted(os.listdir("/downloads/temp"))}


@verb("POST", "/comics/file", "→ CLU files what waits in processed/ now, for issues it still wants")
def comics_file(a):
    return call("POST", f"{CLU}/api/scan-downloads", timeout=600)


@verb("POST", "/comics/cover", "series_id → CLU makes the series' cover, folder.png beside its issues: its first issue's cover (or the one Ali pinned in CLU); Komga shows it after /rescan")
def comics_cover(a):
    st = collection(int(need(a, "series_id")[0]))["issue_status"]
    files = [v["file_path"] for v in st.values() if v.get("found") and v.get("file_path")]
    if not files:
        raise Refused(409, "no issue of that series is filed yet")
    folder = os.path.dirname(files[0])
    r = call("POST", f"{CLU}/api/generate-folder-thumbnail", {"folder_path": folder}, timeout=120)
    return {"success": bool(r.get("success")), "cover": r.get("thumbnail_path") or f"{folder}/folder.png"}


KOMGA_CLU = "/books/Comics/clu/"  # CLU's library (/data here) as Komga sees it


@verb("POST", "/comics/dates", "→ each filed issue's release date in Komga set to the day it went on sale (Metron's, through CLU) and locked; an issue Metron has no such day for keeps its cover month, and a date already locked (set before, or by hand) stays")
def comics_dates(a):
    days = {d["path"]: d["store_date"] for d in call("GET", f"{CLU}/api/skynet/issue-dates") if d.get("store_date")}
    lib = next(x["id"] for x in call("GET", f"{KOMGA}/api/v1/libraries") if x["name"] == "Comics")
    books = call("POST", f"{KOMGA}/api/v1/books/list?unpaged=true", {"condition": {"libraryId": {"operator": "is", "value": lib}}})["content"]
    out = collections.Counter()
    for b in books:
        day = days.get("/data/" + b["url"][len(KOMGA_CLU):]) if b["url"].startswith(KOMGA_CLU) else None
        if b["metadata"].get("releaseDateLock"):
            out["locked"] += 1
        elif not day:
            out["cover month"] += 1
        else:
            call("PATCH", f"{KOMGA}/api/v1/books/{q(b['id'])}/metadata", {"releaseDate": day, "releaseDateLock": True})
            out["set"] += 1
    return dict(out)


def inside(path):
    real = os.path.realpath(path)
    if not real.startswith(("/data/", "/downloads/", "/manga/")):
        raise Refused(403, "only CLU's library (/data) and downloads (/downloads), and the manga (/manga)")
    return real


def dims(head):
    """(width, height) from an image's first bytes: JPEG, PNG, GIF or WebP."""
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", head[16:24])
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", head[6:10])
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        kind = head[12:16]
        if kind == b"VP8 ":
            return tuple(v & 0x3FFF for v in struct.unpack("<HH", head[26:30]))
        if kind == b"VP8L":
            b = int.from_bytes(head[21:25], "little")
            return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
        if kind == b"VP8X":
            return int.from_bytes(head[24:27], "little") + 1, int.from_bytes(head[27:30], "little") + 1
    i = 2 if head[:2] == b"\xff\xd8" else len(head)
    while i + 9 < len(head):  # JPEG: walk its segments to the frame header
        marker = head[i + 1]
        if head[i] != 0xFF or marker == 0xFF:
            i += 1
        elif marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
            i += 2
        elif 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", head[i + 5:i + 9])
            return w, h
        else:
            i += 2 + int.from_bytes(head[i + 2:i + 4], "big")
    return None


@verb("GET", "/comics/inspect", "path (a file from series or downloads, or a chapter in manga/status' folder) → format, pages, page sizes, ComicInfo")
def comics_inspect(a):
    path = inside(need(a, "path")[0])
    out = {"path": path, "mb": round(os.path.getsize(path) / 1e6, 1)}
    with open(path, "rb") as f:
        magic = f.read(4)
    if magic[:2] != b"PK":
        return {**out, "format": "rar" if magic == b"Rar!" else magic.hex(), "note": "not a CBZ; CLU converts CBR to CBZ when it files"}
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        pages = sorted(n for n in names if n.lower().endswith(IMAGES))
        sample = sorted({0, 1, len(pages) // 2, len(pages) - 1} & set(range(len(pages))))
        sizes = {}
        for i in sample:
            with z.open(pages[i]) as f:
                sizes[f"{i + 1}: {pages[i]}"] = dims(f.read(262144))
        info = next((n for n in names if n.lower().endswith("comicinfo.xml")), None)
        tags = "Series|Number|Volume|Year|Month|Title|Format|Notes|PageCount|Publisher|ScanInformation"
        ci = dict(re.findall(rf"<({tags})>([^<]*)</", z.read(info).decode("utf-8", "replace"))) if info else None
    return {**out, "format": "zip", "pages": len(pages), "page_sizes": sizes, "other_files": [n for n in names if n not in pages][:10],
            "comicinfo": ci}


IDLE = 24  # hours an unpacked issue sits untouched before it's put back: before that, Ali may be editing it


def unpacked_at(folder):
    """The issue CLU's editor left unpacked into `folder`, or None. Its Edit renames <issue>.cbz to
    <issue>.zip and unpacks the pages into <issue>_folder; only its Save packs them back, and it has no
    Cancel. `edited`: the pages there differ from the issue's (a crop, a page deleted)."""
    base = folder[: -len("_folder")]
    if not folder.endswith("_folder") or not os.path.isdir(folder) or not os.path.isfile(base + ".zip") \
            or os.path.exists(base + ".cbz"):
        return None
    touched, pages = [], {}
    for root, _, files in os.walk(folder):
        touched.append(os.path.getmtime(root))
        for f in files:
            p = os.path.join(root, f)
            touched.append(os.path.getmtime(p))
            if f.lower().endswith(IMAGES):
                pages[os.path.relpath(p, folder)] = os.path.getsize(p)
    with zipfile.ZipFile(base + ".zip") as z:
        original = {i.filename: i.file_size for i in z.infolist() if i.filename.lower().endswith(IMAGES)}
    return {"issue": base + ".cbz", "path": folder, "idle_hours": round((time.time() - max(touched)) / 3600, 1),
            "edited": pages != original}


@verb("GET", "/comics/unpacked", "→ issues CLU's editor left unpacked in the library (Ali opened Edit and never saved): each one's path, how many hours it has sat untouched, whether its pages were edited")
def comics_unpacked(a):
    out = []
    for root, dirs, _ in os.walk("/data"):
        out += filter(None, (unpacked_at(os.path.join(root, d)) for d in dirs if d.endswith("_folder")))
        dirs[:] = [d for d in dirs if not d.endswith("_folder")]  # not into the pages
    return out


@verb("POST", "/comics/unpacked", f"path (from GET) → the issue back as it was (CLU renames it back to .cbz), the unpacked pages, edits and all, in CLU's trash; only one untouched for {IDLE} hours. Then /rescan with deep")
def comics_put_back(a):
    folder = os.path.realpath(need(a, "path")[0])
    u = unpacked_at(folder) if folder.startswith("/data/") else None
    if not u:
        raise Refused(404, "not an issue CLU's editor left unpacked in the library: GET /comics/unpacked")
    if u["idle_hours"] < IDLE:
        raise Refused(409, f"touched {u['idle_hours']} hours ago: Ali may still be editing it")
    call("POST", f"{CLU}/rename", {"old": folder[: -len("_folder")] + ".zip", "new": u["issue"]})  # the issue first
    trashed = call("POST", f"{CLU}/api/delete-multiple", {"targets": [folder]})["results"][0]
    return {"issue": u["issue"], "edited": u["edited"], "pages": "in CLU's trash" if trashed.get("success") else trashed.get("error")}


@verb("POST", "/comics/trash", "paths: [strays in /downloads/processed] → CLU's trash now; series_id + issues: [numbers] | paths: [other files] → a proposal for Ali's ✅; then code + the ✅'s message_id, thread_id, channel_id → CLU's trash")
def comics_trash(a):
    if a.get("code"):
        return confirm(a)
    acts, said, strays = [], [], []
    if a.get("paths"):
        for path in a["paths"]:
            real = inside(path)
            act = lambda real=real: call("POST", f"{CLU}/api/delete-multiple", {"targets": [real]})
            if real.startswith("/downloads/processed/"):  # a stray CLU won't file: no ✅ (Ali, 2026-11-04)
                strays.append((real, act))
            else:
                acts.append(act)
                said.append(real)
    if a.get("issues"):
        sid = int(need(a, "series_id")[0])
        st = collection(sid)["issue_status"]
        for n in map(str, a["issues"]):
            path = (st.get(n) or {}).get("file_path")
            if not path:
                raise Refused(404, f"#{n} has no file in the library")
            acts.append(lambda n=n, path=path: call("POST", f"{CLU}/api/series/{sid}/issue/{q(n)}/delete-file", {"path": path}))
            said.append(f"{path} (back on the wanted list)")
    if not acts and not strays:
        raise Refused(400, "missing: paths, or series_id and issues")
    trashed = [{"path": real, "result": act()} for real, act in strays]  # after every check above
    if not acts:
        return {"trashed": trashed}
    return {**propose("to CLU's trash", said, acts), **({"trashed": trashed} if trashed else {})}


def propose(what, said, acts):
    """A removal waits for Ali: a code and the post that names it, kept a week (not across a restart)."""
    code = secrets.token_hex(3).upper()
    with LOCK:
        PROPOSALS[code] = (time.time() + 7 * 86400, said, acts)
    return {"code": code, "post": f"🗑️ {code}: {what} —\n" + "\n".join(f"• {s}" for s in said) + "\nReact ✅ to approve.",
            "next": "post `post` as its own message; when Ali's ✅ arrives, call again with code and the ✅'s message_id, thread_id and channel_id"}


def confirm(a):
    """The ✅'s sender context (its message_id, and thread_id or else channel_id) → the proposal's acts."""
    code, message = need(a, "code", "message_id")
    channel = a.get("thread_id") or need(a, "channel_id")[0]
    with LOCK:
        p = PROPOSALS.get(code)
    if not p or p[0] < time.time():
        raise Refused(404, "no such proposal (they last a week, and not across a restart): propose again")
    approved(code, channel, message)
    with LOCK:
        PROPOSALS.pop(code, None)
    return [act() for act in p[2]]


def approved(code, channel, message):
    """Ali's ✅ for `code`: his reaction on the agent's proposal, or his ✅ reply to it, in #comics or a thread of it."""
    ali, home = E["COMICS_ALI"], E["COMICS_CHANNEL"]
    where = call("GET", f"{DISCORD}/channels/{q(channel)}")
    if home not in (where.get("id"), where.get("parent_id")):
        raise Refused(403, "not in #comics")
    msg = call("GET", f"{DISCORD}/channels/{q(channel)}/messages/{q(message)}")
    if msg["author"]["id"] == ali and "✅" in msg["content"] and msg.get("message_reference"):
        ref = msg["message_reference"]
        msg = call("GET", f"{DISCORD}/channels/{q(ref.get('channel_id', channel))}/messages/{q(ref['message_id'])}")
    elif ali not in {u["id"] for u in call("GET", f"{DISCORD}/channels/{q(channel)}/messages/{q(message)}/reactions/%E2%9C%85")}:
        raise Refused(403, "no ✅ from Ali on that message")
    if not ME:
        ME.update(call("GET", f"{DISCORD}/users/@me"))
    if msg["author"]["id"] != ME["id"] or code not in msg["content"]:
        raise Refused(403, "that message is not the agent's proposal " + code)


@verb("GET", "/sab/queue", "→ SABnzbd's queue")
def sab_queue(a):
    r = call("GET", f"{SAB}/api?mode=queue&output=json&apikey={sab_key()}")["queue"]
    keys = ("filename", "status", "percentage", "mb", "mbleft", "timeleft", "cat")
    return {"status": r.get("status"), "speed": r.get("speed"), "slots": [{k: s.get(k) for k in keys} for s in r.get("slots", [])]}


@verb("GET", "/sab/history", "[limit 20], [failed=1] → SABnzbd's finished jobs; a failed one says why")
def sab_history(a):
    extra = f"&limit={int(a.get('limit') or 20)}" + ("&status=Failed" if a.get("failed") else "")
    r = call("GET", f"{SAB}/api?mode=history&output=json&apikey={sab_key()}{extra}")["history"]
    keys = ("name", "status", "fail_message", "size", "completed", "category", "storage")
    return [{k: s.get(k) for k in keys} for s in r.get("slots", [])]


# --- manga: Uchiyomi ------------------------------------------------------------------------------

# adult=1: Uchiyomi leaves out every source whose extension calls itself 18+ (most of the big manga
# sites, for the adult titles they also carry), and the series added from them, unless asked.
@verb("GET", "/manga/search", "q → the best match on each of Uchiyomi's sources (source, source_id, title, lang, inLibrary)")
def manga_search(a):
    hits = call("GET", f"{UCHIYOMI}/api/sources/find?q={q(need(a, 'q')[0])}&adult=1", timeout=180)["content"]
    return [{"source": h["source"], "name": h.get("name"), "source_id": h["sourceId"], "title": h["title"],
             "lang": h.get("lang"), "inLibrary": h.get("inLibrary")} for h in hits]


@verb("GET", "/manga/detail", "source, source_id → that source's copy: status, chapter count, first, last, groups")
def manga_detail(a):
    src, sid = need(a, "source", "source_id")
    d = call("GET", f"{UCHIYOMI}/api/sources/detail?source={q(src)}&sourceId={q(sid)}", timeout=180)
    return {**{k: d.get(k) for k in ("title", "author", "status", "count", "first", "last", "versions", "genres")},
            "numbering": (d.get("numbering") or {}).get("applied"),
            "groups": [{k: g.get(k) for k in ("name", "releases", "first", "last", "langs")} for g in d.get("groups", [])]}


def failed(e):
    return f"{getattr(e, 'status', type(e).__name__)} {str(e)[:120]}"


def number(n):
    return str(int(n)) if n == int(n) else str(n)


def listing(hit):
    """A source's chapters as an add would take them, one copy a number with its translator
    (Uchiyomi's preview: nothing added), or why not."""
    try:
        return call("GET", f"{UCHIYOMI}/api/sources/preview?source={q(hit['source'])}&sourceId={q(hit['source_id'])}", timeout=60)["content"]
    except (Refused, OSError, KeyError) as e:
        return failed(e)


def copy_of(hit, listed, numbers):
    """One source's copy for manga/compare: the work, who translates which chapters, and two interior
    pages of each sampled chapter read from the source, each page's pixel size and KB."""
    src, sid = hit["source"], hit["source_id"]
    out, start = {"name": hit.get("name"), "source": src, "source_id": sid, "title": hit.get("title")}, time.monotonic()
    try:
        d = manga_detail({"source": src, "source_id": sid})
        out.update(author=d.get("author"), status=d.get("status"))
        if isinstance(listed, str):
            return {**out, "error": listed, "seconds": round(time.monotonic() - start, 1)}
        nums = {c["number"] for c in listed}
        out.update(chapters=len(nums), first=min(nums, default=None), last=max(nums, default=None), translators={})
        for c in listed:
            r = out["translators"].setdefault(c.get("scanlator") or "?", [c["number"], c["number"]])
            r[:] = [min(r[0], c["number"]), max(r[1], c["number"])]
        out["pages"] = {}
        for n in numbers:
            if n not in nums:
                out["pages"][number(n)] = "not listed"
                continue
            at = f"source={q(src)}&sourceId={q(sid)}&number={number(n)}"
            count = call("GET", f"{UCHIYOMI}/api/sources/preview/pages?{at}", timeout=60)["count"]
            pages = []
            for i in sorted({count // 3, 2 * count // 3}):
                data = call("GET", f"{UCHIYOMI}/img/sources/preview?{at}&i={i}", timeout=60, raw="bytes")
                pages.append({"px": dims(data[:262144]), "kb": len(data) // 1024})
            out["pages"][number(n)] = {"of": count, "sampled": pages}
    except (Refused, OSError, KeyError) as e:
        out["error"] = failed(e)
    out["seconds"] = round(time.monotonic() - start, 1)
    return out


@verb("GET", "/manga/compare", "q, [numbers: chapters to sample, comma-separated; default the run's middle and last] → each source's copy side by side: the work (title, author, status), its chapters and who translates which, and two pages of each sampled chapter read straight from the source (pixel size, KB); nothing is added. For a series not in the library yet")
def manga_compare(a):
    try:
        numbers = [float(x) for x in str(a.get("numbers") or "").replace(" ", "").split(",") if x]
    except ValueError:
        raise Refused(400, "numbers: chapter numbers, comma-separated") from None
    hits = manga_search({"q": need(a, "q")[0]})
    if not hits:
        return []
    with concurrent.futures.ThreadPoolExecutor(len(hits)) as pool:
        lists = list(pool.map(listing, hits))
        if not numbers:  # the middle and the last of the run, as most sources list it
            lasts = sorted(max(c["number"] for c in x) for x in lists if isinstance(x, list) and x)
            last = lasts[len(lasts) // 2] if lasts else 1
            numbers = sorted({float(max(int(last) // 2, 1)), float(last)})
        return list(pool.map(lambda h: copy_of(h[0], h[1], numbers), zip(hits, lists)))


@verb("POST", "/manga/add", "source, source_id, [chapters: \"none\"], [follow: false] → Uchiyomi adds the series, downloads it, and follows its new chapters; \"none\" downloads nothing yet (an arc: then manga/fill its numbers)")
def manga_add(a):
    src, sid = need(a, "source", "source_id")
    body = {"source": src, "sourceId": sid, "autoUpdate": a.get("follow") not in (False, "false")}
    if a.get("chapters") == "none":  # the row and its listing, no download (Uchiyomi's chapterFrom: none)
        body["chapterFrom"] = "none"
    return call("POST", f"{UCHIYOMI}/api/sources/add", body, timeout=180)


def wiki_page(url, prop):
    """A MediaWiki page's parse (its `prop`), from its /wiki/ link: Fandom's API, then MediaWiki's own path."""
    u = urllib.parse.urlsplit(url)
    base, _, name = urllib.parse.unquote(u.path).partition("/wiki/")
    ask = urllib.parse.urlencode({"action": "parse", "page": name, "prop": prop, "format": "json", "formatversion": 2, "redirects": 1})
    for api in (f"https://{u.netloc}{base}/api.php", f"https://{u.netloc}{base}/w/api.php"):
        try:
            found = call("GET", f"{api}?{ask}", timeout=30)
        except (Refused, OSError, ValueError):
            continue
        if isinstance(found, dict) and "parse" in found:
            return found["parse"]
        break  # that API answered: the wiki has no such page
    raise Refused(404, f"no such page: {url}")


@verb("POST", "/manga/wiki", "komga_id (a manga series in Komga, from library/find), and url (its fan wiki's page for chapter 1: https://…/wiki/…1) and/or chapters (its Wikipedia list of chapters: https://en.wikipedia.org/wiki/List_of_…_chapters) → linked in Komga (Wiki, Chapters): within the hour komga-wiki fills each chapter's title, summary and release date from the fan wiki, and a chapter it has no date for gets its volume's from Wikipedia; answers what each page holds")
def manga_wiki(a):
    sid = need(a, "komga_id")[0]
    url, listing = a.get("url"), a.get("chapters")
    if not url and not listing:
        raise Refused(400, "missing: url or chapters")
    if url and (urllib.parse.urlsplit(url).scheme != "https" or not re.fullmatch(r".*?/wiki/.*?0*1", urllib.parse.unquote(urllib.parse.urlsplit(url).path))):
        raise Refused(400, "url: the wiki's page for chapter 1, https://<wiki>/wiki/<its name>1")
    if listing and not re.fullmatch(r"https://[a-z-]+\.wikipedia\.org/wiki/List_of_.+_chapters(_\(.*\))?", urllib.parse.unquote(listing).replace(" ", "_")):
        raise Refused(400, "chapters: Wikipedia's list, https://en.wikipedia.org/wiki/List_of_<series>_chapters")
    s = call("GET", f"{KOMGA}/api/v1/series/{q(sid)}")
    if call("GET", f"{KOMGA}/api/v1/libraries/{q(s['libraryId'])}").get("name") != "Manga":
        raise Refused(400, "komga_id: a series in Komga's Manga library")
    out, add = {"success": True, "series": s["metadata"].get("title") or s.get("name")}, {}
    if url:
        out["sections"] = [x.get("line") for x in wiki_page(url, "sections").get("sections") or []][:8]
        add["wiki"] = {"label": "Wiki", "url": url}
    if listing:
        text = wiki_page(listing, "wikitext")["wikitext"]
        out["volumes"] = len(re.findall(r"\{\{\s*Graphic novel list\s*[|}]", text, re.I))
        out["sub_pages"] = len(set(re.findall(r"\[\[\s*(List of [^\]|#]*? chapters \([^)\]]*\))", text)))
        if not out["volumes"] and not out["sub_pages"]:
            raise Refused(404, "that page lists no volumes")
        add["chapters"] = {"label": "Chapters", "url": listing}
    links = [x for x in s["metadata"].get("links") or [] if (x.get("label") or "").lower() not in add]
    call("PATCH", f"{KOMGA}/api/v1/series/{q(sid)}/metadata", {"links": links + list(add.values())})
    return out


@verb("GET", "/manga/library", "q → series in Uchiyomi's library (id, name, books)")
def manga_library(a):
    r = call("POST", f"{UCHIYOMI}/api/series/search?adult=1", {"query": a.get("q") or ""})["content"]
    return [{"id": s["id"], "name": s.get("name"), "books": s.get("booksCount"), "following": s.get("autoUpdate")} for s in r]


@verb("GET", "/manga/status", "series_id (from library) → books, its folder here (for inspect), the runs it lacks, what its sources list that it lacks and why, its downloads")
def manga_status(a):
    sid = need(a, "series_id")[0]
    s = call("GET", f"{UCHIYOMI}/api/series/{q(sid)}")
    listing = call("GET", f"{UCHIYOMI}/api/series/{q(sid)}/listing")
    jobs = call("GET", f"{UCHIYOMI}/api/sources/jobs")["content"]
    # Uchiyomi's downloads (its /library-dl) are Unraid's Books/Manga/uchiyomi, here /manga/uchiyomi.
    folder = f"/manga/uchiyomi/{s['folder']}" if s.get("folder") else None
    return {"name": s.get("name"), "books": s.get("booksCount"), "following": s.get("autoUpdate"),
            "folder": folder, "files": sorted(os.listdir(folder))[:3] if folder and os.path.isdir(folder) else None,
            "gaps": call("GET", f"{UCHIYOMI}/api/series/{q(sid)}/gaps")["gaps"], "checked": listing.get("checkedAt"),
            "lacks": [{k: x.get(k) for k in ("number", "why", "sourceName", "scanlator", "attempts")} for x in listing["content"]],
            "jobs": [{k: j.get(k) for k in ("title", "done", "total", "status", "origin", "reason")} for j in jobs if j.get("seriesId") == sid]}


@verb("GET", "/manga/jobs", "→ Uchiyomi's downloads in progress (folder: for manga/stop), and the failed ones with why")
def manga_jobs(a):
    keys = ("title", "folder", "seriesId", "done", "total", "status", "origin", "reason")
    return [{k: j.get(k) for k in keys} for j in call("GET", f"{UCHIYOMI}/api/sources/jobs")["content"]]


@verb("POST", "/manga/fill", "series_id, [numbers] → fetch what its followed sources list that it lacks (default: every missing or failed one)")
def manga_fill(a):
    sid = need(a, "series_id")[0]
    nums = a.get("numbers") or [x["number"] for x in call("GET", f"{UCHIYOMI}/api/series/{q(sid)}/listing")["content"]
                                if x.get("why") in ("missing", "failed")]
    if not nums:
        return {"note": "its sources list nothing it lacks: try /manga/fill-other"}
    return call("POST", f"{UCHIYOMI}/api/sources/fetch", {"seriesId": sid, "numbers": nums}, timeout=180)


@verb("POST", "/manga/fill-other", "series_id → other sources' offers for its missing chapters (plan); then plan, source, source_series_id, numbers → fetch them")
def manga_fill_other(a):
    if a.get("plan"):
        plan, src, ssid, nums = need(a, "plan", "source", "source_series_id", "numbers")
        return call("POST", f"{UCHIYOMI}/api/sources/fill", {"planId": plan, "source": src, "sourceSeriesId": ssid, "numbers": nums}, timeout=180)
    r = call("POST", f"{UCHIYOMI}/api/sources/fill/scan", {"seriesId": need(a, "series_id")[0]}, timeout=180)
    for _ in range(60):
        if r.get("done") or r.get("failed") or not r.get("scanId"):
            break
        time.sleep(3)
        r = call("GET", f"{UCHIYOMI}/api/sources/fill/scan/{q(r['scanId'])}")
    keys = ("source", "name", "sourceSeriesId", "title", "count", "first", "last", "coverage", "fillable", "why")
    return {**{k: r.get(k) for k in ("done", "failed", "planId", "title", "have", "gaps", "following")},
            "candidates": [{k: c.get(k) for k in keys} for c in r.get("candidates", []) if c.get("count")]}


@verb("POST", "/manga/stop", "folder (from manga/jobs) → that download stops after the chapter in flight; what landed stays")
def manga_stop(a):
    return call("POST", f"{UCHIYOMI}/api/sources/jobs/{q(need(a, 'folder')[0])}/cancel")


@verb("POST", "/manga/follow", "series_id, follow: true|false → whether Uchiyomi keeps fetching the series' new chapters")
def manga_follow(a):
    sid, follow = need(a, "series_id")[0], a.get("follow")
    if follow not in (True, False, "true", "false"):
        raise Refused(400, "follow: true or false")
    return call("POST", f"{UCHIYOMI}/api/admin/series/bulk/auto-update", {"seriesIds": [sid], "autoUpdate": follow in (True, "true")})


def series_books(sid):
    """A series' chapters in Uchiyomi: id and number, every page."""
    books, page = [], 0
    while True:
        d = call("GET", f"{UCHIYOMI}/api/series/{q(sid)}/books?size=500&page={page}")
        books += [{"id": b["id"], "number": b.get("number")} for b in d.get("content", [])]
        if d.get("last", True):
            return books
        page += 1


@verb("POST", "/manga/trash", "series_id + numbers: [chapters] | whole: true → a proposal for Ali's ✅; then code + the ✅'s message_id, thread_id, channel_id → those chapters' files deleted (whole: unfollowed, every file deleted, out of the library)")
def manga_trash(a):
    if a.get("code"):
        return confirm(a)
    sid = need(a, "series_id")[0]
    s, books = call("GET", f"{UCHIYOMI}/api/series/{q(sid)}"), series_books(sid)
    if a.get("whole"):
        ids = [b["id"] for b in books]
        acts = [lambda: call("POST", f"{UCHIYOMI}/api/admin/series/bulk/auto-update", {"seriesIds": [sid], "autoUpdate": False}),
                lambda: ids and call("POST", f"{UCHIYOMI}/api/admin/series/{q(sid)}/chapters/delete", {"bookIds": ids}),
                lambda: call("DELETE", f"{UCHIYOMI}/api/admin/series/{q(sid)}")]
        said = [f"{s.get('name')} ({s.get('folder')}): unfollowed, its {len(ids)} chapters' files deleted, out of the library"]
    else:
        wanted = {float(n) for n in need(a, "numbers")[0]}
        found = [b for b in books if b["number"] is not None and float(b["number"]) in wanted]
        if not found:
            raise Refused(404, "none of those chapters is in the series")
        ids = [b["id"] for b in found]
        acts = [lambda: call("POST", f"{UCHIYOMI}/api/admin/series/{q(sid)}/chapters/delete", {"bookIds": ids})]
        numbers = sorted({float(b["number"]) for b in found})
        said = [f"{s.get('name')}: the files of chapters {', '.join(str(n).removesuffix('.0') for n in numbers)} (fetchable again)"]
    return propose("deleted from Uchiyomi", said, acts)


# --- what Ali has, and reads ---------------------------------------------------------------------

@verb("GET", "/library/find", "q → that series in Komga (id, books, how many Ali has read) and in Uchiyomi (id, books): the ids make his links")
def library_find(a):
    term = need(a, "q")[0]
    komga = call("GET", f"{KOMGA}/api/v1/series?search={q(term)}&size=10")["content"]
    uchiyomi = call("POST", f"{UCHIYOMI}/api/series/search?adult=1", {"query": term, "size": 10})["content"]
    return {"komga": [{"id": s["id"], "name": s["name"], "books": s["booksCount"], "read": s["booksReadCount"]} for s in komga],
            "uchiyomi": [{"id": s["id"], "name": s["name"], "books": s.get("booksCount")} for s in uchiyomi]}


@verb("GET", "/library/shelf", "[library: Comics | Manga] → everything on the NAS, from Komga: each series, its books, how many Ali read, its status, publisher and genres; a manga's Komga id and whether its fan wiki and its Wikipedia list of chapters are linked")
def library_shelf(a):
    libraries = {lib["id"]: lib["name"] for lib in call("GET", f"{KOMGA}/api/v1/libraries")}
    want = [i for i, n in libraries.items() if not a.get("library") or n.lower() == str(a["library"]).lower()]
    series = call("GET", f"{KOMGA}/api/v1/series?unpaged=true&deleted=false" + "".join(f"&library_id={q(i)}" for i in want))["content"]

    def row(s):
        r = {"library": libraries.get(s["libraryId"]), "name": s["name"], "books": s["booksCount"],
             "read": s["booksReadCount"], "reading": s["booksInProgressCount"], "status": s["metadata"].get("status"),
             "publisher": s["metadata"].get("publisher") or None, "genres": s["metadata"].get("genres", [])[:3]}
        if r["library"] == "Manga":  # for manga/wiki
            labels = {(x.get("label") or "").lower() for x in s["metadata"].get("links") or []}
            r.update(komga_id=s["id"], wiki="wiki" in labels, chapters="chapters" in labels)
        return r
    return sorted(map(row, series), key=lambda r: (r["library"] or "", r["name"].lower()))


@verb("GET", "/library/reading","→ what Ali reads, from Komga: the books he read last, and each series he has started with how far he is")
def library_reading(a):
    books = call("GET", f"{KOMGA}/api/v1/books?read_status=READ&read_status=IN_PROGRESS&sort=readProgress.readDate,desc&size=30")["content"]
    series = call("GET", f"{KOMGA}/api/v1/series?read_status=READ&read_status=IN_PROGRESS&size=200")["content"]
    return {"latest": [{"series": b["seriesTitle"], "book": b["metadata"]["title"], "number": b["metadata"]["number"],
                        "read": (b.get("readProgress") or {}).get("readDate"), "finished": (b.get("readProgress") or {}).get("completed")} for b in books],
            "series": [{"id": s["id"], "name": s["name"], "books": s["booksCount"], "read": s["booksReadCount"],
                        "reading": s["booksInProgressCount"]} for s in series]}


# --- both -----------------------------------------------------------------------------------------

@verb("POST", "/rescan", "[deep=1] → Komga and Uchiyomi scan their libraries, and Uchiyomi stops following series no source can update (CLU's); deep: Uchiyomi's Rescan everything too (after a trash or swap)")
def rescan(a):
    out = {"komga": [call("POST", f"{KOMGA}/api/v1/libraries/{lib['id']}/scan") or lib["name"] for lib in call("GET", f"{KOMGA}/api/v1/libraries")],
           "uchiyomi": call("POST", f"{UCHIYOMI}/api/refresh", timeout=180), "unfollowed": unfollow_sourceless()}
    if a.get("deep"):  # its preview, then the plan applied: rows of files gone marked, moved files paired
        start = time.time() * 1000
        call("POST", f"{UCHIYOMI}/api/admin/tasks/rescan/run")
        for _ in range(100):
            time.sleep(3)
            s = call("GET", f"{UCHIYOMI}/api/admin/tasks/rescan/status")
            plan = s.get("plan") or {}
            if not s.get("running") and (plan.get("at") or 0) >= start:
                break
        out["deep"] = call("POST", f"{UCHIYOMI}/api/admin/tasks/rescan/apply", {"plan": plan["id"]}) if plan.get("id") else s.get("error") or "no plan"
    return out


def unfollow_sourceless():
    """Uchiyomi follows every series it finds in its folders, CLU's comics too, which no source of its
    own can update: its updater tries them every night and Health lists them as series that can no
    longer update. CLU updates them, so Uchiyomi stops following them. Answers their names."""
    found, page = [], 0
    while True:
        d = call("POST", f"{UCHIYOMI}/api/series/search?adult=1",
                 {"condition": {"allOf": [{"hasMainSource": {"operator": "isFalse"}}]}, "size": 100, "page": page})
        found += [s for s in d.get("content", []) if s.get("autoUpdate")]
        if d.get("last", True):
            break
        page += 1
    for i in range(0, len(found), 500):
        call("POST", f"{UCHIYOMI}/api/admin/series/bulk/auto-update",
             {"seriesIds": [s["id"] for s in found[i:i + 500]], "autoUpdate": False})
    return [s.get("name") for s in found]


@verb("GET", "/", "→ this list")
def help_(a):
    return [f"{m} {p} — {doc}" for (m, p), (fn, doc) in VERBS.items()]


def from_agent(ip):
    """The agent's container, by its name on `backend`; or this container (its health check). It also
    listens on clu_backend and edge, whose other containers get nothing."""
    try:
        return ip == "127.0.0.1" or ip in {x[4][0] for x in socket.getaddrinfo("comics-agent", None)}
    except OSError:
        return False


class Handler(http.server.BaseHTTPRequestHandler):
    def answer(self, method):
        url = urllib.parse.urlsplit(self.path)
        a = dict(urllib.parse.parse_qsl(url.query))
        status, body = 200, None
        try:
            if not from_agent(self.client_address[0]):
                raise Refused(403, "the comics agent's only")
            if url.path == "/healthz":
                body = {"ok": True}
            else:
                fn = VERBS.get((method, url.path), (None,))[0]
                if not fn:
                    raise Refused(404, "not a verb: GET / lists them")
                n = int(self.headers.get("Content-Length") or 0)
                if n > 1_000_000:
                    raise Refused(413, "too big")
                a.update(json.loads(self.rfile.read(n) or b"{}") if n else {})
                body = fn(a)
        except Refused as e:
            status, body = e.status, {"error": str(e)}
        except Exception as e:  # noqa: BLE001 - the agent reads the reason
            status, body = 500, {"error": f"{type(e).__name__}: {e}"}
        data = scrub(json.dumps(body, ensure_ascii=False, default=str)).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.answer("GET")

    def do_POST(self):
        self.answer("POST")

    def log_message(self, fmt, *args):  # one line per call, no query values
        print(f"{self.command} {urllib.parse.urlsplit(self.path).path} {args[1] if len(args) > 1 else ''}", flush=True)


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
