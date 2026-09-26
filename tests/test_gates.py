"""The hard-law gates pass on current truth and fail, never skip, when a boundary is crossed."""

import io
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from skynet import gates


def _gate(repo: Path) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    code = gates.run(repo, out, err)
    return code, err.getvalue()


def _edit(path: Path, change: Any) -> None:
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))


def _stage(repo: Path, name: str, content: str) -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    subprocess.run(["git", "-C", str(repo), "add", "--", name], check=True)


def _commit(repo: Path) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qm", "base", "--no-verify"], check=True)


@pytest.fixture
def repo(repo_copy: Path) -> Path:
    """The disposable checkout with its baseline committed, so only a test's own file is staged."""
    _commit(repo_copy)
    return repo_copy


def test_current_repository_satisfies_every_gate(repo: Path) -> None:
    code, err = _gate(repo)
    assert code == 0, err


def test_the_cli_runs_the_gates(repo: Path) -> None:
    result = subprocess.run(["python3", "-m", "skynet", "check", "--repo", str(repo)],
                            cwd=repo, env={**os.environ, "PYTHONPATH": str(repo / "src")},
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "all machine-checkable hard laws hold" in result.stdout


def test_missing_invariants_cannot_run(repo: Path) -> None:
    (repo / "invariants.json").unlink()
    code, err = _gate(repo)
    assert code == 2 and "invariants.json" in err


def test_excluded_guest_in_a_pool_fails(repo: Path) -> None:
    _edit(repo / "inventory/proxmox-network.json",
          lambda data: data["pools"][0].setdefault("members", []).append({"vmid": 5001}))
    code, err = _gate(repo)
    assert code == 1 and "excluded guest 5001" in err


def test_unreadable_pool_membership_fails(repo: Path) -> None:
    _edit(repo / "inventory/proxmox-network.json",
          lambda data: data["pools"][0].__setitem__("members", None))
    code, err = _gate(repo)
    assert code == 1 and "members:null" in err


def test_malformed_snapshot_fails(repo: Path) -> None:
    (repo / "inventory/proxmox-network.json").write_text("{not json")
    code, err = _gate(repo)
    assert code == 1 and "malformed" in err


@pytest.mark.parametrize("change", [
    lambda data: data["pools"].append({"poolid": "rogue", "members": []}),
    lambda data: data.__setitem__("pools", []),
])
def test_pool_set_drift_either_way_fails(repo: Path, change: Any) -> None:
    _edit(repo / "inventory/proxmox-core.json", change)
    code, err = _gate(repo)
    assert code == 1 and "pool-set drift" in err


def test_plaintext_private_key_in_a_tracked_file_fails(repo: Path) -> None:
    _stage(repo, "compose/leak.txt", "-----BEGIN OPENSSH " + "PRIVATE KEY-----\n")
    _commit(repo)
    code, err = _gate(repo)
    assert code == 1 and "secret pattern" in err and "compose/leak.txt" in err


def test_allowlisted_sops_file_may_hold_the_pattern(repo: Path) -> None:
    _stage(repo, "compose/x/key.sops.yaml", "-----BEGIN OPENSSH " + "PRIVATE KEY-----\n")
    _commit(repo)
    code, err = _gate(repo)
    assert code == 0, err


def test_unscannable_tree_fails(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real = subprocess.run

    def broken(arguments: list[str], **kwargs: Any) -> Any:
        if arguments[:2] == ["git", "grep"]:
            return subprocess.CompletedProcess(arguments, 128, "", "fatal")
        return real(arguments, **kwargs)

    monkeypatch.setattr(gates.subprocess, "run", broken)
    code, err = _gate(repo)
    assert code == 1 and "not scanned" in err


def test_running_unmapped_guest_fails(repo: Path) -> None:
    _edit(repo / "inventory/proxmox-core.json", lambda data: data["resources"].append(
        {"type": "lxc", "vmid": 777, "name": "lxc-stray", "status": "running", "template": 0}))
    code, err = _gate(repo)
    assert code == 1 and "running-unmapped guest/" in err


def test_forbidden_privilege_fails(repo: Path) -> None:
    _edit(repo / "inventory/proxmox-network-acl.json",
          lambda data: data["permissions"].setdefault("/pool/ops-managed", {})
          .__setitem__("Permissions.Modify", 1))
    code, err = _gate(repo)
    assert code == 1 and "Permissions.Modify" in err


def test_node_root_allocation_off_the_declared_node_fails(repo: Path) -> None:
    _edit(repo / "inventory/proxmox-network-acl.json",
          lambda data: data["permissions"].setdefault("/vms", {}).__setitem__("VM.Allocate", 1))
    code, err = _gate(repo)
    assert code == 1 and "not a declared vms_root_node" in err


def test_malformed_acl_fails(repo: Path) -> None:
    _edit(repo / "inventory/proxmox-core-acl.json", lambda data: data.pop("permissions"))
    code, err = _gate(repo)
    assert code == 1 and "cannot verify the operate token" in err


def test_agent_merge_block_removed_fails(repo: Path) -> None:
    path = repo / "nix/home/aliammar.nix"
    path.write_text(path.read_text().replace('"Bash(gh pr merge:*)"', ""))
    code, err = _gate(repo)
    assert code == 1 and "gh pr merge" in err


def test_missing_engine_block_fails(repo: Path) -> None:
    path = repo / "nix/home/aliammar.nix"
    path.write_text(path.read_text().replace("  programs.codex = {", "  programs.notcodex = {"))
    code, err = _gate(repo)
    assert code == 1 and "programs.codex not found" in err


@pytest.mark.parametrize(("name", "content", "reason"), [
    ("compose/x/.env", "A=1\n", "plaintext env"),
    ("certs/host.pem", "x\n", "secret-bearing filename"),
    ("keys/id_ed25519", "x\n", "secret-bearing filename"),
    ("compose/x/notes.md", "-----BEGIN RSA " + "PRIVATE KEY-----\n", "PRIVATE KEY block"),
    ("compose/x/app.yaml", 'API_TOKEN: "' + "a" * 24 + '"\n', "hardcoded secret assignment"),
])
def test_staged_secret_is_blocked(repo: Path, name: str, content: str, reason: str) -> None:
    _stage(repo, name, content)
    code, err = _gate(repo)
    assert code == 1 and name in err and reason in err


@pytest.mark.parametrize(("name", "content"), [
    ("compose/x/.env.git", 'API_TOKEN="' + "a" * 24 + '"\n'),
    ("compose/x/.env.sops", 'API_TOKEN="ENC[' + "a" * 24 + ']"\n'),
    ("keys/host.pub", "ssh-ed25519 AAAA\n"),
    ("compose/x/app.yaml", "PASSWORD:\n  " + "a" * 24 + "\n"),
])
def test_sanctioned_staged_layers_pass(repo: Path, name: str, content: str) -> None:
    _stage(repo, name, content)
    code, err = _gate(repo)
    assert code == 0, err
