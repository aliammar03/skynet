"""Stamp a doctrine-conforming skeleton for a new artifact from its golden template.

The files under templates/ are the single source: a convention change lands in the template and
every future artifact inherits it. Directives (SKY-###) are scaffolded by `skynet plan`.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path

from skynet.planning import slugify

KINDS = ("service", "script", "runbook", "adr", "journal")
JOURNAL_KINDS = ("session", "incident", "decision")


class ScaffoldError(Exception):
    """A refused scaffold; the message is shown as-is."""


def _slug(text: str) -> str:
    slug = slugify(text)
    if not slug:
        raise ScaffoldError(f"empty slug from '{text}'")
    return slug


def _fresh(path: Path, hint: str = "") -> Path:
    if path.exists():
        raise ScaffoldError(f"{path} already exists{hint}")
    return path


def _template(repo: Path, name: str) -> Path:
    path = repo / "templates" / name
    if not path.exists():
        raise ScaffoldError(f"missing template templates/{name}")
    return path


def _stamp(template: Path, destination: Path, values: dict[str, str]) -> None:
    text = template.read_text(encoding="utf-8")
    for placeholder, value in values.items():
        text = text.replace(placeholder, value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def service(repo: Path, name: str) -> Path:
    slug = _slug(name)
    destination = _fresh(repo / "compose" / slug)
    shutil.copytree(_template(repo, "compose"), destination)
    for path in destination.rglob("*"):
        if path.is_file():
            _stamp(path, path, {"__SVC__": slug})
    return destination


def script(repo: Path, name: str) -> Path:
    destination = _fresh(repo / "scripts" / f"{_slug(name)}.sh")
    _stamp(_template(repo, "script.sh"), destination, {"__NAME__": _slug(name)})
    destination.chmod(0o755)
    return destination


def runbook(repo: Path, title: str) -> Path:
    destination = _fresh(repo / "runbooks" / f"{_slug(title)}.md")
    _stamp(_template(repo, "runbook.md"), destination, {"__TITLE__": title})
    return destination


def next_adr(repo: Path) -> str:
    """One more than the highest 4-digit ADR prefix; numbers are never reused."""
    numbers = [int(match[1]) for path in (repo / "docs/decisions").glob("[0-9]*-*.md")
               if (match := re.match(r"(\d+)", path.name))]
    return f"{max(numbers, default=0) + 1:04d}"


def adr(repo: Path, title: str) -> Path:
    number = next_adr(repo)
    destination = _fresh(repo / "docs/decisions" / f"{number}-{_slug(title)}.md")
    _stamp(_template(repo, "adr.md"), destination, {
        "__NUM__": number, "__TITLE__": title, "__DATE__": datetime.now().strftime("%Y-%m-%d"),
    })
    return destination


def journal(repo: Path, kind: str, title: str) -> Path:
    """An append-only episode: journal/<YYYY>/<date>-<kind>-<slug>.md."""
    if kind not in JOURNAL_KINDS:
        raise ScaffoldError("kind must be session|incident|decision")
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    destination = _fresh(repo / "journal" / date[:4] / f"{date}-{kind}-{_slug(title)}.md",
                         " (episodes are append-only — pick a distinct title)")
    _stamp(_template(repo, "journal.md"), destination, {
        "__DATE__": date, "__TIME__": now.strftime("%H:%M:%S"), "__KIND__": kind, "__TITLE__": title,
    })
    return destination
