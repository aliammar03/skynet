"""`skynet plan` and `skynet new`: ids never reused, stages move with status, templates stamp literally."""

import shutil
import subprocess
from pathlib import Path

import pytest

from skynet import cli, planning, scaffold

REPO = Path(__file__).resolve().parents[1]
TRICKY = r"OpenTofu: VM/CT & \back"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "planning/archive").mkdir(parents=True)
    shutil.copy2(REPO / "planning/TEMPLATE.md", root / "planning/TEMPLATE.md")
    (root / "planning/README.md").write_text(
        "# planning\n<!-- ROADMAP:START — generated -->\nold\n<!-- ROADMAP:END -->\ntail\n")
    (root / "planning/archive/SKY-041-old.md").write_text("---\nid: SKY-041\ntitle: old\n---\n")
    shutil.copytree(REPO / "templates", root / "templates")
    (root / "docs/decisions").mkdir(parents=True)
    (root / "docs/decisions/0007-x.md").write_text("x")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return root


def test_idea_mints_after_the_highest_id_even_archived(repo: Path) -> None:
    directive, path = planning.idea(repo, TRICKY, "long")
    assert directive == "SKY-042" and path.parent.name == "ideas"
    assert planning.frontmatter_get(path, "title") == TRICKY
    assert planning.frontmatter_get(path, "status") == "draft"
    assert planning.frontmatter_get(path, "horizon") == "long"
    assert f"# SKY-042 · {TRICKY}" in path.read_text()
    assert "| SKY-042 |" in (repo / "planning/README.md").read_text()


def test_idea_from_scratch_note_consumes_it(repo: Path) -> None:
    note = repo / "planning/scratchpad/2026-08-17-lint-gate.md"
    note.parent.mkdir(parents=True)
    note.write_text("# note\nbody\n")
    _, path = planning.idea(repo, str(note))
    assert path.name == "SKY-042-lint-gate.md" and "## From scratchpad\n# note\nbody" in path.read_text()
    assert not note.exists()


def test_promote_moves_tracked_file_and_sets_status(repo: Path) -> None:
    _, path = planning.idea(repo, "thing")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    moved = planning.promote(repo, "SKY-042", "projects")
    assert moved.parent.name == "projects" and not path.exists()
    assert planning.frontmatter_get(moved, "status") == "in-progress"
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files", "planning"], capture_output=True,
                             text=True, check=True).stdout.split()
    assert "planning/projects/SKY-042-thing.md" in tracked and "planning/ideas/SKY-042-thing.md" not in tracked
    readme = (repo / "planning/README.md").read_text()
    assert "| SKY-042 | thing | projects | in-progress | 0/1 | 🌱 short |" in readme
    assert readme.endswith("<!-- ROADMAP:END -->\ntail\n") and "old\n" not in readme


def test_archive_abandon_and_unknown_id(repo: Path) -> None:
    planning.idea(repo, "doomed")
    assert planning.frontmatter_get(planning.promote(repo, "SKY-042", "archive", abandon=True),
                                    "status") == "abandoned"
    with pytest.raises(planning.PlanError):
        planning.find(repo / "planning", "SKY-999")


def test_new_stamps_each_kind_and_refuses_existing(repo: Path) -> None:
    stamped = [
        scaffold.service(repo, "My App") / "compose.yaml",
        scaffold.script(repo, "do-thing"),
        scaffold.runbook(repo, TRICKY),
        scaffold.adr(repo, TRICKY),
        scaffold.journal(repo, "session", TRICKY),
    ]
    for path in stamped:
        assert path.exists() and "__" not in path.read_text().replace("__init__", "")
    assert stamped[3].name.startswith("0008-")
    assert f"title: {TRICKY}" in stamped[4].read_text()
    with pytest.raises(scaffold.ScaffoldError):
        scaffold.script(repo, "do-thing")
    with pytest.raises(scaffold.ScaffoldError):
        scaffold.journal(repo, "rant", "x")


def test_cli_reports_refusal(repo: Path) -> None:
    assert cli.main(["plan", "--repo", str(repo), "show", "SKY-999"]) == 1
    assert cli.main(["new", "--repo", str(repo), "journal", "session", "hello"]) == 0
