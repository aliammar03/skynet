"""Narrow contracts for compact agent memory and review/closeout ownership."""

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
LIFECYCLE_FILES = (
    "AGENTS.md",
    ".codex/config.toml",
    "docs/conventions/construction.md",
    "runbooks/construction-delegation.md",
    "planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md",
    "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md",
    "planning/prompts/review.md",
    "planning/prompts/README.md",
    "planning/prompts/execute.md",
    "agent_docs/project_overview.md",
    "agent_docs/project_diary.md",
    "agent_docs/project_progress.md",
    "agent_docs/latest_session_work.md",
)
FORBIDDEN_OLD_CLOSEOUT = (
    "post-merge closeout",
    "bounded post-merge",
    "after accept + human merge",
    "then run bounded closeout",
    "closeout-only pr is required",
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
        construction = normalized(
            (ROOT / "docs/conventions/construction.md").read_text(encoding="utf-8")
        )
        archivist = normalized(
            (ROOT / ".codex/agents/archivist.toml").read_text(encoding="utf-8")
        )
        for name in ("project_progress.md", "project_diary.md", "latest_session_work.md"):
            self.assertIn(name, construction)
            self.assertIn(name, archivist)
        for name in ("project_overview.md", "project_core_tech.md", "project_structure.md"):
            self.assertIn(name, construction)
            self.assertIn(name, archivist)
        self.assertIn("implementation-ready / pending fresh review", archivist)
        self.assertIn("accepted closeout is main-only bookkeeping", archivist)
        self.assertIn("do not edit stable memory", archivist)
        self.assertIn("do not commit, push, or merge", archivist)
        self.assertIn("stable memory", construction)
        self.assertIn("frozen after accept", construction)

    def test_native_roles_share_acceptance_marker_and_same_pr_closeout_contract(self) -> None:
        for name in ROLE_FILES:
            text = normalized(
                (ROOT / ".codex" / "agents" / name).read_text(encoding="utf-8")
            )
            self.assertIn("external final acceptance belongs only to a separate fresh reviewer", text, name)
            self.assertIn("target/base sha", text, name)
            self.assertIn("pr head sha", text, name)
            self.assertIn("immediately before verdict", text, name)
            self.assertIn("machine-readable acceptance marker", text, name)
            self.assertIn("same-pr closeout", text, name)
            self.assertTrue(has_private_free_marker(text), name)
            self.assertIn("race window", text, name)
            self.assertNotIn("main owns external final acceptance", text, name)

    def test_canonical_memory_describes_one_pr_one_merge_lifecycle(self) -> None:
        overview = normalized((AGENT_DOCS / "project_overview.md").read_text(encoding="utf-8"))
        diary = normalized((AGENT_DOCS / "project_diary.md").read_text(encoding="utf-8"))
        progress = normalized((AGENT_DOCS / "project_progress.md").read_text(encoding="utf-8"))
        latest = normalized((AGENT_DOCS / "latest_session_work.md").read_text(encoding="utf-8"))

        for name, text in (
            ("overview", overview),
            ("diary", diary),
            ("progress", progress),
            ("latest", latest),
        ):
            self.assertIn("acceptance marker", text, name)
            self.assertIn("same", text, name)
            self.assertIn("pr", text, name)
            self.assertTrue(has_private_free_marker(text), name)
            self.assertIn("race", text, name)

        self.assertIn("one human merge", diary)
        self.assertIn("one human merge", progress)
        self.assertIn("one human merge", latest)
        self.assertIn("previous accept", latest)
        self.assertIn("stale", latest)

    def test_review_acceptance_posts_marker_and_user_only_says_accepted(self) -> None:
        review = normalized((ROOT / "planning/prompts/review.md").read_text(encoding="utf-8"))
        execute = normalized((ROOT / "planning/prompts/execute.md").read_text(encoding="utf-8"))

        self.assertIn("skynet-acceptance:v1", review)
        self.assertIn("verdict=accept", review)
        self.assertIn("base=<full reviewed base sha>", review)
        self.assertIn("head=<full reviewed head sha>", review)
        self.assertIn("posts one machine-readable acceptance marker", review)
        self.assertIn("ali only tells the original", review)
        self.assertIn("accepted", review)
        self.assertIn("when ali returns and says `accepted`", execute)
        self.assertIn("fetch the latest `skynet-acceptance:v1` marker", execute)
        self.assertIn("never ask ali for hashes", execute)

    def test_same_pr_closeout_is_bounded_and_no_second_pr(self) -> None:
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
        for name, text in (("construction", construction), ("runbook", runbook), ("sky026", sky026)):
            self.assertIn("same pr", text, name)
            self.assertIn("closeout-only", text, name)
            self.assertIn("one human merge", text, name)
            self.assertIn("directive", text, name)
            self.assertIn("planning", text, name)
            self.assertIn("journal", text, name)
            self.assertIn("stable", text, name)
            self.assertIn("substantive", text, name)

        self.assertIn("there is no second closeout pr", construction)
        self.assertIn("never create a closeout-only pr", runbook)
        self.assertIn("there is **no post-merge closeout pr**", sky026)

    def test_sanctioned_closeout_head_move_does_not_hide_other_staleness(self) -> None:
        texts = {
            path: normalized((ROOT / path).read_text(encoding="utf-8"))
            for path in (
                "docs/conventions/construction.md",
                "runbooks/construction-delegation.md",
                "planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md",
                "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md",
                "planning/prompts/review.md",
                "planning/prompts/execute.md",
            )
        }
        for path, text in texts.items():
            self.assertIn("closeout", text, path)
            self.assertIn("head", text, path)
            self.assertIn("base", text, path)
            self.assertIn("stale", text, path)
            self.assertIn("substantive", text, path)

        self.assertIn("head movement alone does **not** invalidate accept", texts["docs/conventions/construction.md"])
        self.assertIn("reviewed-base movement", texts["planning/prompts/review.md"])
        self.assertIn("marker-head..final-head", texts["planning/prompts/execute.md"])

    def test_lifecycle_surfaces_do_not_reintroduce_post_merge_closeout_pr(self) -> None:
        for path in LIFECYCLE_FILES:
            text = normalized((ROOT / path).read_text(encoding="utf-8"))
            self.assertTrue(has_private_free_marker(text), path)
            for forbidden in FORBIDDEN_OLD_CLOSEOUT:
                self.assertNotIn(forbidden, text, path)

    def test_sky025_p7_has_one_time_transition_without_closeout_pr(self) -> None:
        review = normalized((ROOT / "planning/prompts/review.md").read_text(encoding="utf-8"))
        directive = normalized(
            (
                ROOT
                / "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md"
            ).read_text(encoding="utf-8")
        )
        disposition = normalized((ROOT / "planning/sky-025-map.md").read_text(encoding="utf-8"))
        prompt_readme = normalized((ROOT / "planning/prompts/README.md").read_text(encoding="utf-8"))

        for text in (review, directive, disposition, prompt_readme):
            self.assertIn("one-time", text)
            for pr in ("#235", "#236", "#237", "#239"):
                self.assertIn(pr, text)

        self.assertIn("do not create a standalone p7 closeout pr", review)
        self.assertIn("no standalone p7 closeout pr", directive)
        self.assertIn("no standalone p7 closeout pr", disposition)
        self.assertIn("no standalone p7 closeout pr", prompt_readme)
        self.assertIn("p8 pr", review)
        self.assertIn("current_phase: 7", review)

    def test_corrective_p7_pr_uses_normal_open_pr_mode_not_legacy_mode(self) -> None:
        review = normalized((ROOT / "planning/prompts/review.md").read_text(encoding="utf-8"))
        directive = normalized(
            (
                ROOT
                / "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("mode a · normal open-pr review", review)
        self.assertIn("corrective p7 pr", review)
        self.assertIn("never falls back to mode b", review)
        self.assertIn("legacy p7 fix opens one corrective p7 pr", directive)
        self.assertIn("normal lifecycle", directive)

    def test_sky025_p8_plus_uses_one_open_pr_per_numbered_phase(self) -> None:
        directive = normalized(
            (
                ROOT
                / "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md"
            ).read_text(encoding="utf-8")
        )
        execute = normalized((ROOT / "planning/prompts/execute.md").read_text(encoding="utf-8"))
        prompt_readme = normalized((ROOT / "planning/prompts/README.md").read_text(encoding="utf-8"))
        diary = normalized((AGENT_DOCS / "project_diary.md").read_text(encoding="utf-8"))

        self.assertIn("one open authored pr", directive)
        self.assertIn("one numbered phase = one open pr", execute)
        self.assertIn("internal lettered slices stay on that same phase pr", execute)
        self.assertIn("one open pr for the numbered phase", prompt_readme)
        self.assertIn("one open authored pr per numbered phase", diary)

    def test_sky025_p8_is_prepared_and_blocked_only_on_p7_accept(self) -> None:
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
        self.assertIn("not executable until p7 accept", directive)
        self.assertIn("p7 has just received the one-time legacy accept", execute)
        self.assertIn("p8 pr", progress)

    def test_closure_shapes_and_latest_session_have_one_entry_point(self) -> None:
        construction = (ROOT / "docs/conventions/construction.md").read_text(encoding="utf-8")
        for state in ("implementation ready", "paused", "blocked", "accepted closeout"):
            rows = [line for line in construction.splitlines() if line.startswith(f"| {state} |")]
            self.assertEqual(len(rows), 1, state)
            self.assertEqual(rows[0].count("|"), 4, state)

        latest = (AGENT_DOCS / "latest_session_work.md").read_text(encoding="utf-8")
        self.assertEqual(latest.count("## Next Entry Point"), 1)
        for heading in ("## Verification", "## Pending Work and Blockers", "## Next Entry Point"):
            self.assertIn(heading, latest)

    def test_diary_is_reusable_not_chronological(self) -> None:
        diary = (AGENT_DOCS / "project_diary.md").read_text(encoding="utf-8")
        self.assertIn("## Decisions", diary)
        self.assertIn("## Lessons", diary)
        for forbidden in ("## Timeline", "## Releases", "## Commits", "## Session Log"):
            self.assertNotIn(forbidden, diary)


if __name__ == "__main__":
    unittest.main()
