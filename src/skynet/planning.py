"""Skynet Directives (SKY-###): mint, move between stages, and regenerate the roadmap table.

planning/README.md owns the lifecycle. IDs are minted once across the whole tree and kept for
life; a tracked file moves with `git mv` so its history follows it.
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path

STAGES = ("scratchpad", "ideas", "backlog", "projects", "services", "archive")
STAGE_STATUS = {"backlog": "approved", "projects": "in-progress", "archive": "done"}
_ID = re.compile(r"^id:[ \t]*SKY-(\d+)", re.M)
ROADMAP = re.compile(r"(<!-- ROADMAP:START[^\n]*\n).*?(?=<!-- ROADMAP:END)", re.S)
EMPTY_ROADMAP = '_No directives yet. `skynet plan idea "…"` to start._'


class PlanError(Exception):
    """A refused planning action; the message is shown as-is."""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def next_id(planning: Path) -> str:
    """One more than the highest id anywhere under planning/, archive included."""
    highest = 0
    for path in planning.rglob("*.md"):
        match = _ID.search(path.read_text(encoding="utf-8"))
        if match:
            highest = max(highest, int(match[1]))
    return f"SKY-{highest + 1:03d}"


def find(planning: Path, directive: str) -> Path:
    pattern = re.compile(rf"^id:[ \t]*{re.escape(directive)}\b", re.M)
    for path in sorted(planning.rglob("*.md")):
        if pattern.search(path.read_text(encoding="utf-8")):
            return path
    raise PlanError(f"no directive {directive} found under planning/")


def frontmatter_get(path: Path, key: str) -> str:
    """The raw value after `key:` in the leading --- block, or ''."""
    text = path.read_text(encoding="utf-8")
    parts = text.split("---\n", 2)
    block = parts[1] if len(parts) == 3 and parts[0] == "" else ""
    match = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", block, re.M)
    return match[1] if match else ""


def frontmatter_set(path: Path, key: str, value: str) -> None:
    """Replace the first `key:` line (trailing comment included) with `key: value`."""
    text = path.read_text(encoding="utf-8")
    updated = re.sub(rf"^{re.escape(key)}:.*$", lambda _: f"{key}: {value}", text, count=1,
                     flags=re.M)
    path.write_text(updated, encoding="utf-8")


def _move(repo: Path, source: Path, stage: str) -> Path:
    destination_dir = repo / "planning" / stage
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files", "--error-unmatch", str(source)],
                             capture_output=True, check=False).returncode == 0
    if tracked:
        subprocess.run(["git", "-C", str(repo), "mv", str(source), str(destination)], check=True)
    else:
        source.rename(destination)
    return destination


def scaffold(repo: Path, directive: str, title: str, stage: str, horizon: str = "short",
             body: str = "") -> Path:
    """Stamp a directive from planning/TEMPLATE.md."""
    slug = slugify(title)
    destination = repo / "planning" / stage / f"{directive}-{slug}.md"
    if destination.exists():
        raise PlanError(f"{destination} already exists")
    text = (repo / "planning/TEMPLATE.md").read_text(encoding="utf-8")
    text = text.replace("SKY-000-slug", f"{directive}-{slug}").replace("SKY-000", directive)
    text = text.replace("<short imperative title>", title, 1)
    text = text.replace(f"# {directive} · <Title>", f"# {directive} · {title}", 1)
    if body:
        text += f"\n{body}\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    for key, value in (("created", _today()), ("updated", _today()), ("horizon", horizon)):
        frontmatter_set(destination, key, value)
    return destination


def scratch(repo: Path, note: str) -> Path:
    path = repo / "planning/scratchpad" / f"{_today()}.md"
    if not path.exists():
        path.write_text(f"# scratchpad — {_today()}\n", encoding="utf-8")
    if note:
        with path.open("a", encoding="utf-8") as stream:
            stream.write(f"- {datetime.now().strftime('%H:%M')} — {note}\n")
    return path


def idea(repo: Path, source: str, horizon: str = "short") -> tuple[str, Path]:
    """Mint an idea from a title, or promote (and consume) a scratch note file."""
    directive = next_id(repo / "planning")
    note = Path(source)
    if not note.is_absolute():
        note = repo / note
    body = ""
    if note.is_file():
        title = re.sub(r"^[0-9-]+", "", note.stem) or "idea"
        body = "## From scratchpad\n" + note.read_text(encoding="utf-8").rstrip("\n")
    else:
        title = source
    destination = scaffold(repo, directive, title, "ideas", horizon, body)
    if note.is_file():
        tracked = subprocess.run(["git", "-C", str(repo), "ls-files", "--error-unmatch", str(note)],
                                 capture_output=True, check=False).returncode == 0
        if tracked:
            subprocess.run(["git", "-C", str(repo), "rm", "-q", str(note)], check=True)
        else:
            note.unlink()
    frontmatter_set(destination, "status", "draft")
    roadmap(repo)
    return directive, destination


def service(repo: Path, name: str) -> tuple[str, Path]:
    directive = next_id(repo / "planning")
    destination = scaffold(repo, directive, name, "services", body=(
        "## Service notes\n- **What / why:**\n- **Image & compose:**\n"
        "- **Secrets / DNS / backup needs:**"))
    frontmatter_set(destination, "status", "draft")
    roadmap(repo)
    return directive, destination


def promote(repo: Path, directive: str, stage: str, *, abandon: bool = False) -> Path:
    if stage not in STAGES:
        raise PlanError(f"unknown stage '{stage}' (one of: {' '.join(STAGES)})")
    destination = _move(repo, find(repo / "planning", directive), stage)
    status = "abandoned" if abandon else STAGE_STATUS.get(stage)
    if status:
        frontmatter_set(destination, "status", status)
    frontmatter_set(destination, "updated", _today())
    roadmap(repo)
    return destination


def table(planning: Path) -> str:
    rows = []
    for path in sorted(planning.rglob("SKY-*.md")):
        directive = frontmatter_get(path, "id") if path.parent != planning else ""
        if not directive:
            continue
        stage = path.parent.name
        phases, current = frontmatter_get(path, "phases"), frontmatter_get(path, "current_phase")
        phase = f"{current or 0}/{phases}" if stage == "projects" and phases else "—"
        horizon = {"short": "🌱 short", "long": "🔭 long"}.get(frontmatter_get(path, "horizon"), "—")
        rows.append(f"| {directive} | {frontmatter_get(path, 'title')} | {stage} | "
                    f"{frontmatter_get(path, 'status')} | {phase} | {horizon} |")
    if not rows:
        return EMPTY_ROADMAP
    return "| ID | Title | Stage | Status | Phase | Horizon |\n|---|---|---|---|---|---|\n" + "\n".join(
        sorted(rows))


def roadmap(repo: Path) -> str:
    """Regenerate the table between the ROADMAP markers in planning/README.md."""
    readme = repo / "planning/README.md"
    rendered = table(repo / "planning")
    text = readme.read_text(encoding="utf-8")
    if not ROADMAP.search(text):
        raise PlanError("planning/README.md lacks the ROADMAP markers")
    readme.write_text(ROADMAP.sub(lambda m: m[1] + rendered + "\n", text, count=1), encoding="utf-8")
    return rendered
