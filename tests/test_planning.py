"""Planning discipline: few active directives, each carrying the frontmatter the roadmap reads."""

import re
from pathlib import Path

PROJECTS = Path(__file__).resolve().parents[1] / "planning/projects"
MAX_ACTIVE = 2


def _frontmatter(path: Path) -> dict[str, str]:
    block = path.read_text(encoding="utf-8").split("---", 2)[1]
    return dict(re.findall(r"^(\w+):\s*([^#\n]*?)\s*(?:#.*)?$", block, flags=re.M))


def test_at_most_two_active_directives() -> None:
    active = sorted(p.name for p in PROJECTS.glob("SKY-*.md"))
    assert len(active) <= MAX_ACTIVE, f"park or archive one of {active} (planning/README.md)"


def test_active_directives_track_their_phase() -> None:
    for path in PROJECTS.glob("SKY-*.md"):
        meta = _frontmatter(path)
        assert meta["status"] in {"in-progress", "blocked"}, path.name
        assert 0 <= int(meta["current_phase"]) <= int(meta["phases"]), path.name
        text = path.read_text(encoding="utf-8")
        assert re.search(r"^## (?:\d+\. )?Status\b", text, flags=re.M), f"{path.name} lacks a Status block"
