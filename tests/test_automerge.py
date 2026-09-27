"""The revert auto-merge gate: every check must hold, and any failure leaves the PR for Ali."""

from pathlib import Path
from typing import Any

import pytest

from skynet import automerge, deploy
from skynet.deploy import HostFacts
from skynet.writepath import Ledger, WriteError

VERIFIED, FAILED, HEAD = "1" * 40, "2" * 40, "9" * 40


class Hub:
    def __init__(self) -> None:
        self.pr: dict[str, Any] = {
            "number": 7, "headRefName": f"revert/demo-{FAILED[:12]}", "headRefOid": HEAD,
            "baseRefName": "main", "author": {"login": "skynet-ops"},
            "files": [{"path": "compose/demo/compose.yaml"}]}
        self.facts = HostFacts(verified=VERIFIED, failed=FAILED)
        self.main = FAILED
        self.trees = {HEAD: "tree-a", VERIFIED: "tree-a"}
        self.green = True
        self.merged: list[list[str]] = []
        self.checks = 0


@pytest.fixture
def hub(monkeypatch: pytest.MonkeyPatch) -> Hub:
    fake = Hub()

    def ok(args: list[str], reason: str, code: int = 3, **kwargs: Any) -> bytes:
        if args[:3] == ["gh", "pr", "merge"]:
            fake.merged.append(args)
            return b""
        if args[:3] == ["gh", "pr", "view"]:
            return b"MERGED\n" if fake.merged else b"OPEN\n"
        raise AssertionError(args)

    def check_green(repo: Path, oid: str) -> None:
        fake.checks += 1
        if not fake.green:
            raise WriteError(automerge.CHECK_RED, 1)

    monkeypatch.setattr(automerge, "open_reverts", lambda repo: [fake.pr])
    monkeypatch.setattr(automerge, "login", lambda repo: "skynet-ops")
    monkeypatch.setattr(automerge, "fetch_head", lambda repo, branch, oid: None)
    monkeypatch.setattr(automerge, "tree", lambda repo, rev, path: fake.trees.get(rev))
    monkeypatch.setattr(automerge, "check_green", check_green)
    monkeypatch.setattr(deploy, "host_facts", lambda context, service: fake.facts)
    monkeypatch.setattr(deploy, "service_revision", lambda repo, service, ref="": fake.main)
    monkeypatch.setattr(deploy, "_ok", ok)
    return fake


def _run(tmp_path: Path) -> list[dict[str, Any]]:
    return automerge.run(tmp_path, context="docker-dmz", ledger=Ledger(tmp_path / "state"))


def test_all_checks_hold_merges_pinned_to_the_checked_head(hub: Hub, tmp_path: Path) -> None:
    [result] = _run(tmp_path)
    assert result["outcome"] == "success"
    assert hub.merged == [["gh", "pr", "merge", "7", "--squash", "--delete-branch",
                           "--match-head-commit", HEAD]]


@pytest.mark.parametrize("breaks, reason", [
    (lambda h: h.pr.update(author={"login": "someone"}), "not opened by the executor"),
    (lambda h: h.pr.update(baseRefName="dev"), "not a revert PR against main"),
    (lambda h: h.pr["files"].append({"path": "AGENTS.md"}), "outside compose/demo/"),
    (lambda h: h.trees.update({HEAD: "tree-b"}), "not the verified revision's tree"),
    (lambda h: setattr(h, "facts", HostFacts(verified=VERIFIED, failed="3" * 40)), "host facts"),
    (lambda h: setattr(h, "main", "4" * 40), "main has moved past"),
    (lambda h: setattr(h, "green", False), "bin/check is not green"),
])
def test_any_failed_check_leaves_the_pr_open(hub: Hub, tmp_path: Path, breaks: Any,
                                             reason: str) -> None:
    breaks(hub)
    [result] = _run(tmp_path)
    assert result["outcome"] == "refused" and reason in result["reason"]
    assert hub.merged == []


def test_a_policy_refusal_is_recorded_once_per_head(hub: Hub, tmp_path: Path) -> None:
    hub.main = "4" * 40
    assert len(_run(tmp_path)) == 1
    assert _run(tmp_path) == []
    hub.pr["headRefOid"] = "8" * 40  # a new push is checked again
    hub.trees["8" * 40] = "tree-a"
    assert len(_run(tmp_path)) == 1


def test_a_red_check_is_retried_then_left_for_ali(hub: Hub, tmp_path: Path) -> None:
    hub.green = False
    for _ in range(automerge.CHECK_TRIES):
        assert _run(tmp_path)[0]["outcome"] == "refused"
    assert _run(tmp_path) == [] and hub.checks == automerge.CHECK_TRIES
    assert hub.merged == []


def test_a_blip_in_bin_check_does_not_block_an_eligible_revert(hub: Hub, tmp_path: Path) -> None:
    hub.green = False
    _run(tmp_path)
    hub.green = True
    assert _run(tmp_path)[0]["outcome"] == "success" and len(hub.merged) == 1


def test_non_revert_branches_are_ignored() -> None:
    assert automerge.BRANCH.fullmatch("revert/demo-" + "a" * 12)
    assert not automerge.BRANCH.fullmatch("feature/revert-demo")
    assert not automerge.BRANCH.fullmatch("revert/demo-" + "a" * 11)
