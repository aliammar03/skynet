"""Narrow contracts for compact agent memory and closure ownership."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DOCS = ROOT / "agent_docs"
EXPECTED = {
    "project_overview.md",
    "project_core_tech.md",
    "project_structure.md",
    "project_progress.md",
    "project_diary.md",
    "latest_session_work.md",
}


class AgentDocsContractTests(unittest.TestCase):
    def test_exact_populated_file_set_has_authority_boundaries(self) -> None:
        actual = {path.name for path in AGENT_DOCS.iterdir() if path.is_file()}
        self.assertEqual(actual, EXPECTED)
        for name in EXPECTED:
            text = (AGENT_DOCS / name).read_text(encoding="utf-8")
            lowered = " ".join(text.lower().replace("\n>", "\n").split())
            self.assertGreater(len(text.split()), 40, name)
            self.assertNotIn("codex-workflow-bootstrap-template", lowered, name)
            self.assertNotIn("no previous session", lowered, name)
            self.assertTrue(
                any(
                    marker in lowered
                    for marker in (
                        "win conflicts",
                        "wins conflicts",
                        "win any conflict",
                        "authoritative when they differ",
                        "outrank it",
                        "decide project status",
                        "win if this map becomes stale",
                    )
                ),
                f"{name}: missing explicit higher-authority conflict rule",
            )

    def test_main_and_archivist_ownership_split_is_explicit(self) -> None:
        construction = (ROOT / "docs/conventions/construction.md").read_text(
            encoding="utf-8"
        )
        archivist = (ROOT / ".codex/agents/archivist.toml").read_text(
            encoding="utf-8"
        )
        for name in ("project_progress.md", "project_diary.md", "latest_session_work.md"):
            self.assertIn(name, construction)
            self.assertIn(name, archivist)
        for name in ("project_overview.md", "project_core_tech.md", "project_structure.md"):
            self.assertIn(name, construction)
            self.assertIn(name, archivist)
        self.assertIn("Main owns acceptance", archivist)
        self.assertIn("Do not edit those\ndeployment-state surfaces", archivist)
        self.assertIn("Never hand-edit\ngenerated outputs", archivist)

    def test_closure_shapes_and_latest_session_have_one_entry_point(self) -> None:
        construction = (ROOT / "docs/conventions/construction.md").read_text(
            encoding="utf-8"
        )
        for state in ("complete", "paused", "blocked"):
            rows = [
                line
                for line in construction.splitlines()
                if line.startswith(f"| {state} |")
            ]
            self.assertEqual(len(rows), 1, state)
            self.assertEqual(rows[0].count("|"), 4, state)

        latest = (AGENT_DOCS / "latest_session_work.md").read_text(encoding="utf-8")
        self.assertEqual(latest.count("## Next Entry Point"), 1)
        for heading in (
            "## Verification",
            "## Pending Work and Blockers",
            "## Next Entry Point",
        ):
            self.assertIn(heading, latest)

    def test_diary_is_reusable_not_chronological(self) -> None:
        diary = (AGENT_DOCS / "project_diary.md").read_text(encoding="utf-8")
        self.assertIn("## Decisions", diary)
        self.assertIn("## Lessons", diary)
        for forbidden in ("## Timeline", "## Releases", "## Commits", "## Session Log"):
            self.assertNotIn(forbidden, diary)


if __name__ == "__main__":
    unittest.main()
