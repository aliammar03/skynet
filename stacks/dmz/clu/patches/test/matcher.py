"""CLU's Usenet matcher on posts.json: real posts for 15 issues that tripped CLU, each labelled.

Run by run.sh inside CLU's image after apply.py, offline: CLU's indexers are replaced by one that
answers every query with the issue's posts, and its own search scores them and picks one. Two
passes: with every post, and with the right ones removed (any pick there is a wrong download).
Exits 1 when the first pass picks a wrong post.
"""

import json
import logging
import sys
import types

logging.disable(logging.CRITICAL)  # CLU logs every query; with no database here, errors too
sys.path.insert(0, "/app")
import core.database as cdb  # noqa: E402
import models.indexers as mi  # noqa: E402
from core.settings import get_list  # noqa: E402
from models.usenet import search_usenet_for_issue  # noqa: E402

cases = json.load(open("/patches/test/posts.json"))
variants = [v.lower() for v in get_list("VARIANT_TYPES")]
cdb.get_enabled_indexers = lambda: [
    {"id": 1, "name": "test", "url": "", "api_key": "", "indexer_type": "newznab", "enabled": True}
]


def search(case, posts):
    """CLU's search for the case's issue over ``posts`` [(index, post)]: (accepted, picked)."""

    class Indexer:
        last_error = None

        def search(self, query, limit=100, indexer_id=0):
            return [
                types.SimpleNamespace(title=p["title"], size=p["size"], nzb_url=f"post:{i}", guid=f"post:{i}",
                                      indexer_id=1, indexer_name="test")
                for i, p in posts
            ]

    mi.get_indexer_impl = lambda *a, **k: Indexer()
    year = int((case["cover_date"] or case["store_date"])[:4])  # as the scheduled search gives it
    res = search_usenet_for_issue(
        case["series"], case["issue"], issue_year=year, series_volume=case["volume"],
        series_year=case["volume_year"], publisher_name=case["publisher"], search_variants=variants,
        series_aliases=case["aliases"])
    accepted = {int(r["nzb_url"][5:]) for r in res["all_results"] if r["decision"] == "ACCEPT"}
    return accepted, (int(res["chosen"][0].nzb_url[5:]) if res["chosen"] else None)


got = best = wrong = found = total = wrong_accepted = wrong_grabs = 0
notes = []
for case in cases:
    right, pack, top = set(case["right"]), set(case["pack"]), set(case["best"])
    accepted, pick = search(case, list(enumerate(case["posts"])))
    total += len(right)
    found += len(accepted & right)
    wrong_accepted += len(accepted - right - pack)
    if pick in right:
        got += 1
        best += pick in top
        if pick not in top:
            notes.append(f"  not the best copy: {case['case']}: {case['posts'][pick]['title']}")
    elif pick is None:
        notes.append(f"  missed: {case['case']}")
    else:
        wrong += 1
        notes.append(f"  WRONG: {case['case']}: {case['posts'][pick]['title']}")
    others = [(i, p) for i, p in enumerate(case["posts"]) if i not in right | pack]
    _, pick = search(case, others)
    if pick is not None:
        wrong_grabs += 1
        notes.append(f"  right post absent, takes: {case['case']}: {case['posts'][pick]['title']}")

n = len(cases)
print(f"issue found {got}/{n} · best copy {best}/{n} · wrong picks {wrong} · right posts recognised "
      f"{found}/{total} · wrong posts accepted {wrong_accepted} · wrong grabs, right post absent {wrong_grabs}/{n}")
print("\n".join(notes))
sys.exit(1 if wrong else 0)
