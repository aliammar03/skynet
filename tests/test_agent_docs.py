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
ROLE_FILES = (
    "archivist.toml",
    "companion.toml",
    "default_executor.toml",
    "investigator.toml",
    "senior_executor.toml",
    "tester.toml",
)
INTERNAL_ACCEPTANCE = "main owns internal integration/implementation acceptance"
EXTERNAL_ACCEPTANCE = (
    "external final acceptance belongs only to a separate fresh reviewer manually started by ali "
    "against the exact open pr head"
)


def normalized(text: str) -> str:
    return " ".join(text.lower().replace("\n>", "\n").split())


class AgentDocsContractTests(unittest.TestCase):
    def test_exact_populated_file_set_has_authority_boundaries(self) -> None:
        actual = {path.name for path in AGENT_DOCS.iterdir() if path.is_file()}
        self.assertEqual(actual, EXPECTED)
        for name in EXPECTED:
            text = (AGENT_DOCS / name).read_text(encoding="utf-8")
            lowered = normalized(text)
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
        self.assertIn("Do not edit those deployment-state", " ".join(archivist.split()))
        self.assertIn("Never hand-edit generated outputs", " ".join(archivist.split()))
        self.assertIn("implementation-ready / pending fresh review", archivist)
        self.assertIn("post-ACCEPT + human-merge closeout", archivist)
        self.assertIn("Treat the open PR as unaccepted and unmerged", archivist)
        self.assertIn("do not write an acceptance record", archivist)

    def test_native_roles_preserve_internal_vs_external_acceptance_boundary(self) -> None:
        for name in ROLE_FILES:
            text = normalized(
                (ROOT / ".codex" / "agents" / name).read_text(encoding="utf-8")
            )
            self.assertIn(INTERNAL_ACCEPTANCE, text, name)
            self.assertIn(EXTERNAL_ACCEPTANCE, text, name)
            self.assertNotIn("main owns acceptance", text, name)
            self.assertNotIn("acceptance decisions stay with main", text, name)
            self.assertNotIn("main has already set directive and state-memory progress and owns the acceptance record", text, name)
            self.assertTrue(
                "do not perform or claim external final acceptance" in text
                or "do not perform or claim either acceptance layer" in text
                or "your pass means only that the assigned verification passed" in text,
                f"{name}: missing explicit worker non-acceptance boundary",
            )

    def test_canonical_memory_does_not_assign_external_final_acceptance_to_main(self) -> None:
        for name in EXPECTED:
            text = normalized((AGENT_DOCS / name).read_text(encoding="utf-8"))
            self.assertNotIn("main owns decisions and acceptance", text, name)
            self.assertNotIn("main owns acceptance", text, name)
            self.assertNotIn("acceptance decisions stay with main", text, name)
            self.assertNotIn("main owns external final acceptance", text, name)

        overview = normalized((AGENT_DOCS / "project_overview.md").read_text(encoding="utf-8"))
        self.assertIn(INTERNAL_ACCEPTANCE, overview)
        self.assertIn(EXTERNAL_ACCEPTANCE, overview)
        self.assertIn("workers and implementation main do not claim it", overview)

        diary = normalized((AGENT_DOCS / "project_diary.md").read_text(encoding="utf-8"))
        self.assertIn(INTERNAL_ACCEPTANCE, diary)
        self.assertIn(EXTERNAL_ACCEPTANCE, diary)

        progress = normalized((AGENT_DOCS / "project_progress.md").read_text(encoding="utf-8"))
        latest = normalized((AGENT_DOCS / "latest_session_work.md").read_text(encoding="utf-8"))
        for name, text in (("project_progress.md", progress), ("latest_session_work.md", latest)):
            self.assertIn("open pr #253", text, name)
            self.assertIn("fresh", text, name)
            self.assertIn("review", text, name)
            self.assertIn("human-merge", text, name)

    def test_closure_shapes_and_latest_session_have_one_entry_point(self) -> None:
        construction = (ROOT / "docs/conventions/construction.md").read_text(
            encoding="utf-8"
        )
        for state in ("implementation ready", "paused", "blocked", "accepted + merged"):
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
