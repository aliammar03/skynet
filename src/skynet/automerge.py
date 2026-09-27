"""The auto-approve gate for the executor's own revert PR (AGENTS.md §3, the list's one entry).

A revert PR restores `compose/<svc>/` to a tree Ali already merged and the executor verified. It
merges without a human only when every check holds; any failure leaves it open for Ali:

1. the executor opened it: base `main`, branch `revert/<svc>-<12hex>`, author = the executor's
   GitHub login;
2. it changes nothing outside `compose/<svc>/`;
3. its `compose/<svc>/` tree is byte-identical (same git tree id) to the host's `verified`
   revision, and the host's `failed` revision is the one the branch names;
4. `main` has not moved past the failed revision for that service;
5. `bin/check` is green on the PR head.

The merge pins the head it checked (`--match-head-commit`). Every attempt is a recorded
operation; a policy refusal at one head is recorded once and then left alone, and a red
`bin/check` is retried on later passes, up to three times per head.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from skynet import deploy, deployment, writepath
from skynet.writepath import FAILED, UNAVAILABLE, USAGE, Ledger, Operation, WriteError

BRANCH = re.compile(r"revert/([A-Za-z0-9][A-Za-z0-9_.-]*)-([0-9a-f]{12})")
CHECK_SECONDS = 900.0
CHECK_TRIES = 3
CHECK_RED = "bin/check is not green on the PR head"


def open_reverts(repo: Path) -> list[dict[str, Any]]:
    """Open PRs whose branch has the executor's revert shape; everything else is not ours."""
    raw = deploy._ok(["gh", "pr", "list", "--state", "open", "--limit", "100", "--json",
                      "number,headRefName,headRefOid,baseRefName,author,files"],
                     "GitHub PR listing unavailable", cwd=repo)
    try:
        rows = json.loads(raw)
    except ValueError:
        raise WriteError("GitHub PR listing malformed", UNAVAILABLE) from None
    if not isinstance(rows, list):
        raise WriteError("GitHub PR listing malformed", UNAVAILABLE)
    return [row for row in rows if isinstance(row, dict)
            and BRANCH.fullmatch(str(row.get("headRefName", "")))]


def login(repo: Path) -> str:
    name = deploy._ok(["gh", "api", "user", "--jq", ".login"], "GitHub identity unavailable",
                      cwd=repo).decode("utf-8", "replace").strip()
    if not re.fullmatch(r"[A-Za-z0-9-]+", name):
        raise WriteError("GitHub identity unavailable", UNAVAILABLE)
    return name


def fetch_head(repo: Path, branch: str, oid: str) -> None:
    deploy._git(repo, "fetch", "--quiet", "origin", f"refs/heads/{branch}",
                reason="revert branch fetch failed")
    if deploy._git(repo, "rev-parse", "FETCH_HEAD") != oid:
        raise WriteError("revert branch moved while being checked", UNAVAILABLE)


def tree(repo: Path, revision: str, path: str) -> str | None:
    result = deploy._run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet",
                          f"{revision}:{path}"])
    return result.stdout.decode().strip() or None if result.returncode == 0 else None


def check_green(repo: Path, oid: str) -> None:
    """`bin/check` in a throwaway worktree at exactly the PR head, inside the dev shell."""
    with tempfile.TemporaryDirectory(prefix="skynet-automerge-") as tmp:
        work = Path(tmp) / "tree"
        deploy._git(repo, "worktree", "add", "--quiet", "--detach", str(work), oid,
                    reason="check worktree failed")
        try:
            result = deploy._run(["nix", "develop", "--command", "bin/check"], cwd=work,
                                 timeout=CHECK_SECONDS)
        finally:
            deploy._run(["git", "-C", str(repo), "worktree", "remove", "--force", str(work)])
    if result.returncode != 0:
        raise WriteError(CHECK_RED, FAILED)  # may be a blip: retried up to CHECK_TRIES per head


def gate(repo: Path, pr: dict[str, Any], *, context: str, executor: str) -> tuple[str, str]:
    """Every check but `bin/check`; returns (service, failed revision) or raises the reason."""
    match = BRANCH.fullmatch(str(pr.get("headRefName", "")))
    author = pr.get("author")
    if not isinstance(author, dict):
        author = {}
    if match is None or pr.get("baseRefName") != "main":
        raise WriteError("not a revert PR against main", USAGE)
    if author.get("login") != executor:
        raise WriteError("revert PR was not opened by the executor", USAGE)
    service, prefix = match[1], match[2]
    files = [row.get("path") for row in pr.get("files") or [] if isinstance(row, dict)]
    if not files or any(not isinstance(path, str) or not path.startswith(f"compose/{service}/")
                        for path in files):
        raise WriteError(f"revert PR changes files outside compose/{service}/", USAGE)
    facts = deploy.host_facts(context, service)
    if facts.verified is None or facts.failed is None or not facts.failed.startswith(prefix):
        raise WriteError("host facts do not name this failure and a verified revision", USAGE)
    oid = str(pr.get("headRefOid", ""))
    fetch_head(repo, str(pr["headRefName"]), oid)
    path = f"compose/{service}"
    head_tree = tree(repo, oid, path)
    if head_tree is None or head_tree != tree(repo, facts.verified, path):
        raise WriteError("revert tree is not the verified revision's tree", USAGE)
    if deploy.service_revision(repo, service) != facts.failed:
        raise WriteError("main has moved past the failed revision", USAGE)
    return service, facts.failed


def refused_before(ledger: Ledger, target: str, oid: str) -> bool:
    """Leave a PR alone at this head after a policy refusal, or after `CHECK_TRIES` red
    `bin/check` runs (a single red run may be a cache or network blip)."""
    reds = 0
    for entry in ledger.entries():
        if (entry.get("kind") != "automerge" or entry.get("target") != target
                or entry.get("phase") != "final" or entry.get("source") != oid
                or entry.get("outcome") != "refused"):
            continue
        if entry.get("code") == USAGE:
            return True
        reds += entry.get("reason") == CHECK_RED
    return reds >= CHECK_TRIES


def merge_one(repo: Path, pr: dict[str, Any], *, context: str, ledger: Ledger,
              executor: str) -> Operation:
    number, oid = pr.get("number"), str(pr.get("headRefOid", ""))
    operation = Operation("automerge", f"pr/{number}", oid)
    if not isinstance(number, int) or not deployment.REVISION.fullmatch(oid):
        return writepath.refuse(operation, ledger, "malformed PR listing", UNAVAILABLE)

    def preflight() -> None:
        service, failed = gate(repo, pr, context=context, executor=executor)
        operation.note("gate", "ok", f"svc/{service}: failed {failed[:12]} → verified tree")
        check_green(repo, oid)

    def execute(_: None) -> None:
        deploy._ok(["gh", "pr", "merge", str(number), "--squash", "--delete-branch",
                    "--match-head-commit", oid], "gh pr merge failed", FAILED, cwd=repo)

    def verify(_: None) -> dict[str, Any]:
        state = deploy._ok(["gh", "pr", "view", str(number), "--json", "state", "--jq", ".state"],
                           "PR state unavailable", cwd=repo).decode().strip()
        if state != "MERGED":
            raise WriteError("PR is not merged", FAILED)
        return {"state": state}

    def rollback(_: None, error: WriteError) -> str:
        return "not-needed"  # nothing merged, or main now holds the verified tree: both safe

    return writepath.run(operation, ledger, preflight=preflight, snapshot=lambda: None,
                         execute=execute, verify=verify, rollback=rollback,
                         reconcile=lambda: {"idempotent": True})


def run(repo: Path, *, context: str, ledger: Ledger) -> list[dict[str, Any]]:
    """Try every open executor revert PR; results in the shared shape."""
    try:
        prs = open_reverts(repo)
        if not prs:
            return []
        executor = login(repo)
    except WriteError as error:
        return [{"target": "automerge", "outcome": "unavailable", "reason": error.reason,
                 "code": error.code}]
    results = []
    for pr in prs:
        target, oid = f"pr/{pr.get('number')}", str(pr.get("headRefOid", ""))
        try:
            if refused_before(ledger, target, oid):
                continue  # left open for Ali; recorded once at this head
        except WriteError as error:
            results.append({"target": target, "outcome": "unavailable", "reason": error.reason,
                            "code": error.code})
            continue
        results.append(writepath.report(merge_one(repo, pr, context=context, ledger=ledger,
                                                  executor=executor)))
    return results
