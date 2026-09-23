"""The local hard-law gate passes on current truth and fails when a leash boundary is crossed."""

import json
import subprocess
from pathlib import Path


def _gate(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(repo / "scripts/check-invariants.sh")], cwd=repo,
                          capture_output=True, text=True, check=False)


def test_current_repository_satisfies_invariants(repo_copy: Path) -> None:
    result = _gate(repo_copy)
    assert result.returncode == 0, result.stderr


def test_excluded_guest_in_a_pool_fails(repo_copy: Path) -> None:
    path = repo_copy / "inventory/proxmox-network.json"
    snapshot = json.loads(path.read_text())
    snapshot["pools"][0].setdefault("members", []).append({"vmid": 5001})
    path.write_text(json.dumps(snapshot))
    result = _gate(repo_copy)
    assert result.returncode == 1 and "5001" in result.stderr


def test_agent_merge_block_removed_fails(repo_copy: Path) -> None:
    path = repo_copy / "nix/home/aliammar.nix"
    path.write_text(path.read_text().replace('"Bash(gh pr merge:*)"', ""))
    result = _gate(repo_copy)
    assert result.returncode == 1


def test_plaintext_private_key_fails(repo_copy: Path) -> None:
    leak = repo_copy / "compose/leak.txt"
    leak.write_text("-----BEGIN OPENSSH " + "PRIVATE KEY-----\n")
    subprocess.run(["git", "-C", str(repo_copy), "add", "-A"], check=True)
    assert _gate(repo_copy).returncode == 1
