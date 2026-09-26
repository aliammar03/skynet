"""The local hard-law gates: `invariants.json` against the tree, and the staged-tree secret scan.

A non-LLM process enforces the hard laws (ADR 0003): the pre-commit hook and `bin/check` run
`skynet check`. T1 local — reads repository files and runs read-only `git`. No network, no
secrets, no writes. The gate checks stored observations, not current live-state freshness.
An unreadable, malformed, or unscannable source is a violation, never a pass.
"""

import json
import re
import subprocess
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from skynet import entities

INVARIANTS = "invariants.json"
_KEY_BLOCK = re.compile(r"BEGIN ([A-Z0-9]+ )?PRIVATE KEY")
# grep is line-oriented, so its [[:space:]] never spans a newline; neither does [^\S\n].
_ASSIGNMENT = re.compile(
    r"(API_?KEY|SECRET|TOKEN|PASSWORD|PASSWD)[^\S\n]*[:=][^\S\n]*\"?[A-Za-z0-9/_+=.-]{20,}",
    re.IGNORECASE,
)


class GateError(Exception):
    """The gate cannot run at all (exit 2), as opposed to finding a violation (exit 1)."""


@dataclass(frozen=True)
class Gate:
    """One named law: its heading, its pass message, and a function returning violations."""

    title: str
    passed: Callable[[Path, dict[str, Any]], str]
    run: Callable[[Path, dict[str, Any]], list[str]]


def load_invariants(repo: Path) -> dict[str, Any]:
    """Read the authored hard-law registry; its absence stops the gate."""
    try:
        data = json.loads((repo / INVARIANTS).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise GateError(f"{INVARIANTS} not readable at the repo root") from None
    if not isinstance(data, dict):
        raise GateError(f"{INVARIANTS} is not an object")
    return data


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None


def _snapshots(repo: Path) -> list[tuple[Path, Any]]:
    return [(path, _json(path)) for path in sorted((repo / "inventory").glob("proxmox-*.json"))]


def _node_of(snapshot: dict[str, Any]) -> str:
    """Canonical node name: the node-typed resource, else the top-level `node`."""
    for resource in snapshot.get("nodes") or []:
        if isinstance(resource, dict) and resource.get("type") == "node" and resource.get("node"):
            return str(resource["node"])
    return str(snapshot.get("node"))


def _pools(snapshot: dict[str, Any]) -> list[dict[str, Any]] | None:
    """The snapshot's pools; None when the pool list or any pool entry is malformed."""
    pools = snapshot.get("pools", [])
    if not isinstance(pools, list) or not all(isinstance(pool, dict) for pool in pools):
        return None
    return pools


def _valid_members(members: Any) -> bool:
    """A readable membership: a list of objects whose `vmid`, when present, is an integer."""
    return isinstance(members, list) and all(
        isinstance(member, dict)
        and ("vmid" not in member or type(member["vmid"]) is int)
        for member in members)


def excluded_guests(repo: Path, invariants: dict[str, Any]) -> list[str]:
    """Excluded guests never appear as a pool member; unreadable membership cannot pass."""
    excluded = [int(guest["vmid"]) for guest in invariants["excluded_guests"]["guests"]]
    violations = []
    for path, snapshot in _snapshots(repo):
        if not isinstance(snapshot, dict):
            violations.append(f"{path.name}: unreadable or malformed — cannot verify exclusions")
            continue
        node = _node_of(snapshot)
        pools = _pools(snapshot)
        if pools is None:
            violations.append(f"{node} ({path.name}): malformed pool list — cannot verify exclusions")
            continue
        # members:null means membership was unreadable at collect time (fix Pool.Audit, recollect).
        if any(pool.get("members") is None for pool in pools):
            violations.append(f"{node} ({path.name}): a pool has members:null (unreadable) — "
                              "cannot verify exclusions")
        # Any other non-list shape is refused, never filtered: dropping entries could hide a guest.
        if any(pool.get("members") is not None and not _valid_members(pool["members"])
               for pool in pools):
            violations.append(f"{node} ({path.name}): a pool has malformed members — "
                              "cannot verify exclusions")
        readable = [pool for pool in pools if _valid_members(pool.get("members"))]
        for vmid in excluded:
            holding = [str(pool.get("poolid")) for pool in readable
                       if any(member.get("vmid") == vmid for member in pool["members"])]
            if holding:
                violations.append(f"{node}: excluded guest {vmid} is a member of pool(s) "
                                  f"[{', '.join(holding)}] — it must NEVER join a pool")
    return violations


def pool_set(repo: Path, invariants: dict[str, Any]) -> list[str]:
    """The observed ops-managed pool set equals the declared blast-radius dial."""
    declared = sorted(f"{pool['node']}\t{pool['pool']}"
                      for pool in invariants["ops_managed_pools"]["pools"])
    observed: list[str] = []
    for path, snapshot in _snapshots(repo):
        if not isinstance(snapshot, dict):
            return [f"{path.name}: unreadable or malformed — cannot observe the pool set"]
        node = _node_of(snapshot)
        pools = _pools(snapshot)
        if pools is None:
            return [f"{path.name}: malformed pool list — cannot observe the pool set"]
        observed.extend(f"{node}\t{pool.get('poolid')}" for pool in pools)
    observed.sort()
    if declared == observed:
        return []
    missing = sorted((Counter(declared) - Counter(observed)).elements())
    extra = sorted((Counter(observed) - Counter(declared)).elements())
    return ["pool-set drift — declared (invariants.json) vs observed (inventory) differ:"
            + "".join(f"\n        < declared only: {line}" for line in missing)
            + "".join(f"\n        > observed only: {line}" for line in extra)
            + "\n      (changing the declared set is a docs/system-design.md PR — it is the dial)"]


def secret_patterns(repo: Path, invariants: dict[str, Any]) -> list[str]:
    """No declared plaintext-secret pattern in tracked, non-allowlisted files."""
    excludes = []
    for entry in invariants["secret_patterns"]["allow"]:
        excludes += [f":(exclude){entry['glob']}", f":(exclude)**/{entry['glob']}"]
    violations = []
    for entry in invariants["secret_patterns"]["patterns"]:
        pattern = entry["pattern"]
        result = subprocess.run(["git", "grep", "-nIE", "-e", pattern, "--", ".", *excludes],
                                cwd=repo, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            hits = "".join(f"\n        {line}" for line in result.stdout.splitlines())
            violations.append(f"secret pattern /{pattern}/ matched tracked file(s):{hits}")
        elif result.returncode != 1:
            violations.append(f"secret pattern /{pattern}/: git grep failed — tree not scanned")
    return violations


def entity_homes(repo: Path, invariants: dict[str, Any]) -> list[str]:
    """Every running guest and service is mapped or a declared exception (the entity audit)."""
    try:
        report = entities.audit(repo)
    except entities.EntityError as error:
        return [f"entity audit unavailable: {error}"]
    if not report["holes"]:
        return []
    return ["running entities with no home — map each (a firewall/DNS host fact, or a "
            "compose/<svc>/ dir) or declare it in invariants.json entity_conventions.exceptions:"
            + "".join(f"\n        running-unmapped {hole}" for hole in report["holes"])]


def _acl_files(repo: Path) -> list[Path]:
    return sorted((repo / "inventory").glob("proxmox-*-acl.json"))


def operate_token(repo: Path, invariants: dict[str, Any]) -> list[str]:
    """The operate token holds no bright-line privilege; node-root allocation only where declared."""
    scope = invariants["operate_token_scope"]
    forbidden = list(scope["forbidden_privileges"])
    vms_root_nodes = {entry["node"] for entry in scope["vms_root_nodes"]}
    violations = []
    for path in _acl_files(repo):
        snapshot = _json(path)
        permissions = snapshot.get("permissions") if isinstance(snapshot, dict) else None
        if not isinstance(permissions, dict) or not all(
                isinstance(privileges, dict) for privileges in permissions.values()):
            violations.append(f"{path.name}: unreadable or malformed permissions — cannot verify "
                              "the operate token")
            continue
        node = str(snapshot.get("node") or "?")
        hits = sorted({f"{acl_path}={privilege}" for acl_path, privileges in permissions.items()
                       for privilege in forbidden if privileges.get(privilege) == 1})
        violations += [f"{node}: operate token holds bright-line privilege {hit} — never standing "
                       "(constitution §2/§6); revoke via pveum" for hit in hits]
        roots = [acl_path for acl_path, privileges in permissions.items()
                 if acl_path in ("/", "/vms") and privileges.get("VM.Allocate") == 1]
        if roots and node not in vms_root_nodes:
            violations.append(f"{node}: operate token has node-root VM.Allocate ({','.join(roots)}) "
                              f"but {node} is not a declared vms_root_node — a /vms grant off the "
                              "declared node is a docs/system-design.md PR, not a silent pveum")
    return violations


def _operate_token_passed(repo: Path, invariants: dict[str, Any]) -> str:
    if not _acl_files(repo):
        return ("no proxmox-*-acl.json in inventory yet — acl audit idle "
                "(run skynet collect proxmox-acl <core|network>)")
    nodes = " ".join(entry["node"] for entry in invariants["operate_token_scope"]["vms_root_nodes"])
    return f"operate token: no bright-line privilege anywhere; /vms-root only on declared node(s) [{nodes}]"


def _block(text: str, block: str) -> str:
    """An engine's block: from `  <block> = {` through its first two-space `  };` line."""
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if line.startswith(f"  {block} = {{"):
            for end in range(start, len(lines)):
                if lines[end].startswith("  };"):
                    return "\n".join(lines[start:end + 1])
            return "\n".join(lines[start:])
    return ""


def engines(repo: Path, invariants: dict[str, Any]) -> list[str]:
    """Every construction engine refuses or human-gates PR merge and root grants."""
    construction = invariants["construction"]
    home_config = construction["home_config"]
    try:
        text = (repo / home_config).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return [f"{home_config} is missing — Home Manager must own every engine's permission rules"]
    violations = []
    for engine in construction["engines"]:
        body = _block(text, engine["block"])
        if not body:
            violations.append(f"{engine['engine']}: {engine['block']} not found in {home_config}")
            continue
        violations += [f"{engine['engine']}: {engine['block']} lacks {needle} — agents never merge "
                       "PRs or grant themselves root"
                       for needle in engine["must_contain"] if needle not in body]
    return violations


INVARIANT_GATES = (
    Gate("excluded guests are never pooled",
         lambda _, inv: "no excluded VMID ({}) appears in any pool".format(
             " ".join(str(g["vmid"]) for g in inv["excluded_guests"]["guests"])),
         excluded_guests),
    Gate("ops-managed pool set matches the declared blast-radius dial",
         lambda _, __: "observed pool set == declared set", pool_set),
    Gate("no plaintext secret patterns in tracked files",
         lambda _, __: "no plaintext secret patterns found in tracked files", secret_patterns),
    Gate("every running entity is mapped or a declared exception",
         lambda _, __: "every running guest & service is mapped or a declared exception",
         entity_homes),
    Gate("operate-token ACL holds the bright lines (no self-leash / node-root; /vms-root only "
         "where declared)", _operate_token_passed, operate_token),
    Gate("every construction engine refuses or human-gates PR merge and root grants",
         lambda _, inv: "engines [{}] leave PR merge and root grants to a human".format(
             ", ".join(e["engine"] for e in inv["construction"]["engines"])),
         engines),
)


def _git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *arguments], cwd=repo, capture_output=True, check=False)


def staged_secrets(repo: Path) -> list[str]:
    """Block plaintext secrets in the staged tree (AGENTS.md §6).

    `*.env.git` (non-secret config) and `*.env.sops` (encrypted) are the sanctioned layers.
    Anything else that looks like a secret — a plaintext `.env`, a `*.key`/`*.pem`, a PRIVATE KEY
    block, or a long TOKEN/SECRET/PASSWORD assignment — is a violation.
    """
    listing = _git(repo, "diff", "--cached", "--name-only", "--diff-filter=ACM", "-z")
    if listing.returncode != 0:
        return ["git diff --cached failed — staged tree not scanned"]
    staged = [name for name in listing.stdout.decode("utf-8", "surrogateescape").split("\0") if name]
    violations = []
    for name in staged:
        if name.endswith((".env.sops", ".env.git")):
            continue
        if name.endswith((".key", ".pem", "id_ed25519")):
            violations.append(f"{name}: secret-bearing filename must never be committed")
        elif name.endswith(".env"):
            violations.append(f"{name}: plaintext env must never be committed "
                              "(use .env.git + .env.sops)")
    for name in staged:
        if name.endswith((".env.sops", ".env.git", ".pub")):
            continue
        blob = _git(repo, "show", f":{name}")
        if blob.returncode != 0:
            continue
        text = blob.stdout.decode("utf-8", "replace")
        if _KEY_BLOCK.search(text):
            violations.append(f"{name}: contains a PRIVATE KEY block")
        if _ASSIGNMENT.search(text):
            violations.append(f"{name}: looks like a hardcoded secret assignment")
    return violations


def run(repo: Path, stdout: TextIO, stderr: TextIO) -> int:
    """Run the staged secret scan, then every invariant gate; 0 pass, 1 violation, 2 cannot run."""
    repo = repo.resolve()
    failed = False

    def report(title: str, violations: list[str], passed: str) -> None:
        nonlocal failed
        print(f"== {title} ==", file=stdout)
        for violation in violations:
            print(f"  ✗ {violation}", file=stderr)
        if violations:
            failed = True
        else:
            print(f"  ✓ {passed}", file=stdout)

    report("no plaintext secrets in the staged tree", staged_secrets(repo),
           "no plaintext secret staged")
    try:
        invariants = load_invariants(repo)
        for gate in INVARIANT_GATES:
            report(gate.title, gate.run(repo, invariants), gate.passed(repo, invariants))
    except GateError as error:
        print(f"check: {error}", file=stderr)
        return 2
    except (KeyError, TypeError, ValueError):
        print(f"check: {INVARIANTS} is missing a required field", file=stderr)
        return 2
    print(file=stdout)
    if failed:
        print("check: FAILED — a hard law is violated (see ✗ above). This change must not land.\n"
              "If a staged-secret match is certainly a false positive: git commit --no-verify",
              file=stderr)
        return 1
    print("check: OK — all machine-checkable hard laws hold.", file=stdout)
    return 0
