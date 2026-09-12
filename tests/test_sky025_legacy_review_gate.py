"""Focused contracts for SKY-025 durable review-state gates."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def p8_released(markers: list[dict[str, str]], current_main: str) -> bool:
    """Only the newest legacy P7 marker can authorize P8."""
    if not markers:
        return False
    latest = markers[-1]
    return (
        latest.get("scope") == "SKY-025 P7"
        and latest.get("anchor_pr") == "239"
        and latest.get("verdict") == "ACCEPT"
        and latest.get("integrated_main") == current_main
    )


def legacy_marker(verdict: str, revision: str) -> dict[str, str]:
    return {
        "scope": "SKY-025 P7",
        "anchor_pr": "239",
        "verdict": verdict,
        "integrated_main": revision,
    }


def closeout_released(
    markers: list[dict[str, str]], scope: str, current_base: str, current_head: str
) -> bool:
    """Only the newest normal open-PR verdict can authorize accepted closeout."""
    if not markers:
        return False
    latest = markers[-1]
    return (
        latest.get("scope") == scope
        and latest.get("verdict") == "ACCEPT"
        and latest.get("base") == current_base
        and latest.get("head") == current_head
    )


def normal_marker(verdict: str, base: str, head: str) -> dict[str, str]:
    return {
        "scope": "SKY-025 P8",
        "verdict": verdict,
        "base": base,
        "head": head,
    }


def test_newer_legacy_fix_revokes_older_accept_on_same_main() -> None:
    revision = "a" * 40
    assert p8_released([legacy_marker("ACCEPT", revision)], revision)
    assert not p8_released(
        [legacy_marker("ACCEPT", revision), legacy_marker("FIX", revision)], revision
    )


def test_newer_legacy_blocked_revokes_older_accept_on_same_main() -> None:
    revision = "b" * 40
    assert p8_released([legacy_marker("ACCEPT", revision)], revision)
    assert not p8_released(
        [legacy_marker("ACCEPT", revision), legacy_marker("BLOCKED", revision)], revision
    )


def test_main_movement_stales_latest_legacy_accept() -> None:
    accepted = "c" * 40
    current = "d" * 40
    assert not p8_released([legacy_marker("ACCEPT", accepted)], current)


def test_newer_normal_fix_revokes_older_accept_on_same_revision() -> None:
    base = "e" * 40
    head = "f" * 40
    markers = [normal_marker("ACCEPT", base, head), normal_marker("FIX", base, head)]
    assert not closeout_released(markers, "SKY-025 P8", base, head)


def test_newer_normal_blocked_revokes_older_accept_on_same_revision() -> None:
    base = "1" * 40
    head = "2" * 40
    markers = [normal_marker("ACCEPT", base, head), normal_marker("BLOCKED", base, head)]
    assert not closeout_released(markers, "SKY-025 P8", base, head)


def test_newest_malformed_normal_marker_fails_closed() -> None:
    base = "3" * 40
    head = "4" * 40
    markers = [normal_marker("ACCEPT", base, head), {"scope": "SKY-025 P8", "verdict": "ACCEPT"}]
    assert not closeout_released(markers, "SKY-025 P8", base, head)


def test_normal_base_or_head_movement_stales_accept() -> None:
    base = "5" * 40
    head = "6" * 40
    markers = [normal_marker("ACCEPT", base, head)]
    assert closeout_released(markers, "SKY-025 P8", base, head)
    assert not closeout_released(markers, "SKY-025 P8", "7" * 40, head)
    assert not closeout_released(markers, "SKY-025 P8", base, "8" * 40)


def test_prompts_encode_newest_marker_semantics_without_mode_jargon() -> None:
    review = (ROOT / "planning/prompts/review.md").read_text(encoding="utf-8").lower()
    execute = (ROOT / "planning/prompts/execute.md").read_text(encoding="utf-8").lower()
    readme = (ROOT / "planning/prompts/README.md").read_text(encoding="utf-8").lower()

    assert "verdict=<accept|fix|blocked>" in review
    assert "newest applicable marker wins" in review
    assert "newer fix or blocked marker" in review
    assert "select the **newest" in execute
    assert "newer fix/blocked" in execute
    assert "do not search for the newest accept" in execute
    assert "newest applicable verdict wins" in readme
    assert "mode a" not in review
    assert "mode b" not in review
    assert "mode a" not in execute
    assert "mode b" not in execute
