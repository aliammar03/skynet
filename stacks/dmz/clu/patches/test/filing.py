"""CLU's filing match on downloads named like ones that stuck, after apply.py (patch 17).

Run by run.sh inside CLU's image, offline: CLU's own matcher pairs each file with a wanted issue,
as its filing pass does. Exits 1 when a file goes to the wrong issue, or the right one misses it.
"""

import logging
import sys

logging.disable(logging.CRITICAL)
sys.path.insert(0, "/app")
from helpers.collection import match_wanted_issues_to_files, normalize_issue_number  # noqa: E402

SERIES = "Ultimate Spider-Man"
CASES = [  # the issues wanted, a file in processed/, the issue that should take it (None: none)
    (["½", "1"], "Ultimate Spider-Man #000.5.cbz", "½"),
    (["½", "1"], "Ultimate Spider-Man (2000) #00½.cbz", "½"),
    (["½", "1"], "Ultimate Spider-Man (2000) #001.cbz", "1"),
    (["1"], "Ultimate Spider-Man #000.5.cbz", None),
    (["5"], "Ultimate Spider-Man (2001) #005.5.cbz", None),
]
SAME = [("½", "000.5"), ("½", "0.5"), ("1/2", ".5"), ("1½", "001.5")]

failed = 0
for a, b in SAME:
    if normalize_issue_number(a) != normalize_issue_number(b):
        failed += 1
        print(f"  NOT ONE NUMBER: {a!r} and {b!r}")
for pattern in ("{series_name} {issue_number}", "{series_name} #{issue_number}"):
    for numbers, name, right in CASES:
        wanted = [{"series_name": SERIES, "number": n, "mapped_path": "/nonexistent"} for n in numbers]
        found = match_wanted_issues_to_files(wanted, [(name, "/nonexistent/" + name)], pattern,
                                             alias_lookup=lambda _: "")
        got = found[0]["issue"]["number"] if found else None
        if got != right:
            failed += 1
            print(f"  WRONG: {pattern!r}: {name} went to #{got}, not #{right}")
print(f"filing: {len(CASES) * 2 + len(SAME) - failed}/{len(CASES) * 2 + len(SAME)} right")
sys.exit(1 if failed else 0)
