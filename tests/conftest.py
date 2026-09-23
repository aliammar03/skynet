"""Shared fixtures: every test runs offline against a disposable copy of repository truth."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
# Enough of the checkout for the gates, entity audit, and cache; history/planning stay behind.
COPIED = ("invariants.json", "lab.json", "inventory", "compose", "scripts", "src",
          "nix/home/aliammar.nix")


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    """A throwaway git checkout holding the files the local gates read."""
    root = tmp_path / "repo"
    for name in COPIED:
        source, target = REPO / name, root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, target)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return root
