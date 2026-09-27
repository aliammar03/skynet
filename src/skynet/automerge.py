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
`bin/check` or a merge that did not land is retried on later passes, up to three times per head.
The gate runs twice: before `bin/check`, and again under the write lock against the PR's
current metadata from GitHub (state, base, head, author) and a freshly fetched `main`, so a
retargeted PR or a fix merged meanwhile is never merged over. After the merge, the squash commit
must be on `main` and hold exactly the verified service tree.
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
NOT_MERGED = "gh pr merge failed; the PR did not merge"
MERGE_UNKNOWN = "gh pr merge failed and whether the PR merged is unknown"
MIXED = "the squash commit's service tree is not the verified tree (main moved during the merge)"
CHECK_RED = "bin/check did not pass on the PR head (red, timed out, or could not run)"


def open_reverts(repo: Path) -> list[dict[str, Any]]:
    """Open PRs whose branch has the executor's revert shape; everything else is not ours."""
    raw = deploy._ok(["gh", "pr", "list", "--state", "open", "--limit", "100", "--json",
                      "number,headRefName,headRefOid,baseRefName,author"],
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
    """Fetch the PR head into a private ref (never FETCH_HEAD, which `skynet watch`'s own fetch
    rewrites in the same checkout) and require it to be the head the listing named."""
    ref = f"refs/skynet/automerge/{branch}"
    deploy._git(repo, "fetch", "--quiet", "--no-tags", "origin", f"+refs/heads/{branch}:{ref}",
                reason="revert branch fetch failed")
    if deploy._git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}",
                   reason="revert branch fetch failed") != oid:
        raise WriteError("revert branch moved while being checked", UNAVAILABLE)


def changed_files(repo: Path, oid: str) -> list[str]:
    """Every path the PR changes against its merge base with main, from git itself (a GitHub
    file listing can be capped). Renames count as both paths."""
    names = deploy._git(repo, "diff", "--name-only", "--no-renames", f"{deploy.MAIN}...{oid}",
                        reason="revert diff unavailable")
    return [name for name in names.splitlines() if name]


def tree(repo: Path, revision: str, path: str) -> str | None:
    result = deploy._run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet",
                          f"{revision}:{path}"])
    return result.stdout.decode().strip() or None if result.returncode == 0 else None


def check_green(repo: Path, oid: str) -> None:
    """`bin/check` in a throwaway worktree at exactly the PR head, inside the dev shell.

    Red, timed out, or unable to start all count as one CHECK_RED try, so the retry limit
    bounds every kind of failure. Runs outside the write lock: it can take minutes.
    """
    try:
        with tempfile.TemporaryDirectory(prefix="skynet-automerge-") as tmp:
            work = Path(tmp) / "tree"
            deploy._git(repo, "worktree", "add", "--quiet", "--detach", str(work), oid,
                        reason="check worktree failed")
            try:
                result = deploy._run(["nix", "develop", "--command", "bin/check"], cwd=work,
                                     timeout=CHECK_SECONDS)
            finally:
                deploy._run(["git", "-C", str(repo), "worktree", "remove", "--force", str(work)])
    except WriteError:
        raise WriteError(CHECK_RED, FAILED) from None
    if result.returncode != 0:
        raise WriteError(CHECK_RED, FAILED)


def gate(repo: Path, pr: dict[str, Any], *, context: str,
         executor: str) -> tuple[str, str, str]:
    """Every check but `bin/check`; returns (service, failed, verified) or raises the reason."""
    match = BRANCH.fullmatch(str(pr.get("headRefName", "")))
    author = pr.get("author")
    if not isinstance(author, dict):
        author = {}
    if match is None or pr.get("baseRefName") != "main":
        raise WriteError("not a revert PR against main", USAGE)
    if author.get("login") != executor:
        raise WriteError("revert PR was not opened by the executor", USAGE)
    service, prefix = match[1], match[2]
    facts = deploy.host_facts(context, service)
    if facts.verified is None or facts.failed is None or not facts.failed.startswith(prefix):
        raise WriteError("host facts do not name this failure and a verified revision", USAGE)
    oid = str(pr.get("headRefOid", ""))
    deploy.fetch(repo)  # main as it is now: a fix merged meanwhile must win over the revert
    fetch_head(repo, str(pr["headRefName"]), oid)
    files = changed_files(repo, oid)
    if not files or any(not path.startswith(f"compose/{service}/") for path in files):
        raise WriteError(f"revert PR changes files outside compose/{service}/", USAGE)
    path = f"compose/{service}"
    head_tree = tree(repo, oid, path)
    if head_tree is None or head_tree != tree(repo, facts.verified, path):
        raise WriteError("revert tree is not the verified revision's tree", USAGE)
    if deploy.service_revision(repo, service) != facts.failed:
        raise WriteError("main has moved past the failed revision", USAGE)
    return service, facts.failed, facts.verified


def landed_as_verified(repo: Path, merge: str, service: str, verified: str) -> None:
    """`--match-head-commit` pins the PR head, not main: a fix to another file of the same
    service merged in the seconds before the squash would be mixed in. Require the squash commit's
    `compose/<svc>/` to be exactly the verified tree; otherwise it is `rollback-failed` and alerts."""
    if not deployment.REVISION.fullmatch(merge):
        raise WriteError(MIXED, FAILED)
    deploy.fetch(repo)
    if not deploy.merged(repo, merge):  # the destination: the squash must be on main itself
        raise WriteError("the merge commit is not on main", FAILED)
    path = f"compose/{service}"
    landed = tree(repo, merge, path)
    if landed is None or landed != tree(repo, verified, path):
        raise WriteError(MIXED, FAILED)


def fresh_pr(repo: Path, number: int) -> dict[str, Any]:
    """The PR's current metadata, straight from GitHub (never the pass's old listing)."""
    raw = deploy._ok(["gh", "pr", "view", str(number), "--json",
                      "number,state,baseRefName,headRefName,headRefOid,author"],
                     "PR state unavailable", cwd=repo)
    try:
        current = json.loads(raw)
    except ValueError:
        raise WriteError("PR state unavailable", UNAVAILABLE) from None
    if not isinstance(current, dict):
        raise WriteError("PR state unavailable", UNAVAILABLE)
    return current


def pr_state(repo: Path, number: int) -> str | None:
    """OPEN, CLOSED, or MERGED; None when GitHub can't say."""
    try:
        state = deploy._ok(["gh", "pr", "view", str(number), "--json", "state", "--jq", ".state"],
                           "PR state unavailable", cwd=repo).decode().strip()
    except WriteError:
        return None
    return state if state in {"OPEN", "CLOSED", "MERGED"} else None


def refused_before(ledger: Ledger, target: str, oid: str) -> bool:
    """Leave a PR alone at this head after a policy refusal, or after `CHECK_TRIES` attempts
    that failed for a reason that might pass next time (a red `bin/check`, a merge that did not
    land)."""
    tries = 0
    for entry in ledger.entries():
        if (entry.get("kind") != "automerge" or entry.get("target") != target
                or entry.get("phase") != "final" or entry.get("source") != oid):
            continue
        if entry.get("outcome") == "refused" and entry.get("code") == USAGE:
            return True
        tries += (entry.get("outcome") == "refused" and entry.get("reason") == CHECK_RED
                  or entry.get("outcome") in {"failed", "rolled-back", "rollback-failed"})
    return tries >= CHECK_TRIES


def merge_one(repo: Path, pr: dict[str, Any], *, context: str, ledger: Ledger,
              executor: str) -> Operation:
    number, oid = pr.get("number"), str(pr.get("headRefOid", ""))
    operation = Operation("automerge", f"pr/{number}", oid)
    if not isinstance(number, int) or not deployment.REVISION.fullmatch(oid):
        return writepath.refuse(operation, ledger, "malformed PR listing", UNAVAILABLE)

    # The slow checks run before the write lock is taken; a refusal is recorded like any other.
    try:
        service, failed, verified = gate(repo, pr, context=context, executor=executor)
        check_green(repo, oid)
    except WriteError as error:
        return writepath.refuse(operation, ledger, error.reason, error.code)
    operation.note("gate", "ok", f"svc/{service}: failed {failed[:12]} → verified tree; bin/check green")
    merge_sent = False

    def preflight() -> None:
        """Under the lock, just before merging: the PR as GitHub has it now (state, base, head,
        author) and a freshly fetched main, since `bin/check` may have taken minutes."""
        nonlocal verified
        current = fresh_pr(repo, number)
        if current.get("state") != "OPEN":  # Ali may have closed it to fix forward
            raise WriteError("PR is no longer open", USAGE)
        if (current.get("headRefName"), current.get("headRefOid")) != (pr.get("headRefName"), oid):
            raise WriteError("PR head changed since it was checked", USAGE)
        verified = gate(repo, current, context=context, executor=executor)[2]

    def execute(_: None) -> None:
        nonlocal merge_sent
        merge_sent = True  # from here a failure may leave a merged PR: rollback must not pass it
        try:
            deploy._ok(["gh", "pr", "merge", str(number), "--squash", "--delete-branch",
                        "--match-head-commit", oid], "gh pr merge failed", FAILED, cwd=repo)
        except WriteError as error:
            state = pr_state(repo, number)
            if state == "MERGED":  # it landed (the error was e.g. the branch delete): verify it
                operation.note("merge", "ok", f"landed despite: {error.reason}")
                return
            if state in {"OPEN", "CLOSED"} and not error.reason.endswith("timed out"):
                raise WriteError(NOT_MERGED, FAILED) from None
            raise WriteError(MERGE_UNKNOWN, FAILED) from None

    def verify(_: None) -> dict[str, Any]:
        state, _space, merge = deploy._ok(
            ["gh", "pr", "view", str(number), "--json", "state,mergeCommit", "--jq",
             '[.state, (.mergeCommit.oid // "")] | join(" ")'],
            "PR state unavailable", cwd=repo).decode().strip().partition(" ")
        if state != "MERGED":
            raise WriteError("PR is not merged", FAILED)
        landed_as_verified(repo, merge, service, verified)
        return {"state": state, "merge_commit": merge}

    def rollback(_: None, error: WriteError) -> str:
        """Only a merge that surely did not happen is safe to leave. A merge that landed, or may
        have, and is not verified is rollback-failed, which alerts: a bot never undoes a merge."""
        if merge_sent and error.reason != NOT_MERGED:
            raise WriteError("merge landed or may have, but is not verified; check main by hand")
        return "not-needed"

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
