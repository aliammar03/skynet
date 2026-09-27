"""The revert auto-merge gate: every check must hold, and any failure leaves the PR for Ali."""

import subprocess
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
        self.fetches = 0
        self.main_after_check: str | None = None  # a fix Ali merges while bin/check runs
        self.merge_fails = False


@pytest.fixture
def hub(monkeypatch: pytest.MonkeyPatch) -> Hub:
    fake = Hub()

    def ok(args: list[str], reason: str, code: int = 3, **kwargs: Any) -> bytes:
        if args[:3] == ["gh", "pr", "merge"]:
            if fake.merge_fails:
                raise WriteError(reason, code)
            fake.merged.append(args)
            return b""
        if args[:3] == ["gh", "pr", "view"]:
            return b"MERGED\n" if fake.merged else b"OPEN\n"
        raise AssertionError(args)

    def check_green(repo: Path, oid: str) -> None:
        fake.checks += 1
        if fake.main_after_check:
            fake.pending_main = fake.main_after_check
        if not fake.green:
            raise WriteError(automerge.CHECK_RED, 1)

    monkeypatch.setattr(automerge, "open_reverts", lambda repo: [fake.pr])
    monkeypatch.setattr(automerge, "login", lambda repo: "skynet-ops")
    def fetch(repo: Path) -> None:
        fake.fetches += 1
        fake.main = getattr(fake, "pending_main", fake.main)

    monkeypatch.setattr(automerge, "fetch_head", lambda repo, branch, oid: None)
    monkeypatch.setattr(automerge, "changed_files", lambda repo, oid: [
        row["path"] for row in fake.pr["files"]])
    monkeypatch.setattr(deploy, "fetch", fetch)
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
    (lambda h: setattr(h, "green", False), "bin/check did not pass"),
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


def test_bin_check_runs_outside_the_write_lock(hub: Hub, tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    held: list[bool] = []
    monkeypatch.setattr(automerge, "check_green",
                        lambda repo, oid: held.append(Ledger(tmp_path / "state").busy()))
    assert _run(tmp_path)[0]["outcome"] == "success" and held == [False]


def test_a_timed_out_check_counts_toward_the_retry_limit(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The real check_green, with the dev shell timing out."""
    calls: list[str] = []

    def run(args: list[str], **kwargs: Any) -> Any:
        if args[0] == "nix":
            calls.append("nix")
            raise WriteError("nix timed out", 3)
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(deploy, "_git", lambda repo, *args, reason="": "")
    monkeypatch.setattr(deploy, "_run", run)
    for _ in range(automerge.CHECK_TRIES):
        with pytest.raises(WriteError) as raised:
            automerge.check_green(tmp_path, HEAD)
        assert (raised.value.reason, raised.value.code) == (automerge.CHECK_RED, 1)
    assert calls == ["nix"] * automerge.CHECK_TRIES


def test_a_fix_merged_during_bin_check_wins_over_the_revert(hub: Hub, tmp_path: Path) -> None:
    """The gate re-runs under the lock against a freshly fetched main."""
    hub.main_after_check = "5" * 40
    [result] = _run(tmp_path)
    assert result["outcome"] == "refused" and "main has moved past" in result["reason"]
    assert hub.merged == [] and hub.fetches == 2


def test_a_merge_that_keeps_failing_stops_after_the_retry_limit(hub: Hub, tmp_path: Path) -> None:
    hub.merge_fails = True
    for _ in range(automerge.CHECK_TRIES):
        assert _run(tmp_path)[0]["outcome"] == "failed"
    assert _run(tmp_path) == [] and hub.checks == automerge.CHECK_TRIES


def test_fetch_head_uses_a_private_ref_not_fetch_head(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, ...]] = []

    def git(repo: Path, *args: str, reason: str = "") -> str:
        seen.append(args)
        return HEAD
    monkeypatch.setattr(deploy, "_git", git)
    automerge.fetch_head(tmp_path, "revert/demo-abc", HEAD)
    assert seen[0][-1] == "+refs/heads/revert/demo-abc:refs/skynet/automerge/revert/demo-abc"
    assert all("FETCH_HEAD" not in arg for args in seen for arg in args)


def test_changed_files_come_from_git_against_main(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "compose" / "demo").mkdir(parents=True)
    (repo / "compose" / "demo" / "compose.yaml").write_text("a\n")
    (repo / "AGENTS.md").write_text("rules\n")

    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c",
                               "user.email=t@t", *args], check=True, capture_output=True,
                              text=True).stdout.strip()
    git("init", "-q")
    git("add", "-A")
    git("commit", "-qm", "base")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    (repo / "compose" / "demo" / "compose.yaml").write_text("b\n")
    git("mv", "AGENTS.md", "compose/demo/AGENTS.md")  # a rename out of a protected path
    git("commit", "-qam", "revert")
    assert automerge.changed_files(repo, git("rev-parse", "HEAD")) == [
        "AGENTS.md", "compose/demo/AGENTS.md", "compose/demo/compose.yaml"]
