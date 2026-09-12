"""Narrow contracts for compact agent memory and review/closure ownership."""

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
    "external final acceptance belongs only to a separate fresh reviewer manually started by ali"
)
PAIR_MARKERS = (
    "target/base sha",
    "pr head sha",
    "immediately before verdict",
)
LIFECYCLE_FILES = (
    "AGENTS.md",
    ".codex/config.toml",
    "docs/conventions/construction.md",
    "runbooks/construction-delegation.md",
    "planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md",
    "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md",
    "planning/prompts/review.md",
    "planning/prompts/README.md",
    "agent_docs/project_overview.md",
    "agent_docs/project_diary.md",
    "agent_docs/project_progress.md",
    "agent_docs/latest_session_work.md",
)
FORBIDDEN_ATOMIC_GUARANTEES = (
    "accept permits human merge only while",
    "human merge is valid only while",
    "human-merges only while",
    "human-merge only while",
    "human merge only while",
    "human merge while pair remains current",
    "while the reviewer-confirmed pair remains current",
    "while the reviewer-confirmed integration pair remains current",
    "human-merge that pr only while both",
)


def normalized(text: str) -> str:
    return " ".join(text.lower().replace("\n>", "\n").split())


def has_private_free_marker(text: str) -> bool:
    return "private github free" in text or "private-github-free" in text


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
        compact = " ".join(archivist.split())
        self.assertIn("Do not edit those deployment-state", compact)
        self.assertIn("Never hand-edit generated outputs", compact)
        self.assertIn("implementation-ready / pending fresh review", archivist)
        self.assertIn("post-ACCEPT + human-merge closeout", archivist)
        self.assertIn("Treat the open PR as unaccepted and unmerged", archivist)
        self.assertIn("do not write an acceptance record", archivist)
        self.assertIn("specific reviewed base+head pair", archivist)

    def test_native_roles_preserve_internal_vs_external_acceptance_boundary(self) -> None:
        for name in ROLE_FILES:
            text = normalized(
                (ROOT / ".codex" / "agents" / name).read_text(encoding="utf-8")
            )
            self.assertIn(INTERNAL_ACCEPTANCE, text, name)
            self.assertIn(EXTERNAL_ACCEPTANCE, text, name)
            for marker in PAIR_MARKERS:
                self.assertIn(marker, text, name)
            self.assertIn("accept approves that exact last-verified pair", text, name)
            self.assertTrue(has_private_free_marker(text), name)
            self.assertIn("race window", text, name)
            self.assertIn("does not mechanically or atomically guarantee", text, name)
            self.assertNotIn("main owns acceptance", text, name)
            self.assertNotIn("acceptance decisions stay with main", text, name)
            self.assertNotIn(
                "main has already set directive and state-memory progress and owns the "
                "acceptance record",
                text,
                name,
            )
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
        for marker in PAIR_MARKERS:
            self.assertIn(marker, overview)
        self.assertIn("workers and implementation main do not claim", overview)
        self.assertTrue(has_private_free_marker(overview))
        self.assertIn("race window", overview)

        diary = normalized((AGENT_DOCS / "project_diary.md").read_text(encoding="utf-8"))
        self.assertIn(INTERNAL_ACCEPTANCE, diary)
        self.assertIn(EXTERNAL_ACCEPTANCE, diary)
        for marker in PAIR_MARKERS:
            self.assertIn(marker, diary)
        self.assertIn("known movement", diary)
        self.assertTrue(has_private_free_marker(diary))
        self.assertIn("race window", diary)

        progress = normalized((AGENT_DOCS / "project_progress.md").read_text(encoding="utf-8"))
        latest = normalized((AGENT_DOCS / "latest_session_work.md").read_text(encoding="utf-8"))
        for name, text in (("project_progress.md", progress), ("latest_session_work.md", latest)):
            self.assertIn("open pr #253", text, name)
            self.assertIn("fresh", text, name)
            self.assertIn("review", text, name)
            self.assertIn("human-merge", text, name)
            self.assertIn("reviewer resolves", text, name)
            self.assertTrue(has_private_free_marker(text), name)
            self.assertIn("race window", text, name)

    def test_review_acceptance_is_last_verified_pair_not_atomic_merge_guarantee(self) -> None:
        review = normalized((ROOT / "planning/prompts/review.md").read_text(encoding="utf-8"))

        self.assertIn("reviewed base sha", review)
        self.assertIn("reviewed head sha", review)
        self.assertIn("review binding (automatic): base", review)
        self.assertIn("immediately before verdict", review)
        self.assertIn("accept approves the exact reviewer-resolved base+head pair", review)
        self.assertIn("if either revision is known to change before merge", review)
        self.assertIn("github mergeability", review)
        self.assertIn("unchanged head alone", review)
        self.assertTrue(has_private_free_marker(review))
        self.assertIn("race window", review)
        self.assertIn("not a mechanical or atomic guarantee", review)
        self.assertIn("do not require a paid github upgrade", review)
        self.assertIn("ali does not compare or shuttle them", review)

    def test_lifecycle_surfaces_expose_private_free_race_and_no_atomic_promise(self) -> None:
        for path in LIFECYCLE_FILES:
            text = normalized((ROOT / path).read_text(encoding="utf-8"))
            self.assertTrue(has_private_free_marker(text), path)
            self.assertIn("race window", text, path)
            for forbidden in FORBIDDEN_ATOMIC_GUARANTEES:
                self.assertNotIn(forbidden, text, path)

        construction = normalized(
            (ROOT / "docs/conventions/construction.md").read_text(encoding="utf-8")
        )
        runbook = normalized(
            (ROOT / "runbooks/construction-delegation.md").read_text(encoding="utf-8")
        )
        sky026 = normalized(
            (
                ROOT
                / "planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md"
            ).read_text(encoding="utf-8")
        )
        for name, text in (
            ("construction", construction),
            ("runbook", runbook),
            ("sky026", sky026),
        ):
            self.assertIn("base+head pair", text, name)
            self.assertIn("known", text, name)
            self.assertIn("atomic", text, name)

    def test_sky025_p7_has_one_time_merged_work_transition(self) -> None:
        review = normalized((ROOT / "planning/prompts/review.md").read_text(encoding="utf-8"))
        directive = normalized(
            (
                ROOT
                / "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md"
            ).read_text(encoding="utf-8")
        )
        disposition = normalized((ROOT / "planning/sky-025-map.md").read_text(encoding="utf-8"))

        for text in (review, directive, disposition):
            self.assertIn("one-time", text)
            for pr in ("#235", "#236", "#237", "#239"):
                self.assertIn(pr, text)

        self.assertIn("historical p7 implementation", review)
        self.assertIn("there is no open p7 pr to review", directive)
        self.assertIn("single current next action", directive)
        self.assertIn("single current next action", disposition)
        self.assertIn("already-integrated p7 result", directive)
        self.assertIn("already-integrated p7 result", disposition)
        self.assertIn("fix opens one bounded corrective p7 pr", directive)
        self.assertNotIn("p7a omada** as the current executable packet", disposition)
        self.assertIn("no implementation packet is currently released", disposition)

    def test_corrective_p7_pr_uses_normal_open_pr_mode_not_legacy_mode(self) -> None:
        review = normalized((ROOT / "planning/prompts/review.md").read_text(encoding="utf-8"))
        prompt_readme = normalized(
            (ROOT / "planning/prompts/README.md").read_text(encoding="utf-8")
        )
        directive = normalized(
            (
                ROOT
                / "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md"
            ).read_text(encoding="utf-8")
        )
        diary = normalized((AGENT_DOCS / "project_diary.md").read_text(encoding="utf-8"))

        self.assertIn("mode a · normal open-pr review", review)
        self.assertIn("every p8+ numbered phase pr", review)
        self.assertIn("any bounded corrective p7 pr created after a legacy p7 fix verdict", review)
        self.assertIn("do not use mode b for a new corrective p7 pr", review)
        self.assertIn("review it with **mode a, the normal open-pr review**", review)
        self.assertNotIn("mode a · normal p8+ open phase pr", review)

        self.assertIn("normal open-pr flow", prompt_readme)
        self.assertIn("corrective p7 pr", prompt_readme)
        self.assertIn("never returns to the integrated-main legacy review", prompt_readme)
        self.assertIn("any corrective p7 pr created after a legacy fix uses the normal open-pr", diary)
        self.assertIn("any corrective p7 pr created after a legacy fix uses the normal open-pr", directive)

    def test_sky025_p8_plus_uses_one_open_pr_per_numbered_phase(self) -> None:
        paths = (
            "planning/prompts/README.md",
            "planning/prompts/execute.md",
            "planning/prompts/review.md",
            "planning/sky-025-map.md",
            "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md",
            "agent_docs/project_diary.md",
        )
        texts = {path: normalized((ROOT / path).read_text(encoding="utf-8")) for path in paths}

        for path, text in texts.items():
            self.assertIn("one", text, path)
            self.assertIn("pr", text, path)

        directive = texts[
            "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md"
        ]
        prompt_readme = texts["planning/prompts/README.md"]
        execute = texts["planning/prompts/execute.md"]
        review = texts["planning/prompts/review.md"]
        diary = texts["agent_docs/project_diary.md"]

        self.assertIn("one open authored pr per numbered phase", directive)
        self.assertIn("human-merge intermediate slices", directive)
        self.assertIn("one open pr for the work", prompt_readme)
        self.assertIn("internal lettered slices", execute)
        self.assertIn("do not merge them separately", execute)
        self.assertIn("exactly one open pr representing that numbered phase", review)
        self.assertIn("one open authored pr per numbered phase from p8 onward", diary)
        self.assertNotIn("intermediate slices may be human-merged", prompt_readme)

    def test_sky025_p8_is_prepared_but_blocked_only_on_p7_acceptance(self) -> None:
        directive = normalized(
            (
                ROOT
                / "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md"
            ).read_text(encoding="utf-8")
        )
        disposition = normalized((ROOT / "planning/sky-025-map.md").read_text(encoding="utf-8"))
        execute = normalized((ROOT / "planning/prompts/execute.md").read_text(encoding="utf-8"))
        progress = normalized((AGENT_DOCS / "project_progress.md").read_text(encoding="utf-8"))

        for text in (directive, disposition, progress):
            self.assertIn("p8", text)
            self.assertIn("prepared", text)

        self.assertIn("p8a", directive)
        self.assertIn("p8b", directive)
        self.assertIn("not executable until p7 accept", directive)
        self.assertIn("do not implement p8", execute)
        self.assertIn("p7 accept", execute)
        self.assertIn("begin p8", progress)

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
