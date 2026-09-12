"""Narrow contracts for compact agent memory and review/closeout ownership."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


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
SKY025_ACTIVE = Path(
    "planning/projects/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md"
)
SKY025_ARCHIVE = Path(
    "planning/archive/SKY-025-make-operational-outcomes-verifiable-and-prune-misleading-guidance.md"
)
SKY026_ACTIVE = Path(
    "planning/projects/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md"
)
SKY026_ARCHIVE = Path(
    "planning/archive/SKY-026-overhaul-agent-orchestration-around-a-main-worker-swarm.md"
)


def resolve_lifecycle_path(root: Path, active: Path, archive: Path) -> Path:
    locations = [path for path in (active, archive) if (root / path).is_file()]
    if len(locations) != 1:
        raise AssertionError(
            f"expected exactly one lifecycle location for {active.name}; found {len(locations)}"
        )
    return locations[0]


SKY025_PATH = resolve_lifecycle_path(ROOT, SKY025_ACTIVE, SKY025_ARCHIVE)
SKY026_PATH = resolve_lifecycle_path(ROOT, SKY026_ACTIVE, SKY026_ARCHIVE)
LIFECYCLE_FILES = (
    "AGENTS.md",
    ".codex/config.toml",
    "docs/conventions/construction.md",
    "runbooks/construction-delegation.md",
    SKY026_PATH.as_posix(),
    SKY025_PATH.as_posix(),
    "planning/prompts/review.md",
    "planning/prompts/README.md",
    "planning/prompts/execute.md",
    "agent_docs/project_overview.md",
    "agent_docs/project_diary.md",
    "agent_docs/project_progress.md",
    "agent_docs/latest_session_work.md",
)
FORBIDDEN_OLD_CLOSEOUT = (
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

    def test_sky026_has_exactly_one_lifecycle_location(self) -> None:
        locations = [ROOT / SKY026_ACTIVE, ROOT / SKY026_ARCHIVE]
        self.assertEqual(sum(path.exists() for path in locations), 1)
        self.assertTrue(ROOT.joinpath(SKY026_PATH).exists())

    def test_sky025_has_exactly_one_lifecycle_location(self) -> None:
        locations = [ROOT / SKY025_ACTIVE, ROOT / SKY025_ARCHIVE]
        self.assertEqual(sum(path.exists() for path in locations), 1)
        self.assertTrue(ROOT.joinpath(SKY025_PATH).exists())

    def test_sky025_path_resolution_survives_archive_move_without_duplicate(self) -> None:
        source = (ROOT / SKY025_PATH).read_text(encoding="utf-8")
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            active = root / SKY025_ACTIVE
            archive = root / SKY025_ARCHIVE
            active.parent.mkdir(parents=True, exist_ok=True)
            archive.parent.mkdir(parents=True, exist_ok=True)

            active.write_text(source, encoding="utf-8")
            self.assertEqual(
                resolve_lifecycle_path(root, SKY025_ACTIVE, SKY025_ARCHIVE),
                SKY025_ACTIVE,
            )

            active.replace(archive)
            self.assertFalse(active.exists())
            self.assertEqual(
                resolve_lifecycle_path(root, SKY025_ACTIVE, SKY025_ARCHIVE),
                SKY025_ARCHIVE,
            )

            active.write_text(source, encoding="utf-8")
            with self.assertRaises(AssertionError):
                resolve_lifecycle_path(root, SKY025_ACTIVE, SKY025_ARCHIVE)

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
        self.assertIn("frozen because", construction)

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
            self.assertTrue(
                "acceptance marker" in text or "skynet-acceptance:v1" in text,
                f"{name}: missing reviewer acceptance marker contract",
            )
            self.assertIn("same", text, name)
            self.assertIn("pr", text, name)
            self.assertTrue(has_private_free_marker(text), name)
            self.assertTrue(
                "race" in text or "non-atomic" in text,
                f"{name}: missing private-Free race limitation",
            )

        self.assertIn("one human merge", diary)
        self.assertIn("one human merge", progress)
        self.assertIn("one human merge", latest)
        self.assertTrue(
            "previous accept" in latest or "accept is stale" in latest or "externally accepted" in latest,
            "latest: missing current acceptance state",
        )

    def test_review_acceptance_posts_marker_and_user_only_says_accepted(self) -> None:
        review = normalized((ROOT / "planning/prompts/review.md").read_text(encoding="utf-8"))
        execute = normalized((ROOT / "planning/prompts/execute.md").read_text(encoding="utf-8"))

        self.assertIn("skynet-acceptance:v1", review)
        self.assertIn("verdict=accept", review)
        self.assertIn("base=<full reviewed base sha>", review)
        self.assertIn("head=<full reviewed head sha>", review)
        self.assertIn("post exactly one machine-readable acceptance marker", review)
        self.assertIn("ali only tells the original", review)
        self.assertIn("accepted", review)
        self.assertIn("when ali returns and says `accepted`", execute)
        self.assertIn("fetch the latest `skynet-acceptance:v1` marker", execute)
        self.assertIn("never ask ali for hashes", execute)

    def test_legacy_p7_acceptance_is_durable_and_revalidated_before_p8(self) -> None:
        review = normalized((ROOT / "planning/prompts/review.md").read_text(encoding="utf-8"))
        execute = normalized((ROOT / "planning/prompts/execute.md").read_text(encoding="utf-8"))
        prompt_readme = normalized((ROOT / "planning/prompts/README.md").read_text(encoding="utf-8"))

        self.assertIn("skynet-legacy-acceptance:v1", review)
        self.assertIn("scope=sky-025 p7", review)
        self.assertIn("integrated_main=<full reviewed main sha>", review)
        self.assertIn("merged pr #239 conversation", review)
        self.assertIn("durable handoff", review)
        self.assertIn("ali never copies or compares its sha", review)

        self.assertIn("fetch the latest valid `skynet-legacy-acceptance:v1` marker", execute)
        self.assertIn("merged **pr #239**", execute)
        self.assertIn("do not rely on the previous review chat", execute)
        self.assertIn("current `main` to equal the marker's `integrated_main`", execute)
        self.assertIn("p7 accept stale/missing", execute)
        self.assertIn("do not advance p7 state from a stale marker", execute)
        self.assertIn("any intervening `main` movement", execute)
        self.assertIn("fresh one-time p7 mode b review", execute)

        self.assertIn("skynet-legacy-acceptance:v1", prompt_readme)
        self.assertIn("durable legacy-acceptance anchor", prompt_readme)
        self.assertIn("any intervening `main` movement makes the legacy accept stale", prompt_readme)

    def test_same_pr_closeout_is_bounded_and_no_second_pr(self) -> None:
        construction = normalized(
            (ROOT / "docs/conventions/construction.md").read_text(encoding="utf-8")
        )
        runbook = normalized(
            (ROOT / "runbooks/construction-delegation.md").read_text(encoding="utf-8")
        )
        sky026 = normalized((ROOT / SKY026_PATH).read_text(encoding="utf-8"))
        for name, text in (("construction", construction), ("runbook", runbook), ("sky026", sky026)):
            self.assertIn("same pr", text, name)
            self.assertIn("closeout-only", text, name)
            self.assertIn("one human merge", text, name)
            self.assertIn("directive", text, name)
            self.assertIn("planning", text, name)
            self.assertIn("journal", text, name)
            self.assertIn("stable", text, name)
            self.assertIn("substantive", text, name)

        self.assertIn("second closeout pr", construction)
        self.assertIn("no automatic second acceptance review", construction)
        self.assertIn("never create a closeout-only pr", runbook)
        self.assertIn("there is **no post-merge closeout pr**", sky026)

    def test_sanctioned_closeout_head_move_does_not_hide_other_staleness(self) -> None:
        paths = (
            Path("docs/conventions/construction.md"),
            Path("runbooks/construction-delegation.md"),
            SKY026_PATH,
            SKY025_PATH,
            Path("planning/prompts/review.md"),
            Path("planning/prompts/execute.md"),
        )
        texts = {
            path.as_posix(): normalized((ROOT / path).read_text(encoding="utf-8")) for path in paths
        }
        for path, text in texts.items():
            self.assertIn("closeout", text, path)
            self.assertIn("head", text, path)
            self.assertIn("base", text, path)
            self.assertTrue(
                "stale" in text or "invalidates accept" in text,
                f"{path}: missing stale-accept semantics",
            )
            self.assertIn("substantive", text, path)

        self.assertIn("head movement alone does **not** invalidate accept", texts["docs/conventions/construction.md"])
        self.assertIn("reviewed-base movement", texts["planning/prompts/review.md"])
        self.assertIn("marker-head..final-head", texts["planning/prompts/execute.md"])

    def test_lifecycle_surfaces_do_not_reintroduce_old_closeout_sequence(self) -> None:
        for path in LIFECYCLE_FILES:
            text = normalized((ROOT / path).read_text(encoding="utf-8"))
            self.assertTrue(has_private_free_marker(text), path)
            for forbidden in FORBIDDEN_OLD_CLOSEOUT:
                self.assertNotIn(forbidden, text, path)

    def test_sky025_p7_has_one_time_transition_without_closeout_pr(self) -> None:
        review = normalized((ROOT / "planning/prompts/review.md").read_text(encoding="utf-8"))
        directive = normalized((ROOT / SKY025_PATH).read_text(encoding="utf-8"))
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
        self.assertIn("current_phase 7", review)

    def test_corrective_p7_pr_uses_normal_open_pr_mode_not_legacy_mode(self) -> None:
        review = normalized((ROOT / "planning/prompts/review.md").read_text(encoding="utf-8"))
        directive = normalized((ROOT / SKY025_PATH).read_text(encoding="utf-8"))
        self.assertIn("mode a · normal open-pr review", review)
        self.assertIn("corrective p7 pr", review)
        self.assertIn("never falls back to mode b", review)
        self.assertIn("legacy p7 fix opens one corrective p7 pr", directive)
        self.assertIn("normal lifecycle", directive)

    def test_sky025_p8_plus_uses_one_open_pr_per_numbered_phase(self) -> None:
        directive = normalized((ROOT / SKY025_PATH).read_text(encoding="utf-8"))
        execute = normalized((ROOT / "planning/prompts/execute.md").read_text(encoding="utf-8"))
        prompt_readme = normalized((ROOT / "planning/prompts/README.md").read_text(encoding="utf-8"))
        diary = normalized((AGENT_DOCS / "project_diary.md").read_text(encoding="utf-8"))

        self.assertIn("one open authored pr", directive)
        self.assertIn("one numbered phase = one open pr", execute)
        self.assertIn("internal lettered slices stay on that same phase pr", execute)
        self.assertIn("one open pr for the numbered phase", prompt_readme)
        self.assertIn("one open authored pr per numbered phase", diary)

    def test_sky025_p8_is_prepared_and_blocked_only_on_valid_p7_accept(self) -> None:
        directive = normalized((ROOT / SKY025_PATH).read_text(encoding="utf-8"))
        disposition = normalized((ROOT / "planning/sky-025-map.md").read_text(encoding="utf-8"))
        execute = normalized((ROOT / "planning/prompts/execute.md").read_text(encoding="utf-8"))
        progress = normalized((AGENT_DOCS / "project_progress.md").read_text(encoding="utf-8"))

        for text in (directive, disposition, progress):
            self.assertIn("p8", text)
            self.assertIn("prepared", text)
        self.assertIn("not executable until p7 accept", directive)
        self.assertIn("skynet-legacy-acceptance:v1", execute)
        self.assertIn("p7 accept stale/missing", execute)
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
