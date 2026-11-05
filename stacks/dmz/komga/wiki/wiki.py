"""komga-wiki (P8; Ali, 2026-11-05): a manga chapter's own title and summary in Komga, from the
series' fan wiki. Komga's manga sources describe series, not chapters; fan wikis have a page per
chapter. A series is linked when it has a link labelled "Wiki" in Komga, to its wiki's page for
chapter 1 (the comics agent sets it: comics-tools' manga/wiki). That page's name gives the rest:
"Chapter_1" → "Chapter_1126". For each chapter, the job reads its page through the wiki's MediaWiki
API, takes the title from the infobox and the short summary as plain text, and writes both into
Komga, locked: nothing overwrites them, and a chapter with both is never read again. A chapter
whose page or summary isn't written yet is read again a week later, and one whose number isn't its
file's (Komf's reset numbers them 1, 2, 3…) once it is again. A Wiki link a later match dropped
(Komf replaces links) is put back. Every chapter in the library, linked or not, loses the series'
description that Uchiyomi writes into each one: a chapter shows its own summary or none. Hourly, a
request a second to a wiki. Python's standard library only."""
import base64
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
EVERY, AGAIN, PAUSE = 3600, 7 * 86400, 1.0  # a pass an hour; a missing page or summary a week later
UA = "skynet-komga-wiki/1.0 (a home library's chapter titles; a request a second)"
SUMMARIES = ("short summary", "summary", "synopsis", "plot summary", "plot")


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


def page(apis, name):
    """A page's wikitext, or None when the wiki has no such page."""
    q = urllib.parse.urlencode({"action": "parse", "page": name, "prop": "wikitext", "format": "json",
                                "formatversion": 2, "redirects": 1})
    for api in [APIS[apis[0]]] if apis[0] in APIS else apis:
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{api}?{q}", headers={"User-Agent": UA}), timeout=30) as r:
                d = json.loads(r.read())
        except (urllib.error.HTTPError, ValueError):
            continue
        APIS[apis[0]] = api
        return None if "error" in d else d["parse"]["wikitext"]
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


def chapter(wikitext, limit=1500):
    """(title, summary) from a chapter's page: the infobox's title (or its English one), and the
    first of its summary sections that has any text, cut at a sentence near `limit`."""
    title = None
    for key in ("title", "ename"):
        m = re.search(rf"^\s*\|\s*{key}\s*=\s*(.*?)\s*$", wikitext[:4000], re.M)
        if m and plain(m.group(1)):
            title = plain(m.group(1))
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
    return title, summary


def load():
    try:
        return json.load(open(STATE))
    except (OSError, ValueError):
        return {"wikis": {}, "checked": {}}


def save(state):
    with open(STATE + ".new", "w") as f:
        json.dump(state, f)
    os.replace(STATE + ".new", STATE)


def wiki_link(series):
    return next((x["url"] for x in series["metadata"].get("links") or [] if x.get("label", "").lower() == "wiki"), None)


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
        link = wiki_link(s)
        if link:
            state["wikis"][s["id"]] = link
        elif s["id"] in state["wikis"]:  # dropped by a later match: put it back
            link = state["wikis"][s["id"]]
            links = (s["metadata"].get("links") or []) + [{"label": "Wiki", "url": link}]
            komga("PATCH", f"/api/v1/series/{s['id']}/metadata", {"links": links})
        wiki = link and wiki_of(link)
        if not wiki:
            continue
        apis, name = wiki
        filled = waiting = renumbered = 0
        for b in books:
            m = b["metadata"]
            if (m.get("titleLock") and m.get("summaryLock")) or now - state["checked"].get(b["id"], 0) < AGAIN:
                continue
            if not numbered(b):
                renumbered += 1
                continue
            try:
                text = page(apis, name(m["number"]))
            except (urllib.error.URLError, OSError, ValueError) as e:
                print(f"{s['name']}: the wiki didn't answer ({e}); next pass", flush=True)
                break
            sleep(PAUSE)
            title, summary = chapter(text) if text else (None, None)
            patch = {}
            if title and not m.get("titleLock"):
                patch.update(title=title, titleLock=True)
            if summary and not m.get("summaryLock"):
                patch.update(summary=summary, summaryLock=True)
            if patch:
                komga("PATCH", f"/api/v1/books/{b['id']}/metadata", patch)
                filled += 1
            if not summary:
                state["checked"][b["id"]] = now
                waiting += 1
            done.append((s["name"], m["number"], bool(title), bool(summary)))
        if filled or waiting:
            print(f"{s['name']}: {filled} chapters filled, {waiting} without a page or summary yet", flush=True)
        if renumbered:
            print(f"{s['name']}: {renumbered} chapters left alone: their number isn't their file's "
                  "(a metadata refresh of the series in Komga reads it back)", flush=True)
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
