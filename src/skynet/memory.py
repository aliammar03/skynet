"""Generated retrieval views and append-only journal helpers."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TextIO


class MemoryError(Exception):
    """A local memory/rendering operation could not complete honestly."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class RecallHit:
    path: Path
    matches: int
    tokens: int
    summary: str
    excerpt: str


def frontmatter(path: Path) -> dict[str, str]:
    """Read simple scalar values from one Markdown opening frontmatter block."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise MemoryError(f"{path}: source unavailable", 3) from None
    if not lines or lines[0] != "---":
        return {}
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if match is None:
            continue
        value = re.sub(r"\s+#.*$", "", match.group(2)).strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        values[match.group(1)] = value
    return values


def _heading(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except (OSError, UnicodeError):
        return ""
    return ""


def summary(path: Path) -> str:
    metadata = frontmatter(path)
    return metadata.get("summary") or metadata.get("title") or _heading(path) or "—"


def token_cost(path: Path, *, omit_tokens_line: bool = False) -> int:
    try:
        data = path.read_bytes()
    except OSError:
        raise MemoryError(f"{path}: source unavailable", 3) from None
    if omit_tokens_line:
        data = b"\n".join(line for line in data.splitlines() if not line.startswith(b"tokens:"))
        if data:
            data += b"\n"
    return len(data) // 4


def _atomic_write(path: Path, content: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                stream.write(content)
            os.replace(temporary, path)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    except OSError:
        raise MemoryError(f"{path}: publication failed", 3) from None


def _markdown_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        (path for path in root.rglob("*.md") if path.name != "README.md"),
        key=lambda path: path.as_posix(),
    )


def _journal_order(path: Path) -> tuple[str, str]:
    metadata = frontmatter(path)
    date = metadata.get("date", "0000-00-00")
    time = metadata.get("time", "00:00:00")
    if re.fullmatch(r"[0-2][0-9]:[0-5][0-9](?::[0-5][0-9])?", time) is None:
        time = "00:00:00"
    return date, time


def _section_bullets(path: Path, heading: str) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise MemoryError(f"{path}: source unavailable", 3) from None
    result: list[str] = []
    active = False
    current = ""
    for line in lines:
        if line.startswith("## "):
            if active and current:
                result.append(current)
            current = ""
            active = line.startswith(heading)
            continue
        if not active:
            continue
        if re.match(r"^-\s", line):
            if current:
                result.append(current)
            current = line
        elif not line.strip():
            if current:
                result.append(current)
                current = ""
        elif current:
            current += " " + line.strip()
    if active and current:
        result.append(current)
    return result


def render_digest(repo: Path, output: Path | None = None, journal: Path | None = None) -> Path:
    """Render the content-stable recent-activity and episodic retrieval view."""
    repo = repo.resolve()
    target = output or repo / "docs/generated/06-agent-digest.md"
    journal_root = journal or repo / "journal"
    if not journal_root.is_absolute():
        journal_root = repo / journal_root
    lines = [
        "---",
        "title: Agent Digest",
        "summary: Recent-activity, episodic, and open-thread retrieval view.",
        "author: skynet-ops (skynet render digest)",
        "tags: [skynet, generated, agent, digest, recent-activity, episodic]",
        "---",
        "",
        "# Skynet — Agent Digest",
        "",
        "Use this view to retrieve recent **decisions**, **open threads**, and **recent episodes**.",
        "Facts and pointers only — follow a link for the full story; distill episodes at read time,",
        "never in this file. Normal fresh-session continuity starts with `AGENTS.md` plus the active",
        "directive; this generated page is optional recent-activity and episodic retrieval.",
        "",
        "## 🧷 Recent decisions",
        "",
    ]
    decisions = sorted(
        (repo / "docs/decisions").glob("[0-9]*-*.md"),
        key=lambda path: path.as_posix(),
        reverse=True,
    )
    for path in decisions:
        base = path.stem
        match = re.match(r"^(\d+)", base)
        number = int(match.group(1)) if match else 0
        title = _heading(path)
        title = re.sub(r"^ADR\s*\d+\s*[—-]?\s*", "", title)
        text = path.read_text(encoding="utf-8")
        status_match = re.search(r"(?im)^-?\s*\*\*Status:\*\*\s*(.*?)\s*$", text)
        date_match = re.search(r"(?im)^-?\s*\*\*Date:\*\*\s*(.*?)\s*$", text)
        status = status_match.group(1) if status_match else "?"
        date = date_match.group(1) if date_match else "?"
        lines.append(f"- **[[{base}|ADR {number:04d}]]** — {title or '?'} · {status} · {date}")
    if not decisions:
        lines.append("- _none recorded yet._")
    lines.extend(
        ["", "## 🧵 Open threads", "", "**Directives in flight** (not done/abandoned):", ""]
    )
    found = False
    for stage in ("projects", "backlog", "ideas"):
        for path in sorted(
            (repo / "planning" / stage).glob("SKY-*.md"), key=lambda item: item.as_posix()
        ):
            metadata = frontmatter(path)
            state = metadata.get("status", "")
            if state in {"", "done", "abandoned"}:
                continue
            phase = ""
            if stage == "projects" and metadata.get("phases"):
                phase = f" · {metadata.get('current_phase', '0')}/{metadata['phases']}"
            lines.append(
                f"- **{metadata.get('id', '')}** ({stage} · {state}{phase}) — "
                f"{metadata.get('title', '')}"
            )
            found = True
    if not found:
        lines.append("- _no open directives._")
    episodes = _markdown_files(journal_root)
    superseded: set[str] = set()
    for path in episodes:
        raw = frontmatter(path).get("resolves", "")
        superseded.update(item for item in re.split(r"[\s,\[\]\"]+", raw) if item)
    lines.extend(["", "**Explicit durable follow-ups:**", ""])
    count = 0
    unknown = 0

    def order(path: Path) -> tuple[str, str, str]:
        return (*_journal_order(path), path.as_posix())

    for path in sorted(episodes, key=order, reverse=True):
        if path.stem in superseded:
            continue
        metadata = frontmatter(path)
        state = metadata.get("thread_status", "")
        if state == "resolved":
            continue
        if state != "open":
            unknown += 1
            continue
        for bullet in _section_bullets(path, "## Follow-ups"):
            if bullet.startswith("- <"):
                continue
            lines.append(f"{bullet} — _{metadata.get('date', '?')} {metadata.get('kind', '?')}_")
            count += 1
            if count >= 8:
                break
        if count >= 8:
            break
    if count == 0:
        lines.append("- _none explicitly open._")
    if unknown:
        lines.append(
            f"- _{unknown} historical episode(s) have unclassified follow-ups; status unknown, "
            "not promoted as current work._"
        )
    lines.extend(["", "## 📓 Recent episodes", ""])
    recent = sorted(episodes, key=order, reverse=True)[:7]
    for path in recent:
        metadata = frontmatter(path)
        lines.append(
            f"- **{metadata.get('date', '?')}** · {metadata.get('kind', '?')} · "
            f"[[{path.stem}|{metadata.get('title', path.stem)}]]"
        )
    if not recent:
        lines.append("- _journal is empty — the nightly will seed it._")
    lines.extend(
        [
            "",
            "---",
            "_Human narrative: [[05-state-of-the-lab]] · on-demand load-cost map: "
            "[[07-context-map]] · full episodic log: [[README|journal/]]. This digest is a cache — "
            "regenerable from git, never a source of truth._",
            "",
            "> [!note] Recent-activity / episodic / open-thread retrieval view — generated by",
            "> `skynet render digest` from ADRs + the journal + the roadmap. Do not hand-edit.",
            "> Content-stable (diffs only on real change). Normal fresh-session continuity starts with",
            "> `AGENTS.md` plus the active directive; this page is optional retrieval.",
            "",
        ]
    )
    _atomic_write(target, "\n".join(lines))
    return target


def _tier(path: Path) -> str:
    metadata = frontmatter(path)
    if metadata.get("tier"):
        return metadata["tier"]
    try:
        match = re.search(r"\*\*Tier:\*\*\s*([^.]*)", path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return ""
    return match.group(1).strip() if match else ""


def _escape(value: str) -> str:
    return value.replace("|", r"\|")


def render_context(repo: Path, output: Path | None = None) -> Path:
    """Render the deterministic on-demand context routing index."""
    repo = repo.resolve()
    target = output or repo / "docs/generated/07-context-map.md"
    runbooks = sorted(
        (path for path in (repo / "runbooks").rglob("*.md") if path.name != "README.md"),
        key=lambda path: path.as_posix(),
    )
    spokes = sorted((repo / "docs/design").glob("*.md"), key=lambda path: path.as_posix())
    conventions = sorted((repo / "docs/conventions").glob("*.md"), key=lambda path: path.as_posix())
    catalogs = sorted(
        (
            repo / path
            for path in (
                "planning/README.md",
                "compose/README.md",
                "journal/README.md",
                "runbooks/README.md",
                "templates/README.md",
            )
            if (repo / path).is_file()
        ),
        key=lambda path: path.as_posix(),
    )
    generated = sorted(
        (
            path
            for path in (repo / "docs/generated").glob("*.md")
            if path.name != "07-context-map.md"
        ),
        key=lambda path: path.as_posix(),
    )
    baseline = sum(
        token_cost(repo / name, omit_tokens_line=True) for name in ("AGENTS.md", "CLAUDE.md")
    )
    lines = [
        "---",
        "title: Context Map",
        "summary: On-demand load-cost and context-routing index.",
        "author: skynet-ops (skynet render context)",
        "tags: [skynet, generated, agent, context-map]",
        "---",
        "",
        "# Skynet — Context Map",
        "",
        f"**Always-loaded contract baseline:** `AGENTS.md` + `CLAUDE.md` ≈ **{baseline}** tok — never in this list.",
        "Use this map after normal continuity intake (`AGENTS.md` + the active directive) to route",
        "additional reads. Everything below is **on-demand**: open a *file*, not a section.",
        "",
        "## Procedures — `runbooks/` (trigger-driven)",
        "",
        "| Path | Tier | Trigger | ~tok | Summary |",
        "|---|---|---|--:|---|",
    ]
    for path in runbooks:
        relative = path.relative_to(repo).as_posix()
        lines.append(
            f"| `{relative}` | {_escape(_tier(path))} | "
            f"{_escape(frontmatter(path).get('trigger', ''))} | {token_cost(path, omit_tokens_line=True)} | "
            f"{_escape(summary(path))} |"
        )
    for heading, paths in (
        ("Design spokes — `docs/design/`", spokes),
        ("Conventions — `docs/conventions/`", conventions),
        ("Catalogs & templates", catalogs),
        (
            "Generated views — `docs/generated/` (machine-owned; edit the renderer, not these)",
            generated,
        ),
    ):
        lines.extend(["", f"## {heading}", "", "| Path | ~tok | Summary |", "|---|--:|---|"])
        for path in paths:
            relative = path.relative_to(repo).as_posix()
            lines.append(
                f"| `{relative}` | {token_cost(path, omit_tokens_line=True)} | {_escape(summary(path))} |"
            )
    episodes = _markdown_files(repo / "journal")
    episode_tokens = sum(len(path.read_bytes()) for path in episodes) // 4
    corpus = runbooks + spokes + conventions + catalogs + generated
    total = sum(token_cost(path, omit_tokens_line=True) for path in corpus)
    lines.extend(
        [
            "",
            "## Episodic memory — retrieve by topic, don't browse",
            "",
            f"- `journal/` — {len(episodes)} raw episodes, ≈ {episode_tokens} tok total. Retrieve by topic: "
            '`skynet recall --repo <checkout> <topic>` or `grep -ri "<topic>" journal/`; use '
            "`06-agent-digest.md` when "
            "recent activity, open threads, or episode pointers are useful. **Do not load the whole store.**",
            "",
            "---",
            f"**On-demand corpus:** ≈ **{total}** tok across {len(corpus)} files — but you load a *row* "
            "(≈ tens of tok) to choose, then one file.",
            "_A cache — regenerable from git via `skynet render context`; never a source of truth._",
            "",
            "> [!note] Generated by `skynet render context` from each loadable's frontmatter.",
            "> Do not hand-edit. Content-stable (diffs only on real change). The **map of what you can",
            "> load and what it costs** — read a ROW, then open only the one file you need. The",
            "> on-demand index complements normal `AGENTS.md` + active-directive continuity ([[memory]]).",
            "",
        ]
    )
    _atomic_write(target, "\n".join(lines))
    return target


def render_runbook_catalog(repo: Path, output: Path | None = None) -> Path:
    """Render the runbook routing catalog from leaf frontmatter."""
    repo = repo.resolve()
    target = output or repo / "runbooks/README.md"
    runbooks = sorted(
        (path for path in (repo / "runbooks").rglob("*.md") if path.name != "README.md"),
        key=lambda path: path.as_posix(),
    )
    lines = [
        "---",
        'summary: "Catalog of task-shaped, engine-neutral operational procedures. Rendered from runbook frontmatter."',
        "---",
        "",
        "# runbooks — procedures any agent can execute",
        "",
        "A runbook is engine-neutral markdown plus plain bash. Read the leaf whose trigger matches the task; do not load unrelated procedures.",
        "",
        "## Catalog",
        "",
        "| Runbook | Tier | Trigger | Summary |",
        "|---|---|---|---|",
    ]
    for path in runbooks:
        relative = path.relative_to(repo / "runbooks").as_posix()
        metadata = frontmatter(path)
        lines.append(
            f"| [`{relative}`]({relative}) | {_escape(_tier(path))} | "
            f"{_escape(metadata.get('trigger', ''))} | {_escape(metadata.get('summary', ''))} |"
        )
    lines.extend(
        [
            "",
            "## Runbook contract",
            "",
            "- Use compact frontmatter: `summary`, `trigger` where natural, `tier`, `executor`, and `rollback`.",
            "- Structure every leaf as **Preconditions → Steps → Verify → Rollback → Evidence**.",
            "- Keep procedures current and task-shaped; doctrine belongs in its authoritative design/convention document, history in `journal/`.",
            "",
            "_A cache — regenerate with `skynet render runbook-catalog`; never hand-edit._",
            "",
        ]
    )
    _atomic_write(target, "\n".join(lines))
    return target


def recall(repo: Path, terms: Iterable[str]) -> list[RecallHit]:
    """Search canonical Markdown memory with GNU ERE and rank matching files."""
    expressions = list(terms)
    if not expressions:
        raise MemoryError("recall requires at least one topic", 2)
    expression = "|".join(expressions)
    try:
        validation = subprocess.run(
            ["grep", "-iEq", "--", expression],
            input="",
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise MemoryError(f"recall grep unavailable: {error}", 3) from None
    if validation.returncode == 2:
        detail = validation.stderr.strip() or "GNU ERE rejected expression"
        raise MemoryError(f"invalid recall expression: {detail}", 2)
    if validation.returncode not in {0, 1}:
        raise MemoryError("recall expression validation failed", 3)
    roots = [repo / name for name in ("journal", "docs", "runbooks", "planning")]
    files: set[Path] = {repo / "AGENTS.md", repo / "README.md"}
    for root in roots:
        if root.is_dir():
            files.update(path for path in root.rglob("*.md") if "generated" not in path.parts)
    hits: list[RecallHit] = []
    for path in sorted(files):
        if not path.is_file():
            continue
        try:
            result = subprocess.run(
                ["grep", "-iIE", "--", expression, str(path)],
                capture_output=True,
                check=False,
            )
        except OSError as error:
            raise MemoryError(f"recall grep unavailable: {error}", 3) from None
        if result.returncode == 1:
            continue
        if result.returncode != 0:
            raise MemoryError(f"{path}: recall search failed", 3)
        matching = result.stdout.split(b"\n")
        if matching[-1] == b"":
            matching.pop()
        first_match = matching[0].decode("utf-8", errors="replace")
        excerpt = re.sub(r"\s+", " ", first_match.strip())[:96]
        hits.append(
            RecallHit(
                path.relative_to(repo), len(matching), token_cost(path), summary(path), excerpt
            )
        )
    return sorted(hits, key=lambda item: (-item.matches, item.tokens, item.path.as_posix()))


def print_recall(repo: Path, terms: Iterable[str], stdout: TextIO) -> int:
    expressions = list(terms)
    hits = recall(repo, expressions)
    expression = "|".join(expressions)
    if not hits:
        print(
            f'recall "{expression}" — no matches. Try broader/other terms, or grep -ri manually.',
            file=stdout,
        )
        return 0
    print(
        f'recall "{expression}" — {len(hits)} file(s) mention it (ranked; open the top few, distill, do NOT load all):\n',
        file=stdout,
    )
    for hit in hits[:20]:
        print(f"  {hit.matches:2d} hit(s) · ~{hit.tokens:5d} tok · {hit.path}", file=stdout)
        print(f"              {hit.summary}", file=stdout)
        if hit.excerpt:
            print(f"              ↳ {hit.excerpt}", file=stdout)
        print(file=stdout)
    print(
        "Retrieval rule: open only what you need, summarize in a throwaway window, return the conclusion.",
        file=stdout,
    )
    print(
        "Never persist that summary — the raw source stays truth (ADR 0002); it lives for one query.",
        file=stdout,
    )
    return 0
