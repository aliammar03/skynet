"""komga-wiki (P8; Ali, 2026-11-05): a manga chapter's own title, summary and release date in Komga,
from the series' fan wiki, and from Wikipedia where the fan wiki has no date. Komga's manga sources
describe series, not chapters; fan wikis have a page per chapter. A series is linked when it has a
link labelled "Wiki" in Komga, to its wiki's page for chapter 1, and one labelled "Chapters", to its
Wikipedia list of chapters (the comics agent sets both: comics-tools' manga/wiki). The Wiki page's
name gives the rest: "Chapter_1" → "Chapter_1126". For each chapter, the job reads its page through
the wiki's MediaWiki API, takes the title from the infobox, the short summary as plain text and the
release date, and writes them into Komga, locked: nothing overwrites them, and a chapter with all
three is never read again. A chapter the fan wiki gives no date gets the day its volume came out in
Japan, from the Wikipedia list; an exact date found later replaces it. A chapter whose page, summary
or date isn't written yet is read again a week later, and one whose number isn't its file's (Komf's
reset numbers them 1, 2, 3…) once it is again. Links a later match dropped (Komf replaces links) are
put back. Every chapter in the library, linked or not, loses the series' description that Uchiyomi
writes into each one: a chapter shows its own summary or none. Hourly, a request a second to a wiki.
Python's standard library only."""
import base64
import datetime
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

E = os.environ
KOMGA = E.get("KOMGA_URL", "http://komga:25600")
LIBRARY = E.get("KOMGA_LIBRARY", "0S2GKXTMMD47G")  # Manga
STATE = E.get("STATE", "/data/state.json")
EVERY, AGAIN, PAUSE = 3600, 7 * 86400, 1.0  # a pass an hour; what's missing a week later
UA = "skynet-komga-wiki/1.0 (a home library's chapter titles and dates; a request a second)"
SUMMARIES = ("short summary", "summary", "synopsis", "plot summary", "plot")
DATES = ("date", "release date", "release_date", "released", "jdate", "publication date")  # a chapter's infobox
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
LABELS = {"wikis": "Wiki", "lists": "Chapters"}  # state's key for each link, and its label in Komga


def komga(method, path, body=None):
    token = base64.b64encode(f"{E['KOMGA_USER']}:{E['KOMF_KOMGA_PASSWORD']}".encode()).decode()
    req = urllib.request.Request(KOMGA + path, None if body is None else json.dumps(body).encode(),
                                 {"Authorization": "Basic " + token, "Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return json.loads(data) if data.strip() else None


def wiki_of(link):
    """(the wiki's APIs to try, a chapter's page name from its number) from a link to the wiki's
    page for chapter 1 ("…/wiki/Chapter_1", or "…/wiki/Chapter_001": the same zeros), or None."""
    u = urllib.parse.urlsplit(link)
    m = re.fullmatch(r"(.*?)/wiki/(.*?)(0*1)", urllib.parse.unquote(u.path))
    if u.scheme != "https" or not m:
        return None
    base, stem, width = f"https://{u.netloc}{m.group(1)}", m.group(2), len(m.group(3))
    name = lambda n: (stem + (n.zfill(width) if n.isdigit() else n)).replace(" ", "_")  # noqa: E731
    return [f"{base}/api.php", f"{base}/w/api.php"], name  # Fandom's, then MediaWiki's own


APIS = {}  # a wiki's API that answered


def page(apis, name, props="wikitext"):
    """A page as the wiki parses it: its wikitext, and with props "wikitext|text" its HTML too (where
    an infobox shows what its template looks up elsewhere); None when the wiki has no such page."""
    q = urllib.parse.urlencode({"action": "parse", "page": name, "prop": props, "format": "json",
                                "formatversion": 2, "redirects": 1})
    for api in [APIS[apis[0]]] if apis[0] in APIS else apis:
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{api}?{q}", headers={"User-Agent": UA}), timeout=30) as r:
                d = json.loads(r.read())
        except (urllib.error.HTTPError, ValueError):
            continue
        APIS[apis[0]] = api
        return None if "error" in d else d["parse"]
    raise urllib.error.URLError(f"no MediaWiki API at {apis[0]}")


def plain(text):
    """Wikitext as plain text: no templates, references, files or markup; links as their words."""
    text = re.sub(r"<!--.*?-->|<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    while True:  # templates, innermost first
        text, n = re.subn(r"\{\{[^{}]*\}\}", "", text)
        if not n:
            break
    text = re.sub(r"\[\[(?:File|Image):[^\[\]]*(?:\[\[[^\]]*\]\][^\[\]]*)*\]\]", "", text, flags=re.I)
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[https?://\S+\s+([^\]]*)\]|\[https?://\S+\]", r"\1", text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>|'{2,}", "", text)
    paragraphs = [re.sub(r"[ \t]+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    return "\n\n".join(p for p in paragraphs if p)


def day(text):
    """A whole date in wikitext ("2024-09-16", "September 16, 2024", "16 Sep 2024", {{Start date|2024|9|16}})
    as YYYY-MM-DD; None for anything less (a year, a magazine's issue)."""
    text = re.sub(r"<!--.*?-->|<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", text or "", flags=re.S)
    if m := re.search(r"\{\{\s*(?:start date|dts)\s*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", text, re.I):
        y, mo, d = map(int, m.groups())
    elif m := re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        y, mo, d = map(int, m.groups())
    elif m := re.search(r"\b([A-Za-z]{3,9})\.? (\d{1,2}),? (\d{4})\b", text):
        y, mo, d = int(m.group(3)), MONTHS.get(m.group(1)[:3].lower()), int(m.group(2))
    elif m := re.search(r"\b(\d{1,2}) ([A-Za-z]{3,9})\.?,? (\d{4})\b", text):
        y, mo, d = int(m.group(3)), MONTHS.get(m.group(2)[:3].lower()), int(m.group(1))
    else:
        return None
    try:
        return datetime.date(y, mo, d).isoformat() if mo and 1900 < y < 2100 else None
    except ValueError:
        return None


def infobox(html):
    """(source, label, value) for each field of a page's rendered infobox (Fandom's portable one)."""
    text = lambda h: " ".join(re.sub(r"<[^>]+>", " ", h or "").split())  # noqa: E731
    out = []
    for m in re.finditer(r'data-source="([^"]*)"(.*?)</div>\s*</div>', html or "", re.S):
        label = re.search(r'class="pi-data-label[^"]*"[^>]*>(.*?)</h3>', m.group(2), re.S)
        value = re.search(r'class="pi-data-value[^"]*"[^>]*>(.*)', m.group(2), re.S)
        out.append((m.group(1), text(label and label.group(1)), text(value and value.group(1))))
    return out


def chapter(wikitext, html=None, limit=1500):
    """(title, summary, date) from a chapter's page: the infobox's title (or its English one), the
    first of its summary sections that has any text, cut at a sentence near `limit`, and the day it
    came out: from the rendered infobox's date field, else from one in the wikitext's infobox."""
    title = date = None
    for key in ("title", "ename"):
        m = re.search(rf"^\s*\|\s*{key}\s*=\s*(.*?)\s*$", wikitext[:4000], re.M)
        if m and plain(m.group(1)):
            title = plain(m.group(1))
            break
    for source, label, value in infobox(html):
        if re.search(r"date|release|publish", f"{source} {label}", re.I) and (date := day(value)):
            break
    for key in DATES if not date else ():
        m = re.search(rf"^\s*\|\s*{key}\s*=\s*(.*?)\s*$", wikitext[:4000], re.M | re.I)
        if m and (date := day(m.group(1))):
            break
    sections = {}
    for m in re.finditer(r"^==\s*([^=].*?)\s*==\s*$(.*?)(?=^==[^=]|\Z)", wikitext, re.M | re.S):
        sections.setdefault(m.group(1).strip().lower(), plain(m.group(2)))
    summary = next((sections[s] for s in SUMMARIES if sections.get(s)), None)
    if not summary and sections.get("long summary"):
        summary = sections["long summary"].split("\n\n")[0]
    if summary and len(summary) > limit:
        cut = summary.rfind(". ", 0, limit)
        summary = summary[:cut + 1] if cut > limit // 2 else summary[:limit].rstrip() + "…"
    return title, summary, date


def templates(text, name):
    """The insides of each {{name …}} in `text`, nested templates and all."""
    out = []
    for m in re.finditer(r"\{\{\s*" + re.escape(name) + r"\s*(?=[|}])", text, re.I):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            if text.startswith("{{", i):
                depth, i = depth + 1, i + 2
            elif text.startswith("}}", i):
                depth, i = depth - 1, i + 2
            else:
                i += 1
        out.append(text[m.end():i - 2])
    return out


def params(inside):
    """({name: value}, [unnamed values]) of a template's insides: its top-level | and = only."""
    parts, depth, start, i = [], 0, 0, 0
    while i < len(inside):
        pair = inside[i:i + 2]
        if pair in ("{{", "[["):
            depth, i = depth + 1, i + 2
            continue
        if pair in ("}}", "]]"):
            depth, i = depth - 1, i + 2
            continue
        if inside[i] == "|" and depth == 0:
            parts.append(inside[start:i])
            start = i + 1
        i += 1
    parts.append(inside[start:])
    named, unnamed = {}, []
    for p in parts[1:]:  # what comes before the first | is the name's own line
        key, eq, value = p.partition("=")
        if eq and "{{" not in key and "[[" not in key:
            named[key.strip().lower()] = value.strip()
        elif p.strip():
            unnamed.append(p.strip())
    return named, unnamed


def volumes(wikitext):
    """({chapter number: the day its volume came out in Japan}, [sub-pages]) from a Wikipedia list of
    chapters: each {{Graphic novel list}}'s date and the chapters it holds, counted from a
    {{Numbered list|start=…}} or numbered at the line's start ("*001."). A volume whose chapters aren't
    numbered is skipped, not guessed. A long series' list is split into sub-pages, "(1–186)" and on."""
    text, dates = re.sub(r"<!--.*?-->", "", wikitext, flags=re.S), {}
    for inside in templates(text, "Graphic novel list"):
        fields, _ = params(inside)
        when = day(fields.get("originalreldate") or fields.get("reldate"))
        for key, value in fields.items():
            if not (when and key.startswith("chapterlist")):
                continue
            numbers = [int(n) for n in re.findall(r"^\s*[*#]+\s*0*(\d+)\s*[.:]", value, re.M)]
            for numbered_list in templates(value, "Numbered list"):
                start, items = params(numbered_list)
                if start.get("start", "").isdigit():
                    numbers += range(int(start["start"]), int(start["start"]) + len(items))
            for n in numbers:
                dates.setdefault(n, when)
    return dates, sorted(set(re.findall(r"\[\[\s*(List of [^\]|#]*? chapters \([^)\]]*\))", text)))


def volume_dates(link, sleep):
    """{chapter number: its volume's date} from a link to a Wikipedia list of chapters, sub-pages and all."""
    u = urllib.parse.urlsplit(link)
    apis, name = [f"https://{u.netloc}/w/api.php"], urllib.parse.unquote(u.path.partition("/wiki/")[2])
    dates, subs = volumes((page(apis, name) or {}).get("wikitext", ""))
    for sub in subs:
        sleep(PAUSE)
        more, _ = volumes((page(apis, sub) or {}).get("wikitext", ""))
        for n, d in more.items():
            dates.setdefault(n, d)
    return dates


def load():
    try:
        return json.load(open(STATE))
    except (OSError, ValueError):
        return {}


def save(state):
    with open(STATE + ".new", "w") as f:
        json.dump(state, f)
    os.replace(STATE + ".new", STATE)


def linked(s, state):
    """(its Wiki link, its Chapters link): one a later match dropped is put back."""
    have = {(x.get("label") or "").lower(): x["url"] for x in s["metadata"].get("links") or []}
    back = []
    for key, label in LABELS.items():
        if label.lower() in have:
            state[key][s["id"]] = have[label.lower()]
        elif s["id"] in state[key]:
            back.append({"label": label, "url": state[key][s["id"]]})
    if back:
        komga("PATCH", f"/api/v1/series/{s['id']}/metadata", {"links": (s["metadata"].get("links") or []) + back})
    return state["wikis"].get(s["id"]), state["lists"].get(s["id"])


def numbered(book):
    """Whether a chapter's number in Komga is the one its file's name ends with, when it ends with one:
    renumbered chapters' pages would be other chapters'."""
    f = re.search(r"(\d+(?:\.\d+)?)\s*$", book["name"])
    try:
        return not f or float(f.group(1)) == float(book["metadata"]["number"])
    except ValueError:
        return False


def run(state, now=None, sleep=time.sleep):
    """A pass over the library: the series' description off every chapter, and every linked series'
    chapters still to fill. Returns what it read."""
    now, done = now or time.time(), []
    for key in ("wikis", "lists", "checked", "listed", "approx"):  # approx: dated by its volume
        state.setdefault(key, {})
    series = komga("GET", f"/api/v1/series?library_id={LIBRARY}&unpaged=true")["content"]
    for s in series:
        books = komga("GET", f"/api/v1/series/{s['id']}/books?unpaged=true")["content"]
        cleared = 0
        for b in books:  # unlocked: from the file's ComicInfo, where Uchiyomi puts the series' description
            if b["metadata"].get("summary") and not b["metadata"].get("summaryLock"):
                komga("PATCH", f"/api/v1/books/{b['id']}/metadata", {"summary": ""})
                cleared += 1
        if cleared:
            print(f"{s['name']}: the series' description cleared from {cleared} chapters", flush=True)
        link, listing = linked(s, state)
        wiki = link and wiki_of(link)
        dated = {b["id"] for b in books if b["metadata"].get("releaseDateLock")}
        if wiki:
            apis, name = wiki
            filled = waiting = renumbered = 0
            for b in books:
                m = b["metadata"]
                need_date = not m.get("releaseDateLock") or b["id"] in state["approx"]
                if (m.get("titleLock") and m.get("summaryLock") and not need_date) or now - state["checked"].get(b["id"], 0) < AGAIN:
                    continue
                if not numbered(b):
                    renumbered += 1
                    continue
                try:
                    parsed = page(apis, name(m["number"]), "wikitext|text")
                except (urllib.error.URLError, OSError, ValueError) as e:
                    print(f"{s['name']}: the wiki didn't answer ({e}); next pass", flush=True)
                    break
                sleep(PAUSE)
                title, summary, date = chapter(parsed["wikitext"], parsed.get("text")) if parsed else (None, None, None)
                patch = {}
                if title and not m.get("titleLock"):
                    patch.update(title=title, titleLock=True)
                if summary and not m.get("summaryLock"):
                    patch.update(summary=summary, summaryLock=True)
                if date and need_date:
                    patch.update(releaseDate=date, releaseDateLock=True)
                    state["approx"].pop(b["id"], None)
                    dated.add(b["id"])
                if patch:
                    komga("PATCH", f"/api/v1/books/{b['id']}/metadata", patch)
                    filled += 1
                if not summary or (need_date and not date):
                    state["checked"][b["id"]] = now
                    waiting += 1
                done.append((s["name"], m["number"], bool(title), bool(summary), date))
            if filled or waiting:
                print(f"{s['name']}: {filled} chapters filled, {waiting} without a page, summary or date yet", flush=True)
            if renumbered:
                print(f"{s['name']}: {renumbered} chapters left alone: their number isn't their file's "
                      "(a metadata refresh of the series in Komga reads it back)", flush=True)
        undated = [b for b in books if b["id"] not in dated and b["metadata"]["number"].isdigit() and numbered(b)]
        if listing and undated and now - state["listed"].get(s["id"], 0) >= AGAIN:
            try:
                dates = volume_dates(listing, sleep)
            except (urllib.error.URLError, OSError, ValueError) as e:
                print(f"{s['name']}: Wikipedia didn't answer ({e}); next pass", flush=True)
                dates = None
            if dates is not None:
                state["listed"][s["id"]] = now
                n, today = 0, datetime.date.fromtimestamp(now).isoformat()
                for b in undated:  # a volume announced for later isn't out yet
                    if (when := dates.get(int(b["metadata"]["number"]))) and when <= today:
                        komga("PATCH", f"/api/v1/books/{b['id']}/metadata", {"releaseDate": when, "releaseDateLock": True})
                        state["approx"][b["id"]] = 1
                        n += 1
                print(f"{s['name']}: {n} chapters dated by their volume, from Wikipedia", flush=True)
        save(state)
    return done


def main():
    state = load()
    while True:
        open("/tmp/alive", "w").close()
        try:
            run(state)
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            print(f"pass failed: {e}; next hour", flush=True)
        open("/tmp/alive", "w").close()
        time.sleep(EVERY)


if __name__ == "__main__":
    main()
