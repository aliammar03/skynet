"""Focused contract tests for the one-time SKY-025 P7 legacy review gate."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def p8_released(markers: list[dict[str, str]], current_main: str) -> bool:
    """Model the documented P8 gate: only the newest P7 marker can authorize P8."""
    if not markers:
        return False
    latest = markers[-1]
    return (
        latest.get("scope") == "SKY-025 P7"
        and latest.get("anchor_pr") == "239"
        and latest.get("verdict") == "ACCEPT"
        and latest.get("integrated_main") == current_main
    )


def marker(verdict: str, revision: str) -> dict[str, str]:
    return {
        "scope": "SKY-025 P7",
        "anchor_pr": "239",
        "verdict": verdict,
        "integrated_main": revision,
    }


def test_newer_fix_revokes_older_accept_on_same_main() -> None:
    revision = "a" * 40
    assert p8_released([marker("ACCEPT", revision)], revision)
    assert not p8_released([marker("ACCEPT", revision), marker("FIX", revision)], revision)


def test_newer_blocked_revokes_older_accept_on_same_main() -> None:
    revision = "b" * 40
    assert p8_released([marker("ACCEPT", revision)], revision)
    assert not p8_released([marker("ACCEPT", revision), marker("BLOCKED", revision)], revision)


def test_main_movement_stales_latest_accept() -> None:
    accepted = "c" * 40
    current = "d" * 40
    assert not p8_released([marker("ACCEPT", accepted)], current)


def test_prompts_encode_newest_marker_semantics() -> None:
    review = (ROOT / "planning/prompts/review.md").read_text(encoding="utf-8").lower()
    execute = (ROOT / "planning/prompts/execute.md").read_text(encoding="utf-8").lower()
    readme = (ROOT / "planning/prompts/readme.md").read_text(encoding="utf-8").lower()

    assert "for **every** mode b verdict" in review
    assert "verdict=<accept|fix|blocked>" in review
    assert "newer fix or blocked marker" in review
    assert "select the **newest**" in execute
    assert "newest marker `verdict=accept`" in execute
    assert "never fall back to an older accept marker" in execute
    assert "newer fix or blocked supersedes every older accept" in readme
